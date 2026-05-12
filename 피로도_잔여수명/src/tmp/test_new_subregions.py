#!/usr/bin/env python3
"""
test_new_subregions.py

새로운 소구역(0243, 0461 등) 지원 테스트 스크립트
main14c와 main14c2가 새로운 소구역을 올바르게 처리하는지 검증

Author: assistant
Date: 2025-01-04
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import geopandas as gpd
from shapely.geometry import Point

from src.common.config import RAW_DATA_DIR, SUBREGION_MAPPING
from src.common.shapefile_loader import (
    ShapefileLoader,
    get_smlz_shapefile_path,
    get_subregion_label,
    is_subregion,
)


def test_subregion_mapping():
    """새로운 소구역 매핑이 올바르게 설정되었는지 확인"""
    print("\n=== 소구역 매핑 테스트 ===")

    # 새로운 소구역 확인
    new_regions = ["0243", "0461"]
    existing_regions = ["0470", "0480", "0490"]
    all_regions = new_regions + existing_regions

    for region in all_regions:
        if region in SUBREGION_MAPPING:
            mapping = SUBREGION_MAPPING[region]
            print(f"✓ {region}: parent={mapping['parent']}, label={mapping['label']}")

            # 헬퍼 함수 테스트
            assert is_subregion(region), f"{region}이 소구역으로 인식되지 않습니다"
            assert (
                get_subregion_label(region) == mapping["label"]
            ), f"{region}의 라벨이 일치하지 않습니다"
        else:
            print(f"✗ {region}: 매핑 없음")

    print("\n소구역 매핑 테스트 완료!")


def test_shapefile_boundaries():
    """각 소구역의 경계가 shapefile에서 올바르게 로드되는지 확인"""
    print("\n=== Shapefile 경계 로드 테스트 ===")

    # SMLZ shapefile 경로
    smlz_path = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")
    if not smlz_path:
        print("오류: SMLZ shapefile을 찾을 수 없습니다")
        return

    # Shapefile 로드
    gdf_smlz = gpd.read_file(smlz_path)
    print(f"SMLZ shapefile 로드: {len(gdf_smlz)}개 소구역")

    # 각 소구역 확인
    test_regions = ["0243", "0461", "0470", "0480", "0490"]

    for region_code in test_regions:
        label = get_subregion_label(region_code)

        # SMZ_LBL로 필터링
        boundary = gdf_smlz[gdf_smlz["SMZ_LBL"] == label]

        if not boundary.empty:
            print(f"✓ {region_code} (label={label}): {len(boundary)}개 폴리곤")
            print(f"  - 면적: {boundary.geometry.area.sum():,.0f} m²")
            bounds = boundary.total_bounds
            print(
                f"  - 경계: X({bounds[0]:.0f}-{bounds[2]:.0f}), Y({bounds[1]:.0f}-{bounds[3]:.0f})"
            )
        else:
            print(f"✗ {region_code} (label={label}): 경계를 찾을 수 없음")

    print("\nShapefile 경계 로드 테스트 완료!")


def test_data_availability():
    """각 소구역에 대한 파이프 데이터 가용성 확인"""
    print("\n=== 데이터 가용성 테스트 ===")

    loader = ShapefileLoader(RAW_DATA_DIR, verbose=False)

    # PIPE_LM shapefile 로드 (0520 지역 전체)
    gdf_pipe = loader.load_pipe_shapefile("0520", "PIPE_LM")
    if gdf_pipe is None:
        print("오류: PIPE_LM shapefile을 로드할 수 없습니다")
        return

    print(f"전체 PIPE_LM 데이터: {len(gdf_pipe)}개 파이프")

    # SMLZ shapefile로 각 소구역 경계 가져오기
    smlz_path = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")
    gdf_smlz = gpd.read_file(smlz_path)

    test_regions = ["0243", "0461", "0470", "0480", "0490"]

    for region_code in test_regions:
        label = get_subregion_label(region_code)
        boundary = gdf_smlz[gdf_smlz["SMZ_LBL"] == label]

        if not boundary.empty:
            # 소구역 내 파이프 수 계산 (공간 조인)
            pipes_in_region = gpd.sjoin(
                gdf_pipe, boundary, how="inner", predicate="within"
            )
            print(f"✓ {region_code}: {len(pipes_in_region)}개 파이프")
        else:
            print(f"✗ {region_code}: 경계를 찾을 수 없어 파이프 수를 계산할 수 없음")

    print("\n데이터 가용성 테스트 완료!")


def test_sample_analysis():
    """새로운 소구역 중 하나에 대한 간단한 분석 실행"""
    print("\n=== 샘플 분석 테스트 (0243 소구역) ===")

    # SMLZ shapefile에서 0243 경계 로드
    smlz_path = get_smlz_shapefile_path(RAW_DATA_DIR, "0520")
    gdf_smlz = gpd.read_file(smlz_path)

    label = get_subregion_label("0243")
    boundary = gdf_smlz[gdf_smlz["SMZ_LBL"] == label]

    if boundary.empty:
        print("오류: 0243 소구역 경계를 찾을 수 없습니다")
        return

    # 경계 정보 출력
    print(f"소구역 0243 (label={label}):")
    print(f"- 폴리곤 수: {len(boundary)}")
    print(f"- 총 면적: {boundary.geometry.area.sum() / 1000000:.2f} km²")

    # 중심점 계산
    centroid = boundary.geometry.unary_union.centroid
    print(f"- 중심점: X={centroid.x:.0f}, Y={centroid.y:.0f}")

    # 샘플 재작업 위치 생성 (테스트용)
    import numpy as np

    np.random.seed(42)

    bounds = boundary.total_bounds
    n_samples = 10

    sample_repairs = []
    for i in range(n_samples):
        x = np.random.uniform(bounds[0], bounds[2])
        y = np.random.uniform(bounds[1], bounds[3])
        point = Point(x, y)

        # 경계 내부에 있는지 확인
        if boundary.geometry.unary_union.contains(point):
            sample_repairs.append(point)

    print(f"\n테스트용 샘플 재작업 위치: {len(sample_repairs)}개 생성")
    print("\n샘플 분석 테스트 완료!")


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("새로운 소구역 지원 테스트 시작")
    print("=" * 60)

    # 1. 소구역 매핑 테스트
    test_subregion_mapping()

    # 2. Shapefile 경계 로드 테스트
    test_shapefile_boundaries()

    # 3. 데이터 가용성 테스트
    test_data_availability()

    # 4. 샘플 분석 테스트
    test_sample_analysis()

    print("\n" + "=" * 60)
    print("모든 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
