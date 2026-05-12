"""
복구 작업(Repair) 데이터 로딩 및 처리를 위한 특화 모듈
data/repair 디렉토리의 CSV 파일을 로드하고 처리하는 비즈니스 로직
"""

import warnings
from pathlib import Path
from typing import Any

import pandas as pd

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_repair_data_dir(base_dir: Path, use_sample: bool = True) -> Path:
    """
    복구 작업 데이터 디렉토리 경로 반환

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)
        use_sample: 샘플 데이터 사용 여부

    Returns:
        repair 디렉토리 경로
    """
    # base_dir이 'raw'로 끝나면 상위 디렉토리 사용
    if base_dir.name == "raw":
        repair_dir = base_dir.parent / "repair"
    else:
        repair_dir = base_dir / "repair"

    # 샘플 데이터 사용 시
    if use_sample:
        sample_dir = repair_dir / "sample"
        if sample_dir.exists():
            return sample_dir

    return repair_dir


def get_repair_file_types() -> dict[str, str]:
    """
    복구 작업 파일 타입 정의

    Returns:
        {파일명: 표시명} 형태의 딕셔너리
    """
    return {
        # "기타공사": "기타공사",  # 제외
        # "지상누수": "지상누수",  # 제외
        # "지하누수": "지하누수",  # 제외
        "긴급복구": "긴급복구",  # 긴급복구만 사용
    }


def validate_repair_data(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    """
    복구 작업 데이터 검증 및 정리

    Args:
        df: 원본 DataFrame
        required_columns: 필수 컬럼 목록

    Returns:
        정리된 DataFrame
    """
    # 필수 컬럼 확인
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_cols}")

    # 소구역번호가 있는 행만 유지
    if "소구역번호" in df.columns:
        # 컬럼명에 공백이 있을 수 있으므로 처리
        col_name = None
        for col in df.columns:
            if "소구역번호" in col:
                col_name = col
                break

        if col_name:
            # NaN이나 빈 값 제거
            df[col_name] = df[col_name].astype(str).str.strip()
            valid_rows = (
                df[col_name].notna() & (df[col_name] != "") & (df[col_name] != "nan")
            )
            removed_count = len(df) - valid_rows.sum()
            if removed_count > 0:
                print(f"경고: 소구역번호가 없는 행 {removed_count}개 제거")
            df = df[valid_rows]

    return df


def load_repair_data(
    csv_path: Path,
    required_columns: list[str] | None = None,
    verbose: bool = True,
) -> pd.DataFrame | None:
    """
    복구 작업 CSV 데이터 로드

    Args:
        csv_path: CSV 파일 경로
        required_columns: 필수 컬럼 목록
        verbose: 상세 정보 출력 여부

    Returns:
        복구 작업 DataFrame 또는 None (실패 시)
    """
    if not csv_path.exists():
        if verbose:
            print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None

    # 기본 필수 컬럼
    if required_columns is None:
        required_columns = ["구군", "주소"]

    try:
        # CSV 파일 읽기 (UTF-8 with BOM)
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 데이터 검증 및 정리
        df = validate_repair_data(df, required_columns)

        if verbose:
            print(f"{csv_path.stem} 데이터 로드 완료: {len(df)}개 행")

            # 구군별 통계
            if "구군" in df.columns:
                print("구군별 작업 건수:")
                for gu, count in df["구군"].value_counts().head(10).items():
                    print(f"  - {gu}: {count}건")

        return df

    except Exception as e:
        if verbose:
            print(f"오류: CSV 데이터 로드 실패 - {e}")
        return None


def filter_by_smlz(df: pd.DataFrame, smlz_numbers: list[str]) -> pd.DataFrame:
    """
    소구역번호로 데이터 필터링

    Args:
        df: 복구 작업 DataFrame
        smlz_numbers: 필터링할 소구역번호 리스트

    Returns:
        필터링된 DataFrame
    """
    # 소구역번호 컬럼 찾기
    col_name = None
    for col in df.columns:
        if "소구역번호" in col:
            col_name = col
            break

    if not col_name:
        print("경고: 소구역번호 컬럼을 찾을 수 없습니다.")
        return df

    # 문자열로 변환하여 비교
    df[col_name] = df[col_name].astype(str).str.strip()
    smlz_numbers_str = [str(s).strip() for s in smlz_numbers]

    # 필터링
    return df[df[col_name].isin(smlz_numbers_str)]


def get_repair_stats(df: pd.DataFrame) -> dict[str, Any]:
    """
    복구 작업 데이터의 통계 정보 반환

    Args:
        df: 복구 작업 DataFrame

    Returns:
        통계 정보를 담은 딕셔너리
    """
    stats = {
        "total_records": len(df),
        "columns": list(df.columns),
    }

    # 구군별 통계
    if "구군" in df.columns:
        stats["by_district"] = df["구군"].value_counts().to_dict()

    # 소구역별 통계
    col_name = None
    for col in df.columns:
        if "소구역번호" in col:
            col_name = col
            break

    if col_name:
        stats["by_smlz"] = df[col_name].value_counts().to_dict()
        stats["unique_smlz_count"] = df[col_name].nunique()

    # 복구공사구분별 통계 (있는 경우)
    if "복구공사구분" in df.columns:
        stats["by_work_type"] = df["복구공사구분"].value_counts().to_dict()

    return stats


def load_all_repair_data(
    base_dir: Path, verbose: bool = True, use_sample: bool = True
) -> dict[str, pd.DataFrame]:
    """
    모든 복구 작업 데이터 로드 (긴급복구 제외)

    Args:
        base_dir: 기본 디렉토리
        verbose: 상세 정보 출력 여부
        use_sample: 샘플 데이터 사용 여부

    Returns:
        {파일타입: DataFrame} 형태의 딕셔너리
    """
    repair_dir = get_repair_data_dir(base_dir, use_sample=use_sample)
    file_types = get_repair_file_types()

    all_data = {}

    for file_name, display_name in file_types.items():
        csv_path = repair_dir / f"{file_name}.csv"
        if csv_path.exists():
            df = load_repair_data(csv_path, verbose=verbose)
            if df is not None and len(df) > 0:
                all_data[file_name] = df

    return all_data
