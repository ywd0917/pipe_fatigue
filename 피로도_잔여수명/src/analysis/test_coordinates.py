"""좌표 시스템 테스트"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

# 파이프 데이터 샘플 확인
shp_path = Path(
    "/Users/jhpark/development/eroumtech/fatigue-qgis/results/shapefiles/PIPE_LM_JOINT.shp"
)
gdf = gpd.read_file(shp_path)

print("원본 좌표계:", gdf.crs)
print("원본 bounds:", gdf.total_bounds)

# 첫 번째 geometry 확인
first_geom = gdf.iloc[0].geometry
print("\n첫 번째 파이프 (원본):")
print("  좌표:", next(iter(first_geom.coords)))

# WGS84로 변환
gdf_wgs84 = gdf.to_crs("EPSG:4326")
print("\nWGS84 변환 후:")
print("  bounds:", gdf_wgs84.total_bounds)

first_geom_wgs84 = gdf_wgs84.iloc[0].geometry
print("  첫 번째 파이프 좌표:", next(iter(first_geom_wgs84.coords)))

# 복구 데이터 샘플 확인
csv_path = Path(
    "/Users/jhpark/development/eroumtech/fatigue-qgis/results/duplicate_repairs_analysis.csv"
)
df_repairs = pd.read_csv(csv_path, encoding="utf-8-sig")

print("\n복구 데이터 샘플:")
print("  첫 번째 위치:")
print(f"    위도: {df_repairs.iloc[0]['위도']}")
print(f"    경도: {df_repairs.iloc[0]['경도']}")

# 범위 확인
print("\n좌표 범위 비교:")
print("파이프 (WGS84):")
print(f"  위도: {gdf_wgs84.total_bounds[1]:.6f} ~ {gdf_wgs84.total_bounds[3]:.6f}")
print(f"  경도: {gdf_wgs84.total_bounds[0]:.6f} ~ {gdf_wgs84.total_bounds[2]:.6f}")

print("\n복구 데이터:")
print(f"  위도: {df_repairs['위도'].min():.6f} ~ {df_repairs['위도'].max():.6f}")
print(f"  경도: {df_repairs['경도'].min():.6f} ~ {df_repairs['경도'].max():.6f}")

# 겹치는지 확인
pipe_lat_min, pipe_lat_max = gdf_wgs84.total_bounds[1], gdf_wgs84.total_bounds[3]
pipe_lon_min, pipe_lon_max = gdf_wgs84.total_bounds[0], gdf_wgs84.total_bounds[2]

repair_lat_min, repair_lat_max = df_repairs["위도"].min(), df_repairs["위도"].max()
repair_lon_min, repair_lon_max = df_repairs["경도"].min(), df_repairs["경도"].max()

lat_overlap = not (repair_lat_max < pipe_lat_min or repair_lat_min > pipe_lat_max)
lon_overlap = not (repair_lon_max < pipe_lon_min or repair_lon_min > pipe_lon_max)

print(f"\n위도 겹침: {lat_overlap}")
print(f"경도 겹침: {lon_overlap}")
print(f"전체 겹침: {lat_overlap and lon_overlap}")
