#!/usr/bin/env python3
"""
visualize_repairs_far_from_pipes.py

100m 이상 파이프에서 떨어진 재작업 위치 시각화
- 재작업 위치와 파이프까지의 거리 분석
- 거리별 색상 구분 시각화
- 통계 정보 표시

Author: assistant
Date: 2025-08-20
"""

import sys
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 시각화 상수
FIGURE_WIDTH = 16
FIGURE_HEIGHT = 12
DPI_HIGH = 300

# 거리 임계값 (미터)
DISTANCE_THRESHOLDS = [50, 100, 150, 200]
DISTANCE_COLORS = {
    "0-50m": "#2ecc71",  # 초록색 - 안전
    "50-100m": "#f39c12",  # 주황색 - 주의
    "100-150m": "#e74c3c",  # 빨간색 - 위험
    "150m+": "#8b0000",  # 진한 빨간색 - 매우 위험
    "파이프": "#87CEEB",  # 하늘색 - 파이프
}


def load_repair_data() -> pd.DataFrame:
    """520 지역 재작업 데이터 로드"""
    repair_files = [
        RESULTS_DIR / "지상누수_520_위치추가.csv",
        RESULTS_DIR / "지하누수_520_위치추가.csv",
    ]

    repairs = []
    for file in repair_files:
        if file.exists():
            df = pd.read_csv(file, encoding="utf-8-sig")
            df["repair_type"] = "지상누수" if "지상" in file.stem else "지하누수"
            # 유효한 좌표만 추가
            valid = df.dropna(subset=["위도", "경도"])
            valid = valid[(valid["위도"] > 0) & (valid["경도"] > 0)]
            print(f"  {file.stem}: {len(valid)}개 로드")
            repairs.append(valid)

    if repairs:
        df_all = pd.concat(repairs, ignore_index=True)
        print(f"재작업 데이터 로드 완료: 총 {len(df_all)}개")
        return df_all
    raise FileNotFoundError("재작업 CSV 파일을 찾을 수 없습니다.")


def load_pipe_data() -> gpd.GeoDataFrame:
    """파이프 shapefile 로드 및 병합"""
    pipe_files = [
        RAW_DATA_DIR / "export_shp_20250704(0520)" / "V_WTL_PIPE_LM.shp",
        RAW_DATA_DIR / "export_shp_20250704(0520)" / "V_WTL_SPLY_LS.shp",
    ]

    pipes = []
    for file in pipe_files:
        if file.exists():
            gdf = gpd.read_file(file)
            gdf["pipe_type"] = "PIPE_LM" if "PIPE_LM" in file.stem else "SPLY_LS"
            pipes.append(gdf)

    if pipes:
        gdf_all = pd.concat(pipes, ignore_index=True)
        gdf_all = gpd.GeoDataFrame(gdf_all, crs=pipes[0].crs)
        print(f"파이프 데이터 로드: {len(gdf_all)}개")
        print(f"  - PIPE_LM: {len(gdf_all[gdf_all['pipe_type'] == 'PIPE_LM'])}개")
        print(f"  - SPLY_LS: {len(gdf_all[gdf_all['pipe_type'] == 'SPLY_LS'])}개")
        return gdf_all
    raise FileNotFoundError("파이프 shapefile을 찾을 수 없습니다.")


