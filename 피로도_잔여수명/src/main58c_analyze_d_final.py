#!/usr/bin/env python3
"""
main58c_analyze_d_final.py

D_final 값의 범위별 분포 분석 및 잔여 수명 평가
main13c의 통합 피로 손상 데이터를 사용하여 위험도별 파이프 분류 및 시각화

입력:
  - results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv

출력:
  - results/main58c_analyze_d_final/d_final_distribution.png
  - results/main58c_analyze_d_final/remaining_life_by_risk.png
  - results/main58c_analyze_d_final/risk_category_summary.csv
  - results/main58c_analyze_d_final/critical_pipes.csv
  - results/main58c_analyze_d_final/analysis_report.md
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# 한글 폰트 설정
from common.korean_font_utils import setup_korean_font
setup_korean_font()

@dataclass
class RiskThresholds:
    """위험도 임계값 정의 (5단계) - 사용자 정의 임계값"""
    # D_final 기준 (분포 최적화를 위한 사용자 정의)
    critical: float = 0.200       # 위험
    monitor: float = 0.100        # 감시
    warning: float = 0.060        # 주의
    safe: float = 0.030           # 안전
    very_safe: float = 0.030      # 매우 안전

    # 잔여 수명 기준 (년)
    life_immediate: int = 5       # 5년 미만: 즉시교체
    life_very_critical: int = 10  # 5-10년: 매우위험
    life_critical: int = 30       # 10-30년: 위험
    life_warning: int = 50        # 30-50년: 주의
    life_normal: int = 100        # 50년+: 안전

    # 색상 정의
    color_critical: str = '#FF0000'      # 빨강 (위험)
    color_monitor: str = '#FF6347'       # 토마토(주황) (감시)
    color_warning: str = '#FFD700'       # 골드(노랑) (주의)
    color_safe: str = '#9ACD32'          # 연두 (안전)
    color_very_safe: str = '#2E8B57'     # 초록 (매우 안전)

class RemainingLifeAnalyzer:
    """잔여 수명 및 위험도 분석 클래스"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thresholds = RiskThresholds()

    def load_data(self) -> pd.DataFrame:
        """통합 데이터 파일 로드"""
        print("1. 데이터 파일 로드")

        # main13c 통합 파일 경로
        merged_path = Path("results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv")

        # 파일 존재 확인
        if not merged_path.exists():
            raise FileNotFoundError(f"필요한 파일이 없습니다: {merged_path}")

        # 데이터 로드
        df = pd.read_csv(merged_path)

        # PIPE_LM과 SPLY_LS 분리
        pipe_count = len(df[df['DATA_SRC'] == 'PIPE_LM'])
        sply_count = len(df[df['DATA_SRC'] == 'SPLY_LS'])

        print(f"  - 전체: {len(df):,} records")
        print(f"  - PIPE_LM: {pipe_count:,} records")
        print(f"  - SPLY_LS: {sply_count:,} records")
        print(f"  - 구역별 분포:")
        for zone in sorted(df['zone'].unique()):
            count = len(df[df['zone'] == zone])
            print(f"    • {zone}: {count:,} records")

        return df

    def analyze_d_final_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """D_final 값의 분포 분석"""
        print("\n2. D_final 분포 분석")

        regions = sorted(df['zone'].unique())
        distribution_data = []

        for region in regions:
            for pipe_type in ['PIPE_LM', 'SPLY_LS']:
                # 지역과 타입별로 필터링
                mask = (df['zone'] == region) & (df['DATA_SRC'] == pipe_type)
                region_df = df[mask]

                if len(region_df) > 0 and 'D_final' in df.columns:
                    values = region_df['D_final'].dropna()
                    if len(values) > 0:
                        distribution_data.append({
                            'Region': region,
                            'Type': pipe_type,
                            'Count': len(values),
                            'Min': values.min(),
                            'Max': values.max(),
                            'Mean': values.mean(),
                            'Median': values.median(),
                            'Std': values.std(),
                            'P25': values.quantile(0.25),
                            'P75': values.quantile(0.75),
                            'P95': values.quantile(0.95),
                            'P99': values.quantile(0.99)
                        })

        distribution_df = pd.DataFrame(distribution_data)
        print(f"  - 분석 완료: {len(distribution_df)} region-type combinations")

        return distribution_df

    def categorize_risk(self, df: pd.DataFrame, region: str = None) -> pd.DataFrame:
        """위험도 카테고리 분류 (5단계)"""
        # 특정 지역만 필터링 (옵션)
        if region:
            df_region = df[df['zone'] == region].copy()
        else:
            df_region = df.copy()

        if 'D_final' not in df_region.columns:
            return pd.DataFrame()

        df_region = df_region.dropna(subset=['D_final'])

        # D_final 기반 위험도 분류 (5단계)
        df_region['risk_category'] = pd.cut(
            df_region['D_final'],
            bins=[0, self.thresholds.very_safe, self.thresholds.safe, self.thresholds.warning,
                  self.thresholds.monitor, self.thresholds.critical, float('inf')],
            labels=['매우 안전', '안전', '주의', '감시', '위험', '심각']
        )

        # 잔여 수명 기반 분류 (5단계, 데이터가 있는 경우)
        if 'remaining_life_years' in df_region.columns:
            df_region['life_category'] = pd.cut(
                df_region['remaining_life_years'],
                bins=[0, self.thresholds.life_immediate, self.thresholds.life_very_critical,
                      self.thresholds.life_critical, self.thresholds.life_warning,
                      self.thresholds.life_normal, float('inf')],
                labels=['즉시교체', '매우위험', '위험', '주의', '안전', '우수']
            )

        return df_region

    def plot_distribution_charts(self, df: pd.DataFrame):
        """D_final 분포 차트 생성"""
        print("\n3. 분포 차트 생성")

        # 필요한 컬럼만 선택하여 plot_df 생성
        plot_df = df[['zone', 'DATA_SRC', 'D_final']].copy()
        plot_df = plot_df.rename(columns={'zone': 'Region', 'DATA_SRC': 'Type'})
        plot_df = plot_df.dropna(subset=['D_final'])

        # Figure 1: 히스토그램과 박스플롯
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('D_final 값 분포 분석', fontsize=16, fontweight='bold')

        # 1-1: 전체 히스토그램 (로그 스케일)
        ax1 = axes[0, 0]
        ax1.hist(plot_df['D_final'], bins=50, edgecolor='black', alpha=0.7)
        ax1.set_xlabel('D_final')
        ax1.set_ylabel('빈도')
        ax1.set_title('전체 D_final 분포')
        ax1.set_yscale('log')
        ax1.grid(True, alpha=0.3)

        # 위험도 임계값 표시 (5단계)
        ax1.axvline(self.thresholds.very_safe, color=self.thresholds.color_very_safe, linestyle='--',
                   label=f'매우 안전 (<{self.thresholds.very_safe:.3f})')
        ax1.axvline(self.thresholds.safe, color=self.thresholds.color_safe, linestyle='--',
                   label=f'안전 ({self.thresholds.safe:.3f})')
        ax1.axvline(self.thresholds.warning, color=self.thresholds.color_warning, linestyle='--',
                   label=f'주의 ({self.thresholds.warning:.3f})')
        ax1.axvline(self.thresholds.monitor, color=self.thresholds.color_monitor, linestyle='--',
                   label=f'감시 ({self.thresholds.monitor:.3f})')
        ax1.axvline(self.thresholds.critical, color=self.thresholds.color_critical, linestyle='--',
                   label=f'위험 (>{self.thresholds.critical:.3f})')
        ax1.legend(loc='upper right', fontsize=8)

        # 1-2: 지역별 박스플롯
        ax2 = axes[0, 1]
        plot_df.boxplot(column='D_final', by='Region', ax=ax2)
        ax2.set_xlabel('지역')
        ax2.set_ylabel('D_final')
        ax2.set_title('지역별 D_final 분포')
        ax2.set_yscale('log')
        plt.sca(ax2)
        plt.xticks(rotation=0)

        # 1-3: 타입별 비교
        ax3 = axes[1, 0]
        plot_df.boxplot(column='D_final', by='Type', ax=ax3)
        ax3.set_xlabel('파이프 타입')
        ax3.set_ylabel('D_final')
        ax3.set_title('파이프 타입별 D_final 분포')
        ax3.set_yscale('log')

        # 1-4: 5단계 위험도별 파이 차트
        ax4 = axes[1, 1]
        ranges = ['매우 안전', '안전', '주의', '감시', '위험']
        counts = [
            (plot_df['D_final'] < self.thresholds.very_safe).sum(),  # 매우 안전: < 0.030
            ((plot_df['D_final'] >= self.thresholds.very_safe) & (plot_df['D_final'] < self.thresholds.safe)).sum(),  # 안전: 0.030 ~ 0.030
            ((plot_df['D_final'] >= self.thresholds.safe) & (plot_df['D_final'] < self.thresholds.warning)).sum(),  # 주의: 0.030 ~ 0.060
            ((plot_df['D_final'] >= self.thresholds.warning) & (plot_df['D_final'] < self.thresholds.monitor)).sum(),  # 감시: 0.060 ~ 0.100
            (plot_df['D_final'] >= self.thresholds.critical).sum()  # 위험: >= 0.200
        ]

        # 0이 아닌 값만 표시
        non_zero_ranges = []
        non_zero_counts = []
        legend_labels = []  # 범례용 레이블

        for r, c in zip(ranges, counts):
            if c > 0:
                non_zero_ranges.append(r)
                non_zero_counts.append(c)
                legend_labels.append(f'{r}: {c:,}개')

        # 5단계 색상 설정
        colors_5levels = [
            self.thresholds.color_very_safe,      # 초록 - 매우 안전
            self.thresholds.color_safe,           # 연두 - 안전
            self.thresholds.color_warning,         # 노랑 - 주의
            self.thresholds.color_monitor,        # 주황 - 감시
            self.thresholds.color_critical        # 빨강 - 위험
        ]
        colors_selected = [colors_5levels[i] for i, c in enumerate(counts) if c > 0]

        # 파이 차트 - 레이블 없이, 퍼센트만 표시
        def autopct_func(pct):
            return f'{pct:.1f}%' if pct > 2 else ''  # 2% 이상만 표시

        wedges, texts, autotexts = ax4.pie(
            non_zero_counts,
            labels=None,  # 레이블 제거
            autopct=autopct_func,
            colors=colors_selected,
            startangle=90,
            pctdistance=0.85,
            textprops={'fontsize': 10, 'weight': 'bold'}
        )

        # 범례 추가
        ax4.legend(wedges, legend_labels,
                  title="위험도 카테고리",
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1),
                  fontsize=9)

        ax4.set_title('5단계 위험도 분포')

        plt.tight_layout()
        output_path = self.output_dir / 'd_final_distribution.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

        # Figure 2: 상세 분포 (지역-타입별)
        regions = sorted(df['zone'].unique())
        n_regions = len(regions)
        n_cols = 3
        n_rows = (n_regions + n_cols - 1) // n_cols  # 올림 나눗셈

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(18, 5*n_rows))
        fig.suptitle('지역별 D_final 상세 분포', fontsize=16, fontweight='bold')

        # 단일 subplot인 경우 axes를 2D 배열로 변환
        if n_rows == 1:
            axes = axes.reshape(1, -1)
        if n_cols == 1:
            axes = axes.reshape(-1, 1)

        for idx, region in enumerate(regions):
            ax = axes[idx // n_cols, idx % n_cols]

            # 지역별 데이터 필터링
            region_df = df[df['zone'] == region]

            if not region_df.empty and 'D_final' in region_df.columns:
                # 타입별 데이터 분리
                pipe_vals = region_df[region_df['DATA_SRC'] == 'PIPE_LM']['D_final'].dropna()
                sply_vals = region_df[region_df['DATA_SRC'] == 'SPLY_LS']['D_final'].dropna()

                # 히스토그램
                if len(pipe_vals) > 0:
                    ax.hist(pipe_vals, bins=30, alpha=0.5, label='PIPE_LM', color='blue', edgecolor='black')
                if len(sply_vals) > 0:
                    ax.hist(sply_vals, bins=30, alpha=0.5, label='SPLY_LS', color='orange', edgecolor='black')

                ax.set_xlabel('D_final')
                ax.set_ylabel('빈도')
                ax.set_title(f'{region} 지역')
                ax.set_yscale('log')
                ax.grid(True, alpha=0.3)
                ax.legend()

                # 통계 정보 추가
                all_vals = region_df['D_final'].dropna()
                if len(all_vals) > 0:
                    ax.text(0.95, 0.95, f'평균: {all_vals.mean():.4f}\n중앙값: {all_vals.median():.4f}',
                           transform=ax.transAxes, ha='right', va='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 빈 subplot 제거
        for idx in range(len(regions), n_rows * n_cols):
            axes[idx // n_cols, idx % n_cols].axis('off')

        plt.tight_layout()
        output_path = self.output_dir / 'd_final_distribution_by_region.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

    def plot_risk_analysis(self, df: pd.DataFrame):
        """위험도 분석 차트 생성"""
        print("\n4. 위험도 분석 차트 생성")

        regions = sorted(df['zone'].unique())  # 데이터에 있는 모든 지역

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('위험도 카테고리별 분석', fontsize=16, fontweight='bold')

        # 전체 위험도 카테고리 집계
        risk_counts = {'매우 안전': 0, '안전': 0, '주의': 0, '감시': 0, '위험': 0}

        if 'D_final' in df.columns:
            values = df['D_final'].dropna()

            for v in values:
                if v < self.thresholds.very_safe:
                    risk_counts['매우 안전'] += 1
                elif v < self.thresholds.safe:
                    risk_counts['안전'] += 1
                elif v < self.thresholds.warning:
                    risk_counts['주의'] += 1
                elif v < self.thresholds.monitor:
                    risk_counts['감시'] += 1
                else:
                    risk_counts['위험'] += 1

        # 2-1: 위험도 카테고리별 파이 차트
        ax1 = axes[0, 0]
        colors = [self.thresholds.color_very_safe, self.thresholds.color_safe,
                  self.thresholds.color_warning, self.thresholds.color_monitor,
                  self.thresholds.color_critical]

        # 텍스트 겹침 방지를 위한 개선된 autopct 함수
        total = sum(risk_counts.values())
        def make_autopct(values):
            def autopct(pct):
                if pct > 2:  # 2% 이상만 퍼센트 표시
                    return f'{pct:.1f}%'
                else:
                    return ''
            return autopct

        # 0이 아닌 값만 표시
        non_zero_labels = []
        non_zero_values = []
        non_zero_colors = []
        legend_labels = []  # 범례용 레이블

        for (label, value), color in zip(risk_counts.items(), colors):
            if value > 0:
                non_zero_labels.append(label)
                non_zero_values.append(value)
                non_zero_colors.append(color)
                legend_labels.append(f'{label}: {value:,}개')

        if non_zero_values:
            wedges, texts, autotexts = ax1.pie(
                non_zero_values,
                labels=None,  # 레이블 제거
                autopct=make_autopct(non_zero_values),
                colors=non_zero_colors,
                startangle=45,
                pctdistance=0.85,
                textprops={'fontsize': 11, 'weight': 'bold'}
            )

        # 범례 추가
        ax1.legend(wedges, legend_labels,
                  title="위험도 카테고리",
                  loc="center left",
                  bbox_to_anchor=(1, 0, 0.5, 1),
                  fontsize=10)

        ax1.set_title('전체 위험도 분포')

        # 2-2: 지역별 위험도 스택 바
        ax2 = axes[0, 1]
        region_risk_data = []

        for region in regions:
            region_counts = {'매우 안전': 0, '안전': 0, '주의': 0, '감시': 0, '위험': 0}

            region_df = df[df['zone'] == region]
            if 'D_final' in region_df.columns:
                values = region_df['D_final'].dropna()
                for v in values:
                    if v < self.thresholds.very_safe:
                        region_counts['매우 안전'] += 1
                    elif v < self.thresholds.safe:
                        region_counts['안전'] += 1
                    elif v < self.thresholds.warning:
                        region_counts['주의'] += 1
                    elif v < self.thresholds.monitor:
                        region_counts['감시'] += 1
                    else:
                        region_counts['위험'] += 1

            region_risk_data.append(region_counts)

        # 스택 바 차트 생성
        bottom = np.zeros(len(regions))
        for category, color in zip(['매우 안전', '안전', '주의', '감시', '위험'], colors):
            values = [d[category] for d in region_risk_data]
            ax2.bar(regions, values, bottom=bottom, label=category, color=color)
            bottom += values

        ax2.set_xlabel('지역')
        ax2.set_ylabel('파이프 수')
        ax2.set_title('지역별 위험도 분포')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # 2-3: D_final vs 잔여수명 산점도 (전체 데이터)
        ax3 = axes[1, 0]

        # D_final과 remaining_life가 있는 경우
        if 'D_final' in df.columns and 'remaining_life_years' in df.columns:
            valid_data = df[['D_final', 'remaining_life_years']].dropna()
            if len(valid_data) > 0:
                scatter = ax3.scatter(valid_data['D_final'], valid_data['remaining_life_years'],
                                    c=valid_data['D_final'], cmap='RdYlGn_r',
                                    alpha=0.6, s=30)
                ax3.set_xlabel('D_final')
                ax3.set_ylabel('잔여 수명 (년)')
                ax3.set_title('피로 손상 vs 잔여 수명')
                ax3.set_xscale('log')
                ax3.grid(True, alpha=0.3)
                plt.colorbar(scatter, ax=ax3, label='D_final')

                # 위험 구역 표시
                ax3.axvline(self.thresholds.critical, color='red', linestyle='--', alpha=0.5)
                ax3.axhline(self.thresholds.life_critical, color='red', linestyle='--', alpha=0.5)
        else:
            ax3.text(0.5, 0.5, '잔여 수명 데이터 없음', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=12)
            ax3.set_title('피로 손상 vs 잔여 수명')

        # 2-4: 타입별 위험도 비교
        ax4 = axes[1, 1]
        type_risk_data = {'PIPE_LM': {'매우 안전': 0, '안전': 0, '주의': 0, '감시': 0, '위험': 0},
                         'SPLY_LS': {'매우 안전': 0, '안전': 0, '주의': 0, '감시': 0, '위험': 0}}

        for pipe_type in ['PIPE_LM', 'SPLY_LS']:
            type_df = df[df['DATA_SRC'] == pipe_type]
            if 'D_final' in type_df.columns:
                values = type_df['D_final'].dropna()
                for v in values:
                    if v < self.thresholds.very_safe:
                        type_risk_data[pipe_type]['매우 안전'] += 1
                    elif v < self.thresholds.safe:
                        type_risk_data[pipe_type]['안전'] += 1
                    elif v < self.thresholds.warning:
                        type_risk_data[pipe_type]['주의'] += 1
                    elif v < self.thresholds.monitor:
                        type_risk_data[pipe_type]['감시'] += 1
                    else:
                        type_risk_data[pipe_type]['위험'] += 1

        x = np.arange(len(['PIPE_LM', 'SPLY_LS']))
        width = 0.15

        for i, (category, color) in enumerate(zip(['매우 안전', '안전', '주의', '감시', '위험'], colors)):
            values = [type_risk_data['PIPE_LM'][category], type_risk_data['SPLY_LS'][category]]
            ax4.bar(x + i * width - 2 * width, values, width, label=category, color=color)

        ax4.set_xlabel('파이프 타입')
        ax4.set_ylabel('파이프 수')
        ax4.set_title('파이프 타입별 위험도 분포')
        ax4.set_xticks(x)
        ax4.set_xticklabels(['PIPE_LM', 'SPLY_LS'])
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = self.output_dir / 'risk_analysis.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

    def save_critical_pipes(self, df: pd.DataFrame):
        """위험 파이프 목록 저장"""
        print("\n5. 위험 파이프 목록 생성")

        if 'D_final' not in df.columns:
            print("  - D_final 컬럼이 없습니다.")
            return pd.DataFrame()

        # 감시 임계값 이상 파이프 필터링 (감시, 위험)
        critical_mask = df['D_final'] >= self.thresholds.monitor

        if critical_mask.any():
            critical_df = df[critical_mask].copy()

            # 필요한 컬럼만 선택
            cols_to_keep = ['FTR_IDN', 'zone', 'DATA_SRC', 'D_final']

            # 추가 컬럼이 있으면 포함
            for col in ['STD_DIP', 'IST_YMD', 'remaining_life_years']:
                if col in critical_df.columns:
                    cols_to_keep.append(col)

            critical_df = critical_df[cols_to_keep]
            critical_df = critical_df.rename(columns={'zone': 'Region', 'DATA_SRC': 'Type'})
            critical_df = critical_df.sort_values('D_final', ascending=False)

            output_path = self.output_dir / 'critical_pipes.csv'
            critical_df.to_csv(output_path, index=False)
            print(f"  - 감시/위험 파이프: {len(critical_df)}개")
            print(f"  - 저장: {output_path}")

            return critical_df
        else:
            print("  - 감시/위험 파이프 없음")
            return pd.DataFrame()

    def generate_report(self, distribution_df: pd.DataFrame, critical_df: pd.DataFrame):
        """분석 보고서 생성"""
        print("\n6. 분석 보고서 생성")

        report_path = self.output_dir / 'analysis_report.md'

        with open(report_path, 'w') as f:
            f.write("# D_final 분포 및 잔여 수명 분석 보고서\n\n")
            f.write(f"생성일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 1. 요약\n\n")
            f.write("### 위험도 임계값\n")
            f.write(f"- 위험 (Critical): > {self.thresholds.critical:.4f}\n")
            f.write(f"- 감시 (Monitor): {self.thresholds.monitor:.4f} - {self.thresholds.critical:.4f}\n")
            f.write(f"- 주의 (Warning): {self.thresholds.warning:.4f} - {self.thresholds.monitor:.4f}\n")
            f.write(f"- 안전 (Safe): {self.thresholds.safe:.4f} - {self.thresholds.warning:.4f}\n")
            f.write(f"- 매우 안전 (Very Safe): < {self.thresholds.very_safe:.4f}\n\n")

            f.write("## 2. 지역별 통계\n\n")
            f.write("| 지역 | 타입 | 평균 | 중앙값 | 95분위수 | 최대값 |\n")
            f.write("|------|------|-----:|-------:|---------:|-------:|\n")

            for _, row in distribution_df.iterrows():
                f.write(f"| {row['Region']} | {row['Type']} | "
                       f"{row['Mean']:.6f} | {row['Median']:.6f} | "
                       f"{row['P95']:.6f} | {row['Max']:.6f} |\n")

            f.write("\n## 3. 감시/위험 파이프 현황\n\n")
            if not critical_df.empty:
                f.write(f"총 {len(critical_df)}개의 감시/위험 파이프 검출\n\n")

                # 지역별 집계
                region_counts = critical_df['Region'].value_counts()
                f.write("### 지역별 분포\n")
                for region, count in region_counts.items():
                    f.write(f"- {region}: {count}개\n")

                f.write("\n### 상위 10개 감시/위험 파이프\n")
                f.write("| 순위 | FTR_IDN | 지역 | 타입 | D_final |\n")
                f.write("|------|---------|------|------|-----------:|\n")

                for idx, row in critical_df.head(10).iterrows():
                    f.write(f"| {idx+1} | {row['FTR_IDN']} | {row['Region']} | "
                           f"{row['Type']} | {row['D_final']:.6f} |\n")
            else:
                f.write("위험 임계값을 초과하는 파이프가 없습니다.\n")

            f.write("\n## 4. 권장사항\n\n")
            f.write("1. **긴급 점검 필요**: D_final > 0.024인 파이프\n")
            f.write("2. **정기 모니터링**: D_final 0.010-0.024 범위의 파이프\n")
            f.write("3. **예방 정비**: 잔여 수명 10년 미만 파이프 우선 교체\n")
            f.write("4. **지역별 대응**: 감시/위험 파이프가 집중된 지역 집중 관리\n")

        print(f"  - 저장: {report_path}")

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("main58c_analyze_d_final.py - D_final 분포 및 잔여 수명 분석")
    print("=" * 60)

    try:
        # 분석기 초기화
        output_dir = Path("results/main58c_analyze_d_final")
        analyzer = RemainingLifeAnalyzer(output_dir)

        # 통합 데이터 로드
        df = analyzer.load_data()

        # 분포 분석
        distribution_df = analyzer.analyze_d_final_distribution(df)

        # 차트 생성
        analyzer.plot_distribution_charts(df)
        analyzer.plot_risk_analysis(df)

        # 감시/위험 파이프 저장
        critical_df = analyzer.save_critical_pipes(df)

        # 보고서 생성
        analyzer.generate_report(distribution_df, critical_df)

        print("\n" + "=" * 60)
        print("✅ 분석이 성공적으로 완료되었습니다!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n❌ 오류: {e}")
        print("필요한 파일을 생성하려면 main13c_zone_fatigue_merge를 먼저 실행하세요.")
        return 1
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())