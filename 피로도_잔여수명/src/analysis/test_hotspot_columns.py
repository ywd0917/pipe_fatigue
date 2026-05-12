"""
test_hotspot_columns.py

핫스팟 컬럼의 고유값을 확인하는 분석 스크립트
"""

import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

# 테스트용 데이터 생성
np.random.seed(42)
n_points = 100
x = np.random.uniform(344000, 346000, n_points)
y = np.random.uniform(366500, 368000, n_points)

gdf = gpd.GeoDataFrame(
    {
        "x": x,
        "y": y,
        "CNT_JNT": np.random.randint(1, 20, n_points),
        "K_total": np.random.uniform(0.5, 2.0, n_points),
        "D_final": np.random.uniform(0.01, 0.1, n_points),
    },
    geometry=[Point(xi, yi) for xi, yi in zip(x, y, strict=False)],
    crs="EPSG:5186",
)

params = {"grid_size": 60, "distance_threshold": 140, "k_neighbors": 13}

from src.main21_spatial_hotspots import SpatialHotspotAnalyzer

print("분석 시작...")
analyzer = SpatialHotspotAnalyzer(gdf, params)
analyzer.grid_gdf = analyzer.create_grid_aggregation()
grid_with_gi = analyzer.calculate_getis_ord_gi()

print("\n=== 핫스팟 컬럼의 고유값 확인 ===")
for col in ["hotspot_confidence_90", "hotspot_confidence_95", "hotspot_confidence_99"]:
    if col in grid_with_gi.columns:
        unique_vals = grid_with_gi[col].unique()
        print(f"\n{col}:")
        print(f"  고유값: {unique_vals}")
        print(f"  값 개수: {len(unique_vals)}")

        # 각 값의 빈도 확인
        value_counts = grid_with_gi[col].value_counts()
        for val, count in value_counts.items():
            print(f"    '{val}': {count}개")
    else:
        print(f"\n{col}: 컬럼이 존재하지 않음")

print("\n=== 사용 가능한 모든 컬럼 ===")
print(grid_with_gi.columns.tolist())
