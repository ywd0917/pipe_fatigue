#!/usr/bin/env python3
"""
main13f_visualize_high_k_repair.py

K_repair_per_m 값이 가장 높은 파이프들을 개별적으로 시각화하는 스크립트
각 파이프와 해당 파이프 30m 내의 누수 지점들을 시각화하여
비정상적으로 높은 K_repair 값이 정상적인지 확인하는 용도

Usage:
    python src/main13f_visualize_high_k_repair.py [--pipe-type PIPE_LM] [--top-n 5]
"""

import argparse
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Circle, Patch
from shapely.geometry import Point
from shapely.strtree import STRtree

from common.config import get_config
from common.korean_font_utils import setup_korean_font

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 시각화 설정 (visualization_rules.md 기준)
PIPE_LINE_WIDTH = 3  # 파이프 강조용 굵은 선
BUFFER_ALPHA = 0.1  # 30m 버퍼 투명도
REPAIR_POINT_SIZE = 50  # 누수 지점 크기
REPAIR_ALPHA = 0.8  # 누수 지점 투명도
CLUSTER_RADIUS = 10  # 클러스터 원 반경 (미터)
CLUSTER_ALPHA = 0.2  # 클러스터 투명도


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="K_repair_per_m 상위 파이프 시각화 (main13a 결과 분석)"
    )
    parser.add_argument(
        "--pipe-type",
        type=str,
        choices=["PIPE_LM", "SPLY_LS"],
        default="PIPE_LM",
        help="파이프 종류 (기본값: PIPE_LM)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="상위 N개 파이프 선택 (기본값: 5)",
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=30.0,
        help="누수 지점 매칭 거리 (미터, 기본값: 30)",
    )
    parser.add_argument(
        "--show-clusters",
        action="store_true",
        help="누수 클러스터 표시 여부",
    )
    parser.add_argument(
        "--cluster-radius",
        type=float,
        default=10.0,
        help="클러스터 반경 (미터, 기본값: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="출력 디렉토리 (기본값: results/main13f_high_k_repair)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="이미지 크기 배율 (기본값: 1.0)",
    )
    parser.add_argument("--debug", action="store_true", help="디버그 모드")

    return parser.parse_args()


def load_k_repair_data(pipe_type: str) -> pd.DataFrame | None:
    """main13a 결과에서 K_repair 데이터 로드

    Args:
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        K_repair 데이터 DataFrame 또는 None
    """
    config = get_config()
    k_repair_dir = config.RESULTS_DIR / "main13a_k_repair"

    if pipe_type == "PIPE_LM":
        csv_file = k_repair_dir / "repair_pipe_lm.csv"
    else:  # SPLY_LS
        csv_file = k_repair_dir / "repair_sply_ls.csv"

    if not csv_file.exists():
        logger.error(f"K_repair 데이터 파일을 찾을 수 없습니다: {csv_file}")
        return None

    try:
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        logger.info(f"{pipe_type} K_repair 데이터 로드 완료: {len(df):,}개 파이프")
        return df
    except Exception as e:
        logger.error(f"K_repair 데이터 로드 실패: {e}")
        return None


def load_pipe_shapefile(pipe_type: str) -> gpd.GeoDataFrame | None:
    """파이프 shapefile 로드

    Args:
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)

    Returns:
        파이프 GeoDataFrame 또는 None
    """
    config = get_config()

    # Export 디렉토리 찾기
    export_dirs = list(config.RAW_DATA_DIR.glob("export_shp_*0520*"))
    if not export_dirs:
        logger.error("0520 export 디렉토리를 찾을 수 없습니다")
        return None

    export_dir = export_dirs[0]
    shp_file = export_dir / f"V_WTL_{pipe_type}.shp"

    if not shp_file.exists():
        logger.error(f"Shapefile을 찾을 수 없습니다: {shp_file}")
        return None

    try:
        gdf = gpd.read_file(shp_file, encoding="euc-kr")

        # CRS 확인 및 변환
        if gdf.crs is None:
            gdf.set_crs("EPSG:5179", inplace=True)
        elif gdf.crs != "EPSG:5179":
            gdf = gdf.to_crs("EPSG:5179")

        logger.info(f"{pipe_type} shapefile 로드 완료: {len(gdf):,}개 파이프")
        return gdf
    except Exception as e:
        logger.error(f"Shapefile 로드 실패: {e}")
        return None


