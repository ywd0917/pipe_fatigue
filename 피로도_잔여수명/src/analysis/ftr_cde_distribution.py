#!/usr/bin/env python3
"""
각 파일별 FTR_CDE 분포 확인
"""
import geopandas as gpd
import pandas as pd

from src.common.config import RAW_DATA_DIR


def check_ftr_cde_distribution() -> None:
    """각 파일별 FTR_CDE 분포 확인"""

    print("=" * 80)
    print("파일별 FTR_CDE 분포 확인")
    print("=" * 80)

    # 모든 shapefile 찾기
    shapefiles = list(RAW_DATA_DIR.rglob("*.shp"))

    # 파일별로 분석
    for shapefile in sorted(shapefiles):
        try:
            # shapefile 읽기
            gdf = gpd.read_file(shapefile, encoding="euc-kr")

            # 상대 경로
            rel_path = shapefile.relative_to(RAW_DATA_DIR)

            print(f"\n{rel_path}:")
            print(f"  총 레코드 수: {len(gdf)}")

            if "FTR_CDE" in gdf.columns:
                # FTR_CDE 값별 카운트
                ftr_counts = gdf["FTR_CDE"].value_counts()

                # NULL 값 카운트
                null_count = gdf["FTR_CDE"].isna().sum()

                print("  FTR_CDE 필드 존재: Yes")
                print(f"  고유한 FTR_CDE 개수: {len(ftr_counts)}")
                print(f"  NULL 값 개수: {null_count}")

                if len(ftr_counts) > 0:
                    print("  FTR_CDE 분포:")
                    for code, count in ftr_counts.items():
                        pct = count / len(gdf) * 100
                        print(f"    - {code}: {count}개 ({pct:.1f}%)")
                else:
                    print("  모든 FTR_CDE 값이 NULL입니다.")

                # 하나의 FTR_CDE만 있는지 확인
                if len(ftr_counts) == 1:
                    print("  → 단일 FTR_CDE 파일 ✓")
                elif len(ftr_counts) > 1:
                    print("  → 복수 FTR_CDE 파일 !")

                    # 추가 분석: 다른 필드와의 관계
                    print("\n  추가 분석:")
                    # 예: FTC_CDE와의 관계
                    if "FTC_CDE" in gdf.columns:
                        cross_tab = pd.crosstab(gdf["FTR_CDE"], gdf["FTC_CDE"])
                        print("  FTR_CDE vs FTC_CDE:")
                        cross_str = cross_tab.to_string(line_width=100)
                        print(cross_str.replace("\n", "\n    "))

            else:
                print("  FTR_CDE 필드 존재: No")

        except Exception as e:
            print(f"\n{shapefile.name}: 오류 - {e}")

    print("\n" + "=" * 80)
    print("요약:")
    print("=" * 80)

    # 재분석하여 요약
    single_code_files = []
    multi_code_files = []
    no_code_files = []

    for shapefile in sorted(shapefiles):
        try:
            gdf = gpd.read_file(shapefile, encoding="euc-kr")
            filename = shapefile.stem

            if "FTR_CDE" in gdf.columns:
                unique_codes = gdf["FTR_CDE"].dropna().unique()
                if len(unique_codes) == 1:
                    single_code_files.append((filename, unique_codes[0]))
                elif len(unique_codes) > 1:
                    multi_code_files.append((filename, list(unique_codes)))
                else:
                    no_code_files.append(filename)
            else:
                no_code_files.append(filename)

        except Exception:
            pass

    print(f"\n단일 FTR_CDE 파일 ({len(single_code_files)}개):")
    for filename, code in single_code_files:
        print(f"  - {filename}: {code}")

    if multi_code_files:
        print(f"\n복수 FTR_CDE 파일 ({len(multi_code_files)}개):")
        for filename, codes in multi_code_files:
            print(f"  - {filename}: {', '.join(codes)}")

    if no_code_files:
        print(f"\nFTR_CDE 없는 파일 ({len(no_code_files)}개):")
        for filename in no_code_files:
            print(f"  - {filename}")


if __name__ == "__main__":
    check_ftr_cde_distribution()
