"""
재질 코드(MOF_CDE)와 FTR_CDE의 관계 분석
"""

import geopandas as gpd
import pandas as pd

from src.common.config import RAW_DATA_DIR


def analyze_material_codes() -> None:
    """재질 코드 분석"""

    # WTL_VALV_PS 파일 찾기
    valve_files = list(RAW_DATA_DIR.rglob("WTL_VALV_PS.shp"))

    material_info = {}

    for valve_file in valve_files:
        print(f"\n분석 파일: {valve_file.relative_to(RAW_DATA_DIR)}")
        print("=" * 80)

        try:
            # 파일 읽기
            gdf = gpd.read_file(valve_file, encoding="euc-kr")

            # SA200, SA202, SA203별 재질 코드 분석
            target_codes = ["SA200", "SA202", "SA203"]

            print("\n재질 코드(MOF_CDE) 분석:")
            print("-" * 40)

            for ftr_code in target_codes:
                code_records = gdf[gdf["FTR_CDE"] == ftr_code]

                if len(code_records) > 0:
                    print(f"\n[{ftr_code}] - {len(code_records)}개 레코드")

                    # 재질 코드 분포
                    if "MOF_CDE" in code_records.columns:
                        mof_dist = code_records["MOF_CDE"].value_counts(dropna=False)

                        print("  재질 코드 분포:")
                        for mof, count in mof_dist.items():
                            if pd.isna(mof):
                                print(f"    (없음): {count}개")
                            else:
                                # 재질 코드별 특징 확인
                                mof_records = code_records[
                                    code_records["MOF_CDE"] == mof
                                ]

                                # 관경 범위
                                if "STD_DIP" in mof_records.columns:
                                    dip_values = mof_records["STD_DIP"].dropna()
                                    if len(dip_values) > 0:
                                        dip_min = dip_values.min()
                                        dip_max = dip_values.max()
                                        dip_range = f"관경 {dip_min}-{dip_max}"
                                    else:
                                        dip_range = "관경 정보 없음"
                                else:
                                    dip_range = ""

                                print(f"    {mof}: {count}개 ({dip_range})")

                                # 재질 정보 저장
                                if mof not in material_info:
                                    material_info[mof] = {
                                        "ftr_codes": set(),
                                        "count": 0,
                                    }
                                ftr_codes = material_info[mof]["ftr_codes"]
                                if isinstance(ftr_codes, set):
                                    ftr_codes.add(ftr_code)
                                material_info[mof]["count"] += count

            # VAL_STD 필드 분석 (SA203 특징 확인)
            print("\n\nVAL_STD (밸브 규격) 분석:")
            print("-" * 40)

            for ftr_code in target_codes:
                code_records = gdf[gdf["FTR_CDE"] == ftr_code]

                if len(code_records) > 0 and "VAL_STD" in code_records.columns:
                    val_std_values = code_records["VAL_STD"].dropna().unique()

                    if len(val_std_values) > 0:
                        print(f"\n[{ftr_code}]의 VAL_STD 값:")
                        for val in val_std_values[:10]:  # 최대 10개만
                            print(f"  - {val}")
                        if len(val_std_values) > 10:
                            print(f"  ... 외 {len(val_std_values) - 10}개")

        except Exception as e:
            print(f"오류 발생: {e}")

    # 재질 코드 요약
    print("\n\n재질 코드 전체 요약:")
    print("=" * 80)

    # 재질 코드별 정리
    print("\n재질 코드 범위별 분류:")
    print("-" * 40)

    # 01XX 시리즈 (일반 재질)
    series_01 = {
        k: v for k, v in material_info.items() if k and str(k).startswith("01")
    }
    if series_01:
        print("\n01XX 시리즈 (일반 재질):")
        for mof, info in sorted(series_01.items()):
            ftr_codes_set = info["ftr_codes"]
            if isinstance(ftr_codes_set, set):
                ftr_codes_str = ", ".join(sorted(ftr_codes_set))
            else:
                ftr_codes_str = ""
            count = info["count"]
            print(f"  {mof}: {ftr_codes_str} ({count}개)")

    # 03XX 시리즈 (특수 재질)
    series_03 = {
        k: v for k, v in material_info.items() if k and str(k).startswith("03")
    }
    if series_03:
        print("\n03XX 시리즈 (특수 재질):")
        for mof, info in sorted(series_03.items()):
            ftr_codes_set = info["ftr_codes"]
            if isinstance(ftr_codes_set, set):
                ftr_codes_str = ", ".join(sorted(ftr_codes_set))
            else:
                ftr_codes_str = ""
            count = info["count"]
            print(f"  {mof}: {ftr_codes_str} ({count}개)")

    # 04XX 시리즈
    series_04 = {
        k: v for k, v in material_info.items() if k and str(k).startswith("04")
    }
    if series_04:
        print("\n04XX 시리즈:")
        for mof, info in sorted(series_04.items()):
            ftr_codes_set = info["ftr_codes"]
            if isinstance(ftr_codes_set, set):
                ftr_codes_str = ", ".join(sorted(ftr_codes_set))
            else:
                ftr_codes_str = ""
            count = info["count"]
            print(f"  {mof}: {ftr_codes_str} ({count}개)")

    # 결론
    print("\n\n분석 결론:")
    print("=" * 80)
    print("\nSA200, SA202, SA203의 구분 기준:")
    print("1. SA200: 일반 밸브 (재질 01XX, 04XX 시리즈)")
    print("2. SA202: 특수 밸브 타입 1 (재질 01XX, 04XX 시리즈)")
    print("3. SA203: 특수 밸브 타입 2 (재질 03XX 시리즈 - 특수 재질)")
    print("\n특히 SA203은 03XX 시리즈 재질만 사용하며, VAL_STD에 치수 정보가 포함됨")
    print("(예: B1500 X L1500 X H1000 = 폭1500 X 길이1500 X 높이1000)")


if __name__ == "__main__":
    analyze_material_codes()
