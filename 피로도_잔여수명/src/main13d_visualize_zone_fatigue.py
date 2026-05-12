#!/usr/bin/env python3
"""
main13d_visualize_zone_fatigue.py

main13c_zone_fatigue_merge.py에서 생성한 CSV 파일을 시각화하는 스크립트
구역별로 파이프를 다른 색상으로 표시하고, 파이프 종류별로 다른 두께 적용
"""

import argparse
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from shapely.geometry import box

from common.config import RESULTS_DIR, SUBREGION_MAPPING, get_config
from common.korean_font_utils import setup_korean_font

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 파이프 종류별 선 두께 설정
PIPE_LM_LINE_WIDTH = 1  # PIPE_LM 선 두께
SPLY_LS_LINE_WIDTH = 0.3  # SPLY_LS 선 두께


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="구역별 피로 손상 데이터 시각화 (main13c 결과)"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=RESULTS_DIR / "main13c_zone_fatigue_merge",
        help="main13c 출력 디렉토리 경로",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_DIR / "main13d_visualize_zone_fatigue",
        help="출력 디렉토리 경로",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="이미지 크기 배율 (기본값: 1.0, 16x12 inch)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="디버그 모드 활성화"
    )
    return parser.parse_args()


def load_zone_boundaries() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """구역 경계 데이터 로드"""
    config = get_config()
    
    # Export 디렉토리 찾기 (가장 최신 것 사용)
    export_dirs = sorted(config.RAW_DATA_DIR.glob("export_shp_*"))
    if not export_dirs:
        raise FileNotFoundError("Export 디렉토리를 찾을 수 없습니다.")
    
    # 0520 지역 디렉토리 찾기
    export_0520 = None
    for export_dir in export_dirs:
        if "(0520)" in export_dir.name:
            export_0520 = export_dir
            break
    
    if export_0520 is None:
        # 0520 디렉토리가 없으면 가장 최신 것 사용
        export_0520 = export_dirs[-1]
    
    latest_export_dir = export_0520
    logger.info(f"Export 디렉토리 사용: {latest_export_dir}")
    
    # MDLZ (중간 구역) 경계 로드 - 0520 지역
    mdlz_path = latest_export_dir / "WEA_MDLZ_AS.shp"
    if not mdlz_path.exists():
        raise FileNotFoundError(f"MDLZ 파일을 찾을 수 없습니다: {mdlz_path}")
    
    mdlz_gdf = gpd.read_file(mdlz_path, encoding="utf-8")
    # WEA_MDLZ_AS는 모두 0520 지역이므로 전체 사용
    mdlz_0520 = mdlz_gdf.copy()
    
    if mdlz_0520.empty:
        raise ValueError("0520 지역을 찾을 수 없습니다.")
    
    # SMLZ (소규모 구역) 경계 로드 - 0470, 0480, 0490
    smlz_path = latest_export_dir / "WEA_SMLZ_AS.shp"
    if not smlz_path.exists():
        raise FileNotFoundError(f"SMLZ 파일을 찾을 수 없습니다: {smlz_path}")
    
    smlz_gdf = gpd.read_file(smlz_path, encoding="utf-8")
    subregions = ["0243", "0461", "0470", "0480", "0490"]
    # WEA_SMLZ_AS에서 SMZ_NUM 필드 사용
    smlz_subregions = smlz_gdf[smlz_gdf["SMZ_NUM"].isin(subregions)].copy()
    
    logger.info(f"0520 지역 로드 완료")
    logger.info(f"하위 구역 로드: {len(smlz_subregions)}개")
    
    return mdlz_0520, smlz_subregions


