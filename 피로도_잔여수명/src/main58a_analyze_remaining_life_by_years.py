#!/usr/bin/env python3
"""
main58a_analyze_remaining_life_by_years.py

remaining_life_years 값의 범위별 분포 분석 및 잔여 수명 시각화
main13c의 통합 피로 손상 데이터에서 잔여 수명을 직접 분석

입력:
  - results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv

출력:
  - results/main58a_analyze_remaining_life_by_years/remaining_life_distribution.png
  - results/main58a_analyze_remaining_life_by_years/remaining_life_by_region.png
  - results/main58a_analyze_remaining_life_by_years/risk_analysis_by_years.png
  - results/main58a_analyze_remaining_life_by_years/critical_pipes_by_years.csv
  - results/main58a_analyze_remaining_life_by_years/analysis_report_by_years.md
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
class LifeThresholds:
    """잔여 수명 임계값 정의 (5단계)"""
    # remaining_life_years 기준
    critical: float = 5.0         # 0-5년: 위험
    monitor: float = 10.0         # 5-10년: 감시
    warning: float = 20.0         # 10-20년: 주의
    safe: float = 50.0            # 20-50년: 안전
    # 50년 초과: 매우 안전

    # 색상 정의
    color_critical: str = '#FF0000'      # 빨강 (위험)
    color_monitor: str = '#FF6347'       # 토마토(주황) (감시)
    color_warning: str = '#FFD700'       # 골드(노랑) (주의)
    color_safe: str = '#9ACD32'          # 연두 (안전)
    color_very_safe: str = '#2E8B57'     # 초록 (매우 안전)

class RemainingLifeAnalyzer:
    """잔여 수명 분석 클래스"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thresholds = LifeThresholds()
        self.REGIONS = [243, 461, 470, 480, 490, 520]  # 정수형 zone 값

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

    def analyze_life_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        """remaining_life_years 값의 분포 분석"""
        print("\n2. remaining_life_years 분포 분석")

        distribution_data = []

        for region in self.REGIONS:
            # PIPE_LM 데이터
            pipe_data = df[(df['zone'] == region) & (df['DATA_SRC'] == 'PIPE_LM')]
            if not pipe_data.empty and 'remaining_life_years' in pipe_data.columns:
                pipe_values = pipe_data['remaining_life_years'].dropna()
                if len(pipe_values) > 0:
                    distribution_data.append({
                        'Region': region,
                        'Type': 'PIPE_LM',
                        'Count': len(pipe_values),
                        'Min': pipe_values.min(),
                        'Max': pipe_values.max(),
                        'Mean': pipe_values.mean(),
                        'Median': pipe_values.median(),
                        'Std': pipe_values.std(),
                        'P25': pipe_values.quantile(0.25),
                        'P75': pipe_values.quantile(0.75),
                        'P95': pipe_values.quantile(0.95),
                        'P99': pipe_values.quantile(0.99)
                    })

            # SPLY_LS 데이터
            sply_data = df[(df['zone'] == region) & (df['DATA_SRC'] == 'SPLY_LS')]
            if not sply_data.empty and 'remaining_life_years' in sply_data.columns:
                sply_values = sply_data['remaining_life_years'].dropna()
                if len(sply_values) > 0:
                    distribution_data.append({
                        'Region': region,
                        'Type': 'SPLY_LS',
                        'Count': len(sply_values),
                        'Min': sply_values.min(),
                        'Max': sply_values.max(),
                        'Mean': sply_values.mean(),
                        'Median': sply_values.median(),
                        'Std': sply_values.std(),
                        'P25': sply_values.quantile(0.25),
                        'P75': sply_values.quantile(0.75),
                        'P95': sply_values.quantile(0.95),
                        'P99': sply_values.quantile(0.99)
                    })

        distribution_df = pd.DataFrame(distribution_data)
        print(f"  - 분석 완료: {len(distribution_df)} region-type combinations")

        return distribution_df

    def categorize_risk_by_life(self, df: pd.DataFrame, region: str) -> pd.DataFrame:
        """잔여 수명 기준 위험도 카테고리 분류"""
        # 해당 지역의 데이터만 필터링
        df_region = df[df['zone'] == region].copy()

        if df_region.empty or 'remaining_life_years' not in df_region.columns:
            return pd.DataFrame()

        df_region = df_region.dropna(subset=['remaining_life_years'])

        # 잔여 수명 기반 위험도 분류 (5단계)
        df_region['risk_category'] = pd.cut(
            df_region['remaining_life_years'],
            bins=[-float('inf'), self.thresholds.critical, self.thresholds.monitor,
                  self.thresholds.warning, self.thresholds.safe, float('inf')],
            labels=['위험', '감시', '주의', '안전', '매우 안전']
        )

        df_region['region'] = region
        df_region['remaining_life'] = df_region['remaining_life_years']
        return df_region

    def plot_distribution_charts(self, df: pd.DataFrame):
        """remaining_life_years 분포 차트 생성"""
        print("\n3. 분포 차트 생성")

        # 전체 데이터 수집
        plot_df = df[['zone', 'DATA_SRC', 'remaining_life_years']].copy()
        plot_df.columns = ['Region', 'Type', 'remaining_life']
        plot_df = plot_df.dropna(subset=['remaining_life'])

        # Figure 1: 히스토그램과 박스플롯
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('잔여 수명 (remaining_life_years) 분포 분석', fontsize=16, fontweight='bold')

        # 1-1: 전체 히스토그램
        ax1 = axes[0, 0]
        ax1.hist(plot_df['remaining_life'], bins=50, edgecolor='black', alpha=0.7)
        ax1.set_xlabel('잔여 수명 (년)')
        ax1.set_ylabel('빈도')
        ax1.set_title('전체 잔여 수명 분포')
        ax1.grid(True, alpha=0.3)

        # 위험도 임계값 표시 (5단계)
        ax1.axvline(self.thresholds.critical, color=self.thresholds.color_critical, linestyle='--',
                   label=f'위험 ({self.thresholds.critical}년)')
        ax1.axvline(self.thresholds.critical, color=self.thresholds.color_critical, linestyle='--',
                   label=f'위험 ({self.thresholds.critical}년)')
        ax1.axvline(self.thresholds.monitor, color=self.thresholds.color_monitor, linestyle='--',
                   label=f'감시 ({self.thresholds.monitor}년)')
        ax1.axvline(self.thresholds.warning, color=self.thresholds.color_warning, linestyle='--',
                   label=f'주의 ({self.thresholds.warning}년)')
        ax1.axvline(self.thresholds.safe, color=self.thresholds.color_safe, linestyle='--',
                   label=f'안전 ({self.thresholds.safe}년)')
        ax1.legend(loc='upper right', fontsize=8)

        # 1-2: 지역별 박스플롯
        ax2 = axes[0, 1]
        plot_df.boxplot(column='remaining_life', by='Region', ax=ax2)
        ax2.set_xlabel('지역')
        ax2.set_ylabel('잔여 수명 (년)')
        ax2.set_title('지역별 잔여 수명 분포')
        plt.sca(ax2)
        plt.xticks(rotation=0)

        # 1-3: 타입별 비교
        ax3 = axes[1, 0]
        plot_df.boxplot(column='remaining_life', by='Type', ax=ax3)
        ax3.set_xlabel('파이프 타입')
        ax3.set_ylabel('잔여 수명 (년)')
        ax3.set_title('파이프 타입별 잔여 수명 분포')

        # 1-4: 5단계 위험도별 파이 차트
        ax4 = axes[1, 1]
        ranges = ['위험', '감시', '주의', '안전', '매우 안전']
        counts = [
            (plot_df['remaining_life'] <= self.thresholds.critical).sum(),
            ((plot_df['remaining_life'] > self.thresholds.critical) &
             (plot_df['remaining_life'] <= self.thresholds.monitor)).sum(),
            ((plot_df['remaining_life'] > self.thresholds.monitor) &
             (plot_df['remaining_life'] <= self.thresholds.warning)).sum(),
            ((plot_df['remaining_life'] > self.thresholds.warning) &
             (plot_df['remaining_life'] <= self.thresholds.safe)).sum(),
            (plot_df['remaining_life'] > self.thresholds.safe).sum()
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
            self.thresholds.color_critical,        # 빨강 (위험)
            self.thresholds.color_monitor,         # 토마토(주황) (감시)
            self.thresholds.color_warning,         # 노랑 (주의)
            self.thresholds.color_safe,            # 연두 (안전)
            self.thresholds.color_very_safe        # 초록 (매우 안전)
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

        ax4.set_title('잔여 수명 기준 5단계 위험도 분포')

        plt.tight_layout()
        output_path = self.output_dir / 'remaining_life_distribution.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

        # Figure 2: 상세 분포 (지역-타입별)
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('지역별 잔여 수명 상세 분포', fontsize=16, fontweight='bold')

        for idx, region in enumerate(self.REGIONS):
            ax = axes[idx // 3, idx % 3]

            # 지역별 데이터 수집
            region_data = df[df['zone'] == region]

            if not region_data.empty:
                # 타입별 데이터 분리
                pipe_data = region_data[region_data['DATA_SRC'] == 'PIPE_LM']
                sply_data = region_data[region_data['DATA_SRC'] == 'SPLY_LS']

                # 히스토그램
                if not pipe_data.empty:
                    ax.hist(pipe_data['remaining_life_years'].dropna(), bins=30, alpha=0.5,
                           label='PIPE_LM', color='blue', edgecolor='black')
                if not sply_data.empty:
                    ax.hist(sply_data['remaining_life_years'].dropna(), bins=30, alpha=0.5,
                           label='SPLY_LS', color='orange', edgecolor='black')

                ax.set_xlabel('잔여 수명 (년)')
                ax.set_ylabel('빈도')
                ax.set_title(f'{region} 지역')
                ax.grid(True, alpha=0.3)
                ax.legend()

                # 통계 정보 추가
                all_vals = region_data['remaining_life_years'].dropna()
                if len(all_vals) > 0:
                    ax.text(0.95, 0.95, f'평균: {all_vals.mean():.1f}년\n중앙값: {all_vals.median():.1f}년',
                           transform=ax.transAxes, ha='right', va='top',
                           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        plt.tight_layout()
        output_path = self.output_dir / 'remaining_life_by_region.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

    def plot_risk_analysis(self, df: pd.DataFrame):
        """위험도 분석 차트 생성"""
        print("\n4. 위험도 분석 차트 생성")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('잔여 수명 기준 위험도 분석', fontsize=16, fontweight='bold')

        # 전체 위험도 카테고리 집계
        risk_counts = {'위험': 0, '감시': 0, '주의': 0, '안전': 0, '매우 안전': 0}

        values = df['remaining_life_years'].dropna()
        for v in values:
            if v <= self.thresholds.critical:
                risk_counts['위험'] += 1
            elif v <= self.thresholds.monitor:
                risk_counts['감시'] += 1
            elif v <= self.thresholds.warning:
                risk_counts['주의'] += 1
            elif v <= self.thresholds.safe:
                risk_counts['안전'] += 1
            else:
                risk_counts['매우 안전'] += 1

        # 2-1: 위험도 카테고리별 파이 차트
        ax1 = axes[0, 0]
        colors = [self.thresholds.color_critical, self.thresholds.color_monitor,
                  self.thresholds.color_warning, self.thresholds.color_safe, self.thresholds.color_very_safe]

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
            # 텍스트 겹침 방지를 위한 개선된 autopct 함수
            total = sum(non_zero_values)
            def make_autopct(values):
                def autopct(pct):
                    if pct > 2:  # 2% 이상만 퍼센트 표시
                        return f'{pct:.1f}%'
                    else:
                        return ''
                return autopct

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

        for region in self.REGIONS:
            region_df = df[df['zone'] == region]
            region_counts = {'위험': 0, '감시': 0, '주의': 0, '안전': 0, '매우 안전': 0}

            values = region_df['remaining_life_years'].dropna()
            for v in values:
                if v <= self.thresholds.critical:
                    region_counts['위험'] += 1
                elif v <= self.thresholds.monitor:
                    region_counts['감시'] += 1
                elif v <= self.thresholds.warning:
                    region_counts['주의'] += 1
                elif v <= self.thresholds.safe:
                    region_counts['안전'] += 1
                else:
                    region_counts['매우 안전'] += 1

            region_risk_data.append(region_counts)

        # 스택 바 차트 생성
        region_labels = [str(r) for r in self.REGIONS]  # 정수를 문자열로 변환
        bottom = np.zeros(len(self.REGIONS))
        for category, color in zip(['위험', '감시', '주의', '안전', '매우 안전'], colors):
            values = [d[category] for d in region_risk_data]
            ax2.bar(region_labels, values, bottom=bottom, label=category, color=color)
            bottom += values

        ax2.set_xlabel('지역')
        ax2.set_ylabel('파이프 수')
        ax2.set_title('지역별 위험도 분포')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # 2-3: D_final vs 잔여수명 산점도 (520 지역)
        ax3 = axes[1, 0]

        # 520 지역 데이터만 추출
        zone_520_data = df[df['zone'] == 520]

        if not zone_520_data.empty and 'D_final_org' in zone_520_data.columns:
            valid_data = zone_520_data[['D_final_org', 'remaining_life_years']].dropna()
            if len(valid_data) > 0:
                scatter = ax3.scatter(valid_data['D_final_org'], valid_data['remaining_life_years'],
                                    c=valid_data['remaining_life_years'], cmap='RdYlGn',
                                    alpha=0.6, s=30)
                ax3.set_xlabel('D_final_org')
                ax3.set_ylabel('잔여 수명 (년)')
                ax3.set_title('520 지역: 피로 손상 vs 잔여 수명')
                ax3.set_xscale('log')
                ax3.grid(True, alpha=0.3)
                plt.colorbar(scatter, ax=ax3, label='잔여 수명 (년)')

                # 위험 구역 표시
                ax3.axhline(self.thresholds.critical, color='red', linestyle='--', alpha=0.5)
                ax3.axhline(self.thresholds.critical, color='orange', linestyle='--', alpha=0.5)
                ax3.axhline(self.thresholds.warning, color='yellow', linestyle='--', alpha=0.5)
                ax3.axhline(self.thresholds.safe, color='lightgreen', linestyle='--', alpha=0.5)
        else:
            ax3.text(0.5, 0.5, '데이터 없음', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=12)
            ax3.set_title('520 지역: 피로 손상 vs 잔여 수명')

        # 2-4: 타입별 위험도 비교
        ax4 = axes[1, 1]
        type_risk_data = {'PIPE_LM': {'위험': 0, '감시': 0, '주의': 0, '안전': 0, '매우 안전': 0},
                         'SPLY_LS': {'위험': 0, '감시': 0, '주의': 0, '안전': 0, '매우 안전': 0}}

        for pipe_type in ['PIPE_LM', 'SPLY_LS']:
            type_df = df[df['DATA_SRC'] == pipe_type]
            values = type_df['remaining_life_years'].dropna()

            for v in values:
                if v <= self.thresholds.critical:
                    type_risk_data[pipe_type]['위험'] += 1
                elif v <= self.thresholds.monitor:
                    type_risk_data[pipe_type]['감시'] += 1
                elif v <= self.thresholds.warning:
                    type_risk_data[pipe_type]['주의'] += 1
                elif v <= self.thresholds.safe:
                    type_risk_data[pipe_type]['안전'] += 1
                else:
                    type_risk_data[pipe_type]['매우 안전'] += 1

        x = np.arange(len(['PIPE_LM', 'SPLY_LS']))
        width = 0.15

        for i, (category, color) in enumerate(zip(['위험', '감시', '주의', '안전', '매우 안전'], colors)):
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
        output_path = self.output_dir / 'risk_analysis_by_years.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  - 저장: {output_path}")
        plt.close()

    def save_critical_pipes(self, df: pd.DataFrame):
        """위험 파이프 목록 저장 (잔여수명 5년 이하)"""
        print("\n5. 위험 파이프 목록 생성")

        # 잔여수명 5년 이하 필터링
        critical_mask = df['remaining_life_years'] <= self.thresholds.critical
        critical_df = df[critical_mask].copy()

        if not critical_df.empty:
            # 필요한 컬럼만 선택
            critical_df['Region'] = critical_df['zone']
            critical_df['Type'] = critical_df['DATA_SRC']
            critical_df['remaining_life'] = critical_df['remaining_life_years']

            cols_to_keep = ['FTR_IDN', 'Region', 'Type', 'remaining_life']
            if 'D_final_org' in critical_df.columns:
                cols_to_keep.append('D_final_org')
            if 'PIP_DIP' in critical_df.columns:
                cols_to_keep.append('PIP_DIP')
            if 'IST_YMD' in critical_df.columns:
                cols_to_keep.append('IST_YMD')

            critical_df = critical_df[cols_to_keep]
            critical_df = critical_df.sort_values('remaining_life', ascending=True)

            output_path = self.output_dir / 'critical_pipes_by_years.csv'
            critical_df.to_csv(output_path, index=False)
            print(f"  - 위험 파이프 (5년 이하): {len(critical_df)}개")
            print(f"  - 저장: {output_path}")

            return critical_df
        else:
            print("  - 위험 파이프 (5년 이하) 없음")
            return pd.DataFrame()

    def generate_report(self, distribution_df: pd.DataFrame, critical_df: pd.DataFrame):
        """분석 보고서 생성"""
        print("\n6. 분석 보고서 생성")

        report_path = self.output_dir / 'analysis_report_by_years.md'

        with open(report_path, 'w') as f:
            f.write("# 잔여 수명 기준 분포 및 위험도 분석 보고서\n\n")
            f.write(f"생성일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 1. 요약\n\n")
            f.write("### 위험도 임계값 (잔여 수명 기준)\n")
            f.write(f"- 위험: 0 - {self.thresholds.critical}년\n")
            f.write(f"- 감시: {self.thresholds.critical} - {self.thresholds.monitor}년\n")
            f.write(f"- 주의: {self.thresholds.monitor} - {self.thresholds.warning}년\n")
            f.write(f"- 안전: {self.thresholds.warning} - {self.thresholds.safe}년\n")
            f.write(f"- 매우 안전: > {self.thresholds.safe}년\n\n")

            f.write("## 2. 지역별 통계\n\n")
            f.write("| 지역 | 타입 | 평균(년) | 중앙값(년) | 최소(년) | 최대(년) |\n")
            f.write("|------|------|---------:|-----------:|---------:|---------:|\n")

            for _, row in distribution_df.iterrows():
                f.write(f"| {row['Region']} | {row['Type']} | "
                       f"{row['Mean']:.1f} | {row['Median']:.1f} | "
                       f"{row['Min']:.1f} | {row['Max']:.1f} |\n")

            f.write("\n## 3. 위험 파이프 현황 (5년 이하)\n\n")
            if not critical_df.empty:
                f.write(f"총 {len(critical_df)}개의 위험 파이프 검출\n\n")

                # 지역별 집계
                region_counts = critical_df['Region'].value_counts()
                f.write("### 지역별 분포\n")
                for region, count in region_counts.items():
                    f.write(f"- {region}: {count}개\n")

                f.write("\n### 상위 10개 위험 파이프\n")
                f.write("| 순위 | FTR_IDN | 지역 | 타입 | 잔여수명(년) |\n")
                f.write("|------|---------|------|------|-------------:|\n")

                for idx, row in critical_df.head(10).iterrows():
                    f.write(f"| {idx+1} | {row['FTR_IDN']} | {row['Region']} | "
                           f"{row['Type']} | {row['remaining_life']:.2f} |\n")
            else:
                f.write("잔여수명 5년 이하인 파이프가 없습니다.\n")

            f.write("\n## 4. 권장사항\n\n")
            f.write("1. **위험 파이프 교체**: 잔여수명 5년 이하 파이프\n")
            f.write("2. **긴급 점검**: 잔여수명 5년 이하 파이프\n")
            f.write("3. **정기 모니터링**: 잔여수명 5-10년 파이프\n")
            f.write("4. **예방 정비 계획**: 잔여수명 10-30년 파이프\n")

        print(f"  - 저장: {report_path}")

def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("main58a_analyze_remaining_life_by_years.py - 잔여 수명 기준 분석")
    print("=" * 60)

    try:
        # 분석기 초기화
        output_dir = Path("results/main58a_analyze_remaining_life_by_years")
        analyzer = RemainingLifeAnalyzer(output_dir)

        # 통합 데이터 로드
        df = analyzer.load_data()

        # 분포 분석
        distribution_df = analyzer.analyze_life_distribution(df)

        # 차트 생성
        analyzer.plot_distribution_charts(df)
        analyzer.plot_risk_analysis(df)

        # 위험 파이프 저장
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