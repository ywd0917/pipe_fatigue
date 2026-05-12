"""
복구 작업 데이터 시각화를 위한 특화 모듈
복구 작업 위치 시각화 및 파이프 피로 손상과의 통합 시각화 로직
"""

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from shapely.geometry import Point

# 복구 작업 점 표시 설정
POINT_SIZE = 50
POINT_ALPHA = 0.8
EDGE_COLOR = "white"
EDGE_WIDTH = 0.5

# 통합 시각화용 설정
RECOVERY_POINT_SIZE = 30
RECOVERY_POINT_ALPHA = 0.3


def get_repair_colors() -> dict[str, tuple[str, str]]:
    """복구 작업 유형별 색상 정의

    Returns:
        {작업유형: (색상코드, 표시명)} 형태의 딕셔너리
    """
    return {
        "긴급복구": ("#FF6B6B", "긴급복구"),  # 연한 빨강
        # "기타공사": ("#FF6B6B", "기타공사"),      # 연한 빨강
        # "지상누수": ("#4ECDC4", "지상누수"),      # 청록색
        # "지하누수": ("#45B7D1", "지하누수"),      # 하늘색
    }


def get_repair_colors_for_pipe() -> dict[str, tuple[str, str]]:
    """파이프 시각화용 복구 작업 색상 (더 진한 색상)

    Returns:
        {작업유형: (색상코드, 표시명)} 형태의 딕셔너리
    """
    return {
        "긴급복구": ("#FF1493", "긴급복구"),  # 진한 핑크 (파이프 색상과 구별되도록)
        # "기타공사": ("#000080", "기타공사"),  # 남색
        # "지상누수": ("#FF1493", "지상누수"),  # 진한 핑크
        # "지하누수": ("#8B4513", "지하누수"),  # 갈색
    }


def convert_coordinates_to_points(
    df: pd.DataFrame,
    x_col: str = "epsg5179위도",  # 실제로는 X 좌표
    y_col: str = "epsg5179경도",  # 실제로는 Y 좌표
    crs: str = "EPSG:5179",
) -> gpd.GeoDataFrame:
    """좌표 데이터를 GeoDataFrame으로 변환

    Args:
        df: 좌표가 포함된 DataFrame
        x_col: X 좌표 컬럼명
        y_col: Y 좌표 컬럼명
        crs: 좌표계

    Returns:
        GeoDataFrame
    """
    # 좌표 컬럼이 있는지 확인
    if x_col not in df.columns or y_col not in df.columns:
        print(f"경고: 좌표 컬럼이 없습니다. 필요한 컬럼: {x_col}, {y_col}")
        print(f"사용 가능한 컬럼: {list(df.columns)}")
        return gpd.GeoDataFrame()

    # 좌표가 있는 행만 필터링
    valid_coords = df.dropna(subset=[x_col, y_col])

    if len(valid_coords) == 0:
        print("경고: 유효한 좌표가 없습니다.")
        return gpd.GeoDataFrame()

    # GeoDataFrame 생성
    geometry = gpd.points_from_xy(valid_coords[x_col], valid_coords[y_col])
    return gpd.GeoDataFrame(valid_coords, geometry=geometry, crs=crs)


def generate_random_points_in_polygon(polygon: Any, num_points: int) -> list[Point]:
    """폴리곤 내부에 랜덤 점 생성

    Args:
        polygon: Shapely Polygon 객체
        num_points: 생성할 점의 개수

    Returns:
        Point 객체 리스트
    """
    points: list[Point] = []
    min_x, min_y, max_x, max_y = polygon.bounds

    attempts = 0
    max_attempts = num_points * 100

    while len(points) < num_points and attempts < max_attempts:
        # 경계 상자 내에서 랜덤 점 생성
        random_point = Point(
            np.random.uniform(min_x, max_x), np.random.uniform(min_y, max_y)
        )

        # 폴리곤 내부에 있는지 확인
        if polygon.contains(random_point):
            points.append(random_point)

        attempts += 1

    # 충분한 점을 생성하지 못했다면 중심점 주변에 생성
    if len(points) < num_points:
        centroid = polygon.centroid
        for _ in range(num_points - len(points)):
            offset_x = np.random.normal(0, (max_x - min_x) * 0.1)
            offset_y = np.random.normal(0, (max_y - min_y) * 0.1)
            points.append(Point(centroid.x + offset_x, centroid.y + offset_y))

    return points