def calculate_distances_to_pipes(
    repairs_gdf: gpd.GeoDataFrame, pipes_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """각 재작업 위치에서 가장 가까운 파이프까지의 거리 계산"""
    print("\n거리 계산 중...")

    # STRtree 생성 (공간 인덱싱)
    pipe_tree = STRtree(pipes_gdf.geometry.tolist())

    results = []
    total = len(repairs_gdf)

    for idx, repair in repairs_gdf.iterrows():
        if idx % 20 == 0:
            print(f"  처리 중: {idx}/{total} ({idx/total*100:.1f}%)")

        point = repair.geometry

        # 500m 버퍼로 후보 찾기
        buffer = point.buffer(500)
        candidates = pipe_tree.query(buffer)

        if len(candidates) == 0:
            # 500m 내에 파이프가 없는 경우
            min_dist = float("inf")
            nearest_pipe_type = "None"
        else:
            # 최소 거리 계산
            min_dist = float("inf")
            nearest_pipe_type = None

            for pipe_idx in candidates:
                pipe = pipes_gdf.iloc[pipe_idx]
                dist = pipe.geometry.distance(point)

                if dist < min_dist:
                    min_dist = dist
                    nearest_pipe_type = pipe.get("pipe_type", "Unknown")

        # 거리 카테고리 결정
        if min_dist <= 50:
            category = "0-50m"
        elif min_dist <= 100:
            category = "50-100m"
        elif min_dist <= 150:
            category = "100-150m"
        else:
            category = "150m+"

        results.append(
            {
                "index": idx,
                "address": repair.get("주소", "N/A"),
                "repair_type": repair.get("repair_type", "N/A"),
                "date": repair.get("작업종료일", "N/A"),
                "lat": repair["위도"],
                "lon": repair["경도"],
                "x": point.x,
                "y": point.y,
                "distance": min_dist,
                "category": category,
                "nearest_pipe_type": nearest_pipe_type,
            }
        )

    df_results = pd.DataFrame(results)

    # 통계 출력
    print("\n=== 거리별 분포 ===")
    for cat in ["0-50m", "50-100m", "100-150m", "150m+"]:
        count = len(df_results[df_results["category"] == cat])
        pct = count / len(df_results) * 100
        print(f"{cat}: {count}개 ({pct:.1f}%)")

    # 100m 이상 떨어진 위치 상세
    far_repairs = df_results[df_results["distance"] > 100].sort_values(
        "distance", ascending=False
    )
    if len(far_repairs) > 0:
        print(f"\n=== 100m 이상 떨어진 재작업 위치 ({len(far_repairs)}개) ===")
        print("Top 5 가장 먼 위치:")
        for _, row in far_repairs.head(5).iterrows():
            print(
                f"  {row['distance']:.1f}m - {row['address'][:30]}... ({row['repair_type']})"
            )

    return df_results


def create_visualization(
    repairs_df: pd.DataFrame, pipes_gdf: gpd.GeoDataFrame, output_path: Path
) -> None:
    """재작업 위치와 파이프 거리 시각화"""
    setup_korean_font()

    fig, ax = plt.subplots(1, 1, figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # 파이프 그리기 (배경)
    pipes_gdf.plot(
        ax=ax,
        color=DISTANCE_COLORS["파이프"],
        linewidth=0.5,
        alpha=0.3,
        label="파이프 네트워크",
    )

    # 거리 카테고리별로 재작업 위치 그리기
    legend_elements = []

    for category in ["0-50m", "50-100m", "100-150m", "150m+"]:
        cat_data = repairs_df[repairs_df["category"] == category]
        if len(cat_data) > 0:
            color = DISTANCE_COLORS[category]

            # 점 크기를 거리에 따라 조정
            if category == "150m+":
                size = 100
                alpha = 0.9
                edgecolor = "black"
                linewidth = 1.5
            elif category == "100-150m":
                size = 70
                alpha = 0.8
                edgecolor = "white"
                linewidth = 1.0
            elif category == "50-100m":
                size = 40
                alpha = 0.7
                edgecolor = "white"
                linewidth = 0.5
            else:
                size = 20
                alpha = 0.6
                edgecolor = "white"
                linewidth = 0.3

            ax.scatter(
                cat_data["x"],
                cat_data["y"],
                c=color,
                s=size,
                alpha=alpha,
                edgecolor=edgecolor,
                linewidth=linewidth,
                zorder=5,
            )

            # 범례 요소 추가
            legend_elements.append(
                mpatches.Circle(
                    (0, 0),
                    1,
                    facecolor=color,
                    edgecolor=edgecolor,
                    label=f"{category} ({len(cat_data)}개)",
                )
            )

    # 100m 이상 떨어진 위치 강조 (빨간 원)
    far_repairs = repairs_df[repairs_df["distance"] > 100]
    if len(far_repairs) > 0:
        for _, repair in far_repairs.iterrows():
            circle = plt.Circle(
                (repair["x"], repair["y"]),
                radius=30,  # 30m 반경 원
                color="red",
                fill=False,
                linewidth=2,
                alpha=0.7,
                linestyle="--",
            )
            ax.add_patch(circle)

    # 경계 설정
    all_bounds = pipes_gdf.total_bounds
    x_margin = (all_bounds[2] - all_bounds[0]) * 0.05
    y_margin = (all_bounds[3] - all_bounds[1]) * 0.05
    ax.set_xlim(all_bounds[0] - x_margin, all_bounds[2] + x_margin)
    ax.set_ylim(all_bounds[1] - y_margin, all_bounds[3] + y_margin)

    # 제목 및 라벨
    ax.set_title(
        "520 지역 재작업 위치와 파이프 네트워크 거리 분석",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=12)
    ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 범례 추가
    ax.legend(
        handles=legend_elements,
        loc="upper right",
        title="파이프까지의 거리",
        title_fontsize=11,
        fontsize=10,
        framealpha=0.9,
    )

    # 통계 정보 박스
    stats_text = f"전체 재작업: {len(repairs_df)}개\n"
    stats_text += f"100m 이내: {len(repairs_df[repairs_df['distance'] <= 100])}개 "
    stats_text += (
        f"({len(repairs_df[repairs_df['distance'] <= 100])/len(repairs_df)*100:.1f}%)\n"
    )
    stats_text += f"100m 초과: {len(far_repairs)}개 "
    stats_text += f"({len(far_repairs)/len(repairs_df)*100:.1f}%)\n"

    if len(far_repairs) > 0:
        stats_text += f"최대 거리: {repairs_df['distance'].max():.1f}m\n"
        stats_text += f"평균 거리 (100m+): {far_repairs['distance'].mean():.1f}m"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    # 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    print(f"\n이미지 저장 완료: {output_path}")
    plt.close()


def create_detailed_map(
    repairs_df: pd.DataFrame, pipes_gdf: gpd.GeoDataFrame, output_path: Path
) -> None:
    """100m 이상 떨어진 위치만 상세 표시"""
    setup_korean_font()

    far_repairs = repairs_df[repairs_df["distance"] > 100].copy()

    if len(far_repairs) == 0:
        print("100m 이상 떨어진 재작업 위치가 없습니다.")
        return

    fig, ax = plt.subplots(1, 1, figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # 파이프 그리기
    pipes_gdf.plot(ax=ax, color=DISTANCE_COLORS["파이프"], linewidth=0.8, alpha=0.5)

    # 100m 이상 떨어진 위치 표시
    scatter = ax.scatter(
        far_repairs["x"],
        far_repairs["y"],
        c=far_repairs["distance"],
        cmap="Reds",
        s=100,
        alpha=0.8,
        edgecolor="black",
        linewidth=1,
        zorder=5,
    )

    # 컬러바 추가
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("파이프까지의 거리 (m)", fontsize=10)

    # 각 위치에 라벨 추가 (상위 10개만)
    for i, row in far_repairs.nlargest(10, "distance").iterrows():
        # 주소 줄임
        addr = row["address"].split()[0:2]
        addr_short = " ".join(addr) if len(addr) > 0 else "N/A"

        ax.annotate(
            f"{row['distance']:.0f}m\n{addr_short}",
            xy=(row["x"], row["y"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
        )

    # 경계 설정 (100m+ 위치 중심)
    x_coords = far_repairs["x"].values
    y_coords = far_repairs["y"].values

    x_min, x_max = x_coords.min(), x_coords.max()
    y_min, y_max = y_coords.min(), y_coords.max()

    x_margin = (x_max - x_min) * 0.2
    y_margin = (y_max - y_min) * 0.2

    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)

    # 제목 및 라벨
    ax.set_title(
        f"100m 이상 파이프에서 떨어진 재작업 위치 ({len(far_repairs)}개)",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=12)
    ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_aspect("equal")

    # 통계 정보
    stats_text = f"100-150m: {len(far_repairs[far_repairs['distance'] <= 150])}개\n"
    stats_text += f"150m 이상: {len(far_repairs[far_repairs['distance'] > 150])}개\n"
    stats_text += f"최대 거리: {far_repairs['distance'].max():.1f}m\n"
    stats_text += f"평균 거리: {far_repairs['distance'].mean():.1f}m"

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    # 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    print(f"상세 지도 저장 완료: {output_path}")
    plt.close()


def save_distance_analysis_csv(repairs_df: pd.DataFrame, output_path: Path) -> None:
    """거리 분석 결과를 CSV로 저장"""
    # 100m 이상 떨어진 위치만 필터링
    far_repairs = repairs_df[repairs_df["distance"] > 100].copy()

    if len(far_repairs) > 0:
        # 정렬
        far_repairs = far_repairs.sort_values("distance", ascending=False)

        # 필요한 컬럼만 선택
        output_df = far_repairs[
            [
                "address",
                "repair_type",
                "date",
                "lat",
                "lon",
                "distance",
                "category",
                "nearest_pipe_type",
            ]
        ]

        # 컬럼명 한글로 변경
        output_df.columns = [
            "주소",
            "작업유형",
            "작업종료일",
            "위도",
            "경도",
            "최단거리(m)",
            "거리구간",
            "가장가까운파이프종류",
        ]

        # CSV 저장
        output_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"분석 결과 저장: {output_path}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("재작업 위치와 파이프 네트워크 거리 분석")
    print("=" * 60)

    try:
        # 데이터 로드
        print("\n1. 데이터 로드 중...")
        repairs_df = load_repair_data()
        pipes_gdf = load_pipe_data()

        # WGS84를 EPSG:5179로 변환
        print("\n2. 좌표계 변환 중...")
        repair_points = [
            Point(lon, lat)
            for lon, lat in zip(repairs_df["경도"], repairs_df["위도"], strict=False)
        ]
        repairs_gdf = gpd.GeoDataFrame(
            repairs_df, geometry=repair_points, crs="EPSG:4326"
        )
        repairs_gdf = repairs_gdf.to_crs("EPSG:5179")

        # 거리 계산
        print("\n3. 파이프까지의 거리 계산 중...")
        distance_results = calculate_distances_to_pipes(repairs_gdf, pipes_gdf)

        # 시각화
        print("\n4. 시각화 생성 중...")
        output_dir = RESULTS_DIR / "pipe_distance_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 전체 맵
        create_visualization(
            distance_results, pipes_gdf, output_dir / "repair_pipe_distance_map.png"
        )

        # 100m+ 상세 맵
        create_detailed_map(
            distance_results, pipes_gdf, output_dir / "far_repairs_detailed_map.png"
        )

        # CSV 저장
        save_distance_analysis_csv(
            distance_results, output_dir / "repairs_far_from_pipes.csv"
        )

        print("\n" + "=" * 60)
        print("분석 완료!")
        print(f"결과 위치: {output_dir}")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
