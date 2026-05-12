#!/usr/bin/env python3
"""
main58b_analyze_overlap.py

D_final과 잔여수명 기준 위험 파이프 중복 분석 및 시각화
main56 피로 데이터를 직접 로드하여 위험 파이프 분류 및 중복 분석

입력:
  - results/main56_calc_fatigure/fatigue_pipe_lm.csv
  - results/main56_calc_fatigure/fatigue_sply_ls.csv
  - raw_data/{region}/PIPE_LM_JOINT.shp (shapefile, 선택사항)
  - raw_data/{region}/SPLY_LS_JOINT.shp (shapefile, 선택사항)

출력:
  - results/main58b_analyze_overlap/overlap_visualization.png
  - results/main58b_analyze_overlap/scatter_plot.png
  - results/main58b_analyze_overlap/bar_chart.png
  - results/main58b_analyze_overlap/geographic_map.png
  - results/main58b_analyze_overlap/overlap_pipes.csv
  - results/main58b_analyze_overlap/analysis_report.md
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import warnings
import geopandas as gpd
from shapely.geometry import LineString, Point
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch, Polygon as MplPolygon
import logging

warnings.filterwarnings('ignore')

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 한글 폰트 설정
from common.korean_font_utils import setup_korean_font
setup_korean_font()

# shapefile 로더 import
from src.common.shapefile_loader import ShapefileLoader
from src.common.config import RAW_DATA_DIR

# 색상 설정
PIPE_COLORS = {
    "main58_only": "#0000FF",     # 파란색 (D_final ≥ 0.13만)
    "main58a_only": "#FF0000",    # 빨간색 (5년 이하만)
    "overlap": "#800080"           # 보라색 (양쪽 모두)
}

# 라인 스타일
LINE_STYLES = {
    "PIPE_LM": {"width": 1.5, "style": "-"},
    "SPLY_LS": {"width": 0.5, "style": "-"}
}

@dataclass
class OverlapThresholds:
    """중복 분석 임계값 정의"""
    d_final_threshold: float = 0.15     # D_final_org 임계값 (상위 35개의 최소값)
    life_threshold: float = 5.0         # remaining_life 임계값 (하위 35개의 최대값)

    # 카테고리 이름
    main58_label: str = "D_final 상위 35개"
    main58a_label: str = "잔여수명 하위 35개"
    overlap_label: str = "중복"


class OverlapAnalyzer:
    """D_final과 잔여수명 기준 중복 분석 클래스"""

    def __init__(self, output_dir: Path, thresholds: Optional[OverlapThresholds] = None):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thresholds = thresholds or OverlapThresholds()

    def load_and_process_fatigue_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """main13c 통합 피로 데이터를 로드하고 위험 파이프 필터링"""
        logger.info("피로 데이터 로드 및 처리 중...")

        # main13c 통합 데이터 로드
        merged_path = Path("results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv")

        if not merged_path.exists():
            raise FileNotFoundError(f"main13c 통합 피로 데이터 파일을 찾을 수 없습니다: {merged_path}")

        # 통합 데이터 로드
        df = pd.read_csv(merged_path)
        logger.info(f"  - 통합 데이터 로드: {len(df):,}개")

        # DATA_SRC별 개수 확인
        pipe_count = len(df[df['DATA_SRC'] == 'PIPE_LM'])
        sply_count = len(df[df['DATA_SRC'] == 'SPLY_LS'])
        logger.info(f"  - PIPE_LM: {pipe_count:,}개")
        logger.info(f"  - SPLY_LS: {sply_count:,}개")

        # 필요한 컬럼 매핑
        df['Region'] = df['zone'].apply(lambda x: f'{int(x):04d}')  # zone을 4자리 문자열로 변환
        df['Type'] = df['DATA_SRC']  # DATA_SRC를 Type으로 사용

        # remaining_life_years를 remaining_life로 매핑 (있는 경우)
        if 'remaining_life_years' in df.columns:
            df['remaining_life'] = df['remaining_life_years']

        # D_final_org 값이 있는 데이터만 필터링
        if 'D_final_org' in df.columns:
            valid_df = df[df['D_final_org'].notna()].copy()

            # main58 기준: D_final_org 상위 35개
            main58_df = valid_df.nlargest(35, 'D_final_org').copy()

            # 상위 35개의 최소값을 임계값으로 저장 (시각화용)
            if len(main58_df) > 0:
                self.thresholds.d_final_threshold = main58_df['D_final_org'].min()

            # main58a 기준: remaining_life 하위 35개
            if 'remaining_life' in valid_df.columns:
                valid_life_df = valid_df[valid_df['remaining_life'].notna()]
                main58a_df = valid_life_df.nsmallest(35, 'remaining_life').copy()

                # 하위 35개의 최대값을 임계값으로 저장 (시각화용)
                if len(main58a_df) > 0:
                    self.thresholds.life_threshold = main58a_df['remaining_life'].max()
            else:
                main58a_df = pd.DataFrame()

            logger.info(f"  - D_final_org 상위 35개 (최소값: {self.thresholds.d_final_threshold:.4f})")
            logger.info(f"  - remaining_life 하위 35개 (최대값: {self.thresholds.life_threshold:.2f}년)")

            return main58_df, main58a_df
        else:
            raise ValueError("D_final_org 컬럼이 없습니다.")

        return pd.DataFrame(), pd.DataFrame()

    def load_fatigue_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """main13c 통합 피로 데이터 로드 (전체 파이프 정보)"""
        logger.info("피로 데이터 로드 중...")

        merged_path = Path("results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv")

        pipe_df = pd.DataFrame()
        sply_df = pd.DataFrame()

        if merged_path.exists():
            df = pd.read_csv(merged_path)
            # DATA_SRC별로 분리
            pipe_df = df[df['DATA_SRC'] == 'PIPE_LM'].copy()
            sply_df = df[df['DATA_SRC'] == 'SPLY_LS'].copy()
            logger.info(f"  - PIPE_LM: {len(pipe_df):,}개")
            logger.info(f"  - SPLY_LS: {len(sply_df):,}개")
        else:
            logger.warning(f"  - 통합 파일 없음: {merged_path}")

        return pipe_df, sply_df

    def filter_and_merge_data(self, pipe_df: pd.DataFrame, sply_df: pd.DataFrame) -> pd.DataFrame:
        """D_final 상위 35개와 remaining_life 하위 35개 모두 포함하여 데이터 병합"""
        logger.info("위험 파이프 데이터 병합 중...")

        all_data = []

        # PIPE_LM 처리
        if not pipe_df.empty and 'D_final_org' in pipe_df.columns:
            valid_df = pipe_df[pipe_df['D_final_org'].notna()].copy()
            valid_df['Region'] = valid_df['zone'].apply(lambda x: f'{int(x):04d}') if 'zone' in valid_df.columns else '0520'
            valid_df['Type'] = 'PIPE_LM'
            # remaining_life_years를 remaining_life로 매핑
            if 'remaining_life_years' in valid_df.columns:
                valid_df['remaining_life'] = valid_df['remaining_life_years']
            # 필요한 컬럼만 선택
            cols = ['FTR_IDN', 'Region', 'Type', 'D_final_org']
            if 'remaining_life' in valid_df.columns:
                cols.append('remaining_life')
            all_data.append(valid_df[cols])

        # SPLY_LS 처리
        if not sply_df.empty and 'D_final_org' in sply_df.columns:
            valid_df = sply_df[sply_df['D_final_org'].notna()].copy()
            valid_df['Region'] = valid_df['zone'].apply(lambda x: f'{int(x):04d}') if 'zone' in valid_df.columns else '0520'
            valid_df['Type'] = 'SPLY_LS'
            # remaining_life_years를 remaining_life로 매핑
            if 'remaining_life_years' in valid_df.columns:
                valid_df['remaining_life'] = valid_df['remaining_life_years']
            # 필요한 컬럼만 선택
            cols = ['FTR_IDN', 'Region', 'Type', 'D_final_org']
            if 'remaining_life' in valid_df.columns:
                cols.append('remaining_life')
            all_data.append(valid_df[cols])

        if not all_data:
            return pd.DataFrame()

        merged_df = pd.concat(all_data, ignore_index=True)

        # D_final 상위 35개와 remaining_life 하위 35개 모두 선택
        critical_pipes = []

        # D_final_org 상위 35개
        top_d_final = merged_df.nlargest(35, 'D_final_org').copy()
        critical_pipes.append(top_d_final)
        logger.info(f"  - D_final 상위 35개 (최소값: {top_d_final['D_final_org'].min():.4f})")

        # remaining_life 하위 35개 (있는 경우)
        if 'remaining_life' in merged_df.columns:
            valid_life_df = merged_df[merged_df['remaining_life'].notna()]
            if not valid_life_df.empty:
                bottom_life = valid_life_df.nsmallest(35, 'remaining_life').copy()
                critical_pipes.append(bottom_life)
                logger.info(f"  - remaining_life 하위 35개 (최대값: {bottom_life['remaining_life'].max():.2f}년)")

        # 중복 제거하여 병합
        if critical_pipes:
            combined_df = pd.concat(critical_pipes, ignore_index=True)
            # pipe_id 생성하여 중복 제거
            combined_df['pipe_id'] = combined_df['FTR_IDN'].astype(str) + '_' + combined_df['Region'].astype(str)
            combined_df = combined_df.drop_duplicates(subset=['pipe_id']).drop(columns=['pipe_id'])
            logger.info(f"  - 전체 위험 파이프: {len(combined_df)}개")
            return combined_df

        return pd.DataFrame()

    def calculate_overlap(self, main58_df: pd.DataFrame, main58a_df: pd.DataFrame,
                         all_pipes_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """중복 파이프 계산"""
        logger.info("중복 파이프 계산 중...")

        # main58_df는 이미 상위 35개로 필터링됨
        main58_filtered = main58_df.copy()
        logger.info(f"  - D_final_org 상위 35개")

        # 고유 식별자 생성 (FTR_IDN + Region)
        main58_filtered['pipe_id'] = main58_filtered['FTR_IDN'].astype(str) + '_' + main58_filtered['Region'].astype(str)
        main58a_df['pipe_id'] = main58a_df['FTR_IDN'].astype(str) + '_' + main58a_df['Region'].astype(str)

        # 집합 생성
        main58_set = set(main58_filtered['pipe_id'])
        main58a_set = set(main58a_df['pipe_id'])

        # 교집합, 차집합 계산
        overlap_set = main58_set & main58a_set
        main58_only_set = main58_set - main58a_set
        main58a_only_set = main58a_set - main58_set

        logger.info(f"  - main58만 해당: {len(main58_only_set):,}개")
        logger.info(f"  - main58a만 해당: {len(main58a_only_set):,}개")
        logger.info(f"  - 중복: {len(overlap_set):,}개")

        # 카테고리 할당
        if not all_pipes_df.empty:
            all_pipes_df['pipe_id'] = all_pipes_df['FTR_IDN'].astype(str) + '_' + all_pipes_df['Region'].astype(str)
            all_pipes_df['category'] = 'none'

            all_pipes_df.loc[all_pipes_df['pipe_id'].isin(main58_only_set), 'category'] = 'main58_only'
            all_pipes_df.loc[all_pipes_df['pipe_id'].isin(main58a_only_set), 'category'] = 'main58a_only'
            all_pipes_df.loc[all_pipes_df['pipe_id'].isin(overlap_set), 'category'] = 'overlap'

        return {
            'main58_set': main58_set,
            'main58a_set': main58a_set,
            'overlap_set': overlap_set,
            'main58_only_set': main58_only_set,
            'main58a_only_set': main58a_only_set,
            'all_pipes': all_pipes_df
        }

    def create_venn_diagram(self, overlap_data: Dict) -> None:
        """벤다이어그램 생성"""
        logger.info("벤다이어그램 생성 중...")

        try:
            from matplotlib_venn import venn2, venn2_circles

            fig, ax = plt.subplots(figsize=(10, 8))

            # 벤다이어그램 생성
            venn = venn2(
                [overlap_data['main58_set'], overlap_data['main58a_set']],
                set_labels=[self.thresholds.main58_label, self.thresholds.main58a_label],
                ax=ax
            )

            # 색상 설정
            if venn.get_patch_by_id('10'):  # main58만
                venn.get_patch_by_id('10').set_color(PIPE_COLORS['main58_only'])
                venn.get_patch_by_id('10').set_alpha(0.5)
            if venn.get_patch_by_id('01'):  # main58a만
                venn.get_patch_by_id('01').set_color(PIPE_COLORS['main58a_only'])
                venn.get_patch_by_id('01').set_alpha(0.5)
            if venn.get_patch_by_id('11'):  # 중복
                venn.get_patch_by_id('11').set_color(PIPE_COLORS['overlap'])
                venn.get_patch_by_id('11').set_alpha(0.5)

            # 원 테두리 추가
            venn2_circles([overlap_data['main58_set'], overlap_data['main58a_set']], ax=ax)

            # 제목 및 설명
            ax.set_title('위험 파이프 분류 기준별 중복 분석', fontsize=16, fontweight='bold', pad=20)

            # 범례 추가
            legend_elements = [
                Patch(facecolor=PIPE_COLORS['main58_only'], alpha=0.5,
                      label=f"{self.thresholds.main58_label}만: {len(overlap_data['main58_only_set']):,}개"),
                Patch(facecolor=PIPE_COLORS['main58a_only'], alpha=0.5,
                      label=f"{self.thresholds.main58a_label}만: {len(overlap_data['main58a_only_set']):,}개"),
                Patch(facecolor=PIPE_COLORS['overlap'], alpha=0.5,
                      label=f"중복: {len(overlap_data['overlap_set']):,}개")
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)

            plt.tight_layout()
            output_path = self.output_dir / 'venn_diagram.png'
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"  - 저장: {output_path}")
            plt.close()

        except ImportError:
            logger.warning("matplotlib_venn이 설치되지 않았습니다. 벤다이어그램을 건너뜁니다.")

    def create_scatter_plot(self, all_pipes_df: pd.DataFrame) -> None:
        """D_final vs remaining_life 산점도 생성"""
        logger.info("산점도 생성 중...")

        if all_pipes_df.empty or 'remaining_life' not in all_pipes_df.columns:
            logger.warning("잔여수명 데이터가 없어 산점도를 생성할 수 없습니다.")
            return

        # remaining_life가 있는 데이터만 필터링
        plot_df = all_pipes_df.dropna(subset=['remaining_life']).copy()

        if plot_df.empty:
            logger.warning("유효한 데이터가 없어 산점도를 생성할 수 없습니다.")
            return

        fig, ax = plt.subplots(figsize=(12, 8))

        # 카테고리별 산점도
        for category, color in PIPE_COLORS.items():
            cat_df = plot_df[plot_df['category'] == category]
            if not cat_df.empty:
                ax.scatter(cat_df['D_final_org'], cat_df['remaining_life'],
                          c=color, label=f'{category}: {len(cat_df)}개',
                          alpha=0.6, s=50, edgecolors='black', linewidth=0.5)

        # 임계선 표시
        ax.axvline(x=self.thresholds.d_final_threshold, color='blue', linestyle='--',
                   alpha=0.5, label=f'D_final = {self.thresholds.d_final_threshold}')
        ax.axhline(y=self.thresholds.life_threshold, color='red', linestyle='--',
                   alpha=0.5, label=f'잔여수명 = {self.thresholds.life_threshold}년')

        # 위험 영역 색칠
        ax.axvspan(self.thresholds.d_final_threshold, ax.get_xlim()[1],
                   ymin=0, ymax=self.thresholds.life_threshold/ax.get_ylim()[1],
                   alpha=0.1, color='purple', label='위험 영역')

        ax.set_xlabel('D_final_org', fontsize=12)
        ax.set_ylabel('잔여 수명 (년)', fontsize=12)
        ax.set_title('D_final vs 잔여수명 산점도', fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / 'scatter_plot.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"  - 저장: {output_path}")
        plt.close()

    def create_bar_chart(self, all_pipes_df: pd.DataFrame) -> None:
        """지역별 카테고리 분포 막대 그래프"""
        logger.info("막대 그래프 생성 중...")

        if all_pipes_df.empty:
            logger.warning("데이터가 없어 막대 그래프를 생성할 수 없습니다.")
            return

        # 지역별 카테고리 집계
        regions = ['0243', '0461', '0470', '0480', '0490', '0520']
        category_counts = {region: {'main58_only': 0, 'main58a_only': 0, 'overlap': 0} for region in regions}

        for _, row in all_pipes_df.iterrows():
            if row['Region'] in regions and row['category'] in PIPE_COLORS:
                category_counts[row['Region']][row['category']] += 1

        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(regions))
        width = 0.25

        # 카테고리별 막대 그래프
        for i, (category, color) in enumerate(PIPE_COLORS.items()):
            values = [category_counts[region][category] for region in regions]
            offset = (i - 1) * width
            bars = ax.bar(x + offset, values, width, label=category, color=color, alpha=0.8)

            # 값 표시
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                           f'{int(height)}', ha='center', va='bottom', fontsize=8)

        ax.set_xlabel('지역', fontsize=12)
        ax.set_ylabel('파이프 수', fontsize=12)
        ax.set_title('지역별 위험 파이프 카테고리 분포', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(regions)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_path = self.output_dir / 'bar_chart.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"  - 저장: {output_path}")
        plt.close()

    def create_integrated_visualization(self, overlap_data: Dict, all_pipes_df: pd.DataFrame) -> None:
        """통합 시각화 (4개 차트)"""
        logger.info("통합 시각화 생성 중...")

        fig = plt.figure(figsize=(16, 12))

        # 1. 벤다이어그램 (matplotlib_venn이 없으면 파이 차트로 대체)
        ax1 = plt.subplot(2, 2, 1)
        try:
            from matplotlib_venn import venn2
            venn2([overlap_data['main58_set'], overlap_data['main58a_set']],
                  set_labels=[self.thresholds.main58_label, self.thresholds.main58a_label],
                  ax=ax1)
            ax1.set_title('중복 관계', fontsize=12, fontweight='bold')
        except ImportError:
            # 파이 차트로 대체
            sizes = [len(overlap_data['main58_only_set']),
                    len(overlap_data['main58a_only_set']),
                    len(overlap_data['overlap_set'])]
            labels = ['main58만', 'main58a만', '중복']
            colors = [PIPE_COLORS['main58_only'], PIPE_COLORS['main58a_only'], PIPE_COLORS['overlap']]

            if sum(sizes) > 0:
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                                    autopct='%1.1f%%', startangle=90)
                ax1.set_title('카테고리별 분포', fontsize=12, fontweight='bold')

        # 2. 산점도
        if not all_pipes_df.empty and 'remaining_life' in all_pipes_df.columns:
            ax2 = plt.subplot(2, 2, 2)
            plot_df = all_pipes_df.dropna(subset=['remaining_life'])

            for category, color in PIPE_COLORS.items():
                cat_df = plot_df[plot_df['category'] == category]
                if not cat_df.empty:
                    ax2.scatter(cat_df['D_final_org'], cat_df['remaining_life'],
                              c=color, label=category, alpha=0.6, s=30)

            ax2.axvline(x=self.thresholds.d_final_threshold, color='blue', linestyle='--', alpha=0.5)
            ax2.axhline(y=self.thresholds.life_threshold, color='red', linestyle='--', alpha=0.5)
            ax2.set_xlabel('D_final_org', fontsize=10)
            ax2.set_ylabel('잔여 수명 (년)', fontsize=10)
            ax2.set_title('D_final vs 잔여수명', fontsize=12, fontweight='bold')
            ax2.set_xscale('log')
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper right', fontsize=8)

        # 3. 지역별 막대 그래프
        ax3 = plt.subplot(2, 2, 3)
        if not all_pipes_df.empty:
            regions = ['0243', '0461', '0470', '0480', '0490', '0520']
            category_counts = {region: {'main58_only': 0, 'main58a_only': 0, 'overlap': 0} for region in regions}

            for _, row in all_pipes_df.iterrows():
                if row['Region'] in regions and row['category'] in PIPE_COLORS:
                    category_counts[row['Region']][row['category']] += 1

            # 스택 바 차트
            bottom = np.zeros(len(regions))
            for category, color in PIPE_COLORS.items():
                values = [category_counts[region][category] for region in regions]
                ax3.bar(regions, values, bottom=bottom, label=category, color=color, alpha=0.8)
                bottom += values

            ax3.set_xlabel('지역', fontsize=10)
            ax3.set_ylabel('파이프 수', fontsize=10)
            ax3.set_title('지역별 분포', fontsize=12, fontweight='bold')
            ax3.legend(loc='upper right', fontsize=8)
            ax3.grid(True, alpha=0.3, axis='y')

        # 4. 요약 통계
        ax4 = plt.subplot(2, 2, 4)
        ax4.axis('off')

        stats_text = "=== 중복 분석 결과 ===\n\n"
        stats_text += f"D_final 상위 35개:\n"
        stats_text += f"  총 {len(overlap_data['main58_set']):,}개\n"
        stats_text += f"  (최소값: {self.thresholds.d_final_threshold:.4f})\n\n"
        stats_text += f"잔여수명 하위 35개:\n"
        stats_text += f"  총 {len(overlap_data['main58a_set']):,}개\n"
        stats_text += f"  (최대값: {self.thresholds.life_threshold:.2f}년)\n\n"
        stats_text += f"카테고리별 분포:\n"
        stats_text += f"  • main58만: {len(overlap_data['main58_only_set']):,}개\n"
        stats_text += f"  • main58a만: {len(overlap_data['main58a_only_set']):,}개\n"
        stats_text += f"  • 중복: {len(overlap_data['overlap_set']):,}개\n\n"

        if len(overlap_data['overlap_set']) > 0:
            overlap_ratio = len(overlap_data['overlap_set']) / min(len(overlap_data['main58_set']),
                                                                   len(overlap_data['main58a_set'])) * 100
            stats_text += f"중복률: {overlap_ratio:.1f}%"

        ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes,
                fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax4.set_title('요약 통계', fontsize=12, fontweight='bold')

        plt.suptitle('위험 파이프 중복 분석 (main58 vs main58a)', fontsize=16, fontweight='bold')
        plt.tight_layout()

        output_path = self.output_dir / 'overlap_visualization.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"  - 저장: {output_path}")
        plt.close()

    def save_overlap_pipes(self, overlap_data: Dict) -> None:
        """중복 파이프 목록 저장"""
        logger.info("중복 파이프 목록 저장 중...")

        all_pipes_df = overlap_data.get('all_pipes', pd.DataFrame())

        if all_pipes_df.empty:
            logger.warning("저장할 데이터가 없습니다.")
            return

        # 카테고리가 있는 파이프만 필터링
        result_df = all_pipes_df[all_pipes_df['category'].isin(PIPE_COLORS.keys())].copy()

        if not result_df.empty:
            # 정렬: 카테고리, D_final_org 내림차순
            result_df = result_df.sort_values(['category', 'D_final_org'], ascending=[True, False])

            output_path = self.output_dir / 'overlap_pipes.csv'
            result_df.to_csv(output_path, index=False)
            logger.info(f"  - 저장: {output_path} ({len(result_df)}개)")

    def generate_report(self, overlap_data: Dict) -> None:
        """분석 보고서 생성"""
        logger.info("분석 보고서 생성 중...")

        report_path = self.output_dir / 'analysis_report.md'

        with open(report_path, 'w') as f:
            f.write("# 위험 파이프 중복 분석 보고서\n\n")
            f.write(f"생성일시: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 1. 분석 기준\n\n")
            f.write(f"- **main58 기준**: D_final_org 상위 35개 (최소값: {self.thresholds.d_final_threshold:.4f})\n")
            f.write(f"- **main58a 기준**: remaining_life_years 하위 35개 (최대값: {self.thresholds.life_threshold:.2f}년)\n\n")

            f.write("## 2. 분석 결과\n\n")
            f.write("### 전체 요약\n")
            f.write(f"- main58 기준 고위험 파이프: {len(overlap_data['main58_set']):,}개 (상위 35개)\n")
            f.write(f"- main58a 기준 즉시교체 파이프: {len(overlap_data['main58a_set']):,}개 (하위 35개)\n")
            f.write(f"- **중복 파이프: {len(overlap_data['overlap_set']):,}개**\n\n")

            f.write("### 카테고리별 분포\n")
            f.write(f"- main58만 해당: {len(overlap_data['main58_only_set']):,}개\n")
            f.write(f"- main58a만 해당: {len(overlap_data['main58a_only_set']):,}개\n")
            f.write(f"- 양쪽 모두 해당: {len(overlap_data['overlap_set']):,}개\n\n")

            # 중복률 계산
            if min(len(overlap_data['main58_set']), len(overlap_data['main58a_set'])) > 0:
                overlap_ratio = len(overlap_data['overlap_set']) / min(len(overlap_data['main58_set']),
                                                                       len(overlap_data['main58a_set'])) * 100
                f.write(f"### 중복률\n")
                f.write(f"- 중복률: {overlap_ratio:.1f}%\n")
                f.write(f"  (중복 파이프 수 / min(main58, main58a) × 100)\n\n")

            # 지역별 분석
            all_pipes_df = overlap_data.get('all_pipes', pd.DataFrame())
            if not all_pipes_df.empty:
                f.write("## 3. 지역별 분석\n\n")
                f.write("| 지역 | main58만 | main58a만 | 중복 | 합계 |\n")
                f.write("|------|----------|-----------|------|------|\n")

                regions = ['0243', '0461', '0470', '0480', '0490', '0520']
                for region in regions:
                    region_df = all_pipes_df[all_pipes_df['Region'] == region]
                    main58_only = len(region_df[region_df['category'] == 'main58_only'])
                    main58a_only = len(region_df[region_df['category'] == 'main58a_only'])
                    overlap = len(region_df[region_df['category'] == 'overlap'])
                    total = main58_only + main58a_only + overlap

                    f.write(f"| {region} | {main58_only} | {main58a_only} | {overlap} | {total} |\n")

            f.write("\n## 4. 권장사항\n\n")
            f.write("1. **최우선 조치 필요**: 중복 파이프 (D_final 높고 잔여수명 짧음)\n")
            f.write("2. **단기 관찰 필요**: main58a만 해당 (잔여수명 5년 이하)\n")
            f.write("3. **중기 모니터링**: main58만 해당 (D_final 0.13 이상)\n")
            f.write("4. **지역별 대응**: 중복 파이프가 많은 지역 집중 관리\n")

        logger.info(f"  - 저장: {report_path}")

    def load_pipe_and_zone_geometries(self, regions: Optional[List[str]] = None) -> Tuple[Optional[gpd.GeoDataFrame], Optional[gpd.GeoDataFrame]]:
        """모든 지역의 파이프와 구역 경계 shapefile에서 geometry 데이터 로드"""
        if regions is None:
            regions = ['0243', '0461', '0470', '0480', '0490', '0520']

        logger.info(f"파이프 및 구역 geometry 데이터 로드 중 (지역: {', '.join(regions)})...")

        try:
            loader = ShapefileLoader(RAW_DATA_DIR, verbose=False)
            all_pipe_gdfs = []
            all_zone_gdfs = []

            for region_code in regions:
                logger.info(f"  지역 {region_code} 로드 중...")

                # PIPE_LM 로드
                pipe_lm = loader.load_pipe_shapefile(region_code, "PIPE_LM")
                if pipe_lm is not None:
                    pipe_lm['PIPE_TYPE'] = 'PIPE_LM'
                    pipe_lm['REGION'] = region_code
                    all_pipe_gdfs.append(pipe_lm)
                    logger.info(f"    - PIPE_LM: {len(pipe_lm):,}개")

                # SPLY_LS 로드
                sply_ls = loader.load_pipe_shapefile(region_code, "SPLY_LS")
                if sply_ls is not None:
                    sply_ls['PIPE_TYPE'] = 'SPLY_LS'
                    sply_ls['REGION'] = region_code
                    all_pipe_gdfs.append(sply_ls)
                    logger.info(f"    - SPLY_LS: {len(sply_ls):,}개")

                # 소블록(SMLZ) 경계 로드
                export_dir = loader.find_export_directory(region_code)
                if export_dir:
                    smlz_path = export_dir / "WEA_SMLZ_AS.shp"
                    if smlz_path.exists():
                        zone_gdf = gpd.read_file(smlz_path, encoding="utf-8")
                        zone_gdf['REGION'] = region_code
                        all_zone_gdfs.append(zone_gdf)
                        logger.info(f"    - 소블록: {len(zone_gdf):,}개")

            # 파이프 데이터 병합
            pipe_gdf = None
            if all_pipe_gdfs:
                pipe_gdf = pd.concat(all_pipe_gdfs, ignore_index=True)
                pipe_gdf = gpd.GeoDataFrame(pipe_gdf, crs=all_pipe_gdfs[0].crs)
                logger.info(f"  - 전체 파이프: {len(pipe_gdf):,}개 ({len(regions)}개 지역)")

            # 구역 데이터 병합
            zone_gdf = None
            if all_zone_gdfs:
                zone_gdf = pd.concat(all_zone_gdfs, ignore_index=True)
                zone_gdf = gpd.GeoDataFrame(zone_gdf, crs=all_zone_gdfs[0].crs)
                logger.info(f"  - 전체 구역: {len(zone_gdf):,}개 ({len(regions)}개 지역)")

            return pipe_gdf, zone_gdf

        except Exception as e:
            logger.error(f"Shapefile 로드 실패: {e}")
            return None, None

    def create_geographic_map(self, overlap_data: Dict, pipe_gdf: Optional[gpd.GeoDataFrame],
                             zone_gdf: Optional[gpd.GeoDataFrame] = None) -> None:
        """파이프 geometry를 사용한 지리적 위치 맵 생성 (카테고리별 색상)"""
        logger.info("지리적 위치 맵 생성 중...")

        if pipe_gdf is None or pipe_gdf.empty:
            logger.warning("파이프 geometry 데이터가 없어 지도를 생성할 수 없습니다.")
            return

        # 카테고리별 파이프 데이터 준비
        all_pipes_df = overlap_data.get('all_pipes', pd.DataFrame())
        categorized_pipes = {}  # {(FTR_IDN, Region): category}

        if not all_pipes_df.empty:
            # 카테고리가 있는 파이프만 필터링
            categorized_df = all_pipes_df[all_pipes_df['category'].isin(PIPE_COLORS.keys())]

            for _, row in categorized_df.iterrows():
                key = (row['FTR_IDN'], row['Region'])
                categorized_pipes[key] = row['category']

            logger.info(f"  - 분류된 파이프: {len(categorized_pipes)}개")

            # 카테고리별 개수
            category_counts = {'main58_only': 0, 'main58a_only': 0, 'overlap': 0}
            for category in categorized_pipes.values():
                category_counts[category] += 1

            logger.info(f"  - main58_only: {category_counts['main58_only']}개")
            logger.info(f"  - main58a_only: {category_counts['main58a_only']}개")
            logger.info(f"  - overlap: {category_counts['overlap']}개")

        # 시각화
        fig, ax = plt.subplots(figsize=(16, 12))

        # 1. 구역 경계 그리기 (가장 아래 레이어)
        if zone_gdf is not None and not zone_gdf.empty:
            logger.info(f"  - 구역 경계 표시: {len(zone_gdf)}개")

            for _, zone in zone_gdf.iterrows():
                if zone.geometry and zone.geometry.geom_type in ['Polygon', 'MultiPolygon']:
                    # 구역 경계 그리기 (밝은 회색 배경)
                    try:
                        # Shapely geometry를 matplotlib polygon으로 변환
                        if zone.geometry.geom_type == 'Polygon':
                            coords = list(zone.geometry.exterior.coords)
                            patch = MplPolygon(coords,
                                             facecolor='#F5F5F5',  # 밝은 회색
                                             edgecolor='#999999',  # 중간 회색 경계
                                             linewidth=0.5,
                                             alpha=0.3,
                                             zorder=1)  # 가장 아래
                            ax.add_patch(patch)
                        elif zone.geometry.geom_type == 'MultiPolygon':
                            # MultiPolygon의 경우 각 polygon을 개별로 처리
                            for poly in zone.geometry.geoms:
                                coords = list(poly.exterior.coords)
                                patch = MplPolygon(coords,
                                                 facecolor='#F5F5F5',
                                                 edgecolor='#999999',
                                                 linewidth=0.5,
                                                 alpha=0.3,
                                                 zorder=1)
                                ax.add_patch(patch)

                        # 구역 라벨 추가
                        centroid = zone.geometry.centroid
                        # SMZ_LBL 또는 SMZ_NUM 필드 사용
                        label = zone.get('SMZ_LBL', zone.get('SMZ_NUM', ''))
                        if label:
                            ax.text(centroid.x, centroid.y,
                                  str(label),
                                  fontsize=6,
                                  ha='center',
                                  va='center',
                                  color='#666666',
                                  alpha=0.6,
                                  zorder=2)
                    except Exception as e:
                        logger.debug(f"구역 그리기 실패: {e}")

        # 2. 전체 파이프 (회색, 얇게)
        for _, pipe in pipe_gdf.iterrows():
            if pipe.geometry and pipe.geometry.geom_type == 'LineString':
                coords = list(pipe.geometry.coords)
                if coords:
                    line = LineCollection([coords], colors='#CCCCCC', linewidths=0.2, alpha=0.3, zorder=5)
                    ax.add_collection(line)

        # 3. 카테고리별 파이프 강조 표시
        category_counts = {'main58_only': 0, 'main58a_only': 0, 'overlap': 0}  # 초기화
        if categorized_pipes:
            pipes_found = 0
            pipes_not_found = 0
            short_pipes = []

            # 카테고리별 개수 계산 (다시 계산)
            for category in categorized_pipes.values():
                if category in category_counts:
                    category_counts[category] += 1

            # 각 파이프별로 그리기
            for (ftr_idn, region), category in categorized_pipes.items():
                # 해당 FTR_IDN과 지역의 파이프 찾기
                mask = (pipe_gdf['FTR_IDN'] == ftr_idn) & (pipe_gdf['REGION'] == region)
                pipe_geom = pipe_gdf[mask]

                # 파이프가 해당 지역에 없으면 0520 지역에서 찾기 (데이터는 0520에만 있음)
                if pipe_geom.empty and region != '0520':
                    mask_520 = (pipe_gdf['FTR_IDN'] == ftr_idn) & (pipe_gdf['REGION'] == '0520')
                    pipe_geom = pipe_gdf[mask_520]
                    if not pipe_geom.empty:
                        logger.debug(f"  - FTR_IDN {ftr_idn}: 지역 {region} 대신 0520에서 geometry 사용")

                if not pipe_geom.empty:
                    pipes_found += 1
                else:
                    pipes_not_found += 1
                    logger.warning(f"  - FTR_IDN {ftr_idn} (지역 {region})의 geometry를 찾을 수 없음")
                    continue

                for _, pipe in pipe_geom.iterrows():
                    if pipe.geometry and pipe.geometry.geom_type == 'LineString':
                        coords = list(pipe.geometry.coords)
                        if coords:
                            # 파이프 길이 확인
                            pipe_length = pipe.geometry.length

                            # 카테고리별 색상 설정
                            color = PIPE_COLORS[category]
                            linewidth = 2.0  # 기본 선 두께

                            # overlap인 경우 더 두껍게
                            if category == 'overlap':
                                linewidth = 3.0

                            # 파이프 타입별 스타일 조정
                            if pipe.get('PIPE_TYPE') == 'SPLY_LS':
                                linewidth *= 0.8  # SPLY_LS는 약간 얇게

                            line = LineCollection([coords], colors=[color], linewidths=linewidth,
                                                alpha=0.9, zorder=10)
                            ax.add_collection(line)

                            # 짧은 파이프(<10m)에 대해 추가 마커 표시
                            if pipe_length < 10:
                                short_pipes.append((ftr_idn, region, pipe_length))
                                # 파이프 중점에 마커 추가
                                midpoint = pipe.geometry.interpolate(0.5, normalized=True)
                                ax.plot(midpoint.x, midpoint.y, 'o',
                                       color=color, markersize=10, markeredgecolor='black',
                                       markeredgewidth=1, zorder=15)
                                # 라벨 추가
                                ax.text(midpoint.x, midpoint.y + 20,
                                       f'{ftr_idn}\n({pipe_length:.1f}m)',
                                       fontsize=7, ha='center', va='bottom',
                                       bbox=dict(boxstyle='round,pad=0.3',
                                                facecolor='white', alpha=0.7))

        # 범례 생성
        legend_elements = []

        # 카테고리별 범례
        legend_elements.append(
            plt.Line2D([0], [0], color=PIPE_COLORS['overlap'], linewidth=3,
                      label=f'중복 (양쪽 모두): {category_counts.get("overlap", 0)}개')
        )
        legend_elements.append(
            plt.Line2D([0], [0], color=PIPE_COLORS['main58_only'], linewidth=2,
                      label=f'D_final 상위 35개만: {category_counts.get("main58_only", 0)}개')
        )
        legend_elements.append(
            plt.Line2D([0], [0], color=PIPE_COLORS['main58a_only'], linewidth=2,
                      label=f'잔여수명 하위 35개만: {category_counts.get("main58a_only", 0)}개')
        )
        legend_elements.append(
            plt.Line2D([0], [0], color='#CCCCCC', linewidth=1,
                      label='일반 파이프')
        )

        # 통계 정보 텍스트 박스
        if categorized_pipes:
            stats_text = "=== 위험 파이프 분류 통계 ===\n"
            stats_text += f"총 파이프: {len(categorized_pipes)}개\n\n"

            stats_text += "카테고리별 분포:\n"
            stats_text += f"  • D_final 상위 35개만: {category_counts.get('main58_only', 0)}개\n"
            stats_text += f"  • 잔여수명 하위 35개만: {category_counts.get('main58a_only', 0)}개\n"
            stats_text += f"  • 중복 (양쪽 모두): {category_counts.get('overlap', 0)}개\n"

            stats_text += f"\n가시성 상태:\n"
            stats_text += f"  표시됨: {pipes_found}개\n"
            stats_text += f"  누락됨: {pipes_not_found}개\n"
            if short_pipes:
                stats_text += f"  짧은 파이프(<10m): {len(short_pipes)}개\n"

            # 지역별 카운트
            region_counts = {}
            for (ftr_idn, region), category in categorized_pipes.items():
                if region not in region_counts:
                    region_counts[region] = {'main58_only': 0, 'main58a_only': 0, 'overlap': 0}
                region_counts[region][category] += 1

            stats_text += "\n지역별 분포:\n"
            for region in sorted(region_counts.keys()):
                counts = region_counts[region]
                total = sum(counts.values())
                stats_text += f"  {region}: {total}개 "
                if counts['overlap'] > 0:
                    stats_text += f"(중복:{counts['overlap']})"
                stats_text += "\n"

            # 텍스트 박스 추가
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=8,
                   verticalalignment='top', bbox=props)

        # 범례 추가
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9,
                 title=f'카테고리별 분류 (총 {len(categorized_pipes)}개)',
                 title_fontsize=10)

        # 축 설정
        ax.set_aspect('equal')
        ax.set_title('위험 파이프 카테고리별 지리적 분포', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('X 좌표', fontsize=10)
        ax.set_ylabel('Y 좌표', fontsize=10)
        ax.grid(True, alpha=0.3)

        # 여백 설정
        if pipe_gdf is not None and not pipe_gdf.empty:
            minx, miny, maxx, maxy = pipe_gdf.total_bounds
            margin = 100  # 100m 여백
            ax.set_xlim(minx - margin, maxx + margin)
            ax.set_ylim(miny - margin, maxy + margin)

        plt.tight_layout()

        # 저장
        output_path = self.output_dir / 'geographic_map.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"  - 저장: {output_path}")
        plt.close()


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description="D_final과 잔여수명 기준 위험 파이프 중복 분석"
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.15,
        help='D_final_org 임계값 (기본값: 0.15)'
    )
    parser.add_argument(
        '--life-limit',
        type=float,
        default=5.0,
        help='잔여수명 임계값 (년, 기본값: 5)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('results/main58b_analyze_overlap'),
        help='출력 디렉토리'
    )
    parser.add_argument(
        '--no-venn',
        action='store_true',
        help='벤다이어그램 생성 안 함'
    )
    parser.add_argument(
        '--no-scatter',
        action='store_true',
        help='산점도 생성 안 함'
    )
    parser.add_argument(
        '--no-bar',
        action='store_true',
        help='막대 그래프 생성 안 함'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='0520',
        help='분석할 지역 코드 (기본값: 0520)'
    )

    return parser.parse_args()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("main58b_analyze_overlap.py - 위험 파이프 중복 분석")
    print("=" * 60)

    # 인수 파싱
    args = parse_arguments()

    # 임계값 설정
    thresholds = OverlapThresholds(
        d_final_threshold=args.threshold,
        life_threshold=args.life_limit
    )

    try:
        # 분석기 초기화
        analyzer = OverlapAnalyzer(args.output_dir, thresholds)

        # 1. main56 피로 데이터에서 직접 로드 및 필터링
        main58_df, main58a_df = analyzer.load_and_process_fatigue_data()

        # 2. 전체 피로 데이터 로드 (시각화용)
        pipe_df, sply_df = analyzer.load_fatigue_data()

        # 3. 데이터 필터링 및 병합 (시각화용)
        all_pipes_df = analyzer.filter_and_merge_data(pipe_df, sply_df) if (not pipe_df.empty or not sply_df.empty) else pd.DataFrame()

        # 4. 중복 계산
        overlap_data = analyzer.calculate_overlap(main58_df, main58a_df, all_pipes_df)

        # 5. 시각화
        print("\n시각화 생성 중...")

        # 통합 시각화 (항상 생성)
        analyzer.create_integrated_visualization(overlap_data, all_pipes_df)

        # 개별 시각화 (옵션에 따라)
        if not args.no_venn:
            analyzer.create_venn_diagram(overlap_data)

        if not args.no_scatter:
            analyzer.create_scatter_plot(all_pipes_df)

        if not args.no_bar:
            analyzer.create_bar_chart(all_pipes_df)

        # 6. 지리적 위치 맵 생성 (항상 실행, 모든 지역)
        pipe_gdf, zone_gdf = analyzer.load_pipe_and_zone_geometries()  # 모든 6개 지역의 파이프 및 구역 로드
        analyzer.create_geographic_map(overlap_data, pipe_gdf, zone_gdf)

        # 7. 결과 저장
        analyzer.save_overlap_pipes(overlap_data)
        analyzer.generate_report(overlap_data)

        print("\n" + "=" * 60)
        print("✅ 분석이 성공적으로 완료되었습니다!")
        print(f"결과 저장 위치: {args.output_dir}")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n❌ 오류: {e}")
        print("필요한 파일이 없습니다. main58과 main58a를 먼저 실행하세요.")
        return 1
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())