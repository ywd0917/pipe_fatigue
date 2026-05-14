"""
관망 데이터 처리 유틸리티 함수들
- CSV 파일 안전 읽기 및 분석
- 청크 단위 메모리 효율적 처리
- 날짜 필드 자동 처리
"""

import pandas as pd
import os
from typing import Optional, Dict, Any, List, Iterator, Union
import warnings

warnings.filterwarnings("ignore")

from pipe_const import MOP_CODE_MAPPING
from pipe_func import validate_pipe_type


def check_file_info(file_path: str) -> Dict[str, Union[str, int, float]]:
    """파일 정보 확인

    Args:
        file_path: 확인할 파일 경로

    Returns:
        파일 정보 딕셔너리:
        - path: 파일 경로 (str)
        - size_bytes: 파일 크기 (bytes, int)
        - size_mb: 파일 크기 (MB, float)

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    file_size = os.path.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)

    print("파일 정보:")
    print(f"  경로: {file_path}")
    print(f"  크기: {file_size:,} bytes ({file_size_mb:.2f} MB)")

    return {"path": file_path, "size_bytes": file_size, "size_mb": file_size_mb}


def analyze_csv_structure(
    file_path: str, nrows: int = 5
) -> Optional[Dict[str, Union[List[str], Dict[str, Any], pd.DataFrame]]]:
    """CSV 파일 구조 분석

    Args:
        file_path: 분석할 CSV 파일 경로
        nrows: 분석할 행 수

    Returns:
        CSV 구조 정보 딕셔너리 또는 None (실패시):
        - columns: 컬럼명 리스트 (List[str])
        - dtypes: 데이터 타입 딕셔너리 (Dict[str, Any])
        - date_fields: 날짜 필드 리스트 (List[str])
        - sample_data: 샘플 데이터 (pd.DataFrame)
    """
    try:
        print(f"\nCSV 구조 분석 (첫 {nrows}행):")
        print("=" * 60)

        # 첫 몇 행만 읽어서 구조 파악
        df_sample = pd.read_csv(file_path, nrows=nrows, encoding="utf-8")

        print(f"컬럼 수: {len(df_sample.columns)}")
        print(f"샘플 행 수: {len(df_sample)}")
        print("\n컬럼 목록:")
        for i, col in enumerate(df_sample.columns):
            print(f"  {i+1:2d}. {col}")

        print("\n데이터 타입:")
        for col in df_sample.columns:
            dtype = df_sample[col].dtype
            sample_value = df_sample[col].iloc[0] if len(df_sample) > 0 else "N/A"
            print(f"  {col}: {dtype} (예시: {sample_value})")

        # 날짜 관련 필드 자동 식별
        date_fields = []
        for col in df_sample.columns:
            if "YMD" in col.upper() or "DATE" in col.upper():
                date_fields.append(col)

        if date_fields:
            print("\n날짜 관련 필드:")
            for field in date_fields:
                sample_value = df_sample[field].iloc[0] if len(df_sample) > 0 else "N/A"
                print(f"  {field}: {sample_value}")

        return {
            "columns": list(df_sample.columns),
            "dtypes": dict(df_sample.dtypes),
            "date_fields": date_fields,
            "sample_data": df_sample,
        }

    except Exception as e:
        print(f"CSV 구조 분석 중 오류 발생: {e}")
        return None


def read_csv_common(
    file_path: str,
    chunksize: int = 10000,
    date_columns: Optional[List[str]] = None,
    verbose: bool = True,
) -> Iterator[pd.DataFrame]:
    """공통 CSV 읽기 (날짜 필드 처리)

    Args:
        file_path: 읽을 CSV 파일 경로
        chunksize: 청크 크기 (행 수)
        date_columns: 날짜로 파싱할 컬럼 리스트
        verbose: 진행상황 출력 여부

    Yields:
        pandas DataFrame 청크들
    """
    try:
        if verbose:
            print(f"\n청크 단위 데이터 읽기 (청크 크기: {chunksize:,}행):")
            print("=" * 60)

        # 날짜 컬럼 파싱 설정 (존재하는 컬럼만 사용)
        if date_columns:
            header = pd.read_csv(file_path, nrows=0, encoding="utf-8")
            available_cols = set(header.columns)
            # utf-8 실패시 utf-8-sig 재시도
            if not available_cols:
                header = pd.read_csv(file_path, nrows=0, encoding="utf-8-sig")
                available_cols = set(header.columns)
            parse_dates = [c for c in date_columns if c in available_cols]
        else:
            parse_dates = []

        chunk_reader = pd.read_csv(
            file_path, chunksize=chunksize, encoding="utf-8", parse_dates=parse_dates
        )

        chunk_count = 0
        total_rows = 0

        for chunk in chunk_reader:
            chunk_count += 1
            total_rows += len(chunk)

            if verbose:
                print(
                    f"청크 {chunk_count}: {len(chunk):,}행 처리됨 (누적: {total_rows:,}행)"
                )

            # 날짜 필드 처리
            if date_columns:
                for date_col in date_columns:
                    if date_col in chunk.columns:
                        # 날짜 형식 확인 및 변환
                        chunk[date_col] = pd.to_datetime(
                            chunk[date_col], format="%Y%m%d", errors="coerce"
                        )

            # IST_YMD와 FNS_YMD 중 더 최신 데이터를 BEG_YMD로 추가
            if "IST_YMD" in chunk.columns and "FNS_YMD" in chunk.columns:
                chunk["BEG_YMD"] = chunk[["IST_YMD", "FNS_YMD"]].max(axis=1)
            elif "IST_YMD" in chunk.columns:
                chunk["BEG_YMD"] = chunk["IST_YMD"]
            elif "FNS_YMD" in chunk.columns:
                chunk["BEG_YMD"] = chunk["FNS_YMD"]
            else:
                # IST_YMD와 FNS_YMD가 모두 없는 경우 1989-01-01로 설정
                chunk["BEG_YMD"] = pd.to_datetime("19890101", format="%Y%m%d")

            yield chunk

    except Exception as e:
        print(f"CSV 읽기 중 오류 발생: {e}")
        return


def read_csv_pipe_lm(
    file_path: str,
    chunksize: int = 10000,
    date_columns: Optional[List[str]] = None,
    verbose: bool = True,
) -> Iterator[pd.DataFrame]:
    """PIPE_LM 파일 전용 CSV 읽기

    Args:
        file_path: 읽을 CSV 파일 경로
        chunksize: 청크 크기 (행 수)
        date_columns: 날짜로 파싱할 컬럼 리스트
        verbose: 진행상황 출력 여부

    Yields:
        pandas DataFrame 청크들 (PIP_TYPE 필드 추가됨)
    """
    chunk_count = 0
    total_valid = 0
    total_invalid = 0

    for chunk in read_csv_common(file_path, chunksize, date_columns, verbose):
        chunk_count += 1

        # PIPE_LM 전용: PIP_LBL에서 PIP_TYPE 추출
        if "PIP_LBL" in chunk.columns:
            chunk["PIP_TYPE"] = chunk["PIP_LBL"].str.split("-").str[1]

            # PIP_TYPE 값의 Literal 검증
            if "PIP_TYPE" in chunk.columns:
                # 유효성 검증 (NaN 값은 제외)
                valid_mask = chunk["PIP_TYPE"].apply(
                    lambda x: validate_pipe_type(x) if pd.notna(x) else True
                )

                # 통계 계산
                valid_count = valid_mask.sum()
                invalid_count = len(chunk) - valid_count
                total_valid += valid_count
                total_invalid += invalid_count

                # 유효하지 않은 값들 확인
                invalid_values = chunk.loc[
                    ~valid_mask & chunk["PIP_TYPE"].notna(), "PIP_TYPE"
                ].unique()

                if len(invalid_values) > 0 and verbose:
                    print(
                        f"  ⚠️  청크 {chunk_count}: {invalid_count}개의 유효하지 않은 PIP_TYPE 발견"
                    )
                    print(f"      유효하지 않은 값들: {list(invalid_values)}")

                # 검증 결과를 새로운 컬럼으로 추가
                chunk["PIP_TYPE_VALID"] = valid_mask

                # 유효하지 않은 값을 NaN으로 변경 (선택적)
                chunk.loc[~valid_mask, "PIP_TYPE"] = None

        yield chunk

    # 전체 검증 결과 요약 출력
    if verbose and (total_valid + total_invalid) > 0:
        total_rows = total_valid + total_invalid
        valid_percentage = (total_valid / total_rows) * 100
        print("\n📊 PIP_TYPE 검증 결과 요약:")
        print(f"   전체 행 수: {total_rows:,}행")
        print(f"   유효한 값: {total_valid:,}행 ({valid_percentage:.1f}%)")
        print(f"   유효하지 않은 값: {total_invalid:,}행 ({100-valid_percentage:.1f}%)")
        if total_invalid > 0:
            print("   ※ 유효하지 않은 값들은 NaN으로 변경되었습니다.")


def read_csv_sply_ls(
    file_path: str,
    chunksize: int = 10000,
    date_columns: Optional[List[str]] = None,
    verbose: bool = True,
) -> Iterator[pd.DataFrame]:
    """SPLY_LS 파일 전용 CSV 읽기

    Args:
        file_path: 읽을 CSV 파일 경로
        chunksize: 청크 크기 (행 수)
        date_columns: 날짜로 파싱할 컬럼 리스트
        verbose: 진행상황 출력 여부

    Yields:
        pandas DataFrame 청크들 (PIP_TYPE 필드 추가됨)
    """
    for chunk in read_csv_common(file_path, chunksize, date_columns, verbose):
        # SPLY_LS 전용: MOP_CDE에서 PIP_TYPE 매핑 (defines.py에서 import)
        if "MOP_CDE" in chunk.columns:
            chunk["PIP_TYPE"] = chunk["MOP_CDE"].map(MOP_CODE_MAPPING)

        yield chunk