"""
공간 분석을 위한 유틸리티 함수 모듈

이 모듈은 공간 가중치 행렬 생성, 시공간 그리드 생성 등의
공간 분석 기능을 제공합니다.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from shapely.geometry import Polygon


def create_spatial_weights_matrix(
    points: gpd.GeoDataFrame | np.ndarray,
    method: str = "distance",
    threshold: float | None = None,
    k: int | None = None,
    binary: bool = True,
) -> np.ndarray:
    """
    공간 가중치 행렬을 생성합니다.

    Parameters
    ----------
    points : GeoDataFrame 또는 numpy array
        포인트 좌표 데이터
    method : str
        가중치 행렬 생성 방법 ('distance', 'knn', 'queen', 'rook')
    threshold : float, optional
        거리 임계값 (method='distance'일 때 사용)
    k : int, optional
        최근접 이웃 수 (method='knn'일 때 사용)
    binary : bool
        이진 가중치 사용 여부

    Returns
    -------
    np.ndarray
        공간 가중치 행렬
    """
    # GeoDataFrame를 numpy array로 변환
    if isinstance(points, gpd.GeoDataFrame):
        # Polygon인 경우 centroid 사용, Point인 경우 x, y 사용
        coords = []
        for geom in points.geometry:
            if hasattr(geom, "x"):  # Point
                coords.append([geom.x, geom.y])
            else:  # Polygon 또는 다른 geometry
                centroid = geom.centroid
                coords.append([centroid.x, centroid.y])
        coords = np.array(coords)
    else:
        coords = points

    n_points = len(coords)

    if method == "distance":
        if threshold is None:
            # 평균 최근접 이웃 거리를 기본값으로 사용
            tree = cKDTree(coords)
            distances, _ = tree.query(coords, k=2)
            threshold = np.mean(distances[:, 1]) * 3

        # 거리 행렬 계산
        dist_matrix = cdist(coords, coords)

        # 가중치 행렬 생성
        if binary:
            W = (dist_matrix <= threshold).astype(float)
        else:
            W = np.where(dist_matrix <= threshold, 1.0 / (dist_matrix + 1e-10), 0)

        # 대각선 요소를 0으로 설정
        np.fill_diagonal(W, 0)

    elif method == "knn":
        if k is None:
            k = min(8, n_points - 1)

        tree = cKDTree(coords)
        W = np.zeros((n_points, n_points))

        for i in range(n_points):
            distances, indices = tree.query(coords[i], k=k + 1)
            indices = indices[1:]  # 자기 자신 제외

            if binary:
                W[i, indices] = 1
            else:
                W[i, indices] = 1.0 / (distances[1:] + 1e-10)

    else:
        raise ValueError(f"지원하지 않는 method: {method}")

    # 행 표준화
    row_sums = W.sum(axis=1)
    row_sums[row_sums == 0] = 1  # 0으로 나누기 방지
    return W / row_sums[:, np.newaxis]


def create_spacetime_grid(
    gdf: gpd.GeoDataFrame,
    grid_size: float = 30.0,
    time_column: str = "작업종료일",
    time_interval: str = "1M",
    extent: tuple[float, float, float, float] | None = None,
) -> gpd.GeoDataFrame:
    """
    시공간 큐브를 위한 그리드를 생성합니다.

    Parameters
    ----------
    gdf : GeoDataFrame
        입력 포인트 데이터
    grid_size : float
        그리드 셀 크기 (미터)
    time_column : str
        시간 정보를 담은 컬럼명
    time_interval : str
        시간 집계 간격 ('D', 'W', 'M', 'Q', 'Y')
    extent : tuple, optional
        그리드 범위 (minx, miny, maxx, maxy)

    Returns
    -------
    GeoDataFrame
        시공간 그리드 데이터
    """
    # 시간 컬럼 파싱
    if time_column in gdf.columns:
        gdf = gdf.copy()
        gdf[time_column] = pd.to_datetime(gdf[time_column], errors="coerce")

    # 그리드 범위 설정
    if extent is None:
        minx, miny, maxx, maxy = gdf.total_bounds
        # 버퍼 추가
        buffer = grid_size
        minx -= buffer
        miny -= buffer
        maxx += buffer
        maxy += buffer
    else:
        minx, miny, maxx, maxy = extent

    # 그리드 셀 생성
    x_coords = np.arange(minx, maxx, grid_size)
    y_coords = np.arange(miny, maxy, grid_size)

    grid_cells = []
    for x in x_coords:
        for y in y_coords:
            # 그리드 셀 polygon 생성
            cell = Polygon(
                [
                    (x, y),
                    (x + grid_size, y),
                    (x + grid_size, y + grid_size),
                    (x, y + grid_size),
                ]
            )
            grid_cells.append(
                {
                    "geometry": cell,
                    "grid_x": x,
                    "grid_y": y,
                    "cell_id": f"{int(x/grid_size)}_{int(y/grid_size)}",
                }
            )

    grid_gdf = gpd.GeoDataFrame(grid_cells, crs=gdf.crs)

    # 시간 차원 추가 (선택사항)
    if time_column in gdf.columns and not gdf[time_column].isna().all():
        # 시간 범위 계산
        time_min = gdf[time_column].min()
        time_max = gdf[time_column].max()

        # 시간 빈 생성
        time_bins = pd.date_range(start=time_min, end=time_max, freq=time_interval)

        # 시공간 큐브 생성
        spacetime_cells = []
        geometries = []
        for _, cell in grid_gdf.iterrows():
            for t in time_bins:
                spacetime_cell = cell.to_dict()
                if "geometry" in spacetime_cell:
                    del spacetime_cell["geometry"]  # geometry는 별도로 처리
                spacetime_cell["time_bin"] = t
                spacetime_cells.append(spacetime_cell)
                geometries.append(cell.geometry)

        spacetime_gdf = gpd.GeoDataFrame(
            spacetime_cells, geometry=geometries, crs=gdf.crs
        )

        # 각 셀에 포인트 카운트 추가
        for idx, cell in spacetime_gdf.iterrows():
            # 공간 필터
            points_in_cell = gdf[gdf.geometry.within(cell.geometry)]

            # 시간 필터
            if not points_in_cell.empty and time_column in gdf.columns:
                time_end = (
                    cell["time_bin"] + pd.DateOffset(months=1)
                    if time_interval == "1M"
                    else cell["time_bin"] + pd.Timedelta(time_interval)
                )
                points_in_cell = points_in_cell[
                    (points_in_cell[time_column] >= cell["time_bin"])
                    & (points_in_cell[time_column] < time_end)
                ]

            spacetime_gdf.at[idx, "point_count"] = len(points_in_cell)

        return spacetime_gdf

    # 시간 정보 없이 공간 그리드만 반환
    # 각 셀에 포인트 카운트 추가
    for idx, cell in grid_gdf.iterrows():
        points_in_cell = gdf[gdf.geometry.within(cell.geometry)]
        grid_gdf.at[idx, "point_count"] = len(points_in_cell)

    return grid_gdf


def calculate_spatial_lag(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """
    공간 지연(spatial lag) 값을 계산합니다.

    Parameters
    ----------
    values : np.ndarray
        관측값
    weights : np.ndarray
        공간 가중치 행렬

    Returns
    -------
    np.ndarray
        공간 지연 값
    """
    return weights @ values


def calculate_morans_i(
    values: np.ndarray, weights: np.ndarray
) -> tuple[float, float, float]:
    """
    Global Moran's I 통계량을 계산합니다.

    Parameters
    ----------
    values : np.ndarray
        관측값
    weights : np.ndarray
        공간 가중치 행렬

    Returns
    -------
    tuple
        (Moran's I, z-score, p-value)
    """
    n = len(values)

    # 평균 중심화
    y = values - np.mean(values)

    # 공간 지연 계산
    wy = calculate_spatial_lag(y, weights)

    # Moran's I 계산
    numerator = np.sum(y * wy)
    denominator = np.sum(y * y)

    if denominator == 0:
        return 0, 0, 1

    I = (n / np.sum(weights)) * (numerator / denominator)

    # 기댓값과 분산
    E_I = -1 / (n - 1)

    # 단순화된 분산 계산
    b2 = np.sum(y**4) / n / (np.sum(y**2) / n) ** 2

    S0 = np.sum(weights)
    S1 = 0.5 * np.sum((weights + weights.T) ** 2)
    S2 = np.sum(np.sum(weights + weights.T, axis=1) ** 2)

    var_I = (
        n * ((n**2 - 3 * n + 3) * S1 - n * S2 + 3 * S0**2)
        - b2 * ((n**2 - n) * S1 - 2 * n * S2 + 6 * S0**2)
    ) / ((n - 1) * (n - 2) * (n - 3) * S0**2)

    # z-score
    z_score = (I - E_I) / np.sqrt(var_I) if var_I > 0 else 0

    # p-value (양측 검정)
    from scipy import stats

    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

    return I, z_score, p_value


def calculate_getis_ord_gi(
    values: np.ndarray, weights: np.ndarray, star: bool = True
) -> np.ndarray:
    """
    Local Getis-Ord Gi 또는 Gi* 통계량을 계산합니다.

    Parameters
    ----------
    values : np.ndarray
        관측값
    weights : np.ndarray
        공간 가중치 행렬
    star : bool
        Gi* (True) 또는 Gi (False) 계산

    Returns
    -------
    np.ndarray
        각 위치의 z-score
    """
    n = len(values)

    # 전역 평균과 표준편차
    x_bar = np.mean(values)
    s = np.std(values)

    if s == 0:
        return np.zeros(n)

    z_scores = np.zeros(n)

    for i in range(n):
        # 가중치 복사
        w_i = weights[i].copy()

        if not star:
            # Gi의 경우 자기 자신 제외
            w_i[i] = 0

        # 통계량 계산
        numerator = np.sum(w_i * values) - x_bar * np.sum(w_i)

        # 분산 계산
        S = s * np.sqrt((n * np.sum(w_i**2) - np.sum(w_i) ** 2) / (n - 1))

        if S > 0:
            z_scores[i] = numerator / S
        else:
            z_scores[i] = 0

    return z_scores


def identify_hotspots(
    z_scores: np.ndarray, confidence_levels: list[float] | None = None
) -> dict[str, np.ndarray]:
    """
    z-score를 기반으로 핫스팟과 콜드스팟을 식별합니다.

    Parameters
    ----------
    z_scores : np.ndarray
        Getis-Ord Gi* z-scores
    confidence_levels : list
        신뢰수준 리스트

    Returns
    -------
    dict
        각 신뢰수준별 핫스팟/콜드스팟 분류
    """
    from scipy import stats

    if confidence_levels is None:
        confidence_levels = [0.9, 0.95, 0.99]
    results = {}

    for confidence in confidence_levels:
        # 임계값 계산
        alpha = 1 - confidence
        z_critical = stats.norm.ppf(1 - alpha / 2)

        # 분류
        classification = np.zeros(len(z_scores), dtype=int)
        classification[z_scores >= z_critical] = 1  # 핫스팟
        classification[z_scores <= -z_critical] = -1  # 콜드스팟

        results[f"confidence_{int(confidence*100)}"] = classification

    return results


def create_distance_band_weights(
    points: gpd.GeoDataFrame | np.ndarray,
    min_distance: float,
    max_distance: float,
    binary: bool = True,
) -> np.ndarray:
    """
    거리 밴드 기반 공간 가중치 행렬을 생성합니다.

    Parameters
    ----------
    points : GeoDataFrame 또는 numpy array
        포인트 좌표 데이터
    min_distance : float
        최소 거리
    max_distance : float
        최대 거리
    binary : bool
        이진 가중치 사용 여부

    Returns
    -------
    np.ndarray
        공간 가중치 행렬
    """
    # GeoDataFrame를 numpy array로 변환
    if isinstance(points, gpd.GeoDataFrame):
        # Polygon인 경우 centroid 사용, Point인 경우 x, y 사용
        coords = []
        for geom in points.geometry:
            if hasattr(geom, "x"):  # Point
                coords.append([geom.x, geom.y])
            else:  # Polygon 또는 다른 geometry
                centroid = geom.centroid
                coords.append([centroid.x, centroid.y])
        coords = np.array(coords)
    else:
        coords = points

    # 거리 행렬 계산
    dist_matrix = cdist(coords, coords)

    # 가중치 행렬 생성
    if binary:
        W = ((dist_matrix >= min_distance) & (dist_matrix <= max_distance)).astype(
            float
        )
    else:
        W = np.where(
            (dist_matrix >= min_distance) & (dist_matrix <= max_distance),
            1.0 / (dist_matrix + 1e-10),
            0,
        )

    # 대각선 요소를 0으로 설정
    np.fill_diagonal(W, 0)

    # 행 표준화
    row_sums = W.sum(axis=1)
    row_sums[row_sums == 0] = 1
    return W / row_sums[:, np.newaxis]


def calculate_ann_distance(points: gpd.GeoDataFrame | np.ndarray) -> float:
    """
    Average Nearest Neighbor (ANN) 거리를 계산합니다.

    Parameters
    ----------
    points : GeoDataFrame 또는 numpy array
        포인트 좌표 데이터

    Returns
    -------
    float
        평균 최근접 이웃 거리
    """
    # GeoDataFrame를 numpy array로 변환
    if isinstance(points, gpd.GeoDataFrame):
        # Polygon인 경우 centroid 사용, Point인 경우 x, y 사용
        coords = []
        for geom in points.geometry:
            if hasattr(geom, "x"):  # Point
                coords.append([geom.x, geom.y])
            else:  # Polygon 또는 다른 geometry
                centroid = geom.centroid
                coords.append([centroid.x, centroid.y])
        coords = np.array(coords)
    else:
        coords = points

    if len(coords) < 2:
        return 0

    # KDTree를 사용한 최근접 이웃 탐색
    tree = cKDTree(coords)
    distances, _ = tree.query(coords, k=2)

    # 첫 번째 최근접 이웃까지의 거리 (자기 자신 제외)
    return np.mean(distances[:, 1])


def convert_to_epsg5179(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    GeoDataFrame을 EPSG:5179 (Korea 2000 / Central Belt 2010) 좌표계로 변환합니다.

    Parameters
    ----------
    gdf : GeoDataFrame
        변환할 GeoDataFrame

    Returns
    -------
    GeoDataFrame
        EPSG:5179 좌표계로 변환된 GeoDataFrame

    Notes
    -----
    - 이미 EPSG:5179인 경우 그대로 반환
    - WGS84 (EPSG:4326) 등 다른 좌표계에서 변환
    """
    if gdf.crs is None:
        raise ValueError("입력 GeoDataFrame에 좌표계(CRS)가 정의되어 있지 않습니다.")

    # 이미 EPSG:5179인 경우 그대로 반환
    if gdf.crs == "EPSG:5179":
        return gdf

    # EPSG:5179로 변환
    return gdf.to_crs("EPSG:5179")