def load_pipe_data(input_dir: Path) -> tuple[gpd.GeoDataFrame | None, gpd.GeoDataFrame | None]:
    """main13c에서 생성한 파이프 데이터와 원본 Shapefile의 geometry를 결합"""
    config = get_config()
    
    # main13c 출력 CSV 파일 로드
    combined_path = input_dir / "zone_fatigue_merged.csv"
    
    pipe_lm_gdf = None
    sply_ls_gdf = None
    
    if not combined_path.exists():
        logger.warning(f"통합 파이프 데이터를 찾을 수 없습니다: {combined_path}")
        return pipe_lm_gdf, sply_ls_gdf
    
    try:
        # 통합 CSV 파일 로드 (zone을 문자열로 읽어서 "0490" 형태 유지)
        combined_df = pd.read_csv(combined_path, encoding="utf-8-sig", dtype={'zone': str})
        
        if combined_df.empty:
            logger.warning("통합 파이프 데이터가 비어있습니다.")
            return pipe_lm_gdf, sply_ls_gdf
        
        # Export 디렉토리 찾기 (0520)
        export_dirs = sorted(config.RAW_DATA_DIR.glob("export_shp_*"))
        export_0520 = None
        for export_dir in export_dirs:
            if "(0520)" in export_dir.name:
                export_0520 = export_dir
                break
        
        if export_0520 is None and export_dirs:
            export_0520 = export_dirs[-1]
        
        if export_0520 is None:
            logger.error("Export 디렉토리를 찾을 수 없습니다.")
            return pipe_lm_gdf, sply_ls_gdf
        
        # DATA_SRC로 분리하고 원본 Shapefile과 조인
        if "DATA_SRC" in combined_df.columns:
            # PIPE_LM 처리
            pipe_lm_df = combined_df[combined_df["DATA_SRC"] == "PIPE_LM"].copy()
            if not pipe_lm_df.empty:
                # 원본 Shapefile 로드
                pipe_lm_shp_path = export_0520 / "V_WTL_PIPE_LM.shp"
                if pipe_lm_shp_path.exists():
                    pipe_lm_shp = gpd.read_file(pipe_lm_shp_path, encoding="utf-8")
                    # FTR_IDN을 기준으로 조인
                    pipe_lm_df["FTR_IDN"] = pipe_lm_df["FTR_IDN"].astype(float)
                    pipe_lm_shp["FTR_IDN"] = pipe_lm_shp["FTR_IDN"].astype(float)
                    
                    # CSV 데이터와 Shapefile geometry 조인
                    pipe_lm_merged = pipe_lm_df.merge(
                        pipe_lm_shp[["FTR_IDN", "geometry"]], 
                        on="FTR_IDN", 
                        how="left"
                    )
                    
                    # GeoDataFrame 생성
                    pipe_lm_with_geom = pipe_lm_merged[pipe_lm_merged["geometry"].notna()]
                    if not pipe_lm_with_geom.empty:
                        pipe_lm_gdf = gpd.GeoDataFrame(pipe_lm_with_geom, crs="EPSG:5179")
                        logger.info(f"PIPE_LM 데이터 로드: {len(pipe_lm_gdf)}개 파이프 (원본 {len(pipe_lm_df)}개 중)")
            
            # SPLY_LS 처리
            sply_ls_df = combined_df[combined_df["DATA_SRC"] == "SPLY_LS"].copy()
            if not sply_ls_df.empty:
                # 원본 Shapefile 로드
                sply_ls_shp_path = export_0520 / "V_WTL_SPLY_LS.shp"
                if sply_ls_shp_path.exists():
                    sply_ls_shp = gpd.read_file(sply_ls_shp_path, encoding="utf-8")
                    # FTR_IDN을 기준으로 조인
                    sply_ls_df["FTR_IDN"] = sply_ls_df["FTR_IDN"].astype(float)
                    sply_ls_shp["FTR_IDN"] = sply_ls_shp["FTR_IDN"].astype(float)
                    
                    # CSV 데이터와 Shapefile geometry 조인
                    sply_ls_merged = sply_ls_df.merge(
                        sply_ls_shp[["FTR_IDN", "geometry"]], 
                        on="FTR_IDN", 
                        how="left"
                    )
                    
                    # GeoDataFrame 생성
                    sply_ls_with_geom = sply_ls_merged[sply_ls_merged["geometry"].notna()]
                    if not sply_ls_with_geom.empty:
                        sply_ls_gdf = gpd.GeoDataFrame(sply_ls_with_geom, crs="EPSG:5179")
                        logger.info(f"SPLY_LS 데이터 로드: {len(sply_ls_gdf)}개 파이프 (원본 {len(sply_ls_df)}개 중)")
        else:
            logger.warning("DATA_SRC 컬럼이 없습니다. 파이프 종류를 구분할 수 없습니다.")
            
    except Exception as e:
        logger.error(f"파이프 데이터 로드 실패: {e}")
    
    return pipe_lm_gdf, sply_ls_gdf


