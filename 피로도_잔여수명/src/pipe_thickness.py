"""
파이프 두께 계산 모듈
관경(직경)에 따른 파이프 두께를 계산하는 함수들을 제공
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from scipy.interpolate import interp1d


# 재질별 관경-두께 매핑 테이블
THICKNESS_TABLES = {
    "DT": {
        # 관경(mm): 두께(mm) - K9 기준
        80: 6.0,
        100: 6.0,
        150: 6.0,
        200: 6.3,
        250: 6.8,
        300: 7.2,
        350: 8.1,
        400: 8.6,
        500: 9.5,
        600: 10.7,
        700: 11.9,
        800: 13.1,
        900: 14.3,
        1000: 15.5,
    },
    "ST": {
        # 호칭경(A): 두께(mm)
        25: 3.25,
        32: 3.25,
        40: 3.25,
        50: 3.65,
        65: 3.65,
        80: 4.05,
        100: 4.5,
        125: 4.85,
        150: 4.85,
        200: 5.85,
        250: 6.4,
        300: 7,
        350: 11.1,
        400: 12.7,
        450: 14.3,
        500: 15.1,
        550: 15.9,
        600: 17.5,
        650: 18.9,
        700: 19.8,
        750: 20.6,
        800: 21.4,
        900: 23,
        1000: 24.6,
    },
    "EPS": {
        # 호칭경: 두께(mm) (STWW 400 A급 및 소구경)
        50: 3.2,  # 50A (2") 최소값
        80: 3.8,  # 80A (3") 최소값
        100: 4.0,  # 100A (4") 최소값
        150: 4.5,  # 150A (6") 최소값
        200: 5.0,  # 200A (8") 최소값
        250: 5.5,  # 250A (10") 최소값
        300: 6.0,  # 300A (12") 최소값
        350: 6,
        400: 6,
        450: 6,
        500: 6,
        600: 6,
        700: 7,
        800: 8,
        900: 8,
        1000: 9,
        1100: 10,
        1200: 11,
        1350: 12,
        1500: 14,
    },
    "STS": {
        # 호칭지름(mm): Sch 10S 두께(mm)
        6: 1.0,
        8: 1.2,
        10: 1.2,
        15: 2.1,
        20: 2.1,
        25: 2.8,
        32: 2.8,
        40: 2.8,
        50: 2.8,
        65: 3,
        80: 3,
        100: 3,
        125: 3.4,
        150: 3.4,
        200: 4,
        250: 4,
        300: 4.5,
    },
    "PE": {
        # 관경(mm): PE100 SDR11 (PN16) 내부 두께(mm)
        50: 4.6,
        75: 6.8,
        100: 9.1,
        150: 13.7,
        200: 18.2,
        250: 22.7,
        300: 27.3,
    },
    "PFP": {
        # 호칭지름(A): STWW 370 두께(mm) + KS 흑관/백관 파이프 기준
        15: 2.65,  # KS 흑관/백관
        20: 2.65,  # KS 흑관/백관
        25: 3.25,  # KS 흑관/백관
        32: 3.25,  # KS 흑관/백관
        40: 3.25,  # KS 흑관/백관
        50: 3.65,  # KS 흑관/백관
        65: 3.65,  # KS 흑관/백관
        80: 4.5,
        100: 4.9,
        125: 5.1,
        150: 5.5,
        200: 6.4,
        250: 6.4,
        300: 6.4,
        350: 6,
        400: 6,
        450: 6,
        500: 6,
        600: 6,
        700: 7,
        800: 8,
        900: 8,
        1000: 9,
        1100: 10,
        1200: 11,
        1350: 12,
        1500: 14,
        1600: 15,
    },
    "GP": {
        # 호칭지름(A): 아연도금 강관 두께(mm)
        6: 2.0,
        8: 2.35,
        10: 2.35,
        15: 2.65,
        20: 2.65,
        25: 3.25,
        32: 3.25,
        40: 3.25,
        50: 3.65,
        65: 3.65,
        80: 4.05,
        100: 4.5,
        150: 4.85,
        200: 5.85,
    },
    "CI": {
        # 관경(mm): 주철관 두께(mm) - 평균값 사용
        200: 11.9,  # 11.9 ~ 16.5
        300: 17.5,  # 17.5 ~ 20.3
        400: 20.3,  # 20.3 ~ 23.4
        500: 22.6,  # 22.6 ~ 26.2
    },
    "PVC": {
        # 호칭 지름(mm): 최소 벽두께 t(mm) (해당 PN 등급)
        13: 1.6,  # PN25
        16: 1.6,  # PN16
        20: 1.5,  # PN12.5
        25: 1.6,  # PN10
        30: 1.8,  # PN10
        35: 2.0,  # PN10
        40: 2.3,  # PN10
        50: 2.3,  # PN8
        65: 2.9,  # PN8
        75: 3.4,  # PN8
        100: 3.5,  # PN8
        125: 4.2,  # PN8
        150: 5.0,  # PN8
        200: 6.5,  # PN8
        250: 8.1,  # PN8
        300: 9.6,  # PN8
        350: 10.9,  # PN8
        400: 9.8,  # PN6
        450: 11.0,  # PN6
        500: 12.3,  # PN6
        560: 13.7,  # PN6
        630: 15.4,  # PN6
    },
    "PB": {
        # 호칭경(mm): 벽 두께(mm) ± 공차
        16: 1.5,  # 1.5 ± 0.3
        20: 1.9,  # 1.9 ± 0.3
        25: 2.3,  # 2.3 ± 0.4
        32: 2.9,  # 2.9 ± 0.4
        40: 3.7,  # 3.7 ± 0.5
        50: 4.6,  # 4.6 ± 0.6
        63: 5.8,  # 5.8 ± 0.7
        75: 6.8,  # 6.8 ± 0.8
    },
    "SPOL": {
        # 공칭 지름(DN): 강관 두께 - B형 (표준)
        80: 4.2,  # 80 A
        100: 5.8,  # 100 A
        200: 5.8,  # 200 A
        300: 6.4,  # 300 A
        400: 6.0,  # 400 A
        600: 6.0,  # 600 A
        700: 6.0,  # 700 A
        800: 7.0,  # 800 A
        1000: 8.0,  # 1000 A
        1500: 11.0,  # 1500 A
        2000: 15.0,  # 2000 A
        2500: 18.0,  # 2500 A
        3000: 22.0,  # 3000 A
    },
    "HIVP": {
        # 공칭지름(A): 벽두께 (PN10)
        25: 1.9,  # 25A (DN25)
        50: 2.9,  # 50A (DN50)
        65: 3.6,  # 65A (DN65)
        75: 4.2,  # 75A (DN75)
        100: 4.4,  # 100A (DN100)
        125: 5.4,  # 125A (DN125)
        150: 6.3,  # 150A (DN150)
        200: 8.3,  # 200A (DN200)
        250: 10.3,  # 250A (DN250)
        300: 12.2,  # 300A (DN300)
    },
}


def get_pipe_thickness(
    diameter: float, material_type: str, strict_mode: bool = False
) -> Optional[float]:
    """
    파이프 재질과 관경에 따른 두께를 계산

    Args:
        diameter: 관경 (mm)
        material_type: 파이프 재질 타입 (예: 'DT', 'ST', 'DTC' 등)
        strict_mode: True일 경우 범위 벗어난 값에 대해 에러 발생

    Returns:
        Optional[float]: 계산된 두께 (mm), 계산할 수 없는 경우 None

    Raises:
        ValueError: strict_mode=True이고 지름이 테이블 범위를 벗어난 경우

    Note:
        테이블 범위를 벗어난 경우의 처리:
        - 최소값보다 작은 경우: 테이블의 최소 두께값 반환
        - 최대값보다 큰 경우: 마지막 두 데이터 포인트의 기울기로 선형 외삽
        - strict_mode=False여도 범위를 벗어난 경우 경고 메시지 출력
    """
    # DTC와 DTEP는 DT와 동일한 테이블 사용
    if material_type in ["DTC", "DTEP"]:
        material_type = "DT"

    # 재질에 대한 테이블이 없는 경우
    if material_type not in THICKNESS_TABLES:
        return None

    thickness_table = THICKNESS_TABLES[material_type]

    # 테이블이 비어있는 경우
    if not thickness_table:
        return None

    # 정확히 일치하는 값이 있는 경우
    if int(diameter) in thickness_table and diameter == int(diameter):
        return thickness_table[int(diameter)]

    # 보간이 필요한 경우
    diameters = sorted(thickness_table.keys())
    thicknesses = [thickness_table[d] for d in diameters]

    # 범위를 벗어난 경우
    if diameter < diameters[0] or diameter > diameters[-1]:
        if strict_mode:
            error_msg = (
                f"오류: {material_type} 재질의 지름 {diameter}mm는 "
                f"테이블 범위({diameters[0]}mm ~ {diameters[-1]}mm)를 벗어났습니다."
            )
            print(error_msg)
            raise ValueError(error_msg)
        else:
            # strict_mode=False여도 경고 메시지 출력
            warning_msg = (
                f"경고: {material_type} 재질의 지름 {diameter}mm는 "
                f"테이블 범위({diameters[0]}mm ~ {diameters[-1]}mm)를 벗어났습니다. "
            )

            # 기존 동작: 최소값보다 작으면 최소값 사용, 최대값보다 크면 외삽
            if diameter < diameters[0]:
                print(warning_msg + f"최소 두께값 {thicknesses[0]}mm를 사용합니다.")
                return thicknesses[0]
            else:
                # 최대값보다 큰 경우 선형 외삽
                slope = (thicknesses[-1] - thicknesses[-2]) / (
                    diameters[-1] - diameters[-2]
                )
                extrapolated = thicknesses[-1] + slope * (diameter - diameters[-1])
                print(
                    warning_msg + f"선형 외삽으로 {extrapolated:.2f}mm를 계산했습니다."
                )
                return extrapolated
    else:
        # 선형 보간
        interpolator = interp1d(diameters, thicknesses, kind="linear")
        return float(interpolator(diameter))


def calculate_thickness_for_dataframe(
    df: pd.DataFrame,
    diameter_column: str = "STD_DIP",
    material_column: str = "PIP_TYPE",
    strict_mode: bool = False,
) -> pd.Series:
    """
    데이터프레임의 각 행에 대해 파이프 두께를 계산

    Args:
        df: 파이프 데이터가 포함된 데이터프레임
        diameter_column: 관경 컬럼명 (기본값: 'STD_DIP')
        material_column: 재질 타입 컬럼명 (기본값: 'PIP_TYPE')
        strict_mode: True일 경우 범위 벗어난 값에 대해 에러 발생

    Returns:
        pd.Series: 계산된 두께 값들

    Raises:
        ValueError: strict_mode=True이고 지름이 테이블 범위를 벗어난 경우

    Note:
        테이블 범위를 벗어난 경우의 처리:
        - 최소값보다 작은 경우: 테이블의 최소 두께값 사용
        - 최대값보다 큰 경우: 마지막 두 데이터 포인트의 기울기로 선형 외삽
        - strict_mode=False여도 범위를 벗어난 경우 경고 메시지 출력
    """
    # 결과를 저장할 시리즈
    thickness_series = pd.Series(index=df.index, dtype=float)

    # 필요한 컬럼이 있는지 확인
    if diameter_column not in df.columns:
        print(f"경고: '{diameter_column}' 컬럼을 찾을 수 없습니다.")
        return pd.Series(np.nan, index=df.index)

    if material_column not in df.columns:
        print(f"경고: '{material_column}' 컬럼을 찾을 수 없습니다.")
        return pd.Series(np.nan, index=df.index)

    # 각 행에 대해 두께 계산
    for idx, row in df.iterrows():
        diameter = row[diameter_column]
        material = row[material_column]

        # 유효한 값인지 확인
        if pd.notna(diameter) and pd.notna(material):
            try:
                thickness = get_pipe_thickness(
                    float(diameter), str(material), strict_mode=strict_mode
                )
                if thickness is not None:
                    thickness_series[idx] = thickness
                else:
                    thickness_series[idx] = np.nan
            except ValueError:
                if strict_mode:
                    raise  # strict_mode에서는 에러를 다시 발생시킴
                else:
                    thickness_series[idx] = np.nan
        else:
            thickness_series[idx] = np.nan

    return thickness_series


def add_thickness_to_dataframe(
    df: pd.DataFrame,
    diameter_column: str = "STD_DIP",
    material_column: str = "PIP_TYPE",
    after_column: str = "design_pressure",
) -> pd.DataFrame:
    """
    데이터프레임에 두께 컬럼을 추가하고 지정된 컬럼 뒤에 배치

    Args:
        df: 파이프 데이터가 포함된 데이터프레임
        diameter_column: 관경 컬럼명 (기본값: 'STD_DIP')
        material_column: 재질 타입 컬럼명 (기본값: 'PIP_TYPE')
        after_column: 두께 컬럼을 배치할 기준 컬럼 (기본값: 'design_pressure')

    Returns:
        pd.DataFrame: 두께 컬럼이 추가된 데이터프레임
    """
    # 데이터프레임 복사
    result_df = df.copy()

    # 두께 계산
    result_df["thickness"] = calculate_thickness_for_dataframe(
        result_df, diameter_column, material_column
    )

    # 컬럼 순서 재배치
    cols = list(result_df.columns)

    # thickness를 after_column 바로 다음으로 이동
    if "thickness" in cols and after_column in cols:
        cols.remove("thickness")
        after_idx = cols.index(after_column)
        cols.insert(after_idx + 1, "thickness")
        result_df = result_df[cols]

    # 통계 출력
    valid_thickness = result_df["thickness"].dropna()
    if len(valid_thickness) > 0:
        print("\n두께 계산 완료:")
        print(f"  - 계산된 행 수: {len(valid_thickness):,}개")
        print(f"  - 평균 두께: {valid_thickness.mean():.2f}mm")
        print(f"  - 최소 두께: {valid_thickness.min():.2f}mm")
        print(f"  - 최대 두께: {valid_thickness.max():.2f}mm")

        # 재질별 통계
        if material_column in result_df.columns:
            print("\n재질별 두께 통계:")
            material_stats = result_df.groupby(material_column)["thickness"].agg(
                ["count", "mean", "min", "max"]
            )
            for material, stats in material_stats.iterrows():
                if stats["count"] > 0:
                    print(
                        f"  - {material}: {stats['count']:,}개, "
                        f"평균 {stats['mean']:.2f}mm, "
                        f"최소 {stats['min']:.2f}mm, "
                        f"최대 {stats['max']:.2f}mm"
                    )
    else:
        print("\n경고: 계산된 두께 값이 없습니다.")

    return result_df


def get_thickness_summary(
    df: pd.DataFrame,
    thickness_column: str = "thickness",
    material_column: str = "PIP_TYPE",
) -> pd.DataFrame:
    """
    두께 데이터의 요약 통계를 반환

    Args:
        df: 두께 데이터가 포함된 데이터프레임
        thickness_column: 두께 컬럼명 (기본값: 'thickness')
        material_column: 재질 타입 컬럼명 (기본값: 'PIP_TYPE')

    Returns:
        pd.DataFrame: 재질별 두께 요약 통계
    """
    if thickness_column not in df.columns:
        print(f"경고: '{thickness_column}' 컬럼을 찾을 수 없습니다.")
        return pd.DataFrame()

    if material_column not in df.columns:
        # 재질 구분 없이 전체 통계만 반환
        overall_summary = df[thickness_column].describe()
        return pd.DataFrame(overall_summary).T

    # 재질별 그룹화하여 통계 계산
    grouped = df.groupby(material_column)[thickness_column]

    # 기본 통계량
    summary: pd.DataFrame = grouped.agg(["count", "mean", "std", "min", "max"])

    # 분위수 계산
    quantiles: pd.DataFrame = grouped.agg(
        [
            lambda x: x.quantile(0.25),
            lambda x: x.quantile(0.5),
            lambda x: x.quantile(0.75),
        ]
    )
    quantiles.columns = ["q25", "median", "q75"]

    # 결과 합치기
    result = pd.concat([summary, quantiles], axis=1).round(2)

    return result


# 향후 추가될 재질별 테이블을 위한 함수
def add_material_thickness_table(
    material_type: str, thickness_table: Dict[int, float]
) -> None:
    """
    새로운 재질의 관경-두께 테이블을 추가

    Args:
        material_type: 재질 타입 (예: 'ST', 'PVC' 등)
        thickness_table: 관경(mm)을 키로, 두께(mm)를 값으로 하는 딕셔너리
    """
    THICKNESS_TABLES[material_type] = thickness_table
    print(f"{material_type} 재질의 두께 테이블이 추가되었습니다.")
    print(f"  - 데이터 포인트: {len(thickness_table)}개")
    print(
        f"  - 관경 범위: {min(thickness_table.keys())}mm ~ {max(thickness_table.keys())}mm"
    )


if __name__ == "__main__":
    # 테스트 코드
    print("파이프 두께 계산 모듈 테스트")
    print("=" * 50)

    # DT 재질 테스트
    test_diameters = [80, 100, 125, 200, 350, 750, 1200]
    print("\nDT 재질 두께 계산 테스트:")
    for d in test_diameters:
        thickness = get_pipe_thickness(d, "DT")
        if thickness is not None:
            print(f"  관경 {d}mm → 두께 {thickness:.2f}mm")
        else:
            print(f"  관경 {d}mm → 계산 불가")

    # 데이터프레임 테스트
    print("\n데이터프레임 테스트:")
    test_df = pd.DataFrame(
        {
            "STD_DIP": [100, 200, 350, 500, 700, 150, 600, 1200, 2000],
            "PIP_TYPE": ["DT", "DT", "DT", "DT", "DT", "ST", "ST", "ST", "ST"],
        }
    )

    test_df["thickness"] = calculate_thickness_for_dataframe(test_df)
    print(test_df)