"""
피로 손상(Fatigue Damage) 데이터 로딩을 위한 공통 모듈
data/pipe_fatigue 디렉토리의 CSV 파일을 로드하고 처리하는 공통 함수들
"""

import warnings
from pathlib import Path
from typing import Any

import pandas as pd

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_fatigue_data_dir(base_dir: Path) -> Path:
    """
    피로 손상 데이터 디렉토리 경로 반환

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)

    Returns:
        pipe_fatigue 디렉토리 경로
    """
    # base_dir이 'raw'로 끝나면 상위 디렉토리 사용
    if base_dir.name == "raw":
        return base_dir.parent / "pipe_fatigue"
    return base_dir / "pipe_fatigue"


def get_available_csv_files(base_dir: Path) -> dict[str, Path]:
    """
    사용 가능한 CSV 파일 목록 반환

    Args:
        base_dir: 기본 디렉토리

    Returns:
        {파일명(확장자 제외): 파일 경로} 형태의 딕셔너리
    """
    fatigue_dir = get_fatigue_data_dir(base_dir)
    csv_files = {}

    if fatigue_dir.exists():
        for csv_path in fatigue_dir.glob("*.csv"):
            csv_files[csv_path.stem] = csv_path

    return csv_files


def validate_fatigue_data(
    df: pd.DataFrame, required_columns: list[str]
) -> pd.DataFrame:
    """
    피로 손상 데이터 검증 및 정리

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

    # NaN 값 제거 (FTR_IDN 기준)
    if "FTR_IDN" in df.columns:
        nan_count = df["FTR_IDN"].isna().sum()
        if nan_count > 0:
            print(f"경고: FTR_IDN이 NaN인 행 {nan_count}개 제거")
            df = df[df["FTR_IDN"].notna()]

    return df


def load_fatigue_data(
    csv_path: Path,
    required_columns: list[str] | None = None,
    verbose: bool = True,
) -> pd.DataFrame | None:
    """
    피로 손상 CSV 데이터 로드

    Args:
        csv_path: CSV 파일 경로
        required_columns: 필수 컬럼 목록 (기본값: FTR_IDN과 D_final 컬럼들)
        verbose: 상세 정보 출력 여부

    Returns:
        피로 손상 DataFrame 또는 None (실패 시)
    """
    if not csv_path.exists():
        if verbose:
            print(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None

    # 기본 필수 컬럼
    if required_columns is None:
        required_columns = ["FTR_IDN"]

    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path)

        # D_final 컬럼 찾기
        d_final_columns = [col for col in df.columns if col.endswith("_D_final")]
        if verbose and d_final_columns:
            print(f"발견된 D_final 컬럼: {d_final_columns}")

        # 데이터 검증 및 정리
        df = validate_fatigue_data(df, required_columns)

        # FTR_IDN을 문자열로 변환 (매칭을 위해)
        df["FTR_IDN"] = df["FTR_IDN"].astype(str)

        if verbose:
            print(f"피로 손상 데이터 로드 완료: {len(df)}개 행")
            if d_final_columns:
                for col in d_final_columns:
                    print(
                        f"  - {col}: min={df[col].min():.6f}, max={df[col].max():.6f}"
                    )

        return df

    except Exception as e:
        if verbose:
            print(f"오류: CSV 데이터 로드 실패 - {e}")
        return None


def get_fatigue_by_ftr_idn(
    df: pd.DataFrame, region_code: str = "0520"
) -> dict[str, float]:
    """
    FTR_IDN별 피로 손상 값 딕셔너리 반환

    Args:
        df: 피로 손상 DataFrame
        region_code: 지역 코드 (D_final 컬럼 선택용)

    Returns:
        {FTR_IDN: D_final 값} 형태의 딕셔너리
    """
    d_final_col = f"{region_code}_D_final"

    if d_final_col not in df.columns:
        print(f"경고: {d_final_col} 컬럼을 찾을 수 없습니다.")
        # 다른 D_final 컬럼 찾기
        d_final_columns = [col for col in df.columns if col.endswith("_D_final")]
        if d_final_columns:
            d_final_col = d_final_columns[0]
            print(f"대체 컬럼 사용: {d_final_col}")
        else:
            return {}

    # FTR_IDN별 D_final 값 딕셔너리 생성
    fatigue_dict = {}
    for _, row in df.iterrows():
        ftr_idn = str(row["FTR_IDN"])
        d_final = row[d_final_col]
        fatigue_dict[ftr_idn] = d_final

    return fatigue_dict


def get_fatigue_info(df: pd.DataFrame) -> dict[str, Any]:
    """
    피로 손상 데이터의 기본 정보 반환

    Args:
        df: 피로 손상 DataFrame

    Returns:
        기본 정보를 담은 딕셔너리
    """
    info: dict[str, Any] = {
        "total_records": len(df),
        "columns": list(df.columns),
    }

    # FTR_IDN 정보
    if "FTR_IDN" in df.columns:
        info["unique_ftr_idn"] = df["FTR_IDN"].nunique()

    # D_final 컬럼 정보
    d_final_columns = [col for col in df.columns if col.endswith("_D_final")]
    if d_final_columns:
        info["d_final_columns"] = d_final_columns
        d_final_stats: dict[str, dict[str, float]] = {}
        for col in d_final_columns:
            stats_dict: dict[str, float] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
            }
            d_final_stats[col] = stats_dict
        info["d_final_stats"] = d_final_stats

    return info
