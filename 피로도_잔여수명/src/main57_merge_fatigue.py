"""
main57_merge_fatigue.py - 피로 손상 계산 결과 파일 통합

main56_calc_fatigure.py에서 생성된 두 개의 CSV 파일을 하나로 병합
- fatigue_pipe_lm.csv (PIPE_LM 데이터)
- fatigue_sply_ls.csv (SPLY_LS 데이터)

병합 전략:
- 모든 고유 컬럼 유지 (IQT_CDE, MET_IDN)
- DATA_SOURCE 컬럼 추가로 출처 구분
- 총 72개 컬럼으로 구성
"""

import pandas as pd
from pathlib import Path
from typing import List
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from common.config import RESULTS_DIR


def define_column_order() -> List[str]:
    """
    통합 CSV 파일의 컬럼 순서 정의

    Returns:
        List[str]: 73개 컬럼의 순서 리스트 (공통 70 + DATA_SOURCE + IQT_CDE + MET_IDN)
    """
    columns = [
        # 1. 데이터 소스 (새로 추가)
        "DATA_SOURCE",
        # 2-3. 기본 식별자
        "FTR_CDE",
        "FTR_IDN",
        # 4-14. 기본 속성
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
        # 15. PIPE_LM 전용 컬럼 (SPLY_LS에서는 이 위치가 비어있음)
        "IQT_CDE",
        # 16-18. 공통 속성
        "GIS_IDN",
        "FTC_CDE",
        "CLS_YMD",
        "MET_IDN",
        # 20-25. 지역 정보
        "GU_CDE",
        "SMZ_NUM",
        "MDZ_NUM",
        "LGZ_NUM",
        "AVG_DEP",
        "WTP_CDE",
        # 26-34. 파이프 정보 및 재료 속성
        "PIP_TYPE",
        "IST_YMD",
        "FNS_YMD",
        "BEG_YMD",
        "DAYS_SINCE_BEG",
        "YEARS_SINCE_BEG",
        "design_pressure",
        "thickness",
        "K_material",
        "fatigue_limit",
        # 35-42. K 계수
        "K_diameter",
        "K_age",
        "K_soil",
        "K_traffic",
        "K_vibration",
        "hoop_stress",
        "K_stress",
        "K_repair",
        "K_total",
        # 44-71. 지역별 피로 분석 (각 지역 7개씩, 총 28개)
        # 0470 지역
        "0470_low_total_cycles",
        "0470_high_total_cycles",
        "0470_low_fatigue_damage",
        "0470_high_fatigue_damage",
        "0470_D_base",
        "0470_D_final",
        "0470_remaining_life_years",
        # 0480 지역
        "0480_low_total_cycles",
        "0480_high_total_cycles",
        "0480_low_fatigue_damage",
        "0480_high_fatigue_damage",
        "0480_D_base",
        "0480_D_final",
        "0480_remaining_life_years",
        # 0490 지역
        "0490_low_total_cycles",
        "0490_high_total_cycles",
        "0490_low_fatigue_damage",
        "0490_high_fatigue_damage",
        "0490_D_base",
        "0490_D_final",
        "0490_remaining_life_years",
        # 0520 지역
        "0520_low_total_cycles",
        "0520_high_total_cycles",
        "0520_low_fatigue_damage",
        "0520_high_fatigue_damage",
        "0520_D_base",
        "0520_D_final",
        "0520_remaining_life_years",
    ]

    return columns


def read_fatigue_csv(file_path: Path, data_source: str) -> pd.DataFrame:
    """
    피로 손상 CSV 파일 읽기 및 DATA_SOURCE 컬럼 추가

    Args:
        file_path: CSV 파일 경로
        data_source: 데이터 소스 이름 ('PIPE_LM' 또는 'SPLY_LS')

    Returns:
        pd.DataFrame: DATA_SOURCE 컬럼이 추가된 데이터프레임
    """
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    df = pd.read_csv(file_path)
    df["DATA_SOURCE"] = data_source

    print(f"{data_source} 데이터 로드 완료: {len(df):,}개 레코드")

    return df


def merge_fatigue_data(
    pipe_lm_df: pd.DataFrame, sply_ls_df: pd.DataFrame
) -> pd.DataFrame:
    """
    PIPE_LM과 SPLY_LS 데이터 병합

    Args:
        pipe_lm_df: PIPE_LM 데이터프레임
        sply_ls_df: SPLY_LS 데이터프레임

    Returns:
        pd.DataFrame: 병합된 데이터프레임
    """
    # 컬럼 순서 정의
    column_order = define_column_order()

    # 두 데이터프레임 합치기 (행 방향)
    merged_df = pd.concat([pipe_lm_df, sply_ls_df], ignore_index=True)

    # 없는 컬럼 추가 (NaN으로 채움)
    for col in column_order:
        if col not in merged_df.columns:
            merged_df[col] = pd.NA

    # 컬럼 순서 재정렬
    merged_df = merged_df[column_order]

    print("\n병합 완료:")
    print(f"- PIPE_LM 레코드: {len(pipe_lm_df):,}개")
    print(f"- SPLY_LS 레코드: {len(sply_ls_df):,}개")
    print(f"- 총 레코드: {len(merged_df):,}개")
    print(f"- 총 컬럼: {len(merged_df.columns)}개")

    return merged_df


