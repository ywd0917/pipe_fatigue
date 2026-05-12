#!/usr/bin/env python3
"""
analyze13_short_pipes.py

1미터 미만 파이프 분석 스크립트
PIPE_LM과 SPLY_LS에서 길이가 1m 미만인 파이프들을 조사하고
길이 분포별 통계를 생성

Usage:
    python src/analysis/analyze13_short_pipes.py [--verbose] [--export-csv]
"""

import argparse
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dataclasses import dataclass

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import get_config
from src.common.korean_font_utils import setup_korean_font

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 분석 상수
LENGTH_THRESHOLD = 1.0  # 1미터 미만
BIN_SIZE = 0.1  # 0.1미터 구간
EXTREME_SHORT_THRESHOLD = 0.05  # 극단적으로 짧은 파이프 (5cm 미만)


@dataclass
class PipeStats:
    """파이프 통계 정보"""
    pipe_type: str
    total_count: int
    short_count: int
    short_percentage: float
    mean_length: float
    median_length: float
    min_length: float
    max_length: float
    std_length: float
    zero_length_count: int
    extreme_short_count: int


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="1미터 미만 파이프 분석")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/analyze13_short_pipes"),
        help="출력 디렉토리 (기본값: results/analyze13_short_pipes)",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="짧은 파이프 목록을 CSV로 내보내기",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="시각화 생성",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세 출력",
    )
    return parser.parse_args()


def load_pipe_shapefile(pipe_type: str, verbose: bool = True) -> gpd.GeoDataFrame | None:
    """파이프 shapefile 로드 (main13a 기반)
    
    Args:
        pipe_type: "PIPE_LM" 또는 "SPLY_LS"
        verbose: 상세 출력 여부
        
    Returns:
        파이프 GeoDataFrame 또는 None
    """
    config = get_config()
    
    # export 디렉토리 찾기
    export_dirs = list(config.RAW_DATA_DIR.glob("export_shp_*0520*"))
    if not export_dirs:
        if verbose:
            logger.error(f"export 디렉토리를 찾을 수 없습니다: {config.RAW_DATA_DIR}")
        return None
    
    export_dir = export_dirs[0]
    shp_file = export_dir / f"V_WTL_{pipe_type}.shp"
    
    if not shp_file.exists():
        if verbose:
            logger.error(f"Shapefile을 찾을 수 없습니다: {shp_file}")
        return None
    
    try:
        # shapefile 로드
        gdf = gpd.read_file(shp_file, encoding="euc-kr")
        
        # CRS 확인 및 변환
        if gdf.crs is None:
            gdf.set_crs("EPSG:5179", inplace=True)
        elif gdf.crs != "EPSG:5179":
            gdf = gdf.to_crs("EPSG:5179")
        
        # FTR_IDN 컬럼 확인
        if "FTR_IDN" not in gdf.columns:
            if verbose:
                logger.warning("FTR_IDN 컬럼이 없습니다.")
            return None
        
        # 길이 계산
        gdf["pipe_length"] = gdf.geometry.length
        
        if verbose:
            logger.info(f"{pipe_type} shapefile 로드 완료: {len(gdf):,}개 파이프")
            
        return gdf
        
    except Exception as e:
        if verbose:
            logger.error(f"Shapefile 로드 실패: {e}")
        return None


