"""
K_repair 계수 로드 모듈
data/main13a_k_repair 폴더에서 K_repair 데이터를 로드하고 매핑
"""

import pandas as pd
from typing import Dict
from common.config import PROJECT_ROOT, C_REPAIR


def load_k_repair_mapping() -> Dict[str, pd.DataFrame]:
    """
    K_repair 데이터를 로드하여 딕셔너리로 반환

    Returns:
        Dict[str, pd.DataFrame]: PIPE_LM과 SPLY_LS의 K_repair 매핑 데이터
    
    Raises:
        FileNotFoundError: K_repair CSV 파일이 없을 때
    """
    k_repair_dir = PROJECT_ROOT / "results" / "main13a_k_repair"

    repair_data = {}

    # PIPE_LM K_repair 로드
    pipe_lm_path = k_repair_dir / "repair_pipe_lm.csv"
    if not pipe_lm_path.exists():
        raise FileNotFoundError(str(pipe_lm_path))
    
    df_pipe = pd.read_csv(pipe_lm_path)
    # FTR_IDN을 인덱스로 설정
    df_pipe.set_index("FTR_IDN", inplace=True)
    repair_data["PIPE_LM"] = df_pipe
    print(f"PIPE_LM K_repair 데이터 로드 완료: {len(df_pipe)} 건")

    # SPLY_LS K_repair 로드
    sply_ls_path = k_repair_dir / "repair_sply_ls.csv"
    if not sply_ls_path.exists():
        raise FileNotFoundError(str(sply_ls_path))
    
    df_sply = pd.read_csv(sply_ls_path)
    # FTR_IDN을 인덱스로 설정
    df_sply.set_index("FTR_IDN", inplace=True)
    repair_data["SPLY_LS"] = df_sply
    print(f"SPLY_LS K_repair 데이터 로드 완료: {len(df_sply)} 건")

    return repair_data


def get_k_repair(
    ftr_idn: float, pipe_type: str, repair_data: Dict[str, pd.DataFrame]
) -> float:
    """
    특정 FTR_IDN과 파이프 타입에 대한 K_repair 값을 반환

    Args:
        ftr_idn: 파이프 ID
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)
        repair_data: K_repair 매핑 데이터

    Returns:
        float: K_repair_per_m 값 (1m당 수리 횟수, 없으면 0.0)
    """
    if pipe_type not in repair_data:
        return 0.0

    df = repair_data[pipe_type]
    if df.empty:
        return 0.0

    # FTR_IDN으로 조회 (K_repair_per_m 컬럼 사용)
    if ftr_idn in df.index:
        return float(df.loc[ftr_idn, "K_repair_per_m"])

    return 0.0


def apply_k_repair_to_dataframe(
    df: pd.DataFrame, pipe_type: str, repair_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    DataFrame에 K_repair 컬럼을 추가하고 K_total을 업데이트

    Args:
        df: 처리할 DataFrame
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)
        repair_data: K_repair 매핑 데이터

    Returns:
        pd.DataFrame: K_repair가 적용된 DataFrame
    """
    # K_repair 컬럼 추가
    df["K_repair"] = df["FTR_IDN"].apply(
        lambda x: get_k_repair(x, pipe_type, repair_data)
    )

    # K_repair 값 검증 (음수 방지)
    df["K_repair"] = df["K_repair"].clip(lower=0.0)

    # K_repair 적용 전의 K_total 값을 보존
    if "K_total" in df.columns:
        df["K_total_without_repair"] = df["K_total"].copy()
        # K_total 재계산: K_total = K_total * (1 + C_REPAIR * K_repair)
        df["K_total"] = df["K_total"] * (1 + C_REPAIR * df["K_repair"])

    # 컬럼 순서 조정 (K_total_without_repair, K_repair를 K_total 바로 앞에 배치)
    cols = list(df.columns)
    if "K_repair" in cols and "K_total" in cols:
        # K_repair 제거
        cols.remove("K_repair")
        # K_total_without_repair 제거 (있다면)
        if "K_total_without_repair" in cols:
            cols.remove("K_total_without_repair")

        # K_total 위치 찾기
        k_total_idx = cols.index("K_total")

        # K_total_without_repair, K_repair 순으로 삽입
        cols.insert(k_total_idx, "K_repair")
        if "K_total_without_repair" in df.columns:
            cols.insert(k_total_idx, "K_total_without_repair")

        df = df[cols]

    return df


def print_k_repair_statistics(df: pd.DataFrame, pipe_type: str) -> None:
    """
    K_repair 통계 정보 출력

    Args:
        df: K_repair가 적용된 DataFrame
        pipe_type: 파이프 타입
    """
    if "K_repair" not in df.columns:
        return

    k_repair_stats = df["K_repair"].describe()
    non_zero_count = (df["K_repair"] > 0).sum()

    print(f"\n{pipe_type} K_repair 통계:")
    print(f"  - 전체 레코드 수: {len(df)}")
    print(
        f"  - K_repair > 0인 레코드 수: {non_zero_count} ({non_zero_count/len(df)*100:.1f}%)"
    )
    print(f"  - 평균 K_repair: {k_repair_stats['mean']:.4f}")
    print(f"  - 최대 K_repair: {k_repair_stats['max']:.4f}")
    print(f"  - 표준편차: {k_repair_stats['std']:.4f}")