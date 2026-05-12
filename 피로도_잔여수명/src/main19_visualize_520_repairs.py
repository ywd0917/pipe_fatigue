"""
520 지역의 복구 공사 데이터와 주변 시설물(인프라)의 상관관계를 분석
- main13_crop_520에서 생성한 520 지역 CSV 파일 사용
- 파일타입 컬럼으로 지상누수, 지하누수, 긴급공사, 관리대장 구분
- 위치 데이터를 지도에 시각화
"""

import argparse
import warnings
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from shapely.geometry import Point

from src.common import korean_font_utils
from src.common.config import (
    DATA_DIR,
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RESULTS_DIR,
)
from src.common.visualization_utils import setup_plot_style

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 시각화 상수
DPI_HIGH = 300
FIGURE_WIDTH = 32
FIGURE_HEIGHT = 24

# 수리내역 점 설정
POINT_SIZE = 50  # 점 크기 축소
POINT_ALPHA = 0.3  # 수리내역 점 투명도 (0.7 -> 0.3으로 변경)
EDGE_WIDTH = 0.5
EDGE_COLOR = "black"  # 점 테두리 색상
EDGE_ALPHA = 0.3  # 점 테두리 투명도

# 파이프 라인 상수
PIPE_LM_WIDTH = 1.5  # main17과 동일
PIPE_LM_COLOR = "gray"  # PIPE_LM 색상
SPLY_LS_WIDTH = 0.5  # main17과 동일
SPLY_LS_COLOR = "red"  # SPLY_LS 색상
PIPE_ALPHA = 0.7  # 투명도 증가

# 경계선 상수
BOUNDARY_WIDTH = 3  # 경계선 두께
BOUNDARY_COLOR = "black"  # 경계선 색상 (검은색으로 변경)
BOUNDARY_ALPHA = 0.7  # 경계선 투명도
BOUNDARY_LINESTYLE = "--"  # 경계선 스타일 (점선)
BOUNDARY_FILL_COLOR = "yellow"  # 경계 내부 채우기 색상
BOUNDARY_FILL_ALPHA = 0.1  # 경계 내부 채우기 투명도

# 밸브와 소화전 상수
VALVE_SIZE = POINT_SIZE * 2  # 복구 작업 점보다 2배 크게
FIRE_SIZE = POINT_SIZE * 2  # 복구 작업 점보다 2배 크게
VALVE_COLOR = "red"  # 밸브 색상
FIRE_COLOR = "red"  # 소화전 색상
VALVE_ALPHA = 0.4  # 밸브 투명도 (0.8 -> 0.4로 변경)
FIRE_ALPHA = 0.4  # 소화전 투명도 (0.8 -> 0.4로 변경)
VALVE_EDGE_COLOR = "darkred"  # 밸브 테두리 색상
FIRE_EDGE_COLOR = "darkred"  # 소화전 테두리 색상
VALVE_EDGE_WIDTH = 0.5  # 밸브 테두리 두께
FIRE_EDGE_WIDTH = 0.5  # 소화전 테두리 두께

# 복구 작업 타입별 색상 정의
REPAIR_COLORS = {
    "지상누수": "#FF1493",  # 진한 핑크
    "지하누수": "#0000FF",  # 파란색
    "긴급공사": "#8B4513",  # 갈색
    "관리대장": "#008000",  # 녹색
}

# 520 지역 CSV 파일 경로 (main13_crop_520에서 생성)
UNIFIED_CSV_PATH = "main13_crop_520/누수공사_통합_520_위치추가.csv"

# 520 지역 코드
ZONE_520 = "520"

# 상관관계 분석 상수
DEFAULT_RADIUS_METERS = 20.0  # 기본 인프라 검색 반경 (미터)
CLUSTER_DISTANCE_METERS = 10.0  # 클러스터링 거리 임계값 (미터)
MIN_REPAIRS_FOR_FREQUENT = 4  # 빈번한 재작업 판단 기준


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """두 지점 간의 거리를 Haversine 공식으로 계산 (미터 단위)

    Args:
        lat1, lon1: 첫 번째 지점의 위도, 경도
        lat2, lon2: 두 번째 지점의 위도, 경도

    Returns:
        두 지점 간 거리 (미터)
    """
    R = 6371000  # 지구 반지름 (미터)
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


def setup_korean_font() -> None:
    """한글 폰트 설정"""
    font_result = korean_font_utils.setup_korean_font()
    if font_result:
        print(f"한글 폰트 설정: {font_result}")
    else:
        print("경고: 한글 폰트를 찾을 수 없습니다.")


def load_520_csv_files(results_dir: Path, verbose: bool = True) -> pd.DataFrame | None:
    """통합 CSV 파일에서 520 지역 데이터 로드

    Args:
        results_dir: 결과 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        520 지역 데이터 DataFrame 또는 None
    """
    print("\n=== 520 데이터 로드 중 ===")

    # 통합 CSV 파일 경로
    csv_path = results_dir / UNIFIED_CSV_PATH

    if not csv_path.exists():
        if verbose:
            print(f"  오류: 520 지역 CSV 파일을 찾을 수 없습니다: {csv_path}")
            print(
                "  먼저 main13_crop_520 스크립트를 실행하여 520 지역 파일을 생성하세요."
            )
        return None

    try:
        # 통합 CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        if verbose:
            print(f"  통합 데이터 로드 완료: 총 {len(df)}개 행")
            print(f"  컬럼: {list(df.columns)}")

        # 필수 컬럼 확인
        required_columns = ["위도", "경도", "파일타입"]
        for col in required_columns:
            if col not in df.columns:
                if verbose:
                    print(f"  오류: 필수 컬럼 '{col}'이(가) 없습니다.")
                return None

        # 위도/경도가 유효한 데이터만 필터링
        df_valid = df.dropna(subset=["위도", "경도"]).copy()
        df_valid = df_valid[(df_valid["위도"] > 0) & (df_valid["경도"] > 0)]

        # 520 지역 데이터만 필터링 (주소 또는 다른 조건으로 필터링)
        # 주소 컬럼이 있다면 520 지역 필터링 가능
        # 현재는 전체 데이터를 사용 (520 지역 필터링 조건 추가 필요)

        # 복구타입 컬럼 추가 (파일타입을 복구타입으로 매핑)
        df_valid["복구타입"] = df_valid["파일타입"]

        # 날짜 정보 파싱 (작업일시 컬럼 사용)
        if "작업일시" in df_valid.columns:
            # pd.to_datetime으로 파싱 시도
            df_valid["작업일시_parsed"] = pd.to_datetime(
                df_valid["작업일시"], errors="coerce"
            )

        # 인덱스 추가
        df_valid["repair_id"] = range(len(df_valid))

        if verbose:
            print(f"  유효한 위치 데이터: {len(df_valid):,}건 (전체 {len(df):,}건 중)")
            # 타입별 통계
            print("\n  파일타입별 통계:")
            for file_type in df_valid["파일타입"].unique():
                count = len(df_valid[df_valid["파일타입"] == file_type])
                print(f"    - {file_type}: {count:,}건")

            # 샘플 데이터 출력
            if len(df_valid) > 0:
                sample = df_valid.iloc[0]
                print("\n  샘플 데이터:")
                print(f"    위도: {sample['위도']:.6f}, 경도: {sample['경도']:.6f}")
                if "주소" in sample:
                    print(f"    주소: {sample['주소']}")
                print(f"    파일타입: {sample['파일타입']}")

        print(f"\n총 {len(df_valid):,}건의 520 데이터 로드 완료")
        return df_valid

    except Exception as e:
        if verbose:
            print(f"  오류: CSV 파일 로드 실패 - {e}")
        return None


