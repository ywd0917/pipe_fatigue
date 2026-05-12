"""
WTL_VALV_PS 파일에서 SA200, SA202, SA203 코드의 의미 분석
"""

import geopandas as gpd
import pandas as pd

from src.common.config import RAW_DATA_DIR


def analyze_valve_codes() -> None:
    """WTL_VALV_PS 파일에서 SA200, SA202, SA203 코드 분석"""

    # WTL_VALV_PS 파일 찾기
    valve_files = list(RAW_DATA_DIR.rglob("WTL_VALV_PS.shp"))

    target_codes = ["SA200", "SA202", "SA203"]

    for valve_file in valve_files:
        print(f"\n분석 파일: {valve_file.relative_to(RAW_DATA_DIR)}")
        print("=" * 80)

        try:
            # 파일 읽기
            gdf = gpd.read_file(valve_file, encoding="euc-kr")

            # 1. 모든 컬럼 정보 출력
            print("\n1. WTL_VALV_PS 파일의 모든 컬럼:")
            print("-" * 40)
            for col in gdf.columns:
                if col != "geometry":
                    # 각 컬럼의 고유값 개수도 표시
                    unique_count = gdf[col].nunique()
                    null_count = gdf[col].isna().sum()
                    print(f"  - {col}: {unique_count}개 고유값, {null_count}개 null")

            # 2. FTR_CDE가 타겟 코드인 레코드 찾기
            print(f"\n2. FTR_CDE가 {', '.join(target_codes)}인 레코드 분석:")
            print("-" * 40)

            for code in target_codes:
                code_records = gdf[gdf["FTR_CDE"] == code]

                if len(code_records) > 0:
                    print(f"\n[{code}] - {len(code_records)}개 레코드 발견")

                    # 첫 번째 레코드의 모든 필드 출력
                    first_record = code_records.iloc[0]
                    print("  첫 번째 레코드의 모든 필드:")
                    for col in gdf.columns:
                        if col != "geometry" and pd.notna(first_record[col]):
                            print(f"    {col}: {first_record[col]}")

                    # 밸브 관련 필드 분석
                    valve_fields = [
                        "VAL_TYP",
                        "VAL_NM",
                        "VAL_MOF",
                        "VAL_STD",
                        "VAL_PUR",
                        "VAL_MOD",
                        "VAL_CDE",
                        "FTC_CDE",
                        "SAA_CDE",
                        "FTR_CDE",
                        "HJD_NAM",
                        "RIP_NAM",
                    ]

                    print("\n  주요 밸브 관련 필드 분석:")
                    for field in valve_fields:
                        if field in gdf.columns:
                            unique_vals = code_records[field].dropna().unique()
                            if len(unique_vals) > 0:
                                if len(unique_vals) <= 5:
                                    vals_str = ", ".join(map(str, unique_vals))
                                    print(f"    {field}: {vals_str}")
                                else:
                                    sample_vals = ", ".join(map(str, unique_vals[:3]))
                                    print(
                                        f"    {field}: {len(unique_vals)}개 "
                                        f"고유값 (예: {sample_vals}...)"
                                    )

                    # 샘플 레코드 3개 출력
                    print(f"\n  {code}의 샘플 레코드 (최대 3개):")
                    sample_count = min(3, len(code_records))
                    for idx in range(sample_count):
                        record = code_records.iloc[idx]
                        attrs = []
                        for field in [
                            "FTR_IDN",
                            "VAL_TYP",
                            "VAL_NM",
                            "VAL_MOF",
                            "HJD_NAM",
                        ]:
                            if field in gdf.columns and pd.notna(record[field]):
                                attrs.append(f"{field}={record[field]}")
                        print(f"    [{idx+1}] {', '.join(attrs)}")
                else:
                    print(f"\n[{code}] - 레코드 없음")

            # 3. 밸브 타입별 FTR_CDE 분포 확인
            if "VAL_TYP" in gdf.columns:
                print("\n3. 밸브 타입(VAL_TYP)별 FTR_CDE 분포:")
                print("-" * 40)
                val_typ_ftr = (
                    gdf.groupby(["VAL_TYP", "FTR_CDE"]).size().reset_index(name="count")
                )
                for _, row in val_typ_ftr.iterrows():
                    if row["FTR_CDE"] in target_codes:
                        val_typ = row["VAL_TYP"]
                        ftr_cde = row["FTR_CDE"]
                        count = row["count"]
                        print(f"  VAL_TYP={val_typ}, FTR_CDE={ftr_cde}: {count}개")

            # 4. 다른 코드 테이블 참조 정보 확인
            print("\n4. 코드 참조 정보:")
            print("-" * 40)

            # FTC_CDE와 SAA_CDE 분포 확인
            if "FTC_CDE" in gdf.columns:
                ftc_dist = (
                    gdf[gdf["FTR_CDE"].isin(target_codes)]
                    .groupby(["FTR_CDE", "FTC_CDE"])
                    .size()
                )
                if len(ftc_dist) > 0:
                    print("  FTC_CDE 분포:")
                    for (ftr, ftc), count in ftc_dist.items():
                        print(f"    {ftr} + {ftc}: {count}개")

            if "SAA_CDE" in gdf.columns:
                saa_dist = (
                    gdf[gdf["FTR_CDE"].isin(target_codes)]
                    .groupby(["FTR_CDE", "SAA_CDE"])
                    .size()
                )
                if len(saa_dist) > 0:
                    print("\n  SAA_CDE 분포:")
                    for (ftr, saa), count in saa_dist.items():
                        print(f"    {ftr} + {saa}: {count}개")

        except Exception as e:
            print(f"오류 발생: {e}")


def check_metadata_files() -> None:
    """메타데이터나 코드 설명 파일 확인"""
    print("\n\n메타데이터 파일 검색:")
    print("=" * 80)

    # 가능한 메타데이터 파일 패턴
    patterns = [
        "*.xml",
        "*.txt",
        "*.csv",
        "*.xlsx",
        "*코드*",
        "*code*",
        "*meta*",
        "*설명*",
    ]

    for pattern in patterns:
        files = list(RAW_DATA_DIR.rglob(pattern))
        if files:
            print(f"\n{pattern} 패턴 파일:")
            for f in files:
                print(f"  - {f.relative_to(RAW_DATA_DIR)}")


if __name__ == "__main__":
    analyze_valve_codes()
    check_metadata_files()
