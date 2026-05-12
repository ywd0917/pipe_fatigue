"""
토양(지질) 데이터 시각화를 위한 특화 모듈
Geology 시리즈 shapefile 시각화 관련 비즈니스 로직
"""

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


def get_soil_files(data_dir: Path) -> dict[str, Path]:
    """Soil 데이터 파일 경로 찾기

    Args:
        data_dir: 데이터 디렉토리

    Returns:
        파일명별 경로 딕셔너리
    """
    # soil 디렉토리는 data 바로 아래에 있음
    soil_dir = data_dir.parent / "soil"
    if not soil_dir.exists():
        raise FileNotFoundError(f"soil 디렉토리를 찾을 수 없습니다: {soil_dir}")

    files = {
        "boundary": soil_dir / "Geology_250K_Boudary.shp",
        "fault": soil_dir / "Geology_250K_Fault.shp",
        "frame": soil_dir / "Geology_250K_Frame.shp",
        "litho": soil_dir / "Geology_250K_Litho.shp",
    }

    # 파일 존재 확인
    missing_files = []
    for name, path in files.items():
        if not path.exists():
            missing_files.append(f"{name}: {path}")

    if missing_files:
        print("경고: 일부 파일을 찾을 수 없습니다:")
        for missing in missing_files:
            print(f"  - {missing}")

    return {k: v for k, v in files.items() if v.exists()}


def load_soil_layer(
    file_path: Path, encoding: str = "euc-kr"
) -> gpd.GeoDataFrame | None:
    """단일 Soil 레이어 로드

    Args:
        file_path: 파일 경로
        encoding: 파일 인코딩

    Returns:
        GeoDataFrame 또는 None
    """
    # Litho 파일은 UTF-8로 읽기
    if "Litho" in file_path.name:
        encoding = "utf-8"

    try:
        gdf = gpd.read_file(file_path, encoding=encoding)
        # CRS 설정 (EPSG:4326 - WGS84)
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)

        # NULL 또는 빈 geometry 제거
        null_geom = gdf[gdf.geometry.isnull()].shape[0]
        if null_geom > 0:
            print(f"경고: NULL geometry {null_geom}개 제거")
            gdf = gdf[~gdf.geometry.isnull()]

        empty_geom = gdf[gdf.geometry.is_empty].shape[0]
        if empty_geom > 0:
            print(f"경고: 빈 geometry {empty_geom}개 제거")
            gdf = gdf[~gdf.geometry.is_empty]

        print(f"{file_path.stem} 로드 완료: {len(gdf)}개 객체")
        return gdf
    except Exception as e:
        print(f"오류: {file_path.stem} 로드 실패 - {e}")
        return None


def get_age_colors() -> dict[str, str]:
    """지질 시대별 색상 정의"""
    return {
        "중생대 백악기": "#8B4513",  # 갈색
        "신생대 제4기": "#FFD700",  # 금색
        "중생대 쥐라기": "#228B22",  # 산림녹색
        "고생대 석탄기": "#696969",  # 어두운 회색
        "고생대 페름기": "#8B008B",  # 어두운 자홍색
        "고생대 오르도비스기": "#FF6347",  # 토마토색
        "고생대 캄브리아기": "#9370DB",  # 중간 보라
        "고생대 실루리아기": "#DC143C",  # 진홍색
        "고생대 데본기": "#B22222",  # 적갈색
        "선캄브리아시대": "#2F4F4F",  # 어두운 슬레이트 회색
        "신생대 신진기~고진기": "#FFA500",  # 오렌지
        "중생대 트라이아스기": "#32CD32",  # 라임 그린
        "시대 미상": "#C0C0C0",  # 은색
        "미분류": "#808080",  # 회색
    }


def get_type_styles() -> dict[str, dict[str, dict[str, Any]]]:
    """타입별 선 스타일 정의"""
    return {
        "boundary": {
            "지질경계": {"color": "#000000", "linestyle": "-", "linewidth": 1.0},
            "추정지질경계": {"color": "#666666", "linestyle": "--", "linewidth": 1.0},
            "점이지질경계": {"color": "#999999", "linestyle": ":", "linewidth": 1.0},
        },
        "fault": {
            "단층": {"color": "#FF0000", "linestyle": "-", "linewidth": 2.0},
            "추정단층": {"color": "#CC0000", "linestyle": "--", "linewidth": 1.5},
            "드러스트": {"color": "#990000", "linestyle": "-.", "linewidth": 2.5},
        },
    }