def load_background_data(data_dir: Path, verbose: bool = True) -> dict[str, Any]:
    """520 지역의 배경 데이터 로드 (파이프, 행정구역 등)

    Args:
        data_dir: 데이터 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        배경 데이터 딕셔너리
    """
    background_data = {}

    # 520 지역 데이터 경로
    shp_dir_520 = data_dir / "raw" / "export_shp_20250704(0520)"

    if verbose:
        print("\n=== 배경 데이터 로드 중 ===")

    # 파이프 라인 데이터 로드
    try:
        # PIPE_LM 로드
        pipe_lm_path = shp_dir_520 / "V_WTL_PIPE_LM.shp"
        if pipe_lm_path.exists():
            pipe_lm = gpd.read_file(pipe_lm_path)
            # CRS가 없으면 EPSG:5179로 설정 (대부분의 한국 데이터는 5179 사용)
            if pipe_lm.crs is None:
                pipe_lm = pipe_lm.set_crs("EPSG:5179")
            elif pipe_lm.crs != "EPSG:5179":
                pipe_lm = pipe_lm.to_crs("EPSG:5179")
            background_data["pipe_lm"] = pipe_lm
            if verbose:
                print(f"  - PIPE_LM 로드: {len(pipe_lm)}개 파이프")

        # SPLY_LS 로드
        sply_ls_path = shp_dir_520 / "V_WTL_SPLY_LS.shp"
        if sply_ls_path.exists():
            sply_ls = gpd.read_file(sply_ls_path)
            if sply_ls.crs is None:
                sply_ls = sply_ls.set_crs("EPSG:5179")
            elif sply_ls.crs != "EPSG:5179":
                sply_ls = sply_ls.to_crs("EPSG:5179")
            background_data["sply_ls"] = sply_ls
            if verbose:
                print(f"  - SPLY_LS 로드: {len(sply_ls)}개 공급관")

    except Exception as e:
        if verbose:
            print(f"  경고: 파이프 데이터 로드 실패 - {e}")

    # 행정구역 경계 데이터 로드 (MDLZ 0520)
    try:
        mdlz_path = shp_dir_520 / "WEA_MDLZ_AS.shp"
        if mdlz_path.exists():
            # MDLZ 전체 로드 (euc-kr 인코딩)
            mdlz = gpd.read_file(mdlz_path, encoding="euc-kr")
            if mdlz.crs is None:
                mdlz = mdlz.set_crs("EPSG:5179")
            elif mdlz.crs != "EPSG:5179":
                mdlz = mdlz.to_crs("EPSG:5179")

            # 0520 구역만 필터링
            if "MDZ_NUM" in mdlz.columns:
                mdlz_520 = mdlz[mdlz["MDZ_NUM"] == "0520"]
                background_data["mdlz_520"] = mdlz_520
                if verbose:
                    print(f"  - MDLZ 0520 경계 로드: {len(mdlz_520)}개 구역")
                    if len(mdlz_520) > 0:
                        print(f"    0520 구역 범위: {mdlz_520.total_bounds}")
            else:
                if verbose:
                    print("  경고: MDZ_NUM 컬럼을 찾을 수 없습니다.")

    except Exception as e:
        if verbose:
            print(f"  경고: MDLZ 데이터 로드 실패 - {e}")

    # 밸브 데이터 로드 (WTL_VALV_PS)
    try:
        valve_path = shp_dir_520 / "WTL_VALV_PS.shp"
        if valve_path.exists():
            valves = gpd.read_file(valve_path)
            if valves.crs is None:
                valves = valves.set_crs("EPSG:5179")
            elif valves.crs != "EPSG:5179":
                valves = valves.to_crs("EPSG:5179")
            background_data["valves"] = valves
            if verbose:
                print(f"  - 밸브 로드: {len(valves)}개")

    except Exception as e:
        if verbose:
            print(f"  경고: 밸브 데이터 로드 실패 - {e}")

    # 소화전 데이터 로드 (WTL_FIRE_PS)
    try:
        fire_path = shp_dir_520 / "WTL_FIRE_PS.shp"
        if fire_path.exists():
            fires = gpd.read_file(fire_path)
            if fires.crs is None:
                fires = fires.set_crs("EPSG:5179")
            elif fires.crs != "EPSG:5179":
                fires = fires.to_crs("EPSG:5179")
            background_data["fires"] = fires
            if verbose:
                print(f"  - 소화전 로드: {len(fires)}개")

    except Exception as e:
        if verbose:
            print(f"  경고: 소화전 데이터 로드 실패 - {e}")

    return background_data