def create_visualization(
    mdlz_0520: gpd.GeoDataFrame,
    smlz_subregions: gpd.GeoDataFrame,
    pipe_lm_gdf: gpd.GeoDataFrame | None,
    sply_ls_gdf: gpd.GeoDataFrame | None,
    output_path: Path,
    scale: float = 1.0,
) -> None:
    """구역별 피로 손상 데이터 시각화"""
    
    # 한글 폰트 설정
    setup_korean_font()
    
    # Figure 크기 설정 (docs/visualization_rules.md 참고)
    base_width, base_height = 16, 12
    fig_width = base_width * scale
    fig_height = base_height * scale
    
    fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height), dpi=300)
    
    # 구역별 색상 정의
    zone_colors = {
        "0243": "#FF9999",  # 연한 빨간색
        "0461": "#99CCFF",  # 연한 파란색
        "0470": "#FF6B6B",  # 빨간색 계열
        "0480": "#4ECDC4",  # 청록색 계열
        "0490": "#45B7D1",  # 파란색 계열
        "0520": "#95E77E",  # 연두색 계열
    }
    
    # 1. 배경: 0520 전체 지역 표시
    mdlz_0520.boundary.plot(
        ax=ax, color="black", linewidth=2, label="0520 지역", zorder=1
    )
    mdlz_0520.plot(ax=ax, color="lightgray", alpha=0.2, zorder=0)
    
    # 2. 하위 구역 경계 표시
    for idx, row in smlz_subregions.iterrows():
        zone = row["SMZ_NUM"]
        color = zone_colors.get(zone, "gray")
        
        # 경계선
        ax.plot(*row.geometry.exterior.xy, color=color, linewidth=1.5, 
                linestyle="--", alpha=0.8, zorder=1)
        
        # 영역 채우기 (투명하게)
        ax.fill(*row.geometry.exterior.xy, color=color, alpha=0.1, zorder=0)
        
        # 구역 라벨 표시
        centroid = row.geometry.centroid
        ax.annotate(
            zone,
            xy=(centroid.x, centroid.y),
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=color,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", 
                     edgecolor=color, alpha=0.8),
            zorder=4
        )
    
    # 3. 파이프 시각화
    legend_elements = []
    zone_stats = {}
    
    # PIPE_LM 그리기
    if pipe_lm_gdf is not None and not pipe_lm_gdf.empty:
        for zone in zone_colors.keys():
            zone_pipes = pipe_lm_gdf[pipe_lm_gdf["zone"] == zone]
            if not zone_pipes.empty:
                zone_pipes.plot(
                    ax=ax,
                    color=zone_colors[zone],
                    linewidth=PIPE_LM_LINE_WIDTH,
                    alpha=0.7,
                    zorder=2
                )
                if zone not in zone_stats:
                    zone_stats[zone] = {"pipe_lm": 0, "sply_ls": 0}
                zone_stats[zone]["pipe_lm"] = len(zone_pipes)
    
    # SPLY_LS 그리기
    if sply_ls_gdf is not None and not sply_ls_gdf.empty:
        for zone in zone_colors.keys():
            zone_pipes = sply_ls_gdf[sply_ls_gdf["zone"] == zone]
            if not zone_pipes.empty:
                zone_pipes.plot(
                    ax=ax,
                    color=zone_colors[zone],
                    linewidth=SPLY_LS_LINE_WIDTH,
                    alpha=0.5,
                    linestyle="-",
                    zorder=2
                )
                if zone not in zone_stats:
                    zone_stats[zone] = {"pipe_lm": 0, "sply_ls": 0}
                zone_stats[zone]["sply_ls"] = len(zone_pipes)
    
    # 4. 범례 생성
    # 구역별 색상 범례
    for zone, color in zone_colors.items():
        if zone in zone_stats:
            label = f"{zone} 구역"
            legend_elements.append(Patch(facecolor=color, alpha=0.5, label=label))
    
    # 파이프 종류별 범례
    if pipe_lm_gdf is not None and not pipe_lm_gdf.empty:
        legend_elements.append(
            plt.Line2D([0], [0], color="black", linewidth=PIPE_LM_LINE_WIDTH, 
                      label=f"PIPE_LM (두께 {PIPE_LM_LINE_WIDTH})")
        )
    if sply_ls_gdf is not None and not sply_ls_gdf.empty:
        legend_elements.append(
            plt.Line2D([0], [0], color="black", linewidth=SPLY_LS_LINE_WIDTH, 
                      label=f"SPLY_LS (두께 {SPLY_LS_LINE_WIDTH})")
        )
    
    ax.legend(handles=legend_elements, loc="upper right", fontsize=10)
    
    # 5. 통계 정보 박스
    stats_text = "=== 구역별 파이프 수 ===\n"
    for zone in sorted(zone_stats.keys()):
        stats = zone_stats[zone]
        stats_text += f"{zone}: PIPE_LM={stats['pipe_lm']}, SPLY_LS={stats['sply_ls']}\n"
    
    total_pipe_lm = sum(s["pipe_lm"] for s in zone_stats.values())
    total_sply_ls = sum(s["sply_ls"] for s in zone_stats.values())
    stats_text += f"\n총계: PIPE_LM={total_pipe_lm}, SPLY_LS={total_sply_ls}"
    
    ax.text(
        0.02, 0.98, stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="gray"),
        zorder=5
    )
    
    # 6. 축 설정
    ax.set_xlabel("X 좌표 (m)", fontsize=10)
    ax.set_ylabel("Y 좌표 (m)", fontsize=10)
    ax.set_title("구역별 피로 손상 데이터 시각화", fontsize=14, fontweight="bold", pad=20)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")
    
    # 레이아웃 조정
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    plt.tight_layout()
    
    # 저장
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    logger.info(f"시각화 저장 완료: {output_path}")
    plt.close()