def load_repair_locations() -> gpd.GeoDataFrame | None:
    """누수 위치 데이터 로드

    Returns:
        누수 위치 GeoDataFrame 또는 None
    """
    config = get_config()
    repair_csv = config.UNIFIED_REPAIR_CSV

    if not repair_csv.exists():
        logger.error(f"누수 데이터 파일을 찾을 수 없습니다: {repair_csv}")
        return None

    try:
        df = pd.read_csv(repair_csv, encoding="utf-8-sig")

        # 파일타입 컬럼을 repair_type으로 변경
        if "파일타입" in df.columns:
            df["repair_type"] = df["파일타입"]

        # 필수 컬럼 확인
        if "위도" not in df.columns or "경도" not in df.columns:
            logger.error("위도/경도 컬럼이 없습니다")
            return None

        # NaN 제거
        df = df.dropna(subset=["위도", "경도"])

        # Point geometry 생성 (WGS84)
        geometry = [Point(lon, lat) for lon, lat in zip(df["경도"], df["위도"])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        # EPSG:5179로 변환
        gdf = gdf.to_crs("EPSG:5179")

        logger.info(f"누수 위치 데이터 로드 완료: {len(gdf):,}개 위치")
        return gdf
    except Exception as e:
        logger.error(f"누수 위치 데이터 로드 실패: {e}")
        return None


def find_top_k_repair_pipes(k_repair_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """K_repair_per_m 기준 상위 N개 파이프 선택

    Args:
        k_repair_df: K_repair 데이터 DataFrame
        top_n: 선택할 상위 개수

    Returns:
        상위 파이프 DataFrame (K_repair_per_m 내림차순)
    """
    # K_repair_per_m 기준 내림차순 정렬
    top_pipes = k_repair_df.nlargest(top_n, "K_repair_per_m").copy()

    logger.info(f"상위 {top_n}개 파이프 선택 완료")
    for i, (_, pipe) in enumerate(top_pipes.iterrows(), 1):
        logger.info(
            f"  {i}위: FTR_IDN={pipe['FTR_IDN']}, "
            f"K_repair_per_m={pipe['K_repair_per_m']:.4f}, "
            f"K_repair={pipe['K_repair']}, "
            f"length={pipe['pipe_length']:.1f}m"
        )

    return top_pipes


def find_nearby_repairs(
    pipe_geometry: Any, repair_gdf: gpd.GeoDataFrame, distance: float
) -> gpd.GeoDataFrame:
    """파이프 주변 누수 지점 찾기

    Args:
        pipe_geometry: 파이프 geometry
        repair_gdf: 누수 위치 GeoDataFrame
        distance: 검색 거리 (미터)

    Returns:
        파이프 주변 누수 지점 GeoDataFrame
    """
    # 파이프 주변 버퍼 생성
    buffer = pipe_geometry.buffer(distance)

    # 버퍼 내 누수 찾기
    nearby_mask = repair_gdf.geometry.within(buffer)
    nearby_repairs = repair_gdf[nearby_mask].copy()

    return nearby_repairs


def detect_clusters(
    repair_gdf: gpd.GeoDataFrame, cluster_radius: float
) -> list[tuple[Point, int]]:
    """누수 클러스터 탐지

    Args:
        repair_gdf: 누수 위치 GeoDataFrame
        cluster_radius: 클러스터 반경 (미터)

    Returns:
        [(클러스터 중심점, 누수 개수)] 리스트
    """
    if len(repair_gdf) == 0:
        return []

    # STRtree 구축
    tree = STRtree(repair_gdf.geometry.values)
    processed = set()
    clusters = []

    for idx, repair in repair_gdf.iterrows():
        if idx in processed:
            continue

        # 클러스터 반경 내 누수 찾기
        buffer = repair.geometry.buffer(cluster_radius)
        nearby_indices = tree.query(buffer)

        if len(nearby_indices) >= 2:  # 2개 이상이면 클러스터
            # 클러스터 중심점 계산
            nearby_points = repair_gdf.iloc[nearby_indices]
            center_x = nearby_points.geometry.x.mean()
            center_y = nearby_points.geometry.y.mean()
            center = Point(center_x, center_y)

            clusters.append((center, len(nearby_indices)))

            # 처리된 인덱스에 추가
            for ni in nearby_indices:
                processed.add(ni)

    return clusters


def visualize_pipe_repairs(
    pipe_row: pd.Series,
    pipe_gdf: gpd.GeoDataFrame,
    repair_gdf: gpd.GeoDataFrame,
    rank: int,
    distance: float,
    show_clusters: bool,
    cluster_radius: float,
    output_dir: Path,
    scale: float,
) -> Path:
    """개별 파이프와 주변 누수 시각화

    Args:
        pipe_row: 파이프 정보 (K_repair 데이터)
        pipe_gdf: 파이프 GeoDataFrame
        repair_gdf: 누수 위치 GeoDataFrame
        rank: 순위
        distance: 누수 검색 거리
        show_clusters: 클러스터 표시 여부
        cluster_radius: 클러스터 반경
        output_dir: 출력 디렉토리
        scale: 이미지 크기 배율

    Returns:
        저장된 이미지 파일 경로
    """
    config = get_config()

    # 해당 파이프 geometry 찾기
    pipe_geom_row = pipe_gdf[pipe_gdf["FTR_IDN"] == pipe_row["FTR_IDN"]]
    if pipe_geom_row.empty:
        logger.warning(f"파이프 geometry를 찾을 수 없습니다: {pipe_row['FTR_IDN']}")
        return None

    pipe_geometry = pipe_geom_row.iloc[0].geometry

    # 주변 누수 찾기
    nearby_repairs = find_nearby_repairs(pipe_geometry, repair_gdf, distance)

    # 클러스터 탐지
    clusters = []
    if show_clusters and len(nearby_repairs) > 0:
        clusters = detect_clusters(nearby_repairs, cluster_radius)

    # 시각화
    fig_width, fig_height = 16 * scale, 12 * scale
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

    # 30m 버퍼 표시
    buffer = pipe_geometry.buffer(distance)
    ax.fill(
        *buffer.exterior.coords.xy,
        color="yellow",
        alpha=BUFFER_ALPHA,
        label=f"{distance}m 버퍼",
        zorder=1,
    )

    # 파이프 표시
    pipe_geom_row.plot(
        ax=ax,
        color="red",
        linewidth=PIPE_LINE_WIDTH,
        label="파이프",
        zorder=3,
    )

    # 누수 지점 표시 (유형별 색상)
    repair_counts = {}
    if len(nearby_repairs) > 0:
        for repair_type, repairs in nearby_repairs.groupby("repair_type"):
            color_info = config.REPAIR_COLORS.get(repair_type, ("#808080", repair_type))
            color, label = color_info

            repairs.plot(
                ax=ax,
                color=color,
                markersize=REPAIR_POINT_SIZE,
                alpha=REPAIR_ALPHA,
                edgecolors="white",
                linewidth=0.5,
                label=f"{label} ({len(repairs)}개)",
                zorder=4,
            )
            repair_counts[repair_type] = len(repairs)

    # 클러스터 원 표시
    if clusters:
        for cluster_center, cluster_count in clusters:
            circle = Circle(
                (cluster_center.x, cluster_center.y),
                cluster_radius,
                facecolor="yellow",
                alpha=CLUSTER_ALPHA,
                edgecolor="orange",
                linewidth=1,
                linestyle="--",
                zorder=2,
            )
            ax.add_patch(circle)

            # 중복 횟수 텍스트
            ax.text(
                cluster_center.x,
                cluster_center.y,
                str(cluster_count),
                fontsize=10,
                fontweight="bold",
                color="black",
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.05",
                    facecolor="white",
                    edgecolor="darkred",
                    linewidth=0.5,
                    alpha=0.9,
                ),
                zorder=5,
            )

    # 제목 설정
    title = (
        f"순위 {rank}: FTR_IDN {pipe_row['FTR_IDN']} - "
        f"K_repair_per_m: {pipe_row['K_repair_per_m']:.4f}\n"
        f"파이프 길이: {pipe_row['pipe_length']:.1f}m, "
        f"총 K_repair: {pipe_row['K_repair']}, "
        f"{distance}m 내 누수: {len(nearby_repairs)}개"
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

    # 축 설정
    ax.set_xlabel("X 좌표 (m)", fontsize=12)
    ax.set_ylabel("Y 좌표 (m)", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # 범례 표시
    if len(nearby_repairs) > 0 or clusters:
        ax.legend(loc="upper right", fontsize=10)

    # 통계 정보 박스
    stats_text = f"K_repair 통계:\n"
    stats_text += f"• 파이프 길이: {pipe_row['pipe_length']:.1f}m\n"
    stats_text += f"• 총 K_repair: {pipe_row['K_repair']}\n"
    stats_text += f"• K_repair_per_m: {pipe_row['K_repair_per_m']:.4f}\n"
    stats_text += f"• {distance}m 내 누수: {len(nearby_repairs)}개\n"

    if repair_counts:
        stats_text += "\n누수 유형별:\n"
        for repair_type, count in repair_counts.items():
            stats_text += f"• {repair_type}: {count}개\n"

    if clusters:
        stats_text += f"\n클러스터: {len(clusters)}개"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.8),
    )

    # 레이아웃 조정
    plt.tight_layout()

    # 파일 저장
    output_file = output_dir / f"rank{rank}_FTR_IDN_{pipe_row['FTR_IDN']}.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"시각화 완료: {output_file}")
    return output_file


def generate_report(
    top_pipes: pd.DataFrame,
    pipe_type: str,
    distance: float,
    output_dir: Path,
    image_files: list[Path],
) -> Path:
    """K_repair 분석 보고서 생성

    Args:
        top_pipes: 상위 파이프 DataFrame
        pipe_type: 파이프 타입
        distance: 검색 거리
        output_dir: 출력 디렉토리
        image_files: 생성된 이미지 파일 목록

    Returns:
        보고서 파일 경로
    """
    report_file = output_dir / f"{pipe_type}_high_k_repair_report.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# {pipe_type} K_repair_per_m 상위 파이프 분석 보고서\n\n")
        f.write(f"**생성일**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**분석 대상**: {pipe_type}\n")
        f.write(f"**검색 거리**: {distance}m\n")
        f.write(f"**상위 파이프**: {len(top_pipes)}개\n\n")

        f.write("## 📊 상위 파이프 목록\n\n")
        f.write("| 순위 | FTR_IDN | 파이프 길이(m) | K_repair | K_repair_per_m | 비고 |\n")
        f.write("|------|---------|----------------|----------|----------------|------|\n")

        for i, (_, pipe) in enumerate(top_pipes.iterrows(), 1):
            length = pipe["pipe_length"]
            k_repair = pipe["K_repair"]
            k_repair_per_m = pipe["K_repair_per_m"]
            
            # 비고 생성
            remark = ""
            if k_repair_per_m > 1.0:
                remark = "⚠️ 매우 높음"
            elif k_repair_per_m > 0.5:
                remark = "🟡 높음"
            else:
                remark = "🟢 정상"

            f.write(
                f"| {i} | {pipe['FTR_IDN']} | {length:.1f} | {k_repair} | "
                f"{k_repair_per_m:.4f} | {remark} |\n"
            )

        f.write("\n## 📈 통계 요약\n\n")
        f.write(f"- **평균 K_repair_per_m**: {top_pipes['K_repair_per_m'].mean():.4f}\n")
        f.write(f"- **최대 K_repair_per_m**: {top_pipes['K_repair_per_m'].max():.4f}\n")
        f.write(f"- **평균 파이프 길이**: {top_pipes['pipe_length'].mean():.1f}m\n")
        f.write(f"- **평균 K_repair**: {top_pipes['K_repair'].mean():.1f}\n\n")

        f.write("## 🖼️ 시각화 이미지\n\n")
        for i, image_file in enumerate(image_files, 1):
            if image_file:
                image_name = image_file.name
                f.write(f"### {i}위: {image_name}\n\n")
                f.write(f"![{image_name}]({image_name})\n\n")

        f.write("## 💡 분석 결과 및 권고사항\n\n")
        f.write("### 주요 발견사항\n")
        
        very_high_count = (top_pipes['K_repair_per_m'] > 1.0).sum()
        high_count = ((top_pipes['K_repair_per_m'] > 0.5) & (top_pipes['K_repair_per_m'] <= 1.0)).sum()
        
        f.write(f"- **매우 높음 (>1.0)**: {very_high_count}개 파이프\n")
        f.write(f"- **높음 (0.5-1.0)**: {high_count}개 파이프\n\n")

        if very_high_count > 0:
            f.write("### ⚠️ 즉시 점검 필요\n")
            f.write("K_repair_per_m > 1.0인 파이프는 1미터당 1회 이상의 재작업이 발생한 것으로, "
                   "파이프 상태 및 주변 환경을 즉시 점검해야 합니다.\n\n")

        f.write("### 📋 권고사항\n")
        f.write("1. 시각화 이미지를 통해 누수 클러스터 패턴 확인\n")
        f.write("2. K_repair_per_m이 높은 파이프의 공통 특성 분석\n")
        f.write("3. 주변 환경 요인 (교통, 토양, 연령 등) 조사\n")
        f.write("4. 예방 정비 계획 수립\n\n")

        f.write("---\n")
        f.write("*본 보고서는 main13f_visualize_high_k_repair.py로 생성되었습니다.*\n")

    logger.info(f"보고서 생성 완료: {report_file}")
    return report_file


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 한글 폰트 설정
    setup_korean_font()

    # 출력 디렉토리 설정
    if args.output_dir is None:
        config = get_config()
        args.output_dir = config.RESULTS_DIR / "main13f_high_k_repair"

    pipe_output_dir = args.output_dir / f"{args.pipe_type}_top{args.top_n}"
    pipe_output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("K_repair_per_m 상위 파이프 시각화")
    logger.info("=" * 60)
    logger.info(f"파이프 타입: {args.pipe_type}")
    logger.info(f"상위 개수: {args.top_n}")
    logger.info(f"검색 거리: {args.distance}m")
    logger.info(f"클러스터 표시: {args.show_clusters}")
    logger.info(f"출력 디렉토리: {pipe_output_dir}")

    # 1. K_repair 데이터 로드
    logger.info("\n1. K_repair 데이터 로드 중...")
    k_repair_df = load_k_repair_data(args.pipe_type)
    if k_repair_df is None:
        logger.error("K_repair 데이터 로드 실패")
        return

    # 2. 파이프 shapefile 로드
    logger.info("\n2. 파이프 shapefile 로드 중...")
    pipe_gdf = load_pipe_shapefile(args.pipe_type)
    if pipe_gdf is None:
        logger.error("파이프 shapefile 로드 실패")
        return

    # 3. 누수 위치 데이터 로드
    logger.info("\n3. 누수 위치 데이터 로드 중...")
    repair_gdf = load_repair_locations()
    if repair_gdf is None:
        logger.error("누수 위치 데이터 로드 실패")
        return

    # 4. 상위 파이프 선택
    logger.info(f"\n4. K_repair_per_m 상위 {args.top_n}개 파이프 선택 중...")
    top_pipes = find_top_k_repair_pipes(k_repair_df, args.top_n)

    if len(top_pipes) == 0:
        logger.error("상위 파이프를 찾을 수 없습니다")
        return

    # 5. 개별 시각화
    logger.info(f"\n5. 개별 파이프 시각화 중...")
    image_files = []

    for rank, (_, pipe_row) in enumerate(top_pipes.iterrows(), 1):
        logger.info(f"\n순위 {rank} 처리 중: FTR_IDN {pipe_row['FTR_IDN']}")

        image_file = visualize_pipe_repairs(
            pipe_row,
            pipe_gdf,
            repair_gdf,
            rank,
            args.distance,
            args.show_clusters,
            args.cluster_radius,
            pipe_output_dir,
            args.scale,
        )
        image_files.append(image_file)

    # 6. 보고서 생성
    logger.info("\n6. 분석 보고서 생성 중...")
    report_file = generate_report(
        top_pipes,
        args.pipe_type,
        args.distance,
        args.output_dir,
        image_files,
    )

    logger.info("\n" + "=" * 60)
    logger.info("✅ K_repair_per_m 상위 파이프 시각화 완료!")
    logger.info(f"📁 출력 디렉토리: {args.output_dir}")
    logger.info(f"📊 보고서: {report_file}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()