def visualize_520_repairs_with_background(
    repair_df: pd.DataFrame,
    title: str,
    output_path: Path,
    show_grid: bool = True,
    show_background: bool = True,
    show_buffers: bool = True,  # 버퍼 표시 여부 추가
    radius: float = DEFAULT_RADIUS_METERS,  # 버퍼 반경 (미터)
    verbose: bool = True,
) -> None:
    """520 복구 작업 데이터 시각화 (배경 지도 포함)

    Args:
        repair_df: 복구 작업 DataFrame
        title: 그래프 제목
        output_path: 출력 파일 경로
        show_grid: 그리드 표시 여부
        show_background: 배경 지도 표시 여부
        show_buffers: 20m 버퍼 표시 여부
        verbose: 상세 숡보 출력 여부
    """
    print(f"\n시각화 시작: {title}")

    # 플롯 설정
    fig, ax = setup_plot_style(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # 배경 데이터 로드 및 그리기
    if show_background:
        background_data = load_background_data(DATA_DIR, verbose=verbose)

        # MDLZ 0520 경계 그리기 (더 진하고 굵게)
        if "mdlz_520" in background_data:
            background_data["mdlz_520"].boundary.plot(
                ax=ax,
                color=BOUNDARY_COLOR,  # 상수 사용
                linewidth=BOUNDARY_WIDTH,  # 3
                alpha=BOUNDARY_ALPHA,  # 0.7
                linestyle=BOUNDARY_LINESTYLE,  # 점선
                zorder=1,
            )
            # 영역도 약간 투명하게 채우기
            background_data["mdlz_520"].plot(
                ax=ax,
                facecolor=BOUNDARY_FILL_COLOR,  # 상수 사용
                alpha=BOUNDARY_FILL_ALPHA,  # 상수 사용
                edgecolor="none",
                zorder=0,
            )

        # 파이프 라인 그리기 (LineCollection 방식 사용)
        from matplotlib.collections import LineCollection

        # PIPE_LM 그리기 (굵고 진한 회색)
        if "pipe_lm" in background_data:
            pipe_lm_gdf = background_data["pipe_lm"]
            lines_lm = []
            for _, row in pipe_lm_gdf.iterrows():
                if row.geometry and row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    if len(coords) >= 2:
                        lines_lm.append(coords)

            if lines_lm:
                lc_lm = LineCollection(
                    lines_lm,
                    colors=PIPE_LM_COLOR,  # 상수 사용
                    linewidths=PIPE_LM_WIDTH,  # 1.5
                    alpha=PIPE_ALPHA,  # 0.7
                    zorder=2,
                )
                ax.add_collection(lc_lm)

        # SPLY_LS 그리기 (얇고 빨간색으로 변경)
        if "sply_ls" in background_data:
            sply_ls_gdf = background_data["sply_ls"]
            lines_ls = []
            for _, row in sply_ls_gdf.iterrows():
                if row.geometry and row.geometry.geom_type == "LineString":
                    coords = list(row.geometry.coords)
                    if len(coords) >= 2:
                        lines_ls.append(coords)

            if lines_ls:
                lc_ls = LineCollection(
                    lines_ls,
                    colors=SPLY_LS_COLOR,  # 상수 사용
                    linewidths=SPLY_LS_WIDTH,  # 0.5
                    alpha=PIPE_ALPHA,  # 0.7
                    zorder=3,
                )
                ax.add_collection(lc_ls)

        # 밸브 그리기 (빨간색 사각형)
        if "valves" in background_data:
            valves_gdf = background_data["valves"]
            if len(valves_gdf) > 0:
                # Point 좌표 추출
                x_valves = [geom.x for geom in valves_gdf.geometry if geom is not None]
                y_valves = [geom.y for geom in valves_gdf.geometry if geom is not None]

                # 사각형 마커로 표시
                ax.scatter(
                    x_valves,
                    y_valves,
                    c=VALVE_COLOR,
                    s=VALVE_SIZE,
                    alpha=VALVE_ALPHA,
                    marker="s",  # 사각형
                    edgecolor=VALVE_EDGE_COLOR,
                    linewidth=VALVE_EDGE_WIDTH,
                    zorder=8,
                    label=f"밸브 ({len(valves_gdf)}개)",
                )
                if verbose:
                    print(f"  - 밸브: {len(x_valves)}개 표시")

        # 소화전 그리기 (빨간색 삼각형)
        if "fires" in background_data:
            fires_gdf = background_data["fires"]
            if len(fires_gdf) > 0:
                # Point 좌표 추출
                x_fires = [geom.x for geom in fires_gdf.geometry if geom is not None]
                y_fires = [geom.y for geom in fires_gdf.geometry if geom is not None]

                # 삼각형 마커로 표시
                ax.scatter(
                    x_fires,
                    y_fires,
                    c=FIRE_COLOR,
                    s=FIRE_SIZE,
                    alpha=FIRE_ALPHA,
                    marker="^",  # 삼각형
                    edgecolor=FIRE_EDGE_COLOR,
                    linewidth=FIRE_EDGE_WIDTH,
                    zorder=9,
                    label=f"소화전 ({len(fires_gdf)}개)",
                )
                if verbose:
                    print(f"  - 소화전: {len(x_fires)}개 표시")

    # WGS84 좌표를 Point 객체로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(repair_df["경도"], repair_df["위도"], strict=False)
    ]
    repair_gdf = gpd.GeoDataFrame(repair_df, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환 (한국 표준 좌표계)
    repair_gdf = repair_gdf.to_crs("EPSG:5179")

    # 복구 타입별로 처리
    repair_type_counts = {}

    if show_buffers:
        # 지정된 반경의 버퍼로 표시 (점 대신)
        print(f"  {radius:.0f}m 반경 버퍼로 공사 위치 표시 중...")

        for repair_type, color in REPAIR_COLORS.items():
            subset = repair_gdf[repair_gdf["복구타입"] == repair_type]
            if len(subset) > 0:
                repair_type_counts[repair_type] = len(subset)

                # 지정된 반경의 버퍼 생성
                buffers = subset.geometry.buffer(radius)
                buffer_gdf = gpd.GeoDataFrame(geometry=buffers, crs="EPSG:5179")

                # 버퍼 그리기 (타입별 색상)
                buffer_gdf.plot(
                    ax=ax,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.2,  # 투명하게
                    linewidth=0.5,
                    zorder=10,  # 배경보다 위에 표시
                    label=f"{repair_type} ({len(subset):,}건)",
                )

                # 중심점도 작게 표시 (선택사항)
                x = [geom.x for geom in subset.geometry]
                y = [geom.y for geom in subset.geometry]
                ax.scatter(
                    x,
                    y,
                    c=color,
                    s=5,  # 매우 작은 점
                    alpha=0.8,
                    zorder=11,
                )

                if verbose:
                    print(f"  - {repair_type}: {len(subset):,}개 버퍼 표시")
    else:
        # 기존 점 방식으로 표시
        for repair_type, color in REPAIR_COLORS.items():
            subset = repair_gdf[repair_gdf["복구타입"] == repair_type]
            if len(subset) > 0:
                repair_type_counts[repair_type] = len(subset)

                # 좌표 추출
                x = [geom.x for geom in subset.geometry]
                y = [geom.y for geom in subset.geometry]

                # 산점도 그리기
                ax.scatter(
                    x,
                    y,
                    c=color,
                    s=POINT_SIZE,
                    alpha=POINT_ALPHA,
                    edgecolor=EDGE_COLOR,
                    linewidth=EDGE_WIDTH,
                    label=f"{repair_type} ({len(subset):,}건)",
                    zorder=10,  # 배경보다 위에 표시
                )

                if verbose:
                    print(f"  - {repair_type}: {len(subset):,}개 점 표시")

    # 전체 범위 설정 (여백 추가)
    bounds = repair_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05

    ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
    ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)

    # 범례 생성
    from matplotlib.lines import Line2D

    legend_elements: list[mpatches.Patch | Line2D] = []

    # 배경 데이터 범례 (있는 경우)
    if show_background:
        legend_elements.append(mpatches.Patch(color="white", label="[배경 지도]"))
        if "mdlz_520" in background_data:
            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=BOUNDARY_COLOR,
                    linewidth=2,
                    linestyle=BOUNDARY_LINESTYLE,
                    alpha=BOUNDARY_ALPHA,
                    label="MDLZ 0520 경계",
                )
            )
            legend_elements.append(
                mpatches.Patch(
                    color=BOUNDARY_FILL_COLOR,
                    alpha=BOUNDARY_FILL_ALPHA,
                    label="MDLZ 0520 영역",
                )
            )
        if "pipe_lm" in background_data:
            from matplotlib.lines import Line2D

            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=PIPE_LM_COLOR,
                    linewidth=2,
                    alpha=PIPE_ALPHA,
                    label=f"파이프 라인(LM) - {len(background_data['pipe_lm'])}개",
                )
            )
        if "sply_ls" in background_data:
            from matplotlib.lines import Line2D

            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    color=SPLY_LS_COLOR,
                    linewidth=1,
                    alpha=PIPE_ALPHA,
                    label=f"공급관(LS) - {len(background_data['sply_ls'])}개",
                )
            )
        if "valves" in background_data:
            from matplotlib.lines import Line2D

            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    marker="s",
                    color="w",
                    markerfacecolor=VALVE_COLOR,
                    markersize=8,
                    alpha=VALVE_ALPHA,
                    label=f"밸브 - {len(background_data['valves'])}개",
                )
            )
        if "fires" in background_data:
            from matplotlib.lines import Line2D

            legend_elements.append(
                Line2D(
                    [0],
                    [0],
                    marker="^",
                    color="w",
                    markerfacecolor=FIRE_COLOR,
                    markersize=8,
                    alpha=FIRE_ALPHA,
                    label=f"소화전 - {len(background_data['fires'])}개",
                )
            )
        legend_elements.append(mpatches.Patch(color="white", label=""))

    # 복구 작업 범례
    legend_elements.append(mpatches.Patch(color="white", label="[520 복구 작업]"))

    if show_buffers:
        legend_elements.append(
            mpatches.Patch(
                color="white",
                label=f"(반경 {radius:.0f}m 버퍼로 표시)",
            )
        )

    for repair_type, count in repair_type_counts.items():
        color = REPAIR_COLORS.get(repair_type, "#808080")
        if show_buffers:
            # 버퍼로 표시할 때는 사각형 패치 사용
            legend_elements.append(
                mpatches.Rectangle(
                    (0, 0),
                    1,
                    1,
                    facecolor=color,
                    edgecolor=color,
                    alpha=0.2,
                    label=f"{repair_type} ({count:,}건)",
                )
            )
        else:
            # 점으로 표시할 때는 원 사용
            legend_elements.append(
                mpatches.Circle(
                    (0, 0),
                    1,
                    facecolor=color,
                    edgecolor=EDGE_COLOR,
                    alpha=POINT_ALPHA,
                    label=f"{repair_type} ({count:,}건)",
                )
            )

    # 통계 정보 추가
    legend_elements.append(mpatches.Patch(color="white", label=""))
    legend_elements.append(mpatches.Patch(color="white", label="[통계 정보]"))
    legend_elements.append(
        mpatches.Patch(color="white", label=f"총 복구 지점: {len(repair_df):,}개")
    )

    # 날짜 범위 추가 (있는 경우)
    if "작업일시_parsed" in repair_df.columns:
        valid_dates = repair_df["작업일시_parsed"].dropna()
        if len(valid_dates) > 0:
            date_min = valid_dates.min()
            date_max = valid_dates.max()
            legend_elements.append(
                mpatches.Patch(
                    color="white",
                    label=f"기간: {date_min:%Y-%m-%d} ~ {date_max:%Y-%m-%d}",
                )
            )

    ax.legend(
        handles=legend_elements,
        loc="upper right",
        fontsize=10,
        framealpha=0.9,
        title="520 데이터 분포",
        title_fontsize=11,
    )

    # 제목 및 라벨
    ax.set_title(title, fontsize=16, fontweight="bold", pad=20)
    ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=12)
    ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=12)

    # 그리드
    if show_grid:
        ax.grid(True, alpha=0.3, linestyle="--")

    ax.set_aspect("equal")

    # 저장
    plt.tight_layout()
    plt.savefig(output_path, dpi=DPI_HIGH, bbox_inches="tight")
    plt.close()

    print(f"이미지 저장 완료: {output_path}")

    # 파일 크기 확인
    file_size = output_path.stat().st_size / (1024 * 1024)  # MB
    print(f"파일 크기: {file_size:.2f} MB")