def analyze_short_pipes(gdf: gpd.GeoDataFrame, pipe_type: str, verbose: bool = True) -> tuple[pd.DataFrame, PipeStats]:
    """짧은 파이프 분석
    
    Args:
        gdf: 파이프 GeoDataFrame
        pipe_type: 파이프 타입
        verbose: 상세 출력 여부
        
    Returns:
        (짧은 파이프 DataFrame, 통계 정보)
    """
    total_count = len(gdf)
    
    # 1m 미만 파이프 필터링
    short_pipes = gdf[gdf["pipe_length"] < LENGTH_THRESHOLD].copy()
    short_count = len(short_pipes)
    short_percentage = (short_count / total_count) * 100 if total_count > 0 else 0
    
    if short_count == 0:
        # 짧은 파이프가 없는 경우
        stats = PipeStats(
            pipe_type=pipe_type,
            total_count=total_count,
            short_count=0,
            short_percentage=0,
            mean_length=0,
            median_length=0,
            min_length=0,
            max_length=0,
            std_length=0,
            zero_length_count=0,
            extreme_short_count=0
        )
        return pd.DataFrame(), stats
    
    # 통계 계산
    lengths = short_pipes["pipe_length"]
    mean_length = lengths.mean()
    median_length = lengths.median()
    min_length = lengths.min()
    max_length = lengths.max()
    std_length = lengths.std()
    
    # 특수 케이스 카운트
    zero_length_count = (lengths == 0).sum()
    extreme_short_count = (lengths < EXTREME_SHORT_THRESHOLD).sum()
    
    # 구간별 분포 계산
    bins = np.arange(0, LENGTH_THRESHOLD + BIN_SIZE, BIN_SIZE)
    short_pipes["length_bin"] = pd.cut(short_pipes["pipe_length"], bins=bins, include_lowest=True)
    
    stats = PipeStats(
        pipe_type=pipe_type,
        total_count=total_count,
        short_count=short_count,
        short_percentage=short_percentage,
        mean_length=mean_length,
        median_length=median_length,
        min_length=min_length,
        max_length=max_length,
        std_length=std_length,
        zero_length_count=zero_length_count,
        extreme_short_count=extreme_short_count
    )
    
    if verbose:
        logger.info(f"{pipe_type} 분석 완료:")
        logger.info(f"  - 전체: {total_count:,}개")
        logger.info(f"  - 1m 미만: {short_count:,}개 ({short_percentage:.2f}%)")
        logger.info(f"  - 평균 길이: {mean_length:.3f}m")
        logger.info(f"  - 0 길이: {zero_length_count}개")
        logger.info(f"  - 극단적으로 짧음 (<{EXTREME_SHORT_THRESHOLD}m): {extreme_short_count}개")
    
    return short_pipes, stats


def create_length_distribution_bins(short_pipes: pd.DataFrame) -> pd.DataFrame:
    """길이 구간별 분포 생성
    
    Args:
        short_pipes: 짧은 파이프 DataFrame
        
    Returns:
        구간별 통계 DataFrame
    """
    if len(short_pipes) == 0:
        return pd.DataFrame(columns=["bin_range", "count", "percentage"])
    
    bins = np.arange(0, LENGTH_THRESHOLD + BIN_SIZE, BIN_SIZE)
    bin_counts, _ = np.histogram(short_pipes["pipe_length"], bins=bins)
    
    # 구간 라벨 생성
    bin_labels = []
    for i in range(len(bin_counts)):
        start = bins[i]
        end = bins[i + 1]
        bin_labels.append(f"{start:.1f}-{end:.1f}")
    
    distribution_df = pd.DataFrame({
        "bin_range": bin_labels,
        "count": bin_counts,
        "percentage": (bin_counts / len(short_pipes)) * 100
    })
    
    return distribution_df


