"""
피로 손상 계산 관련 모듈

이 모듈은 다음 기능을 제공합니다:
- K 계수 계산 (K_material, K_age, K_diameter, K_soil, K_traffic 등)
- 피로 손상 계산 (D_base, D_final)
- 잔여 수명 계산
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# 모듈 import
from pipe_thickness import calculate_thickness_for_dataframe
from soil_loader_k import get_k_soil_for_dataframe
from traffic_loader import get_k_traffic_for_dataframe

# 공통 설정 import
from common.config import (
    HIGH_FREQ_FATIGUE_MULTIPLIER,
    DEFAULT_FATIGUE_LIMIT,
    DEFAULT_PIPE_TYPE,
)


def get_K_material_mapping(pipe_properties: pd.DataFrame) -> Dict[str, float]:
    """
    파이프 속성 데이터프레임에서 타입별 재료계수(K_material) 매핑 딕셔너리를 생성

    Args:
        pipe_properties: 파이프 속성 데이터프레임

    Returns:
        Dict[str, float]: 파이프 타입별 재료계수(K_material) 매핑
    """
    if pipe_properties.empty:
        print("파이프 속성 데이터가 비어있습니다.")
        return {}

    if (
        "type" not in pipe_properties.columns
        or "KmaterialK" not in pipe_properties.columns
    ):
        print("파이프 속성 데이터에 'type' 또는 'KmaterialK' 컬럼이 없습니다.")
        return {}

    # 재료계수(K_material) 매핑 딕셔너리 생성
    k_material_map = dict(zip(pipe_properties["type"], pipe_properties["KmaterialK"]))

    print(f"재료계수(K_material) 매핑 생성 완료: {len(k_material_map)}개 파이프 타입")
    for pipe_type, coeff in k_material_map.items():
        print(f"  - {pipe_type}: {coeff}")

    return k_material_map


def get_fatigue_limit_mapping(pipe_properties: pd.DataFrame) -> Dict[str, float]:
    """
    파이프 속성 데이터프레임에서 타입별 피로한계 매핑 딕셔너리를 생성

    Args:
        pipe_properties: 파이프 속성 데이터프레임

    Returns:
        Dict[str, float]: 파이프 타입별 피로한계 매핑
    """
    if pipe_properties.empty:
        print("파이프 속성 데이터가 비어있습니다.")
        return {}

    if (
        "type" not in pipe_properties.columns
        or "fatigure_limit" not in pipe_properties.columns
    ):
        print("파이프 속성 데이터에 'type' 또는 'fatigure_limit' 컬럼이 없습니다.")
        return {}

    # 피로한계 값 처리 (10⁶ 이상 -> DEFAULT_FATIGUE_LIMIT, 10⁵ -> 100000)
    fatigue_limit_map: Dict[str, float] = {}
    for _, row in pipe_properties.iterrows():
        pipe_type = row["type"]
        fatigue_limit_str = str(row["fatigure_limit"])

        if "10⁶" in fatigue_limit_str or "1000000" in fatigue_limit_str:
            fatigue_limit_map[pipe_type] = DEFAULT_FATIGUE_LIMIT
        elif "10⁵" in fatigue_limit_str or "100000" in fatigue_limit_str:
            fatigue_limit_map[pipe_type] = 100000
        else:
            try:
                # 숫자로 변환 시도
                value = float(fatigue_limit_str)
                # NaN 체크
                if pd.isna(value) or fatigue_limit_str.upper() == "NAN":
                    fatigue_limit_map[pipe_type] = DEFAULT_FATIGUE_LIMIT
                else:
                    fatigue_limit_map[pipe_type] = value
            except (ValueError, TypeError):
                # 기본값 설정
                fatigue_limit_map[pipe_type] = DEFAULT_FATIGUE_LIMIT

    print(f"피로한계 매핑 생성 완료: {len(fatigue_limit_map)}개 파이프 타입")

    return fatigue_limit_map


def add_K_material_to_dataframe(
    result_df: pd.DataFrame, pipe_properties: pd.DataFrame, file_type: str = "PIPE_LM"
) -> pd.DataFrame:
    """
    DataFrame에 재료계수(K_material)와 피로한계 컬럼을 추가

    Args:
        result_df: 결과 데이터프레임
        pipe_properties: 파이프 속성 데이터프레임
        file_type: 파일 타입 ("PIPE_LM" 또는 "SPLY_LS")

    Returns:
        pd.DataFrame: 재료계수(K_material)와 피로한계가 추가된 데이터프레임
    """
    print(f"\n{'='*60}")
    print("재료계수(K_material) 및 피로한계 추가")
    print(f"{'='*60}")

    try:
        # 데이터프레임 복사
        result_df = result_df.copy()
        print(f"데이터프레임 크기: {len(result_df):,}행, {len(result_df.columns)}컬럼")

        # 파이프 타입 컬럼 확인
        pipe_type_column = None
        for col in ["PIP_TYPE", "pipe_type", "type"]:
            if col in result_df.columns:
                pipe_type_column = col
                break

        if pipe_type_column is None:
            print(
                "파이프 타입 컬럼을 찾을 수 없습니다. (PIP_TYPE, pipe_type, type 중 하나가 필요)"
            )
            return result_df

        print(f"파이프 타입 컬럼: {pipe_type_column}")

        # PIP_TYPE이 비어있는 경우 카운트
        null_pipe_type_count = result_df[pipe_type_column].isna().sum()
        if null_pipe_type_count > 0:
            print(f"\n경고: PIP_TYPE이 비어있는 행: {null_pipe_type_count:,}개")
            print(
                f"      → 이러한 행들은 DEFAULT_PIPE_TYPE({DEFAULT_PIPE_TYPE}) 값을 사용합니다."
            )

        # 재료계수(K_material) 매핑 딕셔너리 생성
        k_material_map = get_K_material_mapping(pipe_properties)

        if not k_material_map:
            print("재료계수(K_material) 매핑을 생성할 수 없습니다.")
            print("기본값을 사용합니다.")
            k_material_map = {}

        # 피로한계 매핑 딕셔너리 생성
        fatigue_limit_map = get_fatigue_limit_mapping(pipe_properties)

        # design_pressure 매핑 딕셔너리 생성
        design_pressure_map = {}
        if "design_pressure" in pipe_properties.columns:
            # NaN이 아닌 값만 매핑에 포함
            valid_design_pressure = pipe_properties[
                pipe_properties["design_pressure"].notna()
            ]
            design_pressure_map = dict(
                zip(
                    valid_design_pressure["type"],
                    valid_design_pressure["design_pressure"],
                )
            )
            print(f"설계압력 매핑 생성 완료: {len(design_pressure_map)}개 파이프 타입")

        # design_pressure 컬럼 추가 (PIP_TYPE 바로 다음에 위치하도록)
        if design_pressure_map:
            # 커스텀 매핑 함수 정의
            def get_design_pressure_with_default(pipe_type: Any) -> Optional[float]:
                """PIP_TYPE에 따른 design_pressure 반환 (None 및 ETC 처리 포함)"""
                if pd.isna(pipe_type) or pipe_type is None:
                    # PIP_TYPE이 None인 경우 DEFAULT_PIPE_TYPE 사용
                    return design_pressure_map.get(DEFAULT_PIPE_TYPE)
                elif pipe_type == "ETC" and "ETC" not in design_pressure_map:
                    # ETC 타입인데 매핑이 없으면 DEFAULT_PIPE_TYPE 사용
                    return design_pressure_map.get(DEFAULT_PIPE_TYPE)
                else:
                    # 일반적인 매핑
                    mapped_value = design_pressure_map.get(pipe_type)
                    if mapped_value is None and pipe_type not in ["", None]:
                        # 매핑되지 않은 경우 DEFAULT_PIPE_TYPE 사용
                        return design_pressure_map.get(DEFAULT_PIPE_TYPE)
                    return mapped_value

            result_df["design_pressure"] = result_df[pipe_type_column].apply(
                get_design_pressure_with_default
            )

        # thickness 컬럼 추가 (STD_DIP을 기준으로 계산)
        if "STD_DIP" in result_df.columns:
            try:
                # ETC 타입과 None을 DEFAULT_PIPE_TYPE으로 변환한 임시 컬럼 생성
                temp_material_column = pipe_type_column + "_for_thickness"

                def convert_pipe_type_for_thickness(pipe_type: Any) -> str:
                    """thickness 계산을 위한 pipe_type 변환"""
                    if pd.isna(pipe_type) or pipe_type is None or pipe_type == "ETC":
                        return DEFAULT_PIPE_TYPE
                    else:
                        return pipe_type

                result_df[temp_material_column] = result_df[pipe_type_column].apply(
                    convert_pipe_type_for_thickness
                )

                result_df["thickness"] = calculate_thickness_for_dataframe(
                    result_df,
                    diameter_column="STD_DIP",
                    material_column=temp_material_column,
                    strict_mode=False,  # 범위 벗어난 값에 대해 에러 발생하지 않음.
                )

                # 임시 컬럼 삭제
                result_df.drop(columns=[temp_material_column], inplace=True)

                print(
                    f"두께 컬럼 추가 완료: {result_df['thickness'].notna().sum():,}개 행에 두께값 계산됨"
                )
            except ValueError as e:
                print(f"\n두께 계산 실패: {e}")
                print("프로그램을 종료합니다.")
                import sys

                sys.exit(1)
        else:
            print("경고: STD_DIP 컬럼을 찾을 수 없어 두께를 계산할 수 없습니다.")

        # K_diameter 컬럼 추가 (STD_DIP 필요)
        if "STD_DIP" in result_df.columns:
            result_df["K_diameter"] = 1 + 0.05 * np.log(result_df["STD_DIP"] / 100)
            print(
                f"K_diameter 컬럼 추가 완료: {result_df['K_diameter'].notna().sum():,}개 행에 K_diameter 계산됨"
            )
        else:
            print("경고: STD_DIP 컬럼을 찾을 수 없어 K_diameter를 계산할 수 없습니다.")

        # K_age 컬럼 추가 (YEARS_SINCE_BEG 필요)
        if "YEARS_SINCE_BEG" in result_df.columns:
            result_df["K_age"] = 1 + 0.02 * result_df["YEARS_SINCE_BEG"]
            print(
                f"K_age 컬럼 추가 완료: {result_df['K_age'].notna().sum():,}개 행에 K_age 계산됨"
            )
        else:
            print(
                "경고: YEARS_SINCE_BEG 컬럼을 찾을 수 없어 K_age를 계산할 수 없습니다."
            )

        # K_soil 컬럼 추가 (FTR_IDN 필요)
        if "FTR_IDN" in result_df.columns:
            # file_type에 따라 soil_file_type 결정
            if file_type == "PIPE_LM":
                soil_file_type = "pipe"
            elif file_type == "SPLY_LS":
                soil_file_type = "supply"
            else:
                soil_file_type = "pipe"  # 기본값

            # 지역 컬럼 확인
            region_column = None
            for col in ["GRID_CD", "region", "MID_AREA_CD"]:
                if col in result_df.columns:
                    region_column = col
                    break

            if region_column:
                # GRID_CD나 MID_AREA_CD가 있는 경우 해당 지역값 추출
                regions = result_df[region_column].unique()
                if len(regions) == 1:
                    region = str(regions[0])
                    print(f"K_soil 계산에 사용할 지역: {region}")
                    result_df["K_soil"] = get_k_soil_for_dataframe(
                        result_df,
                        file_type=soil_file_type,
                        region=region,
                        default_value=1.2,
                    )
                else:
                    print(
                        f"경고: 여러 지역이 포함되어 있습니다: {regions}. 전체 매핑을 사용합니다."
                    )
                    result_df["K_soil"] = get_k_soil_for_dataframe(
                        result_df,
                        file_type=soil_file_type,
                        region="all",
                        default_value=1.2,
                    )
            else:
                print("경고: 지역 컬럼을 찾을 수 없어 전체 매핑을 사용합니다.")
                result_df["K_soil"] = get_k_soil_for_dataframe(
                    result_df, file_type=soil_file_type, region="all", default_value=1.2
                )

            print(
                f"K_soil 컬럼 추가 완료: {result_df['K_soil'].notna().sum():,}개 행에 K_soil 계산됨"
            )
        else:
            print("경고: FTR_IDN 컬럼을 찾을 수 없어 K_soil을 계산할 수 없습니다.")

        # K_traffic 컬럼 추가 (FTR_IDN 필요)
        if "FTR_IDN" in result_df.columns:
            # file_type에 따라 traffic_file_type 결정
            if file_type == "PIPE_LM":
                traffic_file_type = "pipe"
            elif file_type == "SPLY_LS":
                traffic_file_type = "supply"
            else:
                traffic_file_type = "pipe"  # 기본값

            # 지역 컬럼 확인
            region_column = None
            for col in ["GRID_CD", "region", "MID_AREA_CD"]:
                if col in result_df.columns:
                    region_column = col
                    break

            if region_column:
                # GRID_CD나 MID_AREA_CD가 있는 경우 해당 지역값 추출
                regions = result_df[region_column].unique()
                if len(regions) == 1:
                    region = str(regions[0])
                    print(f"K_traffic 계산에 사용할 지역: {region}")
                    result_df["K_traffic"] = get_k_traffic_for_dataframe(
                        result_df,
                        file_type=traffic_file_type,
                        region=region,
                        default_value=1.0,
                    )
                else:
                    print(
                        f"경고: 여러 지역이 포함되어 있습니다: {regions}. 전체 매핑을 사용합니다."
                    )
                    result_df["K_traffic"] = get_k_traffic_for_dataframe(
                        result_df,
                        file_type=traffic_file_type,
                        region="all",
                        default_value=1.0,
                    )
            else:
                print("경고: 지역 컬럼을 찾을 수 없어 전체 매핑을 사용합니다.")
                result_df["K_traffic"] = get_k_traffic_for_dataframe(
                    result_df,
                    file_type=traffic_file_type,
                    region="all",
                    default_value=1.0,
                )

            print(
                f"K_traffic 컬럼 추가 완료: {result_df['K_traffic'].notna().sum():,}개 행에 K_traffic 계산됨"
            )
        else:
            print("경고: FTR_IDN 컬럼을 찾을 수 없어 K_traffic을 계산할 수 없습니다.")

        # K_vibration 컬럼 추가 (고정값)
        result_df["K_vibration"] = 1.05
        print(
            f"K_vibration 컬럼 추가 완료: {len(result_df):,}개 행에 K_vibration = 1.05 설정"
        )

        # hoop_stress 컬럼 추가 (압력, 두께, 직경 필요)
        hoop_stress_count = 0
        if (
            "STD_DIP" in result_df.columns
            and "thickness" in result_df.columns
            and "design_pressure" in result_df.columns
        ):
            # PIPE_LM과 SPLY_LS 모두 design_pressure 사용하여 통일
            # 두께가 0이 아닌 경우에만 계산
            valid_thickness_mask = (result_df["thickness"] > 0) & (
                result_df["thickness"].notna()
            )
            result_df.loc[valid_thickness_mask, "hoop_stress"] = (
                result_df.loc[valid_thickness_mask, "design_pressure"]
                * result_df.loc[valid_thickness_mask, "STD_DIP"]
                / (2 * result_df.loc[valid_thickness_mask, "thickness"])
            )
            hoop_stress_count = result_df["hoop_stress"].notna().sum()

            print(
                f"hoop_stress 컬럼 추가 완료: {hoop_stress_count:,}개 행에 hoop_stress 계산됨"
            )
        else:
            missing_cols = []
            if "STD_DIP" not in result_df.columns:
                missing_cols.append("STD_DIP")
            if "thickness" not in result_df.columns:
                missing_cols.append("thickness")
            if "design_pressure" not in result_df.columns:
                missing_cols.append("design_pressure")
            print(
                f"경고: hoop_stress 계산에 필요한 컬럼이 없습니다: {', '.join(missing_cols)}"
            )

        # K_stress 컬럼 추가 (hoop_stress와 design_pressure 필요)
        k_stress_count = 0
        if (
            "hoop_stress" in result_df.columns
            and hoop_stress_count > 0
            and "design_pressure" in result_df.columns
        ):
            # 설계압력이 0이 아닌 경우에만 계산
            valid_design_pressure_mask = (result_df["design_pressure"] > 0) & (
                result_df["design_pressure"].notna()
            )
            result_df.loc[valid_design_pressure_mask, "K_stress"] = 1 + 0.2 * (
                result_df.loc[valid_design_pressure_mask, "hoop_stress"]
                / result_df.loc[valid_design_pressure_mask, "design_pressure"]
                - 1
            )
            k_stress_count = result_df["K_stress"].notna().sum()
            print(f"K_stress 컬럼 추가 완료: {k_stress_count:,}개 행에 K_stress 계산됨")
        else:
            if "hoop_stress" not in result_df.columns or hoop_stress_count == 0:
                print(
                    "경고: hoop_stress가 계산되지 않아 K_stress를 계산할 수 없습니다."
                )
            elif "design_pressure" not in result_df.columns:
                print(
                    "경고: design_pressure 컬럼이 없어 K_stress를 계산할 수 없습니다."
                )

        # K_material 컬럼 추가 (파이프 타입별 매핑)
        if k_material_map:
            # ETC와 GP를 위한 특별 매핑 추가
            k_material_map_extended = k_material_map.copy()
            if DEFAULT_PIPE_TYPE in k_material_map and "ETC" not in k_material_map:
                k_material_map_extended["ETC"] = k_material_map[
                    DEFAULT_PIPE_TYPE
                ]  # ETC는 DEFAULT_PIPE_TYPE 값 사용

            # 매핑 적용
            result_df["K_material"] = result_df[pipe_type_column].map(
                k_material_map_extended
            )

            # 매핑되지 않은 값에 대한 보수적 처리
            unmapped_mask = result_df["K_material"].isna()
            unmapped_count = unmapped_mask.sum()

            if unmapped_count > 0:
                unmapped_types = result_df.loc[unmapped_mask, pipe_type_column].unique()
                print(
                    f"경고: {unmapped_count}개 행의 파이프 타입이 매핑되지 않았습니다: {unmapped_types}"
                )
                # DEFAULT_PIPE_TYPE 값으로 보수적 계산
                default_value = k_material_map.get(DEFAULT_PIPE_TYPE, 3.0)
                result_df.loc[unmapped_mask, "K_material"] = default_value
                print(
                    f"보수적 계산을 위해 {DEFAULT_PIPE_TYPE} 값({default_value})을 사용합니다."
                )

            mapped_count = (~unmapped_mask).sum()
            print(
                f"재료계수(K_material) 컬럼 추가 완료: {mapped_count:,}개 행에 매핑됨"
            )

            # 재료계수(K_material) 분포 출력
            k_material_distribution = (
                result_df["K_material"].value_counts().sort_index()
            )
            print("\n재료계수(K_material) 분포:")
            for coeff, count in k_material_distribution.items():
                print(
                    f"  - K_material = {coeff}: {count:,}개 ({count/len(result_df)*100:.1f}%)"
                )
        else:
            print("경고: 재료계수(K_material) 매핑이 없어 기본값 1.0을 사용합니다.")
            result_df["K_material"] = 1.0

        # K_total 컬럼 추가 (모든 K 계수의 곱)
        k_columns = [
            "K_diameter",
            "K_age",
            "K_soil",
            "K_traffic",
            "K_vibration",
            "K_material",
            "K_stress",
        ]
        available_k_columns = [col for col in k_columns if col in result_df.columns]

        if available_k_columns:
            # K_total 계산
            result_df["K_total"] = 1.0
            for col in available_k_columns:
                # NaN 값은 1.0으로 처리
                result_df["K_total"] *= result_df[col].fillna(1.0)

            print(
                f"K_total 컬럼 추가 완료: {result_df['K_total'].notna().sum():,}개 행에 K_total 계산됨"
            )
            print(f"사용된 K 계수: {', '.join(available_k_columns)}")

            # K_total 분포 출력
            print("\nK_total 통계:")
            print(f"  - 최소값: {result_df['K_total'].min():.3f}")
            print(f"  - 최대값: {result_df['K_total'].max():.3f}")
            print(f"  - 평균값: {result_df['K_total'].mean():.3f}")
            print(f"  - 중앙값: {result_df['K_total'].median():.3f}")
        else:
            print("경고: K 계수 컬럼이 없어 K_total을 계산할 수 없습니다.")

        # 피로한계 컬럼 추가 (fatigue_limit)
        if fatigue_limit_map:
            # ETC와 GP를 위한 특별 매핑 추가
            fatigue_limit_map_extended = fatigue_limit_map.copy()
            if (
                DEFAULT_PIPE_TYPE in fatigue_limit_map
                and "ETC" not in fatigue_limit_map
            ):
                fatigue_limit_map_extended["ETC"] = fatigue_limit_map[
                    DEFAULT_PIPE_TYPE
                ]  # ETC는 DEFAULT_PIPE_TYPE 값 사용

            # 매핑 적용
            result_df["fatigue_limit"] = result_df[pipe_type_column].map(
                fatigue_limit_map_extended
            )

            # 매핑되지 않은 값에 대한 보수적 처리
            unmapped_mask = result_df["fatigue_limit"].isna()
            unmapped_count = unmapped_mask.sum()

            if unmapped_count > 0:
                # DEFAULT_PIPE_TYPE 값으로 보수적 계산
                default_value = fatigue_limit_map.get(
                    DEFAULT_PIPE_TYPE, DEFAULT_FATIGUE_LIMIT
                )
                result_df.loc[unmapped_mask, "fatigue_limit"] = default_value

            mapped_count = (~unmapped_mask).sum()
            print(
                f"피로한계(fatigue_limit) 컬럼 추가 완료: {mapped_count:,}개 행에 매핑됨"
            )

            # 피로한계 분포 출력
            fatigue_limit_distribution = (
                result_df["fatigue_limit"].value_counts().sort_index()
            )
            print("\n피로한계(fatigue_limit) 분포:")
            for limit, count in fatigue_limit_distribution.items():
                if isinstance(limit, (int, float)):
                    limit_str = f"{limit:.0e}" if limit >= 100000 else f"{limit:.0f}"
                else:
                    limit_str = str(limit)
                print(f"  - {limit_str}: {count:,}개 ({count/len(result_df)*100:.1f}%)")
        else:
            print(
                f"경고: 피로한계 매핑이 없어 기본값 {DEFAULT_FATIGUE_LIMIT:.0e}을 사용합니다."
            )
            result_df["fatigue_limit"] = DEFAULT_FATIGUE_LIMIT

        # 경고: 중요 컬럼 누락 검사
        critical_columns = ["K_total", "fatigue_limit"]
        missing_critical = [
            col for col in critical_columns if col not in result_df.columns
        ]
        if missing_critical:
            print(
                f"\n{'!'*60}\n중요 경고: 다음 컬럼이 생성되지 않았습니다: {', '.join(missing_critical)}\n{'!'*60}"
            )

        return result_df

    except Exception as e:
        print(f"재료계수(K_material) 추가 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return result_df


def calculate_fatigue_damage_dataframe(
    result_df: pd.DataFrame,
    region: str,
    data_type: str = "pressure",
    use_k_total: bool = True,
) -> pd.DataFrame:
    """
    데이터프레임의 Rain Flow Counting 결과를 사용하여 피로 손상을 계산

    Args:
        result_df: 결과 데이터프레임
        region: 지역 코드 (예: '0470', '0520')
        data_type: 데이터 타입 (기본값: 'pressure')
        use_k_total: K_total 사용 여부

    Returns:
        pd.DataFrame: 피로 손상이 추가된 데이터프레임
    """
    print(f"\n{'='*60}")
    print(f"{region} 지역 피로 손상 계산")
    print(f"{'='*60}")

    # 필요한 컬럼 존재 여부 확인
    required_columns = []

    # Rain Flow 관련 컬럼
    high_total_col = f"{region}_high_total_cycles"
    low_total_col = f"{region}_low_total_cycles"
    required_columns.extend([high_total_col, low_total_col])

    # 피로한계 컬럼
    if "fatigue_limit" not in result_df.columns:
        print(
            f"경고: fatigue_limit 컬럼이 없습니다. 기본값 {DEFAULT_FATIGUE_LIMIT:.0e}을 사용합니다."
        )
        result_df["fatigue_limit"] = DEFAULT_FATIGUE_LIMIT

    # K_total 컬럼 (선택적)
    if use_k_total and "K_total" not in result_df.columns:
        print("경고: K_total 컬럼이 없습니다. K_total 없이 계산합니다.")
        use_k_total = False

    # 누락된 컬럼 확인
    missing_columns = [col for col in required_columns if col not in result_df.columns]
    if missing_columns:
        print(f"오류: 필요한 컬럼이 없습니다: {missing_columns}")
        return result_df

    # 연간 사이클 수 계산을 위한 나이 정보 확인
    if "YEARS_SINCE_BEG" in result_df.columns:
        print("나이 정보를 사용하여 연간 사이클 수를 계산합니다.")
        years_column = "YEARS_SINCE_BEG"
    else:
        print("경고: YEARS_SINCE_BEG 컬럼이 없습니다. 사이클 수를 그대로 사용합니다.")
        years_column = None

    # 1. High 주파수 피로도 계산 (중간값)
    # 주의: high_total_col은 이제 연간 사이클 수를 직접 저장하므로 나이로 나누지 않음
    high_fatigue_col = f"{region}_high_fatigue_intermediate"
    result_df[high_fatigue_col] = result_df[high_total_col] / (
        result_df["fatigue_limit"] * HIGH_FREQ_FATIGUE_MULTIPLIER
    )

    print(
        f"High 주파수 피로도 중간값 계산 완료: {result_df[high_fatigue_col].notna().sum():,}개 행"
    )

    # 2. Low 주파수 피로도 계산 (중간값)
    # 주의: low_total_col은 이제 연간 사이클 수를 직접 저장하므로 나이로 나누지 않음
    low_fatigue_col = f"{region}_low_fatigue_intermediate"
    result_df[low_fatigue_col] = result_df[low_total_col] / result_df["fatigue_limit"]

    print(
        f"Low 주파수 피로도 중간값 계산 완료: {result_df[low_fatigue_col].notna().sum():,}개 행"
    )

    # 3. 기본손상도 (D_base) 계산
    D_base_col = f"{region}_D_base"
    result_df[D_base_col] = result_df[high_fatigue_col] + result_df[low_fatigue_col]
    print(
        f"기본손상도 (D_base) 계산 완료: {result_df[D_base_col].notna().sum():,}개 행"
    )

    # 4a. K_repair 적용 전 보정손상도 (D_final_org) 계산
    D_final_org_col = f"{region}_D_final_org"
    if use_k_total and "K_total_without_repair" in result_df.columns:
        result_df[D_final_org_col] = result_df[D_base_col] * result_df["K_total_without_repair"]
        print(
            f"K_repair 적용 전 보정손상도 (D_final_org = D_base × K_total_without_repair) 계산 완료: {result_df[D_final_org_col].notna().sum():,}개 행"
        )

    # 4b. 보정손상도 (D_final) 계산 - K_total 적용
    D_final_col = f"{region}_D_final"
    if use_k_total:
        result_df[D_final_col] = result_df[D_base_col] * result_df["K_total"]
        print(
            f"보정손상도 (D_final = D_base × K_total) 계산 완료: {result_df[D_final_col].notna().sum():,}개 행"
        )
    else:
        result_df[D_final_col] = result_df[D_base_col]
        print(
            f"보정손상도 (D_final = D_base) 계산 완료: {result_df[D_final_col].notna().sum():,}개 행"
        )

    # 5. 통계 출력
    print(f"\n{region} 지역 피로 손상 통계:")

    # High 주파수 피로도 통계
    print("\nHigh 주파수 피로도 중간값:")
    print(f"  - 최소값: {result_df[high_fatigue_col].min():.6f}")
    print(f"  - 최대값: {result_df[high_fatigue_col].max():.6f}")
    print(f"  - 평균값: {result_df[high_fatigue_col].mean():.6f}")
    print(f"  - 중앙값: {result_df[high_fatigue_col].median():.6f}")

    # Low 주파수 피로도 통계
    print("\nLow 주파수 피로도 중간값:")
    print(f"  - 최소값: {result_df[low_fatigue_col].min():.6f}")
    print(f"  - 최대값: {result_df[low_fatigue_col].max():.6f}")
    print(f"  - 평균값: {result_df[low_fatigue_col].mean():.6f}")
    print(f"  - 중앙값: {result_df[low_fatigue_col].median():.6f}")

    # 기본손상도 통계
    print("\n기본손상도 (D_base):")
    print(f"  - 최소값: {result_df[D_base_col].min():.6f}")
    print(f"  - 최대값: {result_df[D_base_col].max():.6f}")
    print(f"  - 평균값: {result_df[D_base_col].mean():.6f}")
    print(f"  - 중앙값: {result_df[D_base_col].median():.6f}")

    # 보정손상도 통계
    print("\n보정손상도 (D_final):")
    print(f"  - 최소값: {result_df[D_final_col].min():.6f}")
    print(f"  - 최대값: {result_df[D_final_col].max():.6f}")
    print(f"  - 평균값: {result_df[D_final_col].mean():.6f}")
    print(f"  - 중앙값: {result_df[D_final_col].median():.6f}")

    # 고위험 파이프 확인 (D_final > 1.0)
    high_risk_mask = result_df[D_final_col] > 1.0
    high_risk_count = high_risk_mask.sum()
    if high_risk_count > 0:
        print(
            f"\n⚠️ 경고: {high_risk_count:,}개 파이프의 보정손상도가 100%를 초과했습니다!"
        )
        print("  (D_final > 1.0은 보정손상도가 100% 이상임을 의미)")

    return result_df