def main() -> None:
    """메인 함수"""
    args = parse_arguments()
    
    # 로깅 레벨 설정
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=== main13d_visualize_zone_fatigue.py 시작 ===")
    logger.info(f"입력 디렉토리: {args.input_dir}")
    logger.info(f"출력 디렉토리: {args.output_dir}")
    logger.info(f"이미지 크기 배율: {args.scale}")
    
    # 출력 디렉토리 생성
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 1. 구역 경계 로드
        logger.info("구역 경계 데이터 로드 중...")
        mdlz_0520, smlz_subregions = load_zone_boundaries()
        
        # 2. 파이프 데이터 로드
        logger.info("파이프 데이터 로드 중...")
        pipe_lm_gdf, sply_ls_gdf = load_pipe_data(args.input_dir)
        
        if pipe_lm_gdf is None and sply_ls_gdf is None:
            logger.warning("파이프 데이터를 찾을 수 없습니다.")
            logger.info("구역 경계만 표시합니다.")
        
        # 3. 시각화 생성
        logger.info("시각화 생성 중...")
        output_path = args.output_dir / "zone_fatigue_map.png"
        create_visualization(
            mdlz_0520,
            smlz_subregions,
            pipe_lm_gdf,
            sply_ls_gdf,
            output_path,
            args.scale
        )
        
        logger.info("=== main13d_visualize_zone_fatigue.py 완료 ===")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()