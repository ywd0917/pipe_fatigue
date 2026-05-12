#!/usr/bin/env python3
"""
FTR_CDE 필드 분석 스크립트
모든 shapefile에서 FTR_CDE 값과 파일명의 관계를 분석
"""

from collections import defaultdict

import geopandas as gpd

from src.common.config import RAW_DATA_DIR


def analyze_ftr_cde() -> None:
    """모든 shapefile에서 FTR_CDE 값 분석"""

    # 결과를 저장할 딕셔너리
    file_ftr_mapping: dict[str, set[str]] = defaultdict(set)
    ftr_file_mapping: dict[str, set[str]] = defaultdict(set)
    ftr_count_mapping: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # 모든 shapefile 찾기
    shapefiles = list(RAW_DATA_DIR.rglob("*.shp"))

    print("=" * 80)
    print("FTR_CDE 필드 분석 시작")
    print("=" * 80)

    for shapefile in sorted(shapefiles):
        try:
            # shapefile 읽기
            gdf = gpd.read_file(shapefile, encoding="euc-kr")

            # 파일명 (경로 제외)
            filename = shapefile.stem  # .shp 확장자 제외

            # FTR_CDE 필드가 있는지 확인
            if "FTR_CDE" in gdf.columns:
                # 고유한 FTR_CDE 값들
                unique_ftr_codes = gdf["FTR_CDE"].dropna().unique()

                for ftr_code in unique_ftr_codes:
                    file_ftr_mapping[filename].add(ftr_code)
                    ftr_file_mapping[ftr_code].add(filename)
                    # 각 파일에서 해당 FTR_CDE를 가진 레코드 수
                    count = len(gdf[gdf["FTR_CDE"] == ftr_code])
                    ftr_count_mapping[ftr_code][filename] = count

        except Exception as e:
            print(f"오류 발생 ({shapefile.name}): {e}")

    # 결과 출력
    print("\n" + "=" * 80)
    print("1. 파일별 FTR_CDE 값")
    print("=" * 80)

    for filename in sorted(file_ftr_mapping.keys()):
        ftr_codes = sorted(file_ftr_mapping[filename])
        print(f"\n{filename}:")
        print(f"  FTR_CDE 값: {', '.join(ftr_codes)}")

    print("\n" + "=" * 80)
    print("2. FTR_CDE별 포함된 파일")
    print("=" * 80)

    for ftr_code in sorted(ftr_file_mapping.keys()):
        files = sorted(ftr_file_mapping[ftr_code])
        total_count = sum(ftr_count_mapping[ftr_code].values())
        print(f"\n{ftr_code}: (총 {total_count}개 레코드)")
        for filename in files:
            count = ftr_count_mapping[ftr_code][filename]
            print(f"  - {filename}: {count}개")

    # 패턴 분석
    print("\n" + "=" * 80)
    print("3. 패턴 분석")
    print("=" * 80)

    # SA로 시작하는 코드들 분석
    sa_codes = [code for code in ftr_file_mapping if code.startswith("SA")]
    sa_codes.sort()

    print("\n3.1 SA 코드 분석:")
    print(f"  총 {len(sa_codes)}개의 SA 코드 발견: {', '.join(sa_codes)}")

    # 파일명과 FTR_CDE의 관계 분석
    print("\n3.2 파일명과 FTR_CDE 관계:")

    # WTL (Water Line) 관련
    wtl_files = [f for f in file_ftr_mapping if "WTL" in f]
    print("\n  WTL (상수도) 관련 파일:")
    for filename in sorted(wtl_files):
        codes = sorted(file_ftr_mapping[filename])
        print(f"    {filename}: {', '.join(codes)}")

    # WEA (Water Equipment Area?) 관련
    wea_files = [f for f in file_ftr_mapping if "WEA" in f]
    print("\n  WEA (구역) 관련 파일:")
    for filename in sorted(wea_files):
        codes = sorted(file_ftr_mapping[filename])
        print(f"    {filename}: {', '.join(codes)}")

    # V_ 접두사 파일들
    v_files = [f for f in file_ftr_mapping if f.startswith("V_")]
    print("\n  V_ (View?) 접두사 파일:")
    for filename in sorted(v_files):
        codes = sorted(file_ftr_mapping[filename])
        print(f"    {filename}: {', '.join(codes)}")

    # 코드별 설명 추론
    print("\n" + "=" * 80)
    print("4. FTR_CDE 의미 추론")
    print("=" * 80)

    code_descriptions = {
        "SA001": "상수관로 (V_WTL_PIPE_LM에서 사용)",
        "SA002": "제수변 (WTL_VALV_PS에서 사용)",
        "SA003": "소화전 (WTL_FIRE_PS에서 사용)",
        "SA117": "급수관 (V_WTL_SPLY_LS에서 사용)",
        "SA118": "급수관 (V_WTL_SPLY_LS에서 사용)",
        "SA119": "급수관 (V_WTL_SPLY_LS에서 사용)",
        "SA200": "급수관 (V_WTL_SPLY_LS에서 사용)",
        "SA206": "급수관 (V_WTL_SPLY_LS에서 사용)",
    }

    for code, desc in sorted(code_descriptions.items()):
        if code in ftr_file_mapping:
            total_count = sum(ftr_count_mapping[code].values())
            print(f"\n{code}: {desc}")
            print(f"  - 총 {total_count}개 레코드")
            print(f"  - 포함 파일: {', '.join(sorted(ftr_file_mapping[code]))}")


if __name__ == "__main__":
    analyze_ftr_cde()