def plot_mdlz_background(
    ax: Any, mdlz_gdf: gpd.GeoDataFrame, show_labels: bool = True
) -> None:
    """MDLZ 배경 그리기

    Args:
        ax: matplotlib axes
        mdlz_gdf: MDLZ GeoDataFrame
        show_labels: 라벨 표시 여부
    """
    if mdlz_gdf is None or len(mdlz_gdf) == 0:
        return

    # MDLZ 경계 그리기
    mdlz_gdf.plot(
        ax=ax,
        facecolor="lightgray",
        edgecolor="darkgray",
        linewidth=0.5,
        alpha=0.3,
        zorder=0,
    )

    # MDLZ 라벨 표시
    if show_labels:
        for _, row in mdlz_gdf.iterrows():
            # 라벨 컬럼 찾기
            label_col = None
            for col in ["MDZ_NUM", "MDZ_LBL"]:
                if col in mdlz_gdf.columns:
                    label_col = col
                    break

            if label_col and pd.notna(row[label_col]):
                centroid = row.geometry.centroid
                if centroid:
                    ax.text(
                        centroid.x,
                        centroid.y,
                        str(row[label_col]),
                        fontsize=8,
                        ha="center",
                        va="center",
                        bbox=dict(
                            boxstyle="round,pad=0.2",
                            facecolor="white",
                            edgecolor="gray",
                            alpha=0.7,
                        ),
                    )


def plot_repair_points(
    ax: Any,
    repair_data: dict[str, pd.DataFrame],
    use_pipe_colors: bool = False,
    zorder: int = 3,
    point_size: int = POINT_SIZE,
    point_alpha: float = POINT_ALPHA,
) -> tuple[list[mpatches.Circle], int]:
    """복구 작업 점들을 그리기

    Args:
        ax: matplotlib axes
        repair_data: 복구 작업 데이터
        use_pipe_colors: 파이프 시각화용 색상 사용 여부
        zorder: 그리기 순서
        point_size: 점 크기
        point_alpha: 투명도

    Returns:
        (범례 요소 리스트, 총 점 개수)
    """
    colors = get_repair_colors_for_pipe() if use_pipe_colors else get_repair_colors()
    legend_elements = []
    total_points = 0

    for repair_type, df in repair_data.items():
        if repair_type not in colors:
            continue

        color, label = colors[repair_type]

        # 좌표를 GeoDataFrame으로 변환
        gdf = convert_coordinates_to_points(df)

        if len(gdf) == 0:
            print(f"{repair_type}: 유효한 좌표가 없습니다.")
            continue

        # 점 그리기
        gdf.plot(
            ax=ax,
            color=color,
            markersize=point_size,
            alpha=point_alpha,
            edgecolor=EDGE_COLOR,
            linewidth=EDGE_WIDTH,
            zorder=zorder,
        )

        print(f"{repair_type}: {len(gdf)}개 위치")
        total_points += len(gdf)

        # 범례 추가
        legend_elements.append(
            mpatches.Circle(
                (0, 0),
                1,
                facecolor=color,
                edgecolor=EDGE_COLOR,
                label=f"{label} ({len(gdf)}건)",
            )
        )

    return legend_elements, total_points


def plot_repair_points_on_pipe(
    ax: Any,
    repair_data: dict[str, pd.DataFrame],
    smlz_file: Path | None = None,
) -> tuple[list[mpatches.Circle], int]:
    """파이프 시각화에 복구 작업 점 추가

    Args:
        ax: matplotlib axes
        repair_data: 복구 작업 데이터
        smlz_file: SMLZ 파일 경로 (좌표가 없는 데이터용)

    Returns:
        (범례 요소 리스트, 총 점 개수)
    """
    colors = get_repair_colors_for_pipe()
    legend_elements = []
    total_points = 0

    for repair_type, repair_df in repair_data.items():
        if repair_type not in colors:
            continue

        color, label = colors[repair_type]

        # 좌표 컬럼 확인
        x_col = "epsg5179위도"
        y_col = "epsg5179경도"

        if x_col in repair_df.columns and y_col in repair_df.columns:
            # 실제 좌표가 있는 경우
            valid_coords = repair_df.dropna(subset=[x_col, y_col])

            if len(valid_coords) > 0:
                # GeoDataFrame 생성
                geometry = gpd.points_from_xy(valid_coords[x_col], valid_coords[y_col])
                points_gdf = gpd.GeoDataFrame(
                    valid_coords, geometry=geometry, crs="EPSG:5179"
                )

                # scatter 사용으로 투명도 보장
                ax.scatter(
                    points_gdf.geometry.x,
                    points_gdf.geometry.y,
                    c=color,
                    s=RECOVERY_POINT_SIZE,
                    alpha=RECOVERY_POINT_ALPHA,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=5,
                )

                total_points += len(points_gdf)

                legend_elements.append(
                    mpatches.Circle(
                        (0, 0),
                        1,
                        facecolor=color,
                        edgecolor="white",
                        label=f"{label} ({len(points_gdf)}건)",
                    )
                )

                print(f"{repair_type}: {len(points_gdf)}개 점 표시")

        # 좌표가 없는 경우 SMLZ 기반 생성
        elif smlz_file and smlz_file.exists():
            points = generate_repair_points_from_smlz(repair_df, smlz_file, repair_type)

            if points:
                # scatter로 그리기
                x_coords = [p.x for p in points]
                y_coords = [p.y for p in points]

                ax.scatter(
                    x_coords,
                    y_coords,
                    c=color,
                    s=RECOVERY_POINT_SIZE,
                    alpha=RECOVERY_POINT_ALPHA,
                    edgecolor="white",
                    linewidth=0.5,
                    zorder=5,
                )

                total_points += len(points)

                legend_elements.append(
                    mpatches.Circle(
                        (0, 0),
                        1,
                        facecolor=color,
                        edgecolor="white",
                        label=f"{label} ({len(points)}건)",
                    )
                )

    return legend_elements, total_points


def generate_repair_points_from_smlz(
    repair_df: pd.DataFrame, smlz_file: Path, repair_type: str
) -> list[Point]:
    """SMLZ 기반으로 복구 작업 점 생성

    Args:
        repair_df: 복구 작업 데이터
        smlz_file: SMLZ 파일 경로
        repair_type: 복구 작업 유형

    Returns:
        생성된 점 리스트
    """
    try:
        # SMLZ 데이터 로드
        smlz_gdf = gpd.read_file(smlz_file, encoding="euc-kr")
        if smlz_gdf.crs is None:
            smlz_gdf.set_crs("EPSG:5179", inplace=True)

        # 소구역번호 컬럼 찾기
        smlz_col = None
        for col in smlz_gdf.columns:
            if col in ["SMZ_NUM", "SMZ_LBL"]:
                smlz_col = col
                break

        if not smlz_col:
            return []

        # SMLZ 번호를 문자열로 변환
        smlz_gdf[smlz_col] = smlz_gdf[smlz_col].astype(str).str.strip()
        smlz_numbers = set(smlz_gdf[smlz_col].unique())

        # 복구 데이터의 소구역번호 컬럼 찾기
        repair_smlz_col = None
        for col in repair_df.columns:
            if "소구역번호" in col:
                repair_smlz_col = col
                break

        if not repair_smlz_col:
            return []

        # 복구 데이터 필터링 (직접 구현하여 순환 참조 방지)
        repair_df[repair_smlz_col] = repair_df[repair_smlz_col].astype(str).str.strip()
        filtered_repair = repair_df[repair_df[repair_smlz_col].isin(smlz_numbers)]

        if len(filtered_repair) == 0:
            return []

        # 소구역별로 점 생성
        all_points = []

        for smlz_num in filtered_repair[repair_smlz_col].unique():
            # 해당 소구역의 작업 수
            count = len(filtered_repair[filtered_repair[repair_smlz_col] == smlz_num])

            # 해당 소구역의 폴리곤 찾기
            smlz_polygon = smlz_gdf[smlz_gdf[smlz_col] == str(smlz_num)]

            if len(smlz_polygon) > 0:
                # 첫 번째 폴리곤 사용
                polygon = smlz_polygon.iloc[0].geometry

                # 폴리곤 내부에 랜덤 점 생성
                points = generate_random_points_in_polygon(polygon, count)
                all_points.extend(points)

        return all_points

    except Exception as e:
        print(f"SMLZ 기반 점 생성 중 오류: {e}")
        return []


def calculate_repair_bounds(
    repair_data: dict[str, pd.DataFrame],
) -> np.ndarray | None:
    """모든 복구 작업 데이터의 전체 경계 계산

    Args:
        repair_data: 복구 작업 데이터

    Returns:
        [min_x, min_y, max_x, max_y] 또는 None
    """
    all_bounds = None

    for repair_type, df in repair_data.items():
        gdf = convert_coordinates_to_points(df)

        if len(gdf) > 0:
            bounds = gdf.total_bounds

            if all_bounds is None:
                all_bounds = bounds.copy()
            else:
                all_bounds[0] = min(all_bounds[0], bounds[0])  # min_x
                all_bounds[1] = min(all_bounds[1], bounds[1])  # min_y
                all_bounds[2] = max(all_bounds[2], bounds[2])  # max_x
                all_bounds[3] = max(all_bounds[3], bounds[3])  # max_y

    return all_bounds