def create_type_comparison_plots(repair_df: pd.DataFrame, output_dir: Path) -> None:
    """복구 타입별 비교 플롯 생성

    Args:
        repair_df: 복구 작업 DataFrame
        output_dir: 출력 디렉토리
    """
    print("\n=== 타입별 비교 플롯 생성 ===")

    # 플롯 설정 (4개 타입을 위한 2x2 그리드)
    fig, axes = plt.subplots(2, 2, figsize=(24, 24))

    # WGS84 좌표를 Point 객체로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(repair_df["경도"], repair_df["위도"], strict=False)
    ]
    repair_gdf = gpd.GeoDataFrame(repair_df, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환
    repair_gdf = repair_gdf.to_crs("EPSG:5179")

    # 전체 범위 계산
    bounds = repair_gdf.total_bounds
    x_margin = (bounds[2] - bounds[0]) * 0.05
    y_margin = (bounds[3] - bounds[1]) * 0.05

    # axes를 1차원으로 변환
    axes = axes.flatten()

    # 각 타입별로 플롯
    for idx, (repair_type, color) in enumerate(REPAIR_COLORS.items()):
        ax = axes[idx]

        # 배경으로 전체 데이터를 회색으로 표시
        x_all = [geom.x for geom in repair_gdf.geometry]
        y_all = [geom.y for geom in repair_gdf.geometry]
        ax.scatter(
            x_all,
            y_all,
            c="lightgray",
            s=30,
            alpha=0.3,
            zorder=1,
        )

        # 해당 타입 데이터 강조
        subset = repair_gdf[repair_gdf["복구타입"] == repair_type]
        if len(subset) > 0:
            x = [geom.x for geom in subset.geometry]
            y = [geom.y for geom in subset.geometry]

            ax.scatter(
                x,
                y,
                c=color,
                s=80,
                alpha=0.8,
                edgecolor="white",
                linewidth=0.5,
                zorder=5,
            )

        # 축 설정
        ax.set_xlim(bounds[0] - x_margin, bounds[2] + x_margin)
        ax.set_ylim(bounds[1] - y_margin, bounds[3] + y_margin)
        ax.set_aspect("equal")

        # 제목 및 통계
        count = len(subset)
        percentage = (count / len(repair_df)) * 100
        ax.set_title(
            f"{repair_type}\n{count:,}건 ({percentage:.1f}%)",
            fontsize=14,
            fontweight="bold",
        )

        ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=10)
        if idx == 0:
            ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=10)

        ax.grid(True, alpha=0.3, linestyle="--")

    # 전체 제목
    fig.suptitle(
        f"520 데이터 복구 작업 타입별 분포 (총 {len(repair_df):,}건)",
        fontsize=16,
        fontweight="bold",
        y=1.02,
    )

    # 저장
    plt.tight_layout()
    output_path = output_dir / "520_repairs_type_comparison.png"
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"타입별 비교 플롯 저장: {output_path}")


def create_density_heatmap(repair_df: pd.DataFrame, output_dir: Path) -> None:
    """복구 작업 밀도 히트맵 생성

    Args:
        repair_df: 복구 작업 DataFrame
        output_dir: 출력 디렉토리
    """
    print("\n=== 밀도 히트맵 생성 ===")

    # WGS84 좌표를 Point 객체로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(repair_df["경도"], repair_df["위도"], strict=False)
    ]
    repair_gdf = gpd.GeoDataFrame(repair_df, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환
    repair_gdf = repair_gdf.to_crs("EPSG:5179")

    # 좌표 추출
    x = [geom.x for geom in repair_gdf.geometry]
    y = [geom.y for geom in repair_gdf.geometry]

    # 플롯 생성
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, FIGURE_HEIGHT))

    # 2D 히스토그램 (히트맵)
    h = ax.hist2d(x, y, bins=50, cmap="YlOrRd", alpha=0.8)

    # 컬러바 추가
    cbar = plt.colorbar(h[3], ax=ax)
    cbar.set_label("복구 작업 건수", fontsize=12)

    # 제목 및 라벨
    ax.set_title(
        f"520 데이터 복구 작업 밀도 분포 (총 {len(repair_df):,}건)",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("X 좌표 (EPSG:5179)", fontsize=12)
    ax.set_ylabel("Y 좌표 (EPSG:5179)", fontsize=12)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle="--")

    # 저장
    plt.tight_layout()
    output_path = output_dir / "520_repairs_density_heatmap.png"
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"밀도 히트맵 저장: {output_path}")


def generate_statistics_report(repair_df: pd.DataFrame, output_dir: Path) -> None:
    """통계 보고서 생성

    Args:
        repair_df: 복구 작업 DataFrame
        output_dir: 출력 디렉토리
    """
    print("\n=== 통계 보고서 생성 ===")

    report = []
    report.append("=" * 60)
    report.append("520 데이터 복구 작업 통계 보고서")
    report.append("=" * 60)
    report.append("")

    # 전체 통계
    report.append("1. 전체 통계")
    report.append("-" * 40)
    report.append(f"총 복구 작업 건수: {len(repair_df):,}건")
    report.append("")

    # 타입별 통계
    report.append("2. 타입별 통계")
    report.append("-" * 40)
    for repair_type in ["지상누수", "지하누수", "긴급공사", "관리대장"]:
        subset = repair_df[repair_df["복구타입"] == repair_type]
        count = len(subset)
        percentage = (count / len(repair_df)) * 100
        report.append(f"  - {repair_type}: {count:,}건 ({percentage:.1f}%)")
    report.append("")

    # 날짜 범위 (있는 경우)
    if "작업일시_parsed" in repair_df.columns:
        valid_dates = repair_df["작업일시_parsed"].dropna()
        if len(valid_dates) > 0:
            report.append("3. 작업 기간")
            report.append("-" * 40)
            report.append(f"최초 작업일: {valid_dates.min():%Y-%m-%d}")
            report.append(f"최후 작업일: {valid_dates.max():%Y-%m-%d}")

            # 기간 계산
            days_diff = (valid_dates.max() - valid_dates.min()).days
            report.append(f"총 기간: {days_diff:,}일")
            report.append("")

    # 구군별 통계 (있는 경우)
    if "구군" in repair_df.columns:
        report.append("4. 구군별 통계")
        report.append("-" * 40)
        district_stats = repair_df["구군"].value_counts().head(10)
        for district, count in district_stats.items():
            percentage = (count / len(repair_df)) * 100
            report.append(f"  - {district}: {count:,}건 ({percentage:.1f}%)")
        report.append("")

    # 파일로 저장
    report_text = "\n".join(report)
    report_file = output_dir / "520_repairs_statistics.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"통계 보고서 저장: {report_file}")
    print("\n" + report_text)


def analyze_infrastructure_correlation(
    repair_df: pd.DataFrame,
    background_data: dict[str, Any],
    output_dir: Path,
    radius: float = DEFAULT_RADIUS_METERS,  # 검색 반경 (미터)
    verbose: bool = True,
) -> dict[str, Any]:
    """사고 위치와 지정된 반경 내 인프라 상관관계 분석

    Args:
        repair_df: 복구 작업 DataFrame
        background_data: 배경 데이터 (파이프, 밸브, 소화전)
        output_dir: 출력 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        분석 결과 딕셔너리
    """
    print(f"\n=== 인프라 상관관계 분석 시작 (반경: {radius:.0f}m) ===")

    # WGS84 좌표를 EPSG:5179로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(repair_df["경도"], repair_df["위도"], strict=False)
    ]
    repair_gdf = gpd.GeoDataFrame(repair_df, geometry=geometry, crs="EPSG:4326")
    repair_gdf = repair_gdf.to_crs("EPSG:5179")

    # 인프라 데이터 준비
    sply_ls_gdf = background_data.get("sply_ls")
    valves_gdf = background_data.get("valves")
    fires_gdf = background_data.get("fires")

    # 각 복구 위치에서 50m 반경 내 인프라 카운트
    infrastructure_counts = []

    for idx, repair in repair_gdf.iterrows():
        repair_point = repair.geometry

        # 지정된 반경의 버퍼 생성
        buffer = repair_point.buffer(radius)

        # SPLY_LS 파이프 카운트
        sply_count = 0
        if sply_ls_gdf is not None and len(sply_ls_gdf) > 0:
            # 버퍼와 교차하는 파이프 찾기
            intersects = sply_ls_gdf[sply_ls_gdf.geometry.intersects(buffer)]
            sply_count = len(intersects)

        # 밸브 카운트
        valve_count = 0
        if valves_gdf is not None and len(valves_gdf) > 0:
            # 버퍼 내 밸브 찾기
            within = valves_gdf[valves_gdf.geometry.within(buffer)]
            valve_count = len(within)

        # 소화전 카운트
        fire_count = 0
        if fires_gdf is not None and len(fires_gdf) > 0:
            # 버퍼 내 소화전 찾기
            within = fires_gdf[fires_gdf.geometry.within(buffer)]
            fire_count = len(within)

        infrastructure_counts.append(
            {
                "repair_id": repair["repair_id"],
                "복구타입": repair["복구타입"],
                "위도": repair["위도"],
                "경도": repair["경도"],
                "sply_ls_count": sply_count,
                "valve_count": valve_count,
                "fire_count": fire_count,
                "total_infra": sply_count + valve_count + fire_count,
            }
        )

        if verbose and idx % 100 == 0:
            print(
                f"  처리 중: {idx}/{len(repair_gdf)} ({idx/len(repair_gdf)*100:.1f}%)"
            )

    df_infra = pd.DataFrame(infrastructure_counts)

    # 클러스터링 (중복 재작업 위치)
    print("\n  중복 재작업 클러스터 분석 중...")
    clusters = create_repair_clusters(df_infra)

    # 통계 분석 수행
    results = perform_statistical_analysis(df_infra, clusters)

    # 시각화 생성
    create_correlation_visualizations(df_infra, clusters, results, output_dir, radius)

    # 보고서 생성
    generate_correlation_report(df_infra, clusters, results, output_dir, radius)

    # 데이터 저장
    df_infra.to_csv(
        output_dir / "520_repair_infrastructure_data.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(
        f"\n  인프라 데이터 저장: {output_dir / '520_repair_infrastructure_data.csv'}"
    )

    return results


