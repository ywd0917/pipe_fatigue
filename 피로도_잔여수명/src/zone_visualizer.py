"""
Zone 데이터 시각화를 위한 특화 모듈
Zone shapefile 로딩, 처리, 시각화 관련 비즈니스 로직
"""

import re
from pathlib import Path
from typing import Any

import geopandas as gpd
from matplotlib.patches import Patch

from src.common.config import REGION_CODE_PATTERN


def get_all_zone_files(data_dir: Path) -> dict[str, dict[str, Path]]:
    """모든 export 디렉토리에서 Zone shapefile 경로 찾기

    Returns:
        {directory_version: {zone_type: file_path}}
    """
    all_zone_files = {}
    zone_types = ["LRGZ", "MDLZ", "SCDZ", "SMLZ"]

    # 모든 export 디렉토리 찾기
    export_dirs = sorted(
        [
            d
            for d in data_dir.iterdir()
            if d.is_dir() and d.name.startswith("export_shp_")
        ]
    )

    if not export_dirs:
        raise FileNotFoundError("export_shp_ 디렉토리를 찾을 수 없습니다.")

    for export_dir in export_dirs:
        # 디렉토리명에서 버전 추출
        match = re.search(REGION_CODE_PATTERN, export_dir.name)
        dir_version = match.group(1) if match else "unknown"
        zone_files = {}

        for zone_type in zone_types:
            shp_file = export_dir / f"WEA_{zone_type}_AS.shp"
            if shp_file.exists():
                zone_files[zone_type.lower()] = shp_file

        if zone_files:
            all_zone_files[dir_version] = zone_files
            print(
                f"데이터 디렉토리 발견: {export_dir.name} ({len(zone_files)}개 zone 파일)"
            )

    return all_zone_files


def get_zone_metadata() -> dict[str, tuple[str, str, str]]:
    """Zone별 메타데이터 정의 (색상, 한글명, 영문명)"""
    return {
        "lrgz": ("#FF0000", "대블록 (LRGZ)", "Large Zone (LRGZ)"),
        "mdlz": ("#0000FF", "중블록 (MDLZ)", "Middle Zone (MDLZ)"),
        "scdz": ("#00AA00", "2차구역 (SCDZ)", "Secondary Zone (SCDZ)"),
        "smlz": ("#FF8800", "소블록 (SMLZ)", "Small Zone (SMLZ)"),
    }


def load_zone_data(
    zone_files: dict[str, Path], selected_zone: str | None = None
) -> dict[str, gpd.GeoDataFrame]:
    """Zone 데이터 로드

    Args:
        zone_files: Zone 파일 경로 딕셔너리
        selected_zone: 선택된 특정 Zone (None이면 모두 로드)

    Returns:
        Zone 데이터 딕셔너리
    """
    zone_data = {}
    zones_to_load = [selected_zone] if selected_zone else zone_files.keys()

    for zone_type in zones_to_load:
        if zone_type in zone_files:
            try:
                gdf = gpd.read_file(zone_files[zone_type], encoding="euc-kr")
                # CRS 설정
                if gdf.crs is None:
                    gdf.set_crs("EPSG:5179", inplace=True)
                zone_data[zone_type] = gdf
                print(f"{zone_type.upper()} 로드 완료: {len(gdf)}개 객체")
            except Exception as e:
                print(f"오류: {zone_type.upper()} 로드 실패 - {e}")

    return zone_data


def get_zone_label_column(zone_type: str) -> str | None:
    """Zone 타입별 라벨 컬럼명 반환"""
    label_columns = {
        "lrgz": "LGZ_NUM",  # 대블록 번호
        "mdlz": "MDZ_NUM",  # 중블록 번호
        "scdz": "SCD_NUM",  # 2차구역 번호
        "smlz": "SMZ_LBL",  # 소블록 라벨
    }
    return label_columns.get(zone_type)


def create_zone_legend_elements(
    zone_data: dict[str, gpd.GeoDataFrame],
    zone_metadata: dict[str, tuple[str, str, str]],
    use_english: bool = True,
) -> list[Patch]:
    """Zone 범례 요소 생성

    Args:
        zone_data: Zone 데이터
        zone_metadata: Zone 메타데이터
        use_english: 영문 라벨 사용 여부

    Returns:
        범례 요소 리스트
    """
    legend_elements = []
    zone_order = ["lrgz", "mdlz", "scdz", "smlz"]

    for zone_type in zone_order:
        if zone_type in zone_data:
            color, korean_label, english_label = zone_metadata[zone_type]
            label = english_label if use_english else korean_label

            legend_elements.append(
                Patch(facecolor="none", edgecolor=color, linewidth=1.5, label=label)
            )

    return legend_elements


def plot_zone_labels(
    ax: Any, gdf: gpd.GeoDataFrame, zone_type: str, color: str
) -> None:
    """Zone 라벨 표시

    Args:
        ax: matplotlib axes
        gdf: Zone GeoDataFrame
        zone_type: Zone 타입
        color: Zone 색상
    """
    label_col = get_zone_label_column(zone_type)

    if label_col and label_col in gdf.columns:
        for _, row in gdf.iterrows():
            if row[label_col] is not None:
                # 폴리곤의 중심점 계산
                centroid = row.geometry.centroid

                # 텍스트 표시
                ax.text(
                    centroid.x,
                    centroid.y,
                    str(row[label_col]),
                    fontsize=10,
                    ha="center",
                    va="center",
                    bbox=dict(
                        boxstyle="round,pad=0.3",
                        facecolor="white",
                        edgecolor=color,
                        alpha=0.8,
                    ),
                )


def calculate_bounds_with_margin(
    gdfs: list[gpd.GeoDataFrame], margin_ratio: float = 0.05
) -> tuple[float, float, float, float]:
    """여러 GeoDataFrame의 전체 경계 계산 (여백 포함)

    Args:
        gdfs: GeoDataFrame 리스트
        margin_ratio: 여백 비율

    Returns:
        (minx, miny, maxx, maxy) with margin
    """
    all_bounds = []

    for gdf in gdfs:
        if len(gdf) > 0:
            bounds = gdf.total_bounds
            all_bounds.append(bounds)

    if not all_bounds:
        return (0, 0, 1, 1)

    minx = min(b[0] for b in all_bounds)
    miny = min(b[1] for b in all_bounds)
    maxx = max(b[2] for b in all_bounds)
    maxy = max(b[3] for b in all_bounds)

    # 여백 추가
    x_margin = (maxx - minx) * margin_ratio
    y_margin = (maxy - miny) * margin_ratio

    return (minx - x_margin, miny - y_margin, maxx + x_margin, maxy + y_margin)
