"""도로 데이터의 모든 필드를 확인하는 스크립트."""

import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import geopandas as gpd  # noqa: E402

from src.common.config import RAW_DATA_DIR  # noqa: E402

# 도로 데이터 로드
road_file = RAW_DATA_DIR.parent / "road" / "TL_SPRD_MANAGE.shp"
print(f"파일 경로: {road_file}")

# 데이터 읽기
gdf = gpd.read_file(road_file, encoding="euc-kr")

print("=== 전체 컬럼 목록 ===")
for i, col in enumerate(gdf.columns):
    print(f"{i+1}. {col}")

print(f"\n총 {len(gdf.columns)}개 필드")

# 몇 개 레코드의 전체 데이터 보기
print("\n=== 샘플 데이터 (첫 3개 레코드) ===")
for idx in range(min(3, len(gdf))):
    print(f"\n[레코드 {idx+1}]")
    for col in gdf.columns:
        if col != "geometry":
            print(f"  {col}: {gdf.iloc[idx][col]}")

# 도로명 관련 필드가 있는지 추가 확인
print("\n=== 추가 파일 확인 ===")
road_dir = road_file.parent
for file in road_dir.glob("*.dbf"):
    print(f"DBF 파일: {file.name}")

# 관련된 다른 shapefile이 있는지 확인
print("\n=== 도로 관련 다른 Shapefile ===")
for shp in road_dir.glob("*.shp"):
    print(f"  - {shp.name}")
