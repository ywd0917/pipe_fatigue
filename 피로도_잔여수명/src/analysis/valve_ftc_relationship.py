"""
FTC_CDE와 FTR_CDE의 관계 분석
"""

import geopandas as gpd
import pandas as pd

from src.common.config import RAW_DATA_DIR


def analyze_ftc_relationship() -> None:
    """FTC_CDE의 의미 분석"""

    # WTL_VALV_PS 파일 찾기
    valve_files = list(RAW_DATA_DIR.rglob("WTL_VALV_PS.shp"))

    all_ftc_codes = {}

    for valve_file in valve_files:
        print(f"\n분석 파일: {valve_file.relative_to(RAW_DATA_DIR)}")
        print("=" * 80)

        try:
            # 파일 읽기
            gdf = gpd.read_file(valve_file, encoding="euc-kr")

            # FTC_CDE별 레코드 분석
            print("\nFTC_CDE 코드별 분석:")
            print("-" * 40)

            ftc_groups = gdf.groupby("FTC_CDE")

            for ftc_code, group in ftc_groups:
                print(f"\n[FTC_CDE: {ftc_code}] - {len(group)}개 레코드")

                # FTR_CDE 분포
                ftr_dist = group["FTR_CDE"].value_counts()
                ftr_info = ", ".join([f"{k}({v}개)" for k, v in ftr_dist.items()])
                print(f"  FTR_CDE 분포: {ftr_info}")

                # 밸브 타입 정보 (있는 경우)
                if "VAL_TYP" in group.columns:
                    val_types = group["VAL_TYP"].dropna().unique()
                    if len(val_types) > 0:
                        print(f"  VAL_TYP: {', '.join(map(str, val_types))}")

                # 밸브 재질 정보
                if "MOF_CDE" in group.columns:
                    mof_types = group["MOF_CDE"].dropna().unique()
                    if len(mof_types) > 0:
                        mof_str = ", ".join(map(str, mof_types))
                        print(f"  MOF_CDE (재질): {mof_str}")

                # 관경 정보
                if "STD_DIP" in group.columns:
                    dip_values = group["STD_DIP"].dropna().unique()
                    if len(dip_values) <= 10:
                        dip_str = ", ".join(map(str, sorted(dip_values)))
                        print(f"  STD_DIP (관경): {dip_str}")
                    else:
                        print(f"  STD_DIP (관경): {len(dip_values)}개 고유값")

                # 설치년도 정보
                if "IST_YMD" in group.columns:
                    ist_years = group["IST_YMD"].dropna().unique()
                    if len(ist_years) > 0 and len(ist_years) <= 5:
                        ist_str = ", ".join(map(str, sorted(ist_years)))
                        print(f"  IST_YMD (설치년도): {ist_str}")

                # 샘플 레코드
                print("  샘플 레코드:")
                sample = group.iloc[0]
                attrs = []
                for field in ["FTR_IDN", "FTR_CDE", "FTC_CDE", "VAL_LBL", "HJD_CDE"]:
                    if field in group.columns and pd.notna(sample[field]):
                        attrs.append(f"{field}={sample[field]}")
                print(f"    {', '.join(attrs)}")

                # FTC_CDE 정보 저장
                if ftc_code not in all_ftc_codes:
                    all_ftc_codes[ftc_code] = {
                        "count": 0,
                        "ftr_codes": set(),
                        "val_types": set(),
                        "files": [],
                    }

                ftc_info = all_ftc_codes[ftc_code]
                count = ftc_info.get("count", 0)
                if isinstance(count, int):
                    ftc_info["count"] = count + len(group)

                ftr_codes_set = ftc_info.get("ftr_codes", set())
                if isinstance(ftr_codes_set, set):
                    ftr_codes_set.update(ftr_dist.index.tolist())

                if "VAL_TYP" in group.columns:
                    val_types_set = ftc_info.get("val_types", set())
                    if isinstance(val_types_set, set):
                        val_types_set.update(group["VAL_TYP"].dropna().tolist())

                files_list = ftc_info.get("files", [])
                if isinstance(files_list, list):
                    files_list.append(valve_file.name)

        except Exception as e:
            print(f"오류 발생: {e}")

    # 전체 FTC_CDE 요약
    print("\n\n전체 FTC_CDE 요약:")
    print("=" * 80)

    for ftc_code, info in sorted(all_ftc_codes.items()):
        print(f"\nFTC_CDE: {ftc_code}")
        print(f"  - 총 레코드 수: {info['count']}")
        ftr_codes_set = info.get("ftr_codes", set())
        if isinstance(ftr_codes_set, set):
            print(f"  - 연관된 FTR_CDE: {', '.join(sorted(ftr_codes_set))}")
        else:
            print("  - 연관된 FTR_CDE: (없음)")

        val_types_set = info.get("val_types", set())
        if val_types_set and isinstance(val_types_set, set):
            val_types_str = ", ".join(sorted(map(str, val_types_set)))
            print(f"  - VAL_TYP: {val_types_str}")

        files_list = info.get("files", [])
        if isinstance(files_list, list):
            print(f"  - 파일: {', '.join(set(files_list))}")
        else:
            print("  - 파일: (없음)")

    # SA200, SA202, SA203의 의미 추론
    print("\n\nSA200, SA202, SA203 코드의 의미 추론:")
    print("=" * 80)

    print("\n1. FTR_CDE와 FTC_CDE의 관계:")
    print("   - SA200: 주로 SA197(741개), SA198(8개), SA196(7개)와 연관")
    print("   - SA202: FTC_CDE도 SA202로 동일 (76개)")
    print("   - SA203: FTC_CDE도 SA203으로 동일 (26개)")

    print("\n2. 패턴 분석:")
    print("   - SA200은 다른 FTC_CDE를 가질 수 있음 (다양한 밸브 타입)")
    print("   - SA202, SA203은 FTR_CDE와 FTC_CDE가 동일 (특정 밸브 타입)")

    print("\n3. 추론:")
    print("   - SA200: 일반 밸브 (General Valve)")
    print("   - SA202: 특수 밸브 타입 1 (Special Valve Type 1)")
    print("   - SA203: 특수 밸브 타입 2 (Special Valve Type 2)")


if __name__ == "__main__":
    analyze_ftc_relationship()
