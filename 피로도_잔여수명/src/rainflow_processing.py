"""
Rain Flow Counting 처리 및 데이터 로딩 모듈

이 모듈은 다음 기능을 제공합니다:
- 압력 데이터 로딩 및 날짜 범위 추출
- Rain Flow Counting 계산
- 파이프 데이터 처리
- 나이별 Rain Flow Counting 계산
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

# 기존 모듈 import
from utils import interpolate_nan_values, calculate_sampling_rate
from pass_filter import pass_filter
from rain_flow_counting import rain_flow_counting, analyze_rainflow_cycles
from pipe_data import read_csv_pipe_lm, read_csv_sply_ls
from abnormal_mop_tracker import track_abnormal_mop, print_abnormal_mop_summary

# 공통 설정 import
from common.config import (
    PRESSURE_DATA_FILES,
)


def load_full_data(file_path: str) -> pd.DataFrame:
    """
    전체 데이터 파일을 로드

    Args:
        file_path: 데이터 파일 경로

    Returns:
        pd.DataFrame: 로드된 전체 데이터
    """
    print(f"\n{'='*60}")
    print(f"전체 데이터 로드: {file_path}")
    print(f"{'='*60}")

    # 데이터 로드
    df = pd.read_csv(file_path)
    df["msrmt_dt"] = pd.to_datetime(df["msrmt_dt"])
    df = df.sort_values("msrmt_dt").reset_index(drop=True)

    print(f"전체 데이터 크기: {df.shape}")
    print(f"데이터 기간: {df['msrmt_dt'].min()} ~ {df['msrmt_dt'].max()}")
    print(f"NaN 개수: {df['wtrprsr'].isna().sum()}")

    return df


def extract_date_range_data(
    df: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    지정된 날짜 범위의 데이터를 추출

    Args:
        df: 전체 데이터프레임
        start_date: 시작 날짜 (None이면 2023-01-01 사용)
        end_date: 종료 날짜 (None이면 2023-12-31 사용)

    Returns:
        pd.DataFrame: 지정된 날짜 범위의 데이터
    """
    print(f"\n{'-'*40}")
    print("날짜 범위 데이터 추출")
    print(f"{'-'*40}")

    # 기본값 설정 (2023년 전체)
    if start_date is None:
        start_date = datetime(2023, 1, 1)
    if end_date is None:
        end_date = datetime(2023, 12, 31, 23, 59, 59)

    print(f"시작 날짜: {start_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"종료 날짜: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")

    # 날짜 범위 데이터 필터링
    filtered_df = df[
        (df["msrmt_dt"] >= start_date) & (df["msrmt_dt"] <= end_date)
    ].copy()

    print(f"추출된 데이터 크기: {filtered_df.shape}")
    if not filtered_df.empty:
        print(
            f"추출된 데이터 기간: {filtered_df['msrmt_dt'].min()} ~ {filtered_df['msrmt_dt'].max()}"
        )

        # 기간 계산
        total_days = (
            filtered_df["msrmt_dt"].max() - filtered_df["msrmt_dt"].min()
        ).days + 1
        print(f"총 기간: {total_days}일")

    if filtered_df.empty:
        raise ValueError(
            f"지정된 날짜 범위({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})에 데이터가 없습니다."
        )

    return filtered_df


def process_date_range_data(
    df: pd.DataFrame, file_path: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    지정된 날짜 범위 데이터를 전처리하여 원본, 저대역, 고대역 데이터 반환

    Args:
        df: 날짜 범위 데이터프레임
        file_path: 원본 파일 경로 (필터 적용시 사용)

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: (원본, 저대역, 고대역) 데이터
    """
    print(f"\n{'-'*40}")
    print("날짜 범위 데이터 전처리")
    print(f"{'-'*40}")

    # NaN 값 보간
    pressure_data = interpolate_nan_values(
        np.array(df["wtrprsr"].values), pd.DatetimeIndex(df["msrmt_dt"])
    )

    # 샘플링 주파수 (타임스탬프로부터 자동 감지)
    sampling_rate = calculate_sampling_rate(pd.DatetimeIndex(df["msrmt_dt"]))
    interval_seconds = 1 / sampling_rate
    print(f"샘플링 간격: {interval_seconds:.0f}초 ({interval_seconds/60:.0f}분)")
    print(f"샘플링 주파수: {sampling_rate:.6f} Hz")

    # Pass Filter 적용
    low_pass, high_pass = pass_filter(pressure_data, sampling_rate, file_path)

    print("필터 적용 완료:")
    print(f"  - 원본 데이터 길이: {len(pressure_data)}")
    print(f"  - 저대역 데이터 길이: {len(low_pass)}")
    print(f"  - 고대역 데이터 길이: {len(high_pass)}")

    return pressure_data, low_pass, high_pass


def calculate_rainflow_counting(data: np.ndarray, data_type: str) -> Dict[str, Any]:
    """
    Rain Flow Counting 계산

    Args:
        data: 분석할 데이터
        data_type: 데이터 타입 ("original", "low_pass", "high_pass")

    Returns:
        Dict[str, Any]: Rain Flow Counting 분석 결과
    """
    print(f"\n{'-'*30}")
    print(f"Rain Flow Counting 계산: {data_type}")
    print(f"{'-'*30}")

    # Rain Flow Counting 수행
    cycles = rain_flow_counting(data)

    if not cycles:
        print(f"  경고: {data_type} 데이터에서 사이클을 찾을 수 없습니다.")
        return {
            "data_type": data_type,
            "cycles": [],
            "analysis": {},
            "has_cycles": False,
        }

    # 사이클 분석
    analysis = analyze_rainflow_cycles(cycles)

    print("  Rain Flow Counting 결과:")
    print(f"    - 총 사이클 수: {analysis['total_cycles']:.1f}")
    print(f"    - 전체 사이클: {analysis['full_cycles']}개")
    print(f"    - 반 사이클: {analysis['half_cycles']}개")
    print(f"    - 평균 범위: {analysis['mean_range']:.3f}")
    print(f"    - 최대 범위: {analysis['max_range']:.3f}")
    print(f"    - 표준편차 범위: {analysis['std_range']:.3f}")

    return {
        "data_type": data_type,
        "cycles": cycles,
        "analysis": analysis,
        "has_cycles": True,
    }


def analyze_date_range_rainflow(
    file_path: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    지정된 날짜 범위 데이터의 Rain Flow Counting 분석

    Args:
        file_path: 분석할 파일 경로
        start_date: 시작 날짜 (None이면 2023-01-01 사용)
        end_date: 종료 날짜 (None이면 2023-12-31 사용)

    Returns:
        Dict[str, Any]: 분석 결과
    
    Raises:
        FileNotFoundError: 압력 데이터 파일이 없을 때
    """
    # 파일 존재 확인
    if not Path(file_path).exists():
        raise FileNotFoundError(str(file_path))
    
    file_name = Path(file_path).name

    print(f"\n{'='*80}")
    print(f"날짜 범위 Rain Flow Counting 분석 시작: {file_name}")
    print(f"{'='*80}")

    try:
        # 1. 전체 데이터 로드
        full_df = load_full_data(file_path)

        # 기본값 설정: 명시적 날짜 없으면 데이터 실제 범위에서 최근 1년 사용
        if start_date is None or end_date is None:
            data_end = full_df["msrmt_dt"].max()
            data_start = full_df["msrmt_dt"].min()
            if end_date is None:
                end_date = data_end.to_pydatetime().replace(hour=23, minute=59, second=59)
            if start_date is None:
                # 최근 1년
                candidate = end_date.replace(year=end_date.year - 1)
                start_date = max(candidate, data_start.to_pydatetime())

        print(
            f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        )

        # 2. 지정된 날짜 범위 데이터 추출
        filtered_df = extract_date_range_data(full_df, start_date, end_date)

        # 3. 데이터 전처리 (NaN 보간, 필터링)
        original_data, low_pass_data, high_pass_data = process_date_range_data(
            filtered_df, file_path
        )

        # 4. 각 데이터에 대해 Rain Flow Counting 계산
        results = {
            "original": calculate_rainflow_counting(original_data, "original"),
            "low_pass": calculate_rainflow_counting(low_pass_data, "low_pass"),
            "high_pass": calculate_rainflow_counting(high_pass_data, "high_pass"),
        }

        # 5. 결과 요약
        print(f"\n{'='*60}")
        print(f"분석 완료: {file_name}")
        print(f"{'='*60}")

        return {
            "file_path": file_path,
            "file_name": file_name,
            "start_date": start_date,
            "end_date": end_date,
            "data_count": len(filtered_df),
            "results": results,
            "success": True,
        }

    except Exception as e:
        print(f"파일 {file_name} 분석 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return {
            "file_path": file_path,
            "file_name": file_name,
            "error": str(e),
            "success": False,
        }


def process_pipe_data_with_age(
    file_path: str, file_type: str, output_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    파이프 데이터를 읽어서 현재 날짜와 BEG_YMD 간의 날짜 차이를 계산하여 반환

    Args:
        file_path: 처리할 파일 경로
        file_type: 파일 타입 ("PIPE_LM" 또는 "SPLY_LS")
        output_dir: 출력 디렉토리 (사용하지 않음)

    Returns:
        pd.DataFrame: 날짜 차이가 계산된 데이터프레임
    """
    print(f"\n{'='*80}")
    print(f"{file_type} 파이프 데이터 처리 시작: {file_path}")
    print(f"{'='*80}")

    # 현재 날짜
    current_date = datetime.now()
    print(f"현재 날짜: {current_date.strftime('%Y-%m-%d')}")

    # 선택할 컬럼 목록 (WTP_CDE를 IST_YMD 앞으로 이동, PIP_TYPE 추가)
    # 공통 컬럼 목록
    selected_columns = [
        "FTR_CDE",
        "FTR_IDN",
        "HJD_CDE",
        "SHT_NUM",
        "MNG_CDE",
        "MOP_CDE",
        "STD_DIP",
        "BYC_LEN",
        "JHT_CDE",
        "LOW_DEP",
        "HGH_DEP",
        "CNT_NUM",
        "SYS_CHK",
        "PIP_LBL",
        "GIS_IDN",
        "FTC_CDE",
        "CLS_YMD",
        "GU_CDE",
        "SMZ_NUM",
        "MDZ_NUM",
        "LGZ_NUM",
        "AVG_DEP",
        "WTP_CDE",
        "PIP_TYPE",
        "IST_YMD",
        "FNS_YMD",
        "BEG_YMD",
    ]

    try:
        # 날짜 컬럼 설정
        date_columns = ["IST_YMD", "FNS_YMD", "CLS_YMD"]

        # 파일 타입에 따라 적절한 읽기 함수 선택
        if file_type == "PIPE_LM":
            chunk_reader = read_csv_pipe_lm(
                file_path, chunksize=10000, date_columns=date_columns, verbose=True
            )
        elif file_type == "SPLY_LS":
            chunk_reader = read_csv_sply_ls(
                file_path, chunksize=10000, date_columns=date_columns, verbose=True
            )
        else:
            raise ValueError(f"지원하지 않는 파일 타입: {file_type}")

        # 결과를 저장할 리스트
        processed_chunks = []
        chunk_count = 0
        total_rows = 0

        for chunk in chunk_reader:
            chunk_count += 1

            # 비정상 MOP_CDE 추적
            track_abnormal_mop(chunk, file_type)

            # 파일 타입별 고유 컬럼을 selected_columns에 추가
            columns_to_select = selected_columns.copy()

            # PIPE_LM의 고유 컬럼: IQT_CDE
            if file_type == "PIPE_LM" and "IQT_CDE" in chunk.columns:
                # PIP_LBL 다음에 IQT_CDE 삽입
                idx = columns_to_select.index("GIS_IDN")
                columns_to_select.insert(idx, "IQT_CDE")

            # SPLY_LS의 고유 컬럼: MET_IDN
            elif file_type == "SPLY_LS" and "MET_IDN" in chunk.columns:
                # CLS_YMD 다음에 MET_IDN 삽입
                idx = columns_to_select.index("GU_CDE")
                columns_to_select.insert(idx, "MET_IDN")

            # 필요한 컬럼만 선택 (존재하는 컬럼만)
            available_columns = [
                col for col in columns_to_select if col in chunk.columns
            ]
            chunk_selected = chunk[available_columns].copy()

            # BEG_YMD 처리 (컬럼이 없거나 비어있는 값들 처리)
            if "BEG_YMD" not in chunk_selected.columns:
                chunk_selected["BEG_YMD"] = pd.NaT

            # BEG_YMD가 비어있는 행들에 대해 값 설정
            if pd.isna(chunk_selected["BEG_YMD"]).any():
                # IST_YMD와 FNS_YMD 중 최대값 계산 (둘 다 있으면 max, 하나만 있으면 그 값)
                if (
                    "IST_YMD" in chunk_selected.columns
                    and "FNS_YMD" in chunk_selected.columns
                ):
                    temp_beg = chunk_selected[["IST_YMD", "FNS_YMD"]].max(axis=1)
                elif "IST_YMD" in chunk_selected.columns:
                    temp_beg = chunk_selected["IST_YMD"]
                elif "FNS_YMD" in chunk_selected.columns:
                    temp_beg = chunk_selected["FNS_YMD"]
                else:
                    temp_beg = pd.Series(pd.NaT, index=chunk_selected.index)

                # 기존 BEG_YMD의 빈 값을 temp_beg로 채우고, 그래도 빈 값은 1989-01-01로 설정
                chunk_selected["BEG_YMD"] = (
                    chunk_selected["BEG_YMD"]
                    .fillna(temp_beg)
                    .fillna(pd.to_datetime("1989-01-01"))
                )

            # 날짜 차이 계산 (일 단위)
            if "BEG_YMD" in chunk_selected.columns:
                # BEG_YMD가 유효한 날짜인 경우만 계산
                valid_dates = pd.notna(chunk_selected["BEG_YMD"])
                chunk_selected["DAYS_SINCE_BEG"] = np.nan
                chunk_selected["YEARS_SINCE_BEG"] = np.nan

                if valid_dates.any():
                    # Use pandas to calculate time difference
                    current_date_series = pd.Series(
                        [current_date] * valid_dates.sum(),
                        index=chunk_selected[valid_dates].index,
                    )
                    beg_dates = pd.to_datetime(
                        chunk_selected.loc[valid_dates, "BEG_YMD"]
                    )
                    time_diff = pd.to_datetime(current_date_series) - beg_dates
                    chunk_selected.loc[valid_dates, "DAYS_SINCE_BEG"] = (
                        time_diff.dt.days
                    )
                    # 년 단위로 변환 (365.25일 기준)
                    chunk_selected.loc[valid_dates, "YEARS_SINCE_BEG"] = (
                        chunk_selected.loc[valid_dates, "DAYS_SINCE_BEG"] / 365.25
                    )
            else:
                # BEG_YMD가 없으면 NaN으로 설정
                chunk_selected["DAYS_SINCE_BEG"] = np.nan
                chunk_selected["YEARS_SINCE_BEG"] = np.nan

            processed_chunks.append(chunk_selected)
            total_rows += len(chunk_selected)

            print(
                f"청크 {chunk_count} 처리 완료: {len(chunk_selected):,}행 (누적: {total_rows:,}행)"
            )

        # 모든 청크를 합치기
        if processed_chunks:
            final_df = pd.concat(processed_chunks, ignore_index=True)

            print(f"\n{'='*60}")
            print(f"{file_type} 데이터 처리 완료")
            print(f"{'='*60}")
            print(f"총 처리된 행 수: {len(final_df):,}")
            print(f"총 컬럼 수: {len(final_df.columns)}")

            # 날짜 차이 통계
            if (
                "DAYS_SINCE_BEG" in final_df.columns
                and "YEARS_SINCE_BEG" in final_df.columns
            ):
                valid_age_data = final_df["DAYS_SINCE_BEG"].dropna()
                valid_year_data = final_df["YEARS_SINCE_BEG"].dropna()
                if len(valid_age_data) > 0:
                    print("\n날짜 차이 통계:")
                    print(f"  - 유효한 데이터: {len(valid_age_data):,}행")
                    print(f"  - 평균 경과일: {valid_age_data.mean():.1f}일")
                    print(f"  - 최소 경과일: {valid_age_data.min():.0f}일")
                    print(f"  - 최대 경과일: {valid_age_data.max():.0f}일")
                    print(f"  - 평균 경과년: {valid_year_data.mean():.1f}년")
                    print(f"  - 최소 경과년: {valid_year_data.min():.1f}년")
                    print(f"  - 최대 경과년: {valid_year_data.max():.1f}년")
                else:
                    print("\n경고: 유효한 날짜 차이 데이터가 없습니다.")

            return final_df

        else:
            print(f"처리할 데이터가 없습니다: {file_path}")
            return pd.DataFrame()

    except Exception as e:
        print(f"파일 {file_path} 처리 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


def analyze_rainflow_from_df(
    pressure_df: pd.DataFrame,
    region_code: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    DataFrame으로부터 Rain Flow Counting 분석 (DB 조회 결과 등에서 직접 사용)

    Args:
        pressure_df: 압력 데이터 DataFrame (columns: msrmt_dt, wtrprsr)
        region_code: 구역 코드 (예: "0520")
        start_date: 분석 시작일 (None이면 최근 1년)
        end_date: 분석 종료일 (None이면 데이터 최대일)

    Returns:
        analyze_date_range_rainflow()와 동일한 구조의 결과 dict
    """
    label = f"{region_code} DB"

    print(f"\n{'='*80}")
    print(f"Rain Flow Counting 분석 시작: {label}")
    print(f"{'='*80}")

    try:
        full_df = pressure_df.copy()
        full_df["msrmt_dt"] = pd.to_datetime(full_df["msrmt_dt"])
        full_df = full_df.sort_values("msrmt_dt").reset_index(drop=True)

        print(f"데이터 크기: {full_df.shape}")
        print(f"데이터 기간: {full_df['msrmt_dt'].min()} ~ {full_df['msrmt_dt'].max()}")
        print(f"NaN 개수: {full_df['wtrprsr'].isna().sum()}")

        # 날짜 범위 결정
        data_end = full_df["msrmt_dt"].max()
        data_start = full_df["msrmt_dt"].min()
        if end_date is None:
            end_date = data_end.to_pydatetime().replace(hour=23, minute=59, second=59)
        if start_date is None:
            candidate = end_date.replace(year=end_date.year - 1)
            start_date = max(candidate, data_start.to_pydatetime())

        print(f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

        filtered_df = extract_date_range_data(full_df, start_date, end_date)

        # process_date_range_data는 file_path를 pass filter 설정에 사용하므로
        # 구역코드를 파일명처럼 전달
        original_data, low_pass_data, high_pass_data = process_date_range_data(
            filtered_df, region_code
        )

        results = {
            "original": calculate_rainflow_counting(original_data, "original"),
            "low_pass": calculate_rainflow_counting(low_pass_data, "low_pass"),
            "high_pass": calculate_rainflow_counting(high_pass_data, "high_pass"),
        }

        print(f"\n{'='*60}")
        print(f"분석 완료: {label}")
        print(f"{'='*60}")

        return {
            "file_path": label,
            "file_name": label,
            "start_date": start_date,
            "end_date": end_date,
            "data_count": len(filtered_df),
            "results": results,
            "success": True,
        }

    except Exception as e:
        print(f"{label} 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {
            "file_path": label,
            "file_name": label,
            "error": str(e),
            "success": False,
        }


def calculate_rainflow_by_age(
    pipe_df: pd.DataFrame,
    pipe_type: str,
    pressure_data_files: List[str],
    use_db: bool = False,
) -> pd.DataFrame:
    """
    파이프 데이터의 나이에 비례하여 Rain Flow Counting 값을 계산

    Args:
        pipe_df: 파이프 데이터 DataFrame
        pipe_type: 파이프 타입 ("PIPE_LM" 또는 "SPLY_LS")
        pressure_data_files: 압력 데이터 파일 경로 리스트 (use_db=False 시 사용)
                             use_db=True 시 구역코드 문자열 리스트로 사용
        use_db: True이면 DB에서 압력 데이터 조회, False이면 CSV 파일 사용

    Returns:
        pd.DataFrame: Rain Flow Counting 값이 추가된 데이터프레임
    """
    print(f"\n{'='*80}")
    print(f"나이별 Rain Flow Counting 계산 시작: {pipe_type}")
    print(f"{'='*80}")

    if "YEARS_SINCE_BEG" not in pipe_df.columns:
        print("오류: YEARS_SINCE_BEG 컬럼이 없습니다.")
        return pipe_df

    result_df = pipe_df.copy()

    for pressure_source in pressure_data_files:
        if use_db:
            # DB 모드: pressure_source는 구역코드 문자열
            region_code = str(pressure_source)
            try:
                from pressure_db_loader import load_pressure_from_db
                pressure_df = load_pressure_from_db(region_code)
                if pressure_df.empty:
                    print(f"경고: {region_code} 구역 DB 데이터가 비어있습니다.")
                    continue
                rainflow_result = analyze_rainflow_from_df(pressure_df, region_code)
            except Exception as e:
                print(f"경고: {region_code} 구역 DB 조회 실패: {e}")
                continue
        else:
            # CSV 모드: pressure_source는 파일 경로 문자열
            pressure_file = str(pressure_source)
            if not Path(pressure_file).exists():
                print(f"경고: 압력 데이터 파일을 찾을 수 없습니다: {pressure_file}")
                continue

            file_name = Path(pressure_file).name
            print(f"\n압력 데이터 파일 처리: {file_name}")

            # 파일명에서 지역 코드 추출 (예: 0470 소구역 압력 데이터.csv -> 0470)
            region_code = file_name[:4] if len(file_name) >= 4 else file_name.split("_")[0]
            rainflow_result = analyze_date_range_rainflow(pressure_file)

        if rainflow_result["success"]:
            high_cycles = rainflow_result["results"]["high_pass"]["analysis"].get(
                "total_cycles", 0
            )
            low_cycles = rainflow_result["results"]["low_pass"]["analysis"].get(
                "total_cycles", 0
            )

            print(f"  - High 주파수 총 사이클: {high_cycles:.1f}")
            print(f"  - Low 주파수 총 사이클: {low_cycles:.1f}")

            result_df[f"{region_code}_high_total_cycles"] = high_cycles
            result_df[f"{region_code}_low_total_cycles"] = low_cycles

    rainflow_columns = [col for col in result_df.columns if "_total_cycles" in col]
    print(f"\n추가된 Rain Flow 관련 컬럼 수: {len(rainflow_columns)}")
    if rainflow_columns:
        print(f"컬럼 목록: {', '.join(rainflow_columns)}")

    return result_df


def process_all_pipe_data_with_rainflow(
    pipe_properties: pd.DataFrame,
) -> None:
    """
    모든 파이프 데이터 파일을 처리하고 Rain Flow Counting, 재료계수(K_material), 피로도 계산

    Args:
        pipe_properties: 파이프 속성 데이터프레임
    """
    from fatigue_calculations import (
        add_K_material_to_dataframe,
        calculate_fatigue_damage_dataframe,
    )
    from common.config import (
        RESULTS_DIR,
        PIPE_DATA_FILES,
    )

    print(f"\n{'='*80}")
    print("모든 파이프 데이터 처리 및 Rain Flow Counting 계산")
    print(f"{'='*80}")

    # 압력 데이터 파일 목록
    pressure_data_files = [str(path) for path in PRESSURE_DATA_FILES]

    # 파이프 데이터 파일 목록
    pipe_data_files = PIPE_DATA_FILES

    # 모든 파이프 데이터 파일 처리
    total_processed = 0
    successful_files = 0

    for file_path, file_type in pipe_data_files:
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"\n파일을 찾을 수 없습니다: {file_path}")
            continue

        try:
            # 1. 파이프 데이터 읽기 및 나이 계산
            pipe_df = process_pipe_data_with_age(
                str(file_path), file_type, output_dir=RESULTS_DIR
            )

            if pipe_df.empty:
                print(f"데이터가 비어있습니다: {file_path}")
                continue

            # 2. 나이별 Rain Flow Counting 계산
            result_df = calculate_rainflow_by_age(
                pipe_df, file_type, pressure_data_files
            )

            # 3. 재료계수(K_material), K 계수들, 피로한계 추가
            result_df = add_K_material_to_dataframe(
                result_df, pipe_properties, file_type
            )

            # 4. 각 지역별 피로도 계산
            # 결과 DataFrame에 있는 모든 지역을 자동으로 감지
            regions = [col.replace("_high_total_cycles", "") 
                      for col in result_df.columns 
                      if "_high_total_cycles" in col]
            
            for region in regions:
                # 해당 지역의 Rain Flow 컬럼이 있는지 확인
                if f"{region}_high_total_cycles" in result_df.columns:
                    result_df = calculate_fatigue_damage_dataframe(
                        result_df, region, data_type="pressure", use_k_total=True
                    )

                    # 각 지역별 잔여 수명 계산
                    if f"{region}_D_final" in result_df.columns:
                        result_df[f"{region}_remaining_life_years"] = result_df.apply(
                            lambda row: (
                                (1 - row[f"{region}_D_final"])
                                / row[f"{region}_D_final"]
                                if row[f"{region}_D_final"] < 1
                                and row[f"{region}_D_final"] > 0
                                else 0
                            ),
                            axis=1,
                        )

                    # intermediate 컬럼명을 fatigue_damage로 변경
                    if f"{region}_high_fatigue_intermediate" in result_df.columns:
                        result_df[f"{region}_high_fatigue_damage"] = result_df[
                            f"{region}_high_fatigue_intermediate"
                        ]
                        del result_df[f"{region}_high_fatigue_intermediate"]

                    if f"{region}_low_fatigue_intermediate" in result_df.columns:
                        result_df[f"{region}_low_fatigue_damage"] = result_df[
                            f"{region}_low_fatigue_intermediate"
                        ]
                        del result_df[f"{region}_low_fatigue_intermediate"]

            # 5. 통합 피로 손상 및 잔여 수명 계산 (제거 - 이제 필요 없음)
            # total_D_final과 remaining_life_years는 더 이상 생성하지 않음

            # 6. 결과 저장
            # 파일명 생성
            file_stem = file_path.stem
            if file_type == "PIPE_LM":
                output_filename = "fatigue_pipe_lm_by_age.csv"
            elif file_type == "SPLY_LS":
                output_filename = "fatigue_sply_ls_by_age.csv"
            else:
                output_filename = f"fatigue_{file_stem}_by_age.csv"

            output_dir = RESULTS_DIR / "main55_calc_fatigure"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / output_filename

            # 컬럼 순서 재정렬
            # 공통 기본 컬럼
            basic_columns = [
                "FTR_CDE",
                "FTR_IDN",
                "HJD_CDE",
                "SHT_NUM",
                "MNG_CDE",
                "MOP_CDE",
                "STD_DIP",
                "BYC_LEN",
                "JHT_CDE",
                "LOW_DEP",
                "HGH_DEP",
                "CNT_NUM",
                "SYS_CHK",
                "PIP_LBL",
            ]

            # 파일 타입별 고유 컬럼 추가
            if file_type == "PIPE_LM":
                # PIPE_LM: IQT_CDE를 PIP_LBL 다음에 추가
                basic_columns.append("IQT_CDE")

            basic_columns.extend(
                [
                    "GIS_IDN",
                    "FTC_CDE",
                    "CLS_YMD",
                ]
            )

            if file_type == "SPLY_LS":
                # SPLY_LS: MET_IDN을 CLS_YMD 다음에 추가
                basic_columns.append("MET_IDN")

            basic_columns.extend(
                [
                    "GU_CDE",
                    "SMZ_NUM",
                    "MDZ_NUM",
                    "LGZ_NUM",
                    "AVG_DEP",
                    "WTP_CDE",
                    "PIP_TYPE",
                    "design_pressure",
                    "thickness",
                    "K_material",
                    "fatigue_limit",
                    "IST_YMD",
                    "FNS_YMD",
                    "BEG_YMD",
                    "DAYS_SINCE_BEG",
                    "YEARS_SINCE_BEG",
                ]
            )

            # K 계수 컬럼들
            k_columns = [
                "K_diameter",
                "K_age",
                "K_soil",
                "K_traffic",
                "K_vibration",
                "hoop_stress",
                "K_stress",
                "K_total",
            ]

            # 0470 지역 컬럼들 (지정된 순서대로)
            region_0470_columns = [
                "0470_low_total_cycles",
                "0470_high_total_cycles",
                "0470_low_fatigue_damage",
                "0470_high_fatigue_damage",
                "0470_D_base",
                "0470_D_final",
                "0470_remaining_life_years",
            ]

            # 0480 지역 컬럼들 (지정된 순서대로)
            region_0480_columns = [
                "0480_low_total_cycles",
                "0480_high_total_cycles",
                "0480_low_fatigue_damage",
                "0480_high_fatigue_damage",
                "0480_D_base",
                "0480_D_final",
                "0480_remaining_life_years",
            ]

            # 0490 지역 컬럼들 (지정된 순서대로)
            region_0490_columns = [
                "0490_low_total_cycles",
                "0490_high_total_cycles",
                "0490_low_fatigue_damage",
                "0490_high_fatigue_damage",
                "0490_D_base",
                "0490_D_final",
                "0490_remaining_life_years",
            ]

            # 0520 지역 컬럼들 (지정된 순서대로)
            region_0520_columns = [
                "0520_low_total_cycles",
                "0520_high_total_cycles",
                "0520_low_fatigue_damage",
                "0520_high_fatigue_damage",
                "0520_D_base",
                "0520_D_final",
                "0520_remaining_life_years",
            ]

            # 보정손상도 및 잔여 수명 컬럼 제거 (이제 필요 없음)
            final_columns = []

            # 기타 계산 결과 컬럼들 제거 (hoop_stress 제거)
            other_columns = []

            # 실제 존재하는 컬럼만 선택
            ordered_columns = []
            for col_group in [
                basic_columns,
                k_columns,
                region_0470_columns,
                region_0480_columns,
                region_0490_columns,
                region_0520_columns,
                final_columns,
                other_columns,
            ]:
                for col in col_group:
                    if col in result_df.columns and col not in ordered_columns:
                        ordered_columns.append(col)

            # 나머지 컬럼들은 추가하지 않음 (중복 방지)

            # 재정렬된 DataFrame 저장
            result_df[ordered_columns].to_csv(output_path, index=False)
            print(f"\n결과 파일 저장 완료: {output_path}")
            print(f"  - 파일 크기: {output_path.stat().st_size / 1024:.1f} KB")
            print(f"  - 총 행 수: {len(result_df):,}")
            print(f"  - 총 컬럼 수: {len(ordered_columns)}")

            successful_files += 1

        except Exception as e:
            print(f"\n파일 {file_path} 처리 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()

        total_processed += 1

    print(f"\n{'='*80}")
    print("모든 파이프 데이터 처리 완료")
    print(f"총 처리 시도: {total_processed}개 파일")
    print(f"성공적으로 처리: {successful_files}개 파일")
    print(f"{'='*80}")

    # 비정상 MOP_CDE 경고 출력
    print_abnormal_mop_summary()