def save_merged_data(df: pd.DataFrame, output_dir: Path) -> Path:
    """
    병합된 데이터를 CSV 파일로 저장

    Args:
        df: 병합된 데이터프레임
        output_dir: 출력 디렉토리

    Returns:
        Path: 저장된 파일 경로
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성 (타임스탬프 포함)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"merged_fatigue_analysis_{timestamp}.csv"

    # 최신 파일 링크 (타임스탬프 없는 버전)
    latest_file = output_dir / "merged_fatigue_analysis.csv"

    # CSV 저장
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n파일 저장 완료: {output_file}")

    # 최신 파일 링크 생성 (덮어쓰기)
    df.to_csv(latest_file, index=False, encoding="utf-8-sig")
    print(f"최신 파일 링크: {latest_file}")

    return output_file


def print_statistics(df: pd.DataFrame) -> None:
    """
    병합된 데이터의 통계 정보 출력

    Args:
        df: 병합된 데이터프레임
    """
    print("\n" + "=" * 60)
    print("병합 데이터 통계")
    print("=" * 60)

    # 데이터 소스별 통계
    source_counts = df["DATA_SOURCE"].value_counts()
    print("\n데이터 소스별 레코드 수:")
    for source, count in source_counts.items():
        print(f"  - {source}: {count:,}개")

    # 고유 컬럼 데이터 존재 여부
    print("\n고유 컬럼 데이터 현황:")
    iqt_count = df["IQT_CDE"].notna().sum()
    met_count = df["MET_IDN"].notna().sum()
    print(f"  - IQT_CDE (PIPE_LM): {iqt_count:,}개 레코드")
    print(f"  - MET_IDN (SPLY_LS): {met_count:,}개 레코드")

    # 파이프 타입별 통계
    print("\n파이프 타입별 분포:")
    pipe_types = df.groupby(["DATA_SOURCE", "PIP_TYPE"]).size()
    for (source, pipe_type), count in pipe_types.items():
        print(f"  - {source} / {pipe_type}: {count:,}개")

    # K_repair 적용 통계
    k_repair_stats = df[df["K_repair"] > 0].groupby("DATA_SOURCE").size()
    print("\nK_repair 적용 레코드:")
    for source, count in k_repair_stats.items():
        print(f"  - {source}: {count:,}개")

    # 피로 손상 요약 (D_final)
    print("\n피로 손상 (D_final) 요약:")
    for region in ["0470", "0480", "0490", "0520"]:
        d_final_col = f"{region}_D_final"
        if d_final_col in df.columns:
            valid_data = df[df[d_final_col].notna()]
            if not valid_data.empty:
                print(f"\n  {region} 지역:")
                print(f"    - 평균: {valid_data[d_final_col].mean():.6f}")
                print(f"    - 최소: {valid_data[d_final_col].min():.6f}")
                print(f"    - 최대: {valid_data[d_final_col].max():.6f}")
                print(f"    - 중앙값: {valid_data[d_final_col].median():.6f}")


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("main57_merge_fatigue.py - 피로 손상 결과 파일 통합")
    print("=" * 60)

    # 입력 파일 경로 설정
    main56_dir = RESULTS_DIR / "main56_calc_fatigure"
    pipe_lm_path = main56_dir / "fatigue_pipe_lm.csv"
    sply_ls_path = main56_dir / "fatigue_sply_ls.csv"

    # 파일 존재 확인
    if not main56_dir.exists():
        print(f"오류: main56_calc_fatigure 디렉토리를 찾을 수 없습니다: {main56_dir}")
        print("먼저 main56_calc_fatigure.py를 실행하여 결과 파일을 생성하세요.")
        return

    try:
        # 1. 데이터 읽기
        print("\n1. 데이터 파일 읽기")
        pipe_lm_df = read_fatigue_csv(pipe_lm_path, "PIPE_LM")
        sply_ls_df = read_fatigue_csv(sply_ls_path, "SPLY_LS")

        # 2. 데이터 병합
        print("\n2. 데이터 병합 수행")
        merged_df = merge_fatigue_data(pipe_lm_df, sply_ls_df)

        # 3. 결과 저장
        print("\n3. 결과 파일 저장")
        output_dir = RESULTS_DIR / "main57_merge_fatigue"
        output_file = save_merged_data(merged_df, output_dir)

        # 4. 통계 출력
        print_statistics(merged_df)

        print("\n" + "=" * 60)
        print("✅ 파일 병합이 성공적으로 완료되었습니다!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"\n❌ 오류: {e}")
        print("main56_calc_fatigure.py를 먼저 실행하여 필요한 파일을 생성하세요.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()