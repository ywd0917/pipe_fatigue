"""
비정상 MOP_CDE 추적 모듈
MOP_CDE=99 또는 null인 파이프들을 추적하고 경고를 출력
"""

from typing import Dict, Set
import pandas as pd


class AbnormalMOPTracker:
    """비정상 MOP_CDE를 가진 파이프 추적"""

    def __init__(self) -> None:
        self.mop_99_pipes: Set[str] = set()  # MOP_CDE=99인 파이프들
        self.mop_null_pipes: Set[str] = set()  # MOP_CDE가 null인 파이프들
        self.file_counters: Dict[str, Dict[str, int]] = {}  # 파일별 카운터

    def track_abnormal_mop(self, df: pd.DataFrame, file_type: str) -> None:
        """
        데이터프레임에서 비정상 MOP_CDE를 추적

        Args:
            df: 검사할 데이터프레임
            file_type: 파일 타입 (PIPE_LM, SPLY_LS 등)
        """
        if "MOP_CDE" not in df.columns or "FTR_IDN" not in df.columns:
            return

        # MOP_CDE=99인 파이프 추적
        mop_99_mask = df["MOP_CDE"] == 99
        if mop_99_mask.any():
            ftr_idn_list = df.loc[mop_99_mask, "FTR_IDN"].astype(str).tolist()
            self.mop_99_pipes.update(ftr_idn_list)

        # MOP_CDE가 null인 파이프 추적
        mop_null_mask = df["MOP_CDE"].isna()
        if mop_null_mask.any():
            ftr_idn_list = df.loc[mop_null_mask, "FTR_IDN"].astype(str).tolist()
            self.mop_null_pipes.update(ftr_idn_list)

        # 파일별 카운터 업데이트
        if file_type not in self.file_counters:
            self.file_counters[file_type] = {"mop_99": 0, "mop_null": 0}

        self.file_counters[file_type]["mop_99"] += mop_99_mask.sum()
        self.file_counters[file_type]["mop_null"] += mop_null_mask.sum()

    def print_summary(self) -> None:
        """비정상 MOP_CDE에 대한 요약 출력"""
        print("\n" + "=" * 80)
        print("비정상 MOP_CDE 경고")
        print("=" * 80)

        # MOP_CDE=99 출력
        mop_99_count = len(self.mop_99_pipes)
        if mop_99_count > 0:
            print(f"\nMOP_CDE=99인 파이프: {mop_99_count}개")
            # 최대 10개까지만 표시
            sample_pipes = list(self.mop_99_pipes)[:10]
            for pipe in sample_pipes:
                print(f"  - FTR_IDN: {pipe}")
            if mop_99_count > 10:
                print(f"  ... 외 {mop_99_count - 10}개")
        else:
            print("\nMOP_CDE=99인 파이프: 없음")

        # MOP_CDE=null 출력
        mop_null_count = len(self.mop_null_pipes)
        if mop_null_count > 0:
            print(f"\nMOP_CDE가 없는 파이프: {mop_null_count}개")
            # 최대 10개까지만 표시
            sample_pipes = list(self.mop_null_pipes)[:10]
            for pipe in sample_pipes:
                print(f"  - FTR_IDN: {pipe}")
            if mop_null_count > 10:
                print(f"  ... 외 {mop_null_count - 10}개")
        else:
            print("\nMOP_CDE가 없는 파이프: 없음")

        # 파일별 통계
        if self.file_counters:
            print("\n파일별 통계:")
            for file_type, counts in self.file_counters.items():
                print(f"  {file_type}:")
                print(f"    - MOP_CDE=99: {counts['mop_99']}개")
                print(f"    - MOP_CDE=null: {counts['mop_null']}개")

        # 경고 메시지
        if mop_99_count > 0 or mop_null_count > 0:
            print(
                "\n* 이들 파이프는 보수적 계산을 위해 GP(아연도강관) 값으로 처리되었습니다."
            )
            print("* PIP_TYPE: MOP_CDE=99는 'ETC'로, null은 빈 값으로 표시됩니다.")
        else:
            print("\n모든 파이프의 MOP_CDE가 정상입니다.")


# 전역 인스턴스
_tracker = AbnormalMOPTracker()


def track_abnormal_mop(df: pd.DataFrame, file_type: str) -> None:
    """전역 추적기에 비정상 MOP_CDE 추적"""
    _tracker.track_abnormal_mop(df, file_type)


def print_abnormal_mop_summary() -> None:
    """비정상 MOP_CDE 요약 출력"""
    _tracker.print_summary()