def create_repair_clusters(df_infra: pd.DataFrame) -> pd.DataFrame:
    """재작업 위치 클러스터링 (10m 이내)

    Args:
        df_infra: 인프라 카운트가 포함된 DataFrame

    Returns:
        클러스터 정보 DataFrame
    """
    clusters = []
    visited = set()

    for idx1, row1 in df_infra.iterrows():
        i = int(idx1) if not isinstance(idx1, int) else idx1  # type: ignore[call-overload]
        if i in visited:
            continue

        cluster = [i]
        visited.add(i)

        for idx2, row2 in df_infra.iterrows():
            j = int(idx2) if not isinstance(idx2, int) else idx2  # type: ignore[call-overload]
            if j <= i or j in visited:
                continue

            dist = calculate_haversine_distance(
                row1["위도"], row1["경도"], row2["위도"], row2["경도"]
            )

            if dist <= CLUSTER_DISTANCE_METERS:
                cluster.append(j)
                visited.add(j)

        clusters.append(cluster)

    # 클러스터 정보 생성
    cluster_data = []
    for cluster_id, indices in enumerate(clusters):
        cluster_df = df_infra.iloc[list(indices)]

        cluster_data.append(
            {
                "cluster_id": cluster_id,
                "repair_count": len(indices),
                "avg_lat": cluster_df["위도"].mean(),
                "avg_lon": cluster_df["경도"].mean(),
                "avg_sply_ls": cluster_df["sply_ls_count"].mean(),
                "avg_valve": cluster_df["valve_count"].mean(),
                "avg_fire": cluster_df["fire_count"].mean(),
                "avg_total_infra": cluster_df["total_infra"].mean(),
                "max_sply_ls": cluster_df["sply_ls_count"].max(),
                "max_valve": cluster_df["valve_count"].max(),
                "max_fire": cluster_df["fire_count"].max(),
                "max_total_infra": cluster_df["total_infra"].max(),
                "is_frequent": len(indices) >= MIN_REPAIRS_FOR_FREQUENT,
            }
        )

    df_clusters = pd.DataFrame(cluster_data)
    print(f"  생성된 클러스터: {len(df_clusters)}개")
    print(
        f"  빈번한 재작업 클러스터 (≥4회): {len(df_clusters[df_clusters['is_frequent']])}개"
    )

    return df_clusters


def perform_statistical_analysis(
    df_infra: pd.DataFrame, df_clusters: pd.DataFrame
) -> dict[str, Any]:
    """통계적 상관관계 분석

    Args:
        df_infra: 인프라 카운트 DataFrame
        df_clusters: 클러스터 DataFrame

    Returns:
        분석 결과 딕셔너리
    """
    print("\n  통계 분석 수행 중...")

    results: dict[str, Any] = {}

    # 기본 통계
    results["total_repairs"] = len(df_infra)
    results["total_clusters"] = len(df_clusters)
    results["frequent_clusters"] = len(df_clusters[df_clusters["is_frequent"]])

    # 인프라 평균
    results["avg_sply_ls"] = float(df_infra["sply_ls_count"].mean())
    results["avg_valve"] = float(df_infra["valve_count"].mean())
    results["avg_fire"] = float(df_infra["fire_count"].mean())
    results["avg_total"] = float(df_infra["total_infra"].mean())

    # 클러스터 기반 상관계수 (재작업 횟수와 인프라 수)
    if len(df_clusters) > 1:
        # Pearson 상관계수
        for infra_type in ["sply_ls", "valve", "fire", "total_infra"]:
            corr_avg, p_avg = stats.pearsonr(
                df_clusters[f"avg_{infra_type}"], df_clusters["repair_count"]
            )
            corr_max, p_max = stats.pearsonr(
                df_clusters[f"max_{infra_type}"], df_clusters["repair_count"]
            )

            results[f"corr_{infra_type}_avg"] = float(corr_avg)
            results[f"p_{infra_type}_avg"] = float(p_avg)
            results[f"corr_{infra_type}_max"] = float(corr_max)
            results[f"p_{infra_type}_max"] = float(p_max)

            print(f"    {infra_type} (평균): r={corr_avg:.3f}, p={p_avg:.4f}")
            print(f"    {infra_type} (최대): r={corr_max:.3f}, p={p_max:.4f}")

    # 빈번한 재작업 vs 일반 그룹 비교
    if results["frequent_clusters"] > 0:
        frequent = df_clusters[df_clusters["is_frequent"]]
        normal = df_clusters[~df_clusters["is_frequent"]]

        if len(normal) > 0:
            for infra_type in ["sply_ls", "valve", "fire", "total_infra"]:
                # t-test
                t_stat, t_p = stats.ttest_ind(
                    frequent[f"avg_{infra_type}"], normal[f"avg_{infra_type}"]
                )

                results[f"t_test_{infra_type}"] = float(t_stat)
                results[f"t_p_{infra_type}"] = float(t_p)
                results[f"frequent_avg_{infra_type}"] = float(
                    frequent[f"avg_{infra_type}"].mean()
                )
                results[f"normal_avg_{infra_type}"] = float(
                    normal[f"avg_{infra_type}"].mean()
                )

                print(f"\n    {infra_type} 그룹 비교:")
                print(f"      빈번한: {frequent[f'avg_{infra_type}'].mean():.2f}")
                print(f"      일반: {normal[f'avg_{infra_type}'].mean():.2f}")
                print(f"      t-test: t={t_stat:.3f}, p={t_p:.4f}")

    return results