def create_visualizations(pipe_lm_short: pd.DataFrame, sply_ls_short: pd.DataFrame, 
                         output_dir: Path) -> None:
    """시각화 생성
    
    Args:
        pipe_lm_short: PIPE_LM 짧은 파이프 DataFrame
        sply_ls_short: SPLY_LS 짧은 파이프 DataFrame
        output_dir: 출력 디렉토리
    """
    setup_korean_font()
    
    # 1. 길이 분포 히스토그램
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    if len(pipe_lm_short) > 0:
        ax1.hist(pipe_lm_short["pipe_length"], bins=np.arange(0, LENGTH_THRESHOLD + BIN_SIZE, BIN_SIZE), 
                alpha=0.7, color='blue', edgecolor='black', linewidth=0.5)
        ax1.set_title(f"PIPE_LM 길이 분포 (n={len(pipe_lm_short)})", fontsize=14)
        ax1.set_xlabel("파이프 길이 (m)", fontsize=12)
        ax1.set_ylabel("개수", fontsize=12)
        ax1.grid(True, alpha=0.3)
    
    if len(sply_ls_short) > 0:
        ax2.hist(sply_ls_short["pipe_length"], bins=np.arange(0, LENGTH_THRESHOLD + BIN_SIZE, BIN_SIZE), 
                alpha=0.7, color='orange', edgecolor='black', linewidth=0.5)
        ax2.set_title(f"SPLY_LS 길이 분포 (n={len(sply_ls_short)})", fontsize=14)
        ax2.set_xlabel("파이프 길이 (m)", fontsize=12)
        ax2.set_ylabel("개수", fontsize=12)
        ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / "length_distribution.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 박스플롯 비교
    if len(pipe_lm_short) > 0 and len(sply_ls_short) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        data_to_plot = [pipe_lm_short["pipe_length"], sply_ls_short["pipe_length"]]
        labels = [f"PIPE_LM (n={len(pipe_lm_short)})", f"SPLY_LS (n={len(sply_ls_short)})"]
        
        bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')
        
        ax.set_title("PIPE_LM vs SPLY_LS 길이 비교 (1m 미만)", fontsize=14)
        ax.set_ylabel("파이프 길이 (m)", fontsize=12)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "comparison_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    # 3. 누적 분포 함수 (CDF)
    if len(pipe_lm_short) > 0 or len(sply_ls_short) > 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if len(pipe_lm_short) > 0:
            sorted_lengths = np.sort(pipe_lm_short["pipe_length"])
            p = np.arange(1, len(sorted_lengths) + 1) / len(sorted_lengths)
            ax.plot(sorted_lengths, p, label=f"PIPE_LM (n={len(pipe_lm_short)})", color='blue', linewidth=2)
        
        if len(sply_ls_short) > 0:
            sorted_lengths = np.sort(sply_ls_short["pipe_length"])
            p = np.arange(1, len(sorted_lengths) + 1) / len(sorted_lengths)
            ax.plot(sorted_lengths, p, label=f"SPLY_LS (n={len(sply_ls_short)})", color='orange', linewidth=2)
        
        ax.set_title("누적 분포 함수 (CDF) - 1m 미만 파이프", fontsize=14)
        ax.set_xlabel("파이프 길이 (m)", fontsize=12)
        ax.set_ylabel("누적 확률", fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "cumulative_distribution.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    logger.info("시각화 생성 완료")


def generate_summary_report(pipe_lm_stats: PipeStats, sply_ls_stats: PipeStats,
                          pipe_lm_distribution: pd.DataFrame, sply_ls_distribution: pd.DataFrame,
                          pipe_lm_short: pd.DataFrame, sply_ls_short: pd.DataFrame,
                          output_dir: Path) -> None:
    """요약 보고서 생성
    
    Args:
        pipe_lm_stats: PIPE_LM 통계
        sply_ls_stats: SPLY_LS 통계
        pipe_lm_distribution: PIPE_LM 길이 분포
        sply_ls_distribution: SPLY_LS 길이 분포
        pipe_lm_short: PIPE_LM 짧은 파이프 데이터
        sply_ls_short: SPLY_LS 짧은 파이프 데이터
        output_dir: 출력 디렉토리
    """
    report_path = output_dir / "short_pipes_summary.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 1미터 미만 파이프 분석 결과\n\n")
        f.write(f"**생성일**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**분석 기준**: 길이 < {LENGTH_THRESHOLD}m\n")
        f.write(f"**극단 기준**: 길이 < {EXTREME_SHORT_THRESHOLD}m\n\n")
        
        # PIPE_LM 통계
        f.write("## 📊 PIPE_LM 통계\n\n")
        f.write(f"- **전체 파이프**: {pipe_lm_stats.total_count:,}개\n")
        f.write(f"- **1m 미만 파이프**: {pipe_lm_stats.short_count:,}개 ({pipe_lm_stats.short_percentage:.2f}%)\n")
        
        if pipe_lm_stats.short_count > 0:
            f.write(f"- **평균 길이**: {pipe_lm_stats.mean_length:.3f}m\n")
            f.write(f"- **중간값**: {pipe_lm_stats.median_length:.3f}m\n")
            f.write(f"- **최소/최대**: {pipe_lm_stats.min_length:.3f}m / {pipe_lm_stats.max_length:.3f}m\n")
            f.write(f"- **표준편차**: {pipe_lm_stats.std_length:.3f}m\n")
            f.write(f"- **0 길이**: {pipe_lm_stats.zero_length_count}개\n")
            f.write(f"- **극단적으로 짧음** (< {EXTREME_SHORT_THRESHOLD}m): {pipe_lm_stats.extreme_short_count}개\n\n")
            
            # 길이 구간별 분포
            if len(pipe_lm_distribution) > 0:
                f.write("### 길이 구간별 분포\n\n")
                f.write("| 구간 (m) | 개수 | 비율 (%) |\n")
                f.write("|----------|------|----------|\n")
                for _, row in pipe_lm_distribution.iterrows():
                    f.write(f"| {row['bin_range']} | {row['count']} | {row['percentage']:.1f} |\n")
                f.write("\n")
            
            # 최단 파이프 Top 10
            if len(pipe_lm_short) > 0:
                top10_shortest = pipe_lm_short.nsmallest(10, "pipe_length")
                f.write("### 최단 파이프 Top 10\n\n")
                f.write("| 순위 | FTR_IDN | 길이 (m) | 비고 |\n")
                f.write("|------|---------|----------|------|\n")
                for i, (_, pipe) in enumerate(top10_shortest.iterrows(), 1):
                    remark = ""
                    if pipe["pipe_length"] == 0:
                        remark = "⚠️ 0 길이"
                    elif pipe["pipe_length"] < EXTREME_SHORT_THRESHOLD:
                        remark = "🔍 극단적으로 짧음"
                    f.write(f"| {i} | {pipe['FTR_IDN']} | {pipe['pipe_length']:.4f} | {remark} |\n")
                f.write("\n")
        
        # SPLY_LS 통계
        f.write("## 📊 SPLY_LS 통계\n\n")
        f.write(f"- **전체 파이프**: {sply_ls_stats.total_count:,}개\n")
        f.write(f"- **1m 미만 파이프**: {sply_ls_stats.short_count:,}개 ({sply_ls_stats.short_percentage:.2f}%)\n")
        
        if sply_ls_stats.short_count > 0:
            f.write(f"- **평균 길이**: {sply_ls_stats.mean_length:.3f}m\n")
            f.write(f"- **중간값**: {sply_ls_stats.median_length:.3f}m\n")
            f.write(f"- **최소/최대**: {sply_ls_stats.min_length:.3f}m / {sply_ls_stats.max_length:.3f}m\n")
            f.write(f"- **표준편차**: {sply_ls_stats.std_length:.3f}m\n")
            f.write(f"- **0 길이**: {sply_ls_stats.zero_length_count}개\n")
            f.write(f"- **극단적으로 짧음** (< {EXTREME_SHORT_THRESHOLD}m): {sply_ls_stats.extreme_short_count}개\n\n")
            
            # 길이 구간별 분포
            if len(sply_ls_distribution) > 0:
                f.write("### 길이 구간별 분포\n\n")
                f.write("| 구간 (m) | 개수 | 비율 (%) |\n")
                f.write("|----------|------|----------|\n")
                for _, row in sply_ls_distribution.iterrows():
                    f.write(f"| {row['bin_range']} | {row['count']} | {row['percentage']:.1f} |\n")
                f.write("\n")
            
            # 최단 파이프 Top 10
            if len(sply_ls_short) > 0:
                top10_shortest = sply_ls_short.nsmallest(10, "pipe_length")
                f.write("### 최단 파이프 Top 10\n\n")
                f.write("| 순위 | FTR_IDN | 길이 (m) | 비고 |\n")
                f.write("|------|---------|----------|------|\n")
                for i, (_, pipe) in enumerate(top10_shortest.iterrows(), 1):
                    remark = ""
                    if pipe["pipe_length"] == 0:
                        remark = "⚠️ 0 길이"
                    elif pipe["pipe_length"] < EXTREME_SHORT_THRESHOLD:
                        remark = "🔍 극단적으로 짧음"
                    f.write(f"| {i} | {pipe['FTR_IDN']} | {pipe['pipe_length']:.4f} | {remark} |\n")
                f.write("\n")
        
        # 비교 분석
        if pipe_lm_stats.short_count > 0 and sply_ls_stats.short_count > 0:
            f.write("## 🔍 비교 분석\n\n")
            f.write(f"- **1m 미만 비율**: PIPE_LM {pipe_lm_stats.short_percentage:.2f}% vs SPLY_LS {sply_ls_stats.short_percentage:.2f}%\n")
            f.write(f"- **평균 길이 차이**: {abs(pipe_lm_stats.mean_length - sply_ls_stats.mean_length):.3f}m\n")
            f.write(f"- **극단적으로 짧은 파이프**: PIPE_LM {pipe_lm_stats.extreme_short_count}개 vs SPLY_LS {sply_ls_stats.extreme_short_count}개\n\n")
        
        # 데이터 품질 검증
        f.write("## ⚠️ 데이터 품질 검증\n\n")
        total_zero_pipes = pipe_lm_stats.zero_length_count + sply_ls_stats.zero_length_count
        total_extreme_pipes = pipe_lm_stats.extreme_short_count + sply_ls_stats.extreme_short_count
        
        if total_zero_pipes > 0:
            f.write(f"- **주의**: 길이가 0인 파이프 {total_zero_pipes}개 발견 → 데이터 검토 필요\n")
        
        if total_extreme_pipes > 0:
            f.write(f"- **검토 권장**: {EXTREME_SHORT_THRESHOLD}m 미만 극단적으로 짧은 파이프 {total_extreme_pipes}개\n")
        
        if total_zero_pipes == 0 and total_extreme_pipes == 0:
            f.write("- ✅ 데이터 품질 양호: 이상 징후 없음\n")
        
        f.write("\n## 📁 생성 파일\n\n")
        f.write("- `short_pipes_summary.md`: 이 요약 보고서\n")
        if pipe_lm_stats.short_count > 0:
            f.write("- `pipe_lm_short_pipes.csv`: PIPE_LM 1m 미만 파이프 상세 목록\n")
        if sply_ls_stats.short_count > 0:
            f.write("- `sply_ls_short_pipes.csv`: SPLY_LS 1m 미만 파이프 상세 목록\n")
        f.write("- `length_distribution.png`: 길이 분포 히스토그램\n")
        f.write("- `comparison_boxplot.png`: PIPE_LM vs SPLY_LS 박스플롯\n")
        f.write("- `cumulative_distribution.png`: 누적 분포 함수\n\n")
        
        f.write("---\n")
        f.write("*본 보고서는 analyze13_short_pipes.py로 생성되었습니다.*\n")
    
    logger.info(f"요약 보고서 생성 완료: {report_path}")


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()
    
    # 한글 폰트 설정
    setup_korean_font()
    
    # 출력 디렉토리 생성
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("1미터 미만 파이프 분석 시작")
    logger.info("=" * 60)
    logger.info(f"출력 디렉토리: {args.output_dir}")
    logger.info(f"길이 임계값: {LENGTH_THRESHOLD}m")
    
    # 1. PIPE_LM 데이터 로드 및 분석
    logger.info("\n1. PIPE_LM 데이터 분석 중...")
    pipe_lm_gdf = load_pipe_shapefile("PIPE_LM", args.verbose)
    if pipe_lm_gdf is not None:
        pipe_lm_short, pipe_lm_stats = analyze_short_pipes(pipe_lm_gdf, "PIPE_LM", args.verbose)
        pipe_lm_distribution = create_length_distribution_bins(pipe_lm_short)
    else:
        logger.error("PIPE_LM 데이터 로드 실패")
        return
    
    # 2. SPLY_LS 데이터 로드 및 분석
    logger.info("\n2. SPLY_LS 데이터 분석 중...")
    sply_ls_gdf = load_pipe_shapefile("SPLY_LS", args.verbose)
    if sply_ls_gdf is not None:
        sply_ls_short, sply_ls_stats = analyze_short_pipes(sply_ls_gdf, "SPLY_LS", args.verbose)
        sply_ls_distribution = create_length_distribution_bins(sply_ls_short)
    else:
        logger.error("SPLY_LS 데이터 로드 실패")
        return
    
    # 3. CSV 내보내기
    if args.export_csv:
        logger.info("\n3. CSV 파일 내보내기...")
        if len(pipe_lm_short) > 0:
            csv_path = args.output_dir / "pipe_lm_short_pipes.csv"
            pipe_lm_short[["FTR_IDN", "pipe_length"]].to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info(f"PIPE_LM CSV 저장: {csv_path}")
        
        if len(sply_ls_short) > 0:
            csv_path = args.output_dir / "sply_ls_short_pipes.csv"
            sply_ls_short[["FTR_IDN", "pipe_length"]].to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info(f"SPLY_LS CSV 저장: {csv_path}")
    
    # 4. 시각화 생성
    if args.visualize:
        logger.info("\n4. 시각화 생성 중...")
        create_visualizations(pipe_lm_short, sply_ls_short, args.output_dir)
    
    # 5. 요약 보고서 생성
    logger.info("\n5. 요약 보고서 생성 중...")
    generate_summary_report(
        pipe_lm_stats, sply_ls_stats,
        pipe_lm_distribution, sply_ls_distribution,
        pipe_lm_short, sply_ls_short,
        args.output_dir
    )
    
    # 최종 요약
    logger.info("\n" + "=" * 60)
    logger.info("분석 완료!")
    logger.info(f"PIPE_LM: {pipe_lm_stats.total_count:,}개 중 {pipe_lm_stats.short_count:,}개 ({pipe_lm_stats.short_percentage:.2f}%)")
    logger.info(f"SPLY_LS: {sply_ls_stats.total_count:,}개 중 {sply_ls_stats.short_count:,}개 ({sply_ls_stats.short_percentage:.2f}%)")
    logger.info(f"📁 결과: {args.output_dir}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()