def analyze_layer_data(gdf: gpd.GeoDataFrame, file_type: str) -> tuple[str | None, str]:
    """레이어 데이터 분석 및 그룹화 필드 결정

    Args:
        gdf: GeoDataFrame
        file_type: 파일 타입

    Returns:
        (그룹화 필드, 기본 그룹화 필드)
    """
    default_groups = {
        "boundary": "TYPE",
        "fault": "TYPE",
        "frame": "MAPNAME",
        "litho": "age",
    }

    default_group = default_groups.get(file_type)

    # 그룹화 필드 확인
    if default_group and default_group in gdf.columns:
        unique_values = gdf[default_group].unique()
        print(f"{default_group}별 {len(unique_values)}개 그룹 발견")
        return default_group, default_group

    return None, default_group or ""


def plot_frame_background(ax: Any, frame_gdf: gpd.GeoDataFrame) -> None:
    """Frame 배경 그리기

    Args:
        ax: matplotlib axes
        frame_gdf: Frame GeoDataFrame
    """
    frame_gdf.plot(
        ax=ax,
        facecolor="lightgray",
        edgecolor="darkgray",
        linewidth=0.5,
        alpha=0.3,
        zorder=0,
    )


def plot_layer_by_group(
    ax: Any, gdf: gpd.GeoDataFrame, group_by: str, file_type: str
) -> list[Any]:
    """그룹별로 레이어 시각화

    Args:
        ax: matplotlib axes
        gdf: GeoDataFrame
        group_by: 그룹화 필드
        file_type: 파일 타입

    Returns:
        범례 요소 리스트
    """
    legend_elements: list[Any] = []
    unique_values = gdf[group_by].unique()

    # 지오메트리 타입 확인
    geom_types = gdf.geometry.geom_type.unique()
    is_line = any(t in ["LineString", "MultiLineString"] for t in geom_types)
    is_polygon = any(t in ["Polygon", "MultiPolygon"] for t in geom_types)

    if file_type in ["boundary", "fault"] and group_by == "TYPE":
        # 선 타입별 스타일 적용
        styles = get_type_styles()[file_type]
        for value in unique_values:
            if value in styles:
                style = styles[value]
                group_gdf = gdf[gdf[group_by] == value]
                group_gdf.plot(ax=ax, **style, zorder=2)
                legend_elements.append(
                    Line2D(
                        [0],
                        [0],
                        color=style["color"],
                        linestyle=style["linestyle"],
                        linewidth=style["linewidth"],
                        label=value,
                    )
                )

    elif file_type == "litho" and group_by == "age":
        # 지질시대별 색상 적용
        age_colors = get_age_colors()
        for value in unique_values:
            color = age_colors.get(value, "#808080")
            group_gdf = gdf[gdf[group_by] == value]
            group_gdf.plot(
                ax=ax,
                facecolor=color,
                edgecolor="black",
                linewidth=0.5,
                alpha=0.7,
                zorder=1,
            )
            legend_elements.append(
                Patch(facecolor=color, edgecolor="black", label=value)
            )

    else:
        # 일반적인 색상 구분
        cmap = plt.cm.get_cmap("tab20")
        colors = [cmap(i) for i in range(len(unique_values))]

        # lithoidx의 경우 상위 15개만 범례에 표시
        max_legend_items = 15 if group_by == "lithoidx" else len(unique_values)
        top_values = determine_top_values(
            gdf, group_by, unique_values, max_legend_items, is_polygon
        )

        for i, value in enumerate(unique_values):
            group_gdf = gdf[gdf[group_by] == value]
            color = mcolors.to_hex(colors[i % 20])

            if is_polygon:
                group_gdf.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor="black",
                    linewidth=0.5,
                    alpha=0.7,
                    zorder=1,
                )
                if value in top_values:
                    legend_elements.append(
                        Patch(facecolor=color, edgecolor="black", label=str(value))
                    )
            elif is_line:
                group_gdf.plot(ax=ax, color=color, linewidth=1.5, alpha=0.8, zorder=2)
                if value in top_values:
                    legend_elements.append(
                        Line2D([0], [0], color=color, linewidth=1.5, label=str(value))
                    )

    return legend_elements


def determine_top_values(
    gdf: gpd.GeoDataFrame,
    group_by: str,
    unique_values: list[Any],
    max_items: int,
    is_polygon: bool,
) -> list[Any]:
    """범례에 표시할 상위 값들 결정

    Args:
        gdf: GeoDataFrame
        group_by: 그룹화 필드
        unique_values: 고유 값 리스트
        max_items: 최대 항목 수
        is_polygon: 폴리곤 여부

    Returns:
        상위 값 리스트
    """
    if group_by == "lithoidx" and is_polygon and len(unique_values) > max_items:
        # 각 그룹의 객체 수 계산
        group_counts = {}
        for value in unique_values:
            group_counts[value] = len(gdf[gdf[group_by] == value])

        # 객체 수 기준으로 정렬
        sorted_values = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
        return [v[0] for v in sorted_values[:max_items]]

    return list(unique_values)


def plot_frame_labels(ax: Any, frame_gdf: gpd.GeoDataFrame) -> None:
    """Frame의 mapname 라벨 표시

    Args:
        ax: matplotlib axes
        frame_gdf: Frame GeoDataFrame
    """
    for _, row in frame_gdf.iterrows():
        if "MAPNAME" in row and row.geometry is not None:
            centroid = row.geometry.centroid
            ax.text(
                centroid.x,
                centroid.y,
                row["MAPNAME"],
                fontsize=10,
                ha="center",
                va="center",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="black",
                    alpha=0.7,
                ),
            )


def plot_integrated_layers(
    ax: Any, soil_files: dict[str, Path], layers: list[str], base_dir: Path
) -> list[Any]:
    """통합 레이어 시각화

    Args:
        ax: matplotlib axes
        soil_files: 파일 경로 딕셔너리
        layers: 표시할 레이어 리스트
        base_dir: 기본 데이터 디렉토리

    Returns:
        범례 요소 리스트
    """
    legend_elements: list[Any] = []

    # 1. Frame 레이어 (배경)
    if "frame" in layers and "frame" in soil_files:
        frame_gdf = load_soil_layer(soil_files["frame"])
        if frame_gdf is not None:
            frame_gdf.plot(
                ax=ax,
                facecolor="none",
                edgecolor="black",
                linewidth=2.0,
                alpha=1.0,
                zorder=0,
            )
            plot_frame_labels(ax, frame_gdf)

    # 2. Litho 레이어 (암상)
    if "litho" in layers and "litho" in soil_files:
        # load_soil_layer 사용하여 순환 참조 방지
        litho_gdf = load_soil_layer(soil_files["litho"])
        if litho_gdf is not None:
            # CRS 변환 (EPSG:5179 -> EPSG:4326)
            if litho_gdf.crs != "EPSG:4326":
                litho_gdf = litho_gdf.to_crs("EPSG:4326")

            # age별로 색상 구분
            age_colors = get_age_colors()
            unique_ages = litho_gdf["age"].unique()

            for age in unique_ages[:14]:  # 최대 14개 시대만 표시
                color = age_colors.get(age, "#808080")
                age_gdf = litho_gdf[litho_gdf["age"] == age]
                age_gdf.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor="none",
                    alpha=0.6,
                    zorder=1,
                )
                legend_elements.append(
                    Patch(facecolor=color, edgecolor="black", label=age, alpha=0.6)
                )

    # 3. Boundary 레이어 (경계선)
    if "boundary" in layers and "boundary" in soil_files:
        boundary_gdf = load_soil_layer(soil_files["boundary"])
        if boundary_gdf is not None:
            styles = get_type_styles()["boundary"]
            for type_name, style in styles.items():
                type_gdf = boundary_gdf[boundary_gdf["TYPE"] == type_name]
                if len(type_gdf) > 0:
                    type_gdf.plot(ax=ax, **style, zorder=2)

    # 4. Fault 레이어 (단층)
    if "fault" in layers and "fault" in soil_files:
        fault_gdf = load_soil_layer(soil_files["fault"])
        if fault_gdf is not None:
            styles = get_type_styles()["fault"]
            for type_name, style in styles.items():
                type_gdf = fault_gdf[fault_gdf["TYPE"] == type_name]
                if len(type_gdf) > 0:
                    type_gdf.plot(ax=ax, **style, zorder=3)
                    legend_elements.append(
                        Line2D(
                            [0],
                            [0],
                            color=style["color"],
                            linestyle=style["linestyle"],
                            linewidth=style["linewidth"],
                            label=f"단층: {type_name}",
                        )
                    )

    return legend_elements