def create_correlation_visualizations(
    df_infra: pd.DataFrame,
    df_clusters: pd.DataFrame,
    results: dict[str, Any],
    output_dir: Path,
    radius: float = DEFAULT_RADIUS_METERS,
) -> None:
    """상관관계 분석 결과 시각화

    Args:
        df_infra: 인프라 카운트 DataFrame
        df_clusters: 클러스터 DataFrame
        results: 분석 결과
        output_dir: 출력 디렉토리
    """
    print("\n  시각화 생성 중...")

    # 한글 폰트 설정
    setup_korean_font()

    # 1. 산점도 매트릭스 (4개 패널)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    infra_types = [
        ("sply_ls", "SPLY_LS 파이프"),
        ("valve", "밸브"),
        ("fire", "소화전"),
        ("total_infra", "총 인프라"),
    ]

    for ax, (col_name, title) in zip(axes.flat, infra_types, strict=False):
        # 클러스터 데이터 사용
        x = df_clusters[f"avg_{col_name}"]
        y = df_clusters["repair_count"]

        # 색상 설정 (빈번한 재작업 여부)
        colors = ["red" if f else "blue" for f in df_clusters["is_frequent"]]

        ax.scatter(x, y, c=colors, alpha=0.6, s=50)

        # 회귀선
        if len(x) > 1:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2)

        # 상관계수 표시
        corr_key = f"corr_{col_name}_avg"
        p_key = f"p_{col_name}_avg"
        if corr_key in results:
            corr = results[corr_key]
            p_val = results[p_key]
            sig = "*" if p_val < 0.05 else ""
            ax.set_title(f"{title}\nr={corr:.3f} (p={p_val:.4f}){sig}", fontsize=12)
        else:
            ax.set_title(title, fontsize=12)

        ax.set_xlabel(f"{title} 수 ({radius:.0f}m 반경)", fontsize=10)
        ax.set_ylabel("재작업 횟수", fontsize=10)
        ax.grid(True, alpha=0.3)

        # 4회 이상 기준선
        ax.axhline(y=MIN_REPAIRS_FOR_FREQUENT, color="red", linestyle="--", alpha=0.3)

    # 범례
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="blue", alpha=0.6, label="일반 (<4회)"),
        Patch(facecolor="red", alpha=0.6, label="빈번 (≥4회)"),
    ]
    fig.legend(
        handles=legend_elements, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.98)
    )

    plt.suptitle(
        f"{radius:.0f}m 반경 내 인프라와 재작업 횟수 상관관계",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    plt.savefig(
        output_dir / "520_infrastructure_correlation_scatter.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # 2. 박스플롯 (빈번한 vs 일반 그룹)
    if results["frequent_clusters"] > 0:
        fig, axes = plt.subplots(1, 4, figsize=(20, 6))

        frequent = df_clusters[df_clusters["is_frequent"]]
        normal = df_clusters[~df_clusters["is_frequent"]]

        for ax, (col_name, title) in zip(axes, infra_types, strict=False):
            data_to_plot = []
            labels = []

            if len(normal) > 0:
                data_to_plot.append(normal[f"avg_{col_name}"].values)
                labels.append(f"일반\n(n={len(normal)})")

            if len(frequent) > 0:
                data_to_plot.append(frequent[f"avg_{col_name}"].values)
                labels.append(f"빈번\n(n={len(frequent)})")

            if data_to_plot:
                bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)

                # 색상 설정
                colors = ["lightblue", "lightcoral"]
                for patch, color in zip(
                    bp["boxes"], colors[: len(bp["boxes"])], strict=False
                ):
                    patch.set_facecolor(color)

                ax.set_ylabel("평균 수", fontsize=10)
                ax.set_title(title, fontsize=12)
                ax.grid(True, alpha=0.3)

                # 통계 검정 결과 표시
                t_p_key = f"t_p_{col_name}"
                if t_p_key in results:
                    p_value = results[t_p_key]
                    sig = "*" if p_value < 0.05 else ""
                    ax.text(
                        0.5,
                        0.95,
                        f"p={p_value:.4f}{sig}",
                        transform=ax.transAxes,
                        ha="center",
                        va="top",
                        bbox=dict(
                            boxstyle="round",
                            facecolor="yellow" if p_value < 0.05 else "white",
                            alpha=0.5,
                        ),
                    )

        plt.suptitle(
            "빈번한 재작업 위치 vs 일반 위치의 인프라 분포",
            fontsize=14,
            fontweight="bold",
        )
        plt.tight_layout()
        plt.savefig(
            output_dir / "520_infrastructure_correlation_boxplot.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    # 3. 상관계수 히트맵
    if len(df_clusters) > 1:
        # 상관관계 매트릭스 계산
        corr_cols = [
            "repair_count",
            "avg_sply_ls",
            "avg_valve",
            "avg_fire",
            "avg_total_infra",
        ]
        corr_matrix = df_clusters[corr_cols].corr()

        # 히트맵 그리기
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".3f",
            cmap="coolwarm",
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8},
            ax=ax,
        )

        # 레이블 설정
        ax.set_xticklabels(
            ["재작업 횟수", "SPLY_LS", "밸브", "소화전", "총 인프라"],
            rotation=45,
            ha="right",
        )
        ax.set_yticklabels(
            ["재작업 횟수", "SPLY_LS", "밸브", "소화전", "총 인프라"], rotation=0
        )

        plt.title(
            "인프라 요소 간 상관계수 히트맵", fontsize=14, fontweight="bold", pad=20
        )
        plt.tight_layout()
        plt.savefig(
            output_dir / "520_infrastructure_correlation_heatmap.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    print("    - 산점도 매트릭스 저장")
    print("    - 박스플롯 저장")
    print("    - 상관계수 히트맵 저장")


def analyze_d_final_correlation(
    repair_df: pd.DataFrame,
    output_dir: Path,
    radius: float = DEFAULT_RADIUS_METERS,  # 검색 반경 (미터)
    verbose: bool = True,
) -> dict[str, Any]:
    """D_final과 재작업 빈도 상관관계 분석

    Args:
        repair_df: 복구 작업 DataFrame
        output_dir: 출력 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        분석 결과 딕셔너리
    """
    print(f"\n=== D_final 상관관계 분석 시작 (반경: {radius:.0f}m) ===")

    # 파이프 피로 손상 데이터 로드
    pipe_lm_csv = FATIGUE_PIPE_LM_CSV
    sply_ls_csv = FATIGUE_SPLY_LS_CSV

    if not pipe_lm_csv.exists() or not sply_ls_csv.exists():
        print("  경고: 피로 손상 데이터 파일을 찾을 수 없습니다.")
        return {}

    # CSV 파일 로드
    df_pipe_lm = pd.read_csv(pipe_lm_csv)
    df_sply_ls = pd.read_csv(sply_ls_csv)

    # 필요한 컬럼만 선택
    cols_needed = ["FTR_IDN", "0520_D_final"]
    df_pipe_lm = df_pipe_lm[cols_needed].copy()
    df_sply_ls = df_sply_ls[cols_needed].copy()

    # D_final이 0이 아닌 것만 필터링
    df_pipe_lm = df_pipe_lm[df_pipe_lm["0520_D_final"] > 0]
    df_sply_ls = df_sply_ls[df_sply_ls["0520_D_final"] > 0]

    if verbose:
        print(f"  PIPE_LM: {len(df_pipe_lm)}개 파이프 (D_final > 0)")
        print(f"  SPLY_LS: {len(df_sply_ls)}개 파이프 (D_final > 0)")
        print(
            f"  D_final 범위: {min(df_pipe_lm['0520_D_final'].min(), df_sply_ls['0520_D_final'].min()):.6f} ~ "
            f"{max(df_pipe_lm['0520_D_final'].max(), df_sply_ls['0520_D_final'].max()):.6f}"
        )

    # Shapefile에서 geometry 정보 로드
    pipe_lm_shp = RESULTS_DIR / "shapefiles" / "PIPE_LM_JOINT.shp"
    sply_ls_shp = RESULTS_DIR / "shapefiles" / "SPLY_LS_JOINT.shp"

    if not pipe_lm_shp.exists() or not sply_ls_shp.exists():
        print("  경고: Shapefile을 찾을 수 없습니다.")
        return {}

    gdf_pipe_lm = gpd.read_file(pipe_lm_shp)
    gdf_sply_ls = gpd.read_file(sply_ls_shp)

    # ORIG_FTR을 기준으로 피로 손상 데이터와 매칭
    pipe_lm_geom = []
    for orig_ftr in df_pipe_lm["FTR_IDN"].unique():
        segments = gdf_pipe_lm[gdf_pipe_lm["ORIG_FTR"] == orig_ftr]
        if not segments.empty:
            centroids = segments.geometry.centroid
            avg_x = centroids.x.mean()
            avg_y = centroids.y.mean()
            pipe_lm_geom.append({"FTR_IDN": orig_ftr, "geometry": Point(avg_x, avg_y)})

    sply_ls_geom = []
    for orig_ftr in df_sply_ls["FTR_IDN"].unique():
        segments = gdf_sply_ls[gdf_sply_ls["ORIG_FTR"] == orig_ftr]
        if not segments.empty:
            centroids = segments.geometry.centroid
            avg_x = centroids.x.mean()
            avg_y = centroids.y.mean()
            sply_ls_geom.append({"FTR_IDN": orig_ftr, "geometry": Point(avg_x, avg_y)})

    # GeoDataFrame 생성 및 WGS84 변환
    gdf_pipe_lm_fatigue = gpd.GeoDataFrame(
        pd.merge(df_pipe_lm, pd.DataFrame(pipe_lm_geom), on="FTR_IDN"), crs="EPSG:5179"
    )
    gdf_sply_ls_fatigue = gpd.GeoDataFrame(
        pd.merge(df_sply_ls, pd.DataFrame(sply_ls_geom), on="FTR_IDN"), crs="EPSG:5179"
    )

    gdf_pipe_lm_fatigue = gdf_pipe_lm_fatigue.to_crs("EPSG:4326")
    gdf_sply_ls_fatigue = gdf_sply_ls_fatigue.to_crs("EPSG:4326")

    # 위도/경도 추출
    gdf_pipe_lm_fatigue["경도"] = gdf_pipe_lm_fatigue.geometry.x
    gdf_pipe_lm_fatigue["위도"] = gdf_pipe_lm_fatigue.geometry.y
    gdf_sply_ls_fatigue["경도"] = gdf_sply_ls_fatigue.geometry.x
    gdf_sply_ls_fatigue["위도"] = gdf_sply_ls_fatigue.geometry.y

    # 통합
    df_pipes = pd.concat(
        [
            gdf_pipe_lm_fatigue[["FTR_IDN", "0520_D_final", "위도", "경도"]],
            gdf_sply_ls_fatigue[["FTR_IDN", "0520_D_final", "위도", "경도"]],
        ],
        ignore_index=True,
    )

    print(f"  총 {len(df_pipes)}개 파이프 준비 완료")

    # 클러스터링 (repair_df를 직접 사용)
    clusters = []
    visited = set()

    for idx1, row1 in repair_df.iterrows():
        i = int(idx1) if not isinstance(idx1, int) else idx1  # type: ignore[call-overload]
        if i in visited:
            continue

        cluster = [i]
        visited.add(i)

        for idx2, row2 in repair_df.iterrows():
            j = int(idx2) if not isinstance(idx2, int) else idx2  # type: ignore[call-overload]
            if j <= i or j in visited:
                continue

            dist = calculate_haversine_distance(
                row1["위도"], row1["경도"], row2["위도"], row2["경도"]
            )

            if dist <= CLUSTER_DISTANCE_METERS:
                cluster.append(j)
                visited.add(j)

        clusters.append(cluster)

    # 클러스터 정보 생성
    cluster_data = []
    for cluster_id, indices in enumerate(clusters):
        cluster_df = repair_df.iloc[list(indices)]

        cluster_data.append(
            {
                "cluster_id": cluster_id,
                "repair_count": len(indices),
                "avg_lat": cluster_df["위도"].mean(),
                "avg_lon": cluster_df["경도"].mean(),
            }
        )

    clusters = pd.DataFrame(cluster_data)  # type: ignore[assignment]
    print(f"  생성된 클러스터: {len(clusters)}개")
    print(
        f"  빈번한 재작업 클러스터 (≥4회): {len(clusters[clusters['repair_count'] >= MIN_REPAIRS_FOR_FREQUENT])}개"  # type: ignore
    )

    # 클러스터와 파이프 매칭 (지정된 반경)
    matched_data = []
    for _, cluster in clusters.iterrows():  # type: ignore
        distances = []
        for _, pipe in df_pipes.iterrows():
            dist = calculate_haversine_distance(
                cluster["avg_lat"], cluster["avg_lon"], pipe["위도"], pipe["경도"]
            )
            if dist <= radius:
                distances.append(
                    {
                        "FTR_IDN": pipe["FTR_IDN"],
                        "0520_D_final": pipe["0520_D_final"],
                        "distance": dist,
                    }
                )

        if distances:
            # 가장 가까운 파이프
            nearest = min(distances, key=lambda x: x["distance"])
            # 최대 D_final
            max_d = max(distances, key=lambda x: x["0520_D_final"])
            # 거리 가중 평균
            weights = [1 / (d["distance"] + 1) for d in distances]
            weight_sum = sum(weights)
            avg_d = (
                sum(
                    w * d["0520_D_final"]
                    for w, d in zip(weights, distances, strict=False)
                )
                / weight_sum
            )

            matched_data.append(
                {
                    "cluster_id": cluster["cluster_id"],
                    "repair_count": cluster["repair_count"],
                    "nearest_d_final": nearest["0520_D_final"],
                    "max_d_final": max_d["0520_D_final"],
                    "avg_d_final": avg_d,
                    "pipe_count": len(distances),
                    "is_frequent": cluster["repair_count"] >= MIN_REPAIRS_FOR_FREQUENT,
                }
            )

    df_matched = pd.DataFrame(matched_data)

    if len(df_matched) == 0:
        print("  경고: 매칭된 데이터가 없습니다.")
        return {}

    print(f"  매칭된 클러스터: {len(df_matched)}개 / {len(clusters)}개")

    # 상관관계 분석
    results = {}

    # Pearson 상관계수
    for strategy in ["nearest_d_final", "max_d_final", "avg_d_final"]:
        if strategy in df_matched.columns:
            corr, p_value = stats.pearsonr(
                df_matched[strategy], df_matched["repair_count"]
            )
            results[f"{strategy}_corr"] = corr
            results[f"{strategy}_p"] = p_value
            print(f"  {strategy}: r={corr:.4f}, p={p_value:.4f}")

    # 빈번한 재작업 그룹 vs 일반 그룹
    df_frequent = df_matched[df_matched["is_frequent"]]
    df_normal = df_matched[~df_matched["is_frequent"]]

    results["frequent_count"] = len(df_frequent)
    results["normal_count"] = len(df_normal)

    if len(df_frequent) > 0 and len(df_normal) > 0:
        for strategy in ["nearest_d_final", "max_d_final", "avg_d_final"]:
            t_stat, t_p = stats.ttest_ind(df_frequent[strategy], df_normal[strategy])
            results[f"{strategy}_t_p"] = t_p
            results[f"{strategy}_frequent_mean"] = df_frequent[strategy].mean()
            results[f"{strategy}_normal_mean"] = df_normal[strategy].mean()

            print(f"\n  {strategy} 그룹 비교:")
            print(f"    빈번한: {df_frequent[strategy].mean():.6f}")
            print(f"    일반: {df_normal[strategy].mean():.6f}")
            print(f"    t-test p={t_p:.4f}")

    # D_final 시각화
    if len(df_matched) > 1:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        strategies = [
            ("nearest_d_final", "가장 가까운 파이프"),
            ("max_d_final", "최대 D_final"),
            ("avg_d_final", "평균 D_final (거리 가중)"),
        ]

        for ax, (strategy, title) in zip(axes, strategies, strict=False):
            x = df_matched[strategy]
            y = df_matched["repair_count"]
            colors = ["red" if f else "blue" for f in df_matched["is_frequent"]]

            ax.scatter(x, y, c=colors, alpha=0.6, s=50)

            # 회귀선
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.5, linewidth=2)

            ax.set_xlabel(f"{title} D_final", fontsize=10)
            ax.set_ylabel("재작업 횟수", fontsize=10)
            corr = results.get(f"{strategy}_corr", 0)
            p_val = results.get(f"{strategy}_p", 1)
            ax.set_title(f"{title}\nr={corr:.4f} (p={p_val:.4f})", fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.axhline(
                y=MIN_REPAIRS_FOR_FREQUENT, color="red", linestyle="--", alpha=0.3
            )

        plt.suptitle(
            f"파이프 피로 손상(D_final)과 재작업 횟수 상관관계 ({radius:.0f}m 반경)",
            fontsize=14,
            fontweight="bold",
        )
        plt.tight_layout()
        plt.savefig(
            output_dir / f"520_d_final_correlation_{radius:.0f}m.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()
        print(
            f"  D_final 상관관계 시각화 저장: 520_d_final_correlation_{radius:.0f}m.png"
        )

    # 보고서 생성
    report = []
    report.append("\n" + "=" * 70)
    report.append(f"D_final과 재작업 빈도 상관관계 분석 ({radius:.0f}m 반경)")
    report.append("=" * 70)
    report.append(f"매칭된 클러스터: {len(df_matched)}개")
    report.append(
        f"D_final 범위: {df_matched['nearest_d_final'].min():.6f} ~ {df_matched['nearest_d_final'].max():.6f}"
    )
    report.append("\n상관계수:")
    for strategy in ["nearest_d_final", "max_d_final", "avg_d_final"]:
        if f"{strategy}_corr" in results:
            report.append(
                f"  {strategy}: r={results[f'{strategy}_corr']:.4f}, p={results[f'{strategy}_p']:.4f}"
            )

    report_text = "\n".join(report)
    report_file = output_dir / "520_d_final_correlation_report.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"  D_final 상관관계 보고서 저장: {report_file}")

    return results


def generate_correlation_report(
    df_infra: pd.DataFrame,
    df_clusters: pd.DataFrame,
    results: dict[str, Any],
    output_dir: Path,
    radius: float = DEFAULT_RADIUS_METERS,
) -> None:
    """상관관계 분석 보고서 생성

    Args:
        df_infra: 인프라 카운트 DataFrame
        df_clusters: 클러스터 DataFrame
        results: 분석 결과
        output_dir: 출력 디렉토리
    """
    print("\n  보고서 생성 중...")

    report = []
    report.append("=" * 70)
    report.append(f"520 지역 사고 위치와 {radius:.0f}m 반경 내 인프라 상관관계 분석")
    report.append("=" * 70)
    report.append("")

    # 기본 통계
    report.append("1. 전체 통계")
    report.append("-" * 40)
    report.append(f"총 복구 작업: {results['total_repairs']:,}건")
    report.append(f"클러스터 수: {results['total_clusters']:,}개")
    report.append(f"빈번한 재작업 클러스터 (≥4회): {results['frequent_clusters']:,}개")
    report.append("")

    # 지정된 반경 내 평균 인프라
    report.append(f"2. {radius:.0f}m 반경 내 평균 인프라 수")
    report.append("-" * 40)
    report.append(f"SPLY_LS 파이프: {results['avg_sply_ls']:.2f}개")
    report.append(f"밸브: {results['avg_valve']:.2f}개")
    report.append(f"소화전: {results['avg_fire']:.2f}개")
    report.append(f"총 인프라: {results['avg_total']:.2f}개")
    report.append("")

    # 상관계수 분석
    report.append("3. 상관계수 분석 (재작업 횟수와 인프라 수)")
    report.append("-" * 40)

    for infra_type, name in [
        ("sply_ls", "SPLY_LS"),
        ("valve", "밸브"),
        ("fire", "소화전"),
        ("total_infra", "총 인프라"),
    ]:
        corr_key = f"corr_{infra_type}_avg"
        p_key = f"p_{infra_type}_avg"

        if corr_key in results:
            corr = results[corr_key]
            p_val = results[p_key]
            sig = "(유의미)" if p_val < 0.05 else "(유의미하지 않음)"
            report.append(f"{name}: r={corr:.3f}, p={p_val:.4f} {sig}")

    report.append("")

    # 그룹 비교
    if results["frequent_clusters"] > 0:
        report.append("4. 빈번한 재작업 vs 일반 그룹 비교")
        report.append("-" * 40)

        for infra_type, name in [
            ("sply_ls", "SPLY_LS"),
            ("valve", "밸브"),
            ("fire", "소화전"),
            ("total_infra", "총 인프라"),
        ]:
            freq_key = f"frequent_avg_{infra_type}"
            norm_key = f"normal_avg_{infra_type}"
            t_p_key = f"t_p_{infra_type}"

            if freq_key in results:
                freq_avg = results[freq_key]
                norm_avg = results[norm_key]
                diff = freq_avg - norm_avg
                diff_pct = (diff / norm_avg * 100) if norm_avg > 0 else 0

                report.append(f"\n{name}:")
                report.append(f"  빈번한 그룹: {freq_avg:.2f}개")
                report.append(f"  일반 그룹: {norm_avg:.2f}개")
                report.append(f"  차이: {diff:+.2f}개 ({diff_pct:+.1f}%)")

                if t_p_key in results:
                    p_val = results[t_p_key]
                    sig = "유의미" if p_val < 0.05 else "유의미하지 않음"
                    report.append(f"  t-test p-value: {p_val:.4f} ({sig})")

    report.append("")

    # 결론
    report.append("5. 결론")
    report.append("-" * 40)

    # 가장 강한 상관관계 찾기
    max_corr = 0
    max_corr_name = ""
    for infra_type, name in [
        ("sply_ls", "SPLY_LS"),
        ("valve", "밸브"),
        ("fire", "소화전"),
        ("total_infra", "총 인프라"),
    ]:
        corr_key = f"corr_{infra_type}_avg"
        if corr_key in results and abs(results[corr_key]) > abs(max_corr):
            max_corr = results[corr_key]
            max_corr_name = name

    if max_corr_name:
        report.append(f"가장 강한 상관관계: {max_corr_name} (r={max_corr:.3f})")

    # 유의미한 차이 요약
    sig_diffs = []
    for infra_type, name in [
        ("sply_ls", "SPLY_LS"),
        ("valve", "밸브"),
        ("fire", "소화전"),
        ("total_infra", "총 인프라"),
    ]:
        t_p_key = f"t_p_{infra_type}"
        if t_p_key in results and results[t_p_key] < 0.05:
            sig_diffs.append(name)

    if sig_diffs:
        report.append(
            f"빈번한 재작업 위치에서 유의미하게 많은 인프라: {', '.join(sig_diffs)}"
        )
    else:
        report.append(
            "빈번한 재작업 위치와 일반 위치 간 인프라 차이가 통계적으로 유의미하지 않음"
        )

    report.append("")
    report.append("=" * 70)

    # 파일로 저장
    report_text = "\n".join(report)
    report_file = output_dir / "520_infrastructure_correlation_report.txt"
    with report_file.open("w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"    보고서 저장: {report_file}")


def parse_arguments() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="520 데이터 복구 작업 위치 통합 시각화"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 (기본값: results/)",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="입력 디렉토리 (기본값: results/)",
    )
    parser.add_argument(
        "--no-grid",
        action="store_true",
        help="그리드 표시하지 않음",
    )
    parser.add_argument(
        "--skip-comparison",
        action="store_true",
        help="타입별 비교 플롯 생성 건너뛰기",
    )
    parser.add_argument(
        "--skip-heatmap",
        action="store_true",
        help="밀도 히트맵 생성 건너뛰기",
    )
    parser.add_argument(
        "--skip-correlation",
        action="store_true",
        help="인프라 상관관계 분석 건너뛰기",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=DEFAULT_RADIUS_METERS,
        help=f"분석 반경 (미터, 기본값: {DEFAULT_RADIUS_METERS:.0f}m)",
    )
    return parser.parse_args()


def main() -> None:
    """메인 실행 함수"""
    args = parse_arguments()

    # 한글 폰트 설정
    setup_korean_font()

    # 디렉토리 설정
    input_dir = Path(args.input_dir) if args.input_dir else RESULTS_DIR
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else RESULTS_DIR / "main19_visualize_520_repairs"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("520 데이터 복구 작업 위치 통합 시각화")
    print("=" * 60)
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")

    # 데이터 로드
    repair_df = load_520_csv_files(input_dir, verbose=True)

    if repair_df is None or len(repair_df) == 0:
        print("\n오류: 로드된 데이터가 없습니다.")
        return

    # 반경 설정
    radius = args.radius
    print(f"\n분석 반경: {radius:.0f}m")

    # 1. 전체 통합 시각화 (배경 지도 포함)
    print("\n=== 전체 통합 시각화 (배경 지도 포함) ===")
    output_path = output_dir / "520_repairs_with_background.png"
    visualize_520_repairs_with_background(
        repair_df,
        f"520 데이터 복구 작업 위치 분포 ({radius:.0f}m 버퍼 포함)",
        output_path,
        show_grid=not args.no_grid,
        show_background=True,
        show_buffers=True,  # 버퍼 표시
        radius=radius,  # 반경 전달
        verbose=True,
    )

    # 2. 타입별 비교 플롯
    if not args.skip_comparison:
        create_type_comparison_plots(repair_df, output_dir)

    # 3. 밀도 히트맵
    if not args.skip_heatmap:
        create_density_heatmap(repair_df, output_dir)

    # 4. 통계 보고서 생성
    generate_statistics_report(repair_df, output_dir)

    # 5. 인프라 상관관계 분석
    if not args.skip_correlation:
        # 배경 데이터 로드 (상관관계 분석을 위해)
        background_data = load_background_data(DATA_DIR, verbose=True)
        analyze_infrastructure_correlation(
            repair_df, background_data, output_dir, radius=radius, verbose=True
        )

        # D_final 상관관계 분석 추가
        analyze_d_final_correlation(repair_df, output_dir, radius=radius, verbose=True)

    # 6. 데이터 요약 CSV 저장
    print("\n=== 데이터 요약 저장 ===")
    summary_file = output_dir / "520_repairs_summary.csv"

    # 필요한 컬럼만 선택하여 저장
    save_columns = ["repair_id", "복구타입", "위도", "경도"]
    if "주소" in repair_df.columns:
        save_columns.append("주소")
    if "작업일시" in repair_df.columns:
        save_columns.append("작업일시")
    if "구군" in repair_df.columns:
        save_columns.append("구군")

    summary_df = repair_df[save_columns].copy()
    summary_df.to_csv(summary_file, index=False, encoding="utf-8-sig")
    print(f"데이터 요약 저장: {summary_file}")

    print("\n" + "=" * 60)
    print("시각화 완료!")
    print("=" * 60)
    print("생성된 파일:")
    print("  - 전체 시각화 (배경 포함): 520_repairs_with_background.png")
    if not args.skip_comparison:
        print("  - 타입별 비교: 520_repairs_type_comparison.png")
    if not args.skip_heatmap:
        print("  - 밀도 히트맵: 520_repairs_density_heatmap.png")
    print("  - 통계 보고서: 520_repairs_statistics.txt")
    print("  - 데이터 요약: 520_repairs_summary.csv")
    if not args.skip_correlation:
        print("  - 인프라 상관관계 산점도: 520_infrastructure_correlation_scatter.png")
        print(
            "  - 인프라 상관관계 박스플롯: 520_infrastructure_correlation_boxplot.png"
        )
        print("  - 인프라 상관관계 히트맵: 520_infrastructure_correlation_heatmap.png")
        print("  - 인프라 상관관계 보고서: 520_infrastructure_correlation_report.txt")
        print("  - 인프라 데이터: 520_repair_infrastructure_data.csv")
        print(f"  - D_final 상관관계 시각화: 520_d_final_correlation_{radius:.0f}m.png")
        print("  - D_final 상관관계 보고서: 520_d_final_correlation_report.txt")


if __name__ == "__main__":
    main()
