#!/usr/bin/env python
"""
Geocoding 실패 분석 스크립트
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.common.config import RESULTS_DIR  # noqa: E402


def analyze_geocoding_failures() -> None:
    """Geocoding 실패한 주소들을 분석"""

    # 결과 파일 읽기
    result_file = RESULTS_DIR / "지하누수_sample_위치추가.csv"
    df = pd.read_csv(result_file, encoding="utf-8-sig")

    # 위도/경도가 없는 행 찾기
    failed_mask = df["위도"].isna() | df["경도"].isna()
    failed_df = df[failed_mask].copy()

    print(f"\n총 {len(df)}개 중 {len(failed_df)}개 geocoding 실패")
    print(f"성공률: {(len(df) - len(failed_df)) / len(df) * 100:.1f}%")

    if len(failed_df) > 0:
        print("\n실패한 주소 목록:")
        print("-" * 80)

        # 실패한 주소들을 출력
        for idx, row in failed_df.iterrows():
            if isinstance(idx, int):
                print(f"행 {idx + 2}: {row['주소']}")
            else:
                print(f"행 {idx}: {row['주소']}")

        # 실패한 주소들을 별도 파일로 저장
        failed_file = RESULTS_DIR / "geocoding_failures.csv"
        failed_df[["긴급복구공사일련번호", "주소"]].to_csv(
            failed_file, index=False, encoding="utf-8-sig"
        )
        print(f"\n실패한 주소들을 저장: {failed_file}")

        # 패턴 분석
        print("\n실패 패턴 분석:")
        print("-" * 40)

        # 구별 집계
        gu_counts: dict[str, int] = {}
        for addr in failed_df["주소"]:
            if pd.notna(addr):
                for gu in [
                    "남구",
                    "북구",
                    "동구",
                    "서구",
                    "중구",
                    "수성구",
                    "달서구",
                    "달성군",
                ]:
                    if gu in addr:
                        gu_counts[gu] = gu_counts.get(gu, 0) + 1
                        break

        if gu_counts:
            print("\n구별 실패 건수:")
            for gu, count in sorted(
                gu_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {gu}: {count}건")

        # 특수 패턴 검사
        patterns: dict[str, Callable[[Any], bool]] = {
            "번지 없음": lambda x: pd.notna(x) and "번지" not in str(x),
            "숫자 주소": lambda x: pd.notna(x)
            and str(x).strip().replace("-", "").replace(" ", "").isdigit(),
            "특수문자 포함": lambda x: pd.notna(x)
            and any(c in str(x) for c in "()[]{}"),
            "길 이름 없음": lambda x: pd.notna(x)
            and not any(suffix in str(x) for suffix in ["길", "로", "번지"]),
        }

        print("\n특수 패턴:")
        for pattern_name, pattern_func in patterns.items():
            matching = [addr for addr in failed_df["주소"] if pattern_func(addr)]
            if matching:
                print(f"\n{pattern_name} ({len(matching)}건):")
                for addr in matching[:3]:  # 최대 3개만 표시
                    print(f"  - {addr}")
                if len(matching) > 3:
                    print(f"  ... 외 {len(matching) - 3}건")


if __name__ == "__main__":
    analyze_geocoding_failures()
