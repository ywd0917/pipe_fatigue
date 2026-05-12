"""도로 데이터의 속성 필드를 상세 분석하는 스크립트."""

import sys
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR  # noqa: E402
from src.road_loader import load_road_data  # noqa: E402


def analyze_sig_cd_mapping() -> dict[str, str]:
    """시군구 코드 매핑 정보"""
    # 대구광역시 시군구 코드 매핑
    return {
        "27110": "중구",
        "27140": "동구",
        "27170": "서구",
        "27200": "남구",
        "27230": "북구",
        "27260": "수성구",
        "27290": "달서구",
        "27710": "달성군",
        "27720": "군위군",
    }


def analyze_road_attributes() -> None:
    """도로 속성 상세 분석"""
    # 도로 데이터 로드
    print("도로 데이터 로딩 중...")
    gdf = load_road_data(RAW_DATA_DIR)
    if gdf is None:
        print("도로 데이터 로드 실패")
        return

    print("\n" + "=" * 80)
    print("대구광역시 도로 네트워크 속성 분석 (TL_SPRD_MANAGE)")
    print("=" * 80)

    # 필드별 상세 설명
    field_descriptions = {
        "BSI_INT_SN": "기초구간 일련번호 (Basic Section Internal Serial Number)",
        "EVE_BSI_MN": "짝수쪽 기초번호 (Even side Basic Main Number)",
        "EVE_BSI_SL": "짝수쪽 기초번호 보조번호 (Even side Basic Sub Number)",
        "ODD_BSI_MN": "홀수쪽 기초번호 (Odd side Basic Main Number)",
        "ODD_BSI_SL": "홀수쪽 기초번호 보조번호 (Odd side Basic Sub Number)",
        "OPERT_DE": "운영일자 (Operation Date)",
        "RDS_MAN_NO": "도로관리번호 (Road Management Number)",
        "SIG_CD": "시군구코드 (City/County/District Code)",
    }

    print("\n### 필드 설명")
    for field, desc in field_descriptions.items():
        print(f"- **{field}**: {desc}")

    # 각 필드별 상세 분석
    print("\n### 필드별 상세 분석")

    # 1. BSI_INT_SN 분석
    print("\n#### 1. BSI_INT_SN (기초구간 일련번호)")
    print(f"- 전체 구간 수: {len(gdf):,}")
    print(f"- 고유 구간 수: {gdf['BSI_INT_SN'].nunique():,}")
    print(f"- 중복 구간 수: {len(gdf) - gdf['BSI_INT_SN'].nunique():,}")
    print(f"- 번호 범위: {gdf['BSI_INT_SN'].min()} ~ {gdf['BSI_INT_SN'].max()}")

    # 2. 시군구별 도로 통계
    print("\n#### 2. SIG_CD (시군구코드) 분석")
    sig_cd_map = analyze_sig_cd_mapping()
    sig_stats = gdf["SIG_CD"].value_counts()

    print("시군구별 도로 구간 수:")
    total_length = 0
    for sig_cd, count in sig_stats.items():
        district_name = sig_cd_map.get(sig_cd, "알 수 없음")
        percentage = (count / len(gdf)) * 100
        print(f"  - {sig_cd} ({district_name}): {count:,}개 ({percentage:.1f}%)")

        # 해당 구의 도로 총 길이 계산
        district_gdf = gdf[gdf["SIG_CD"] == sig_cd]
        district_length = district_gdf.geometry.length.sum() / 1000  # km 단위
        total_length += district_length
        print(f"    도로 총 길이: {district_length:,.1f} km")

    print(f"\n전체 도로 총 길이: {total_length:,.1f} km")

    # 3. 도로관리번호 분석
    print("\n#### 3. RDS_MAN_NO (도로관리번호)")
    print(f"- 고유 도로 수: {gdf['RDS_MAN_NO'].nunique():,}")
    print(f"- 도로당 평균 구간 수: {len(gdf) / gdf['RDS_MAN_NO'].nunique():.1f}")

    # 가장 많은 구간을 가진 도로 Top 10
    top_roads = gdf["RDS_MAN_NO"].value_counts().head(10)
    print("\n구간이 가장 많은 도로 Top 10:")
    for road_no, count in top_roads.items():
        print(f"  - 도로번호 {road_no}: {count}개 구간")

    # 4. 주소 번호 분석
    print("\n#### 4. 주소 번호 체계 분석")
    print(
        f"- 짝수쪽 기초번호 범위: {gdf['EVE_BSI_MN'].min()} ~ {gdf['EVE_BSI_MN'].max()}"
    )
    print(
        f"- 홀수쪽 기초번호 범위: {gdf['ODD_BSI_MN'].min()} ~ {gdf['ODD_BSI_MN'].max()}"
    )
    print(
        f"- 짝수쪽 보조번호 범위: {gdf['EVE_BSI_SL'].min()} ~ {gdf['EVE_BSI_SL'].max()}"
    )
    print(
        f"- 홀수쪽 보조번호 범위: {gdf['ODD_BSI_SL'].min()} ~ {gdf['ODD_BSI_SL'].max()}"
    )

    # 5. 운영일자 분석
    print("\n#### 5. OPERT_DE (운영일자)")
    valid_dates = gdf[gdf["OPERT_DE"].notna()]["OPERT_DE"]
    null_count = gdf["OPERT_DE"].isnull().sum()

    print(f"- NULL 값: {null_count:,}개 ({(null_count/len(gdf)*100):.1f}%)")
    print(
        f"- 유효한 날짜: {len(valid_dates):,}개 ({(len(valid_dates)/len(gdf)*100):.1f}%)"
    )

    if len(valid_dates) > 0:
        # 날짜 형식 분석
        date_lengths = valid_dates.str.len().value_counts()
        print("\n날짜 형식별 개수:")
        for length, count in date_lengths.items():
            print(f"  - {length}자리: {count:,}개")
            # 샘플 출력
            sample = valid_dates[valid_dates.str.len() == length].iloc[0]
            print(f"    예시: {sample}")

        # 년도별 통계 (8자리 날짜 기준)
        dates_8digit = valid_dates[valid_dates.str.len() == 8]
        if len(dates_8digit) > 0:
            years = dates_8digit.str[:4].value_counts().sort_index()
            print("\n년도별 운영 시작 도로 수 (8자리 날짜 기준):")
            for year, count in years.tail(10).items():
                print(f"  - {year}년: {count:,}개")

    # 결과를 파일로 저장
    output_file = RESULTS_DIR / "road_attributes_analysis.txt"
    print(f"\n분석 결과를 {output_file}에 저장합니다...")

    with Path(output_file).open("w", encoding="utf-8") as f:
        # 위의 모든 출력을 파일에도 저장
        f.write("대구광역시 도로 네트워크 속성 분석 (TL_SPRD_MANAGE)\n")
        f.write("=" * 80 + "\n\n")

        f.write("### 필드 설명\n")
        for field, desc in field_descriptions.items():
            f.write(f"- **{field}**: {desc}\n")

        f.write("\n### 데이터 요약\n")
        f.write(f"- 전체 도로 구간 수: {len(gdf):,}\n")
        f.write(f"- 전체 도로 총 길이: {total_length:,.1f} km\n")
        f.write(f"- 고유 도로 수: {gdf['RDS_MAN_NO'].nunique():,}\n")
        f.write(f"- 시군구 수: {gdf['SIG_CD'].nunique()}\n")


if __name__ == "__main__":
    analyze_road_attributes()
