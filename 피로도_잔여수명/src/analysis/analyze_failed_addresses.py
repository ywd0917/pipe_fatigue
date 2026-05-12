#!/usr/bin/env python
"""
실패한 주소들의 패턴을 분석하여 개선 방안 도출
"""

import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from src.common.config import RESULTS_DIR


def get_failed_addresses(db_path: Path) -> list[str]:
    """실패한 주소들을 조회"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT query_address
            FROM geocoding_cache
            WHERE status = 'not_found'
            ORDER BY created_at DESC
        """
        )
        return [row[0] for row in cursor.fetchall()]


def analyze_patterns(addresses: list[str]) -> dict[str, list[str]]:
    """주소 패턴 분석"""
    patterns = defaultdict(list)

    for addr in addresses:
        # 1. 번지만 있는 경우
        if re.match(r"^[\d\-]+$", addr):
            patterns["번지만 있음"].append(addr)

        # 2. 특수문자만 있는 경우
        elif re.match(r"^[\-_]+$", addr):
            patterns["특수문자만"].append(addr)

        # 3. 공사/작업 설명인 경우
        elif any(
            keyword in addr
            for keyword in [
                "공사",
                "설치",
                "교체",
                "작업",
                "외부함",
                "유량계",
                "바이패스",
            ]
        ):
            patterns["공사 설명"].append(addr)

        # 4. 날짜 패턴이 있는 경우
        elif re.search(r"\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}", addr):
            patterns["날짜 포함"].append(addr)

        # 5. 특수 표기가 있는 경우 (B동, 79B 13L 등)
        elif re.search(r"\d+[A-Z]\s+\d+L|[A-Z]동|외\d+필지", addr):
            patterns["특수 표기"].append(addr)

        # 6. 폐업/폐전 등 키워드
        elif any(
            keyword in addr
            for keyword in ["폐전", "폐지", "폐업", "철거", "이전", "없음"]
        ):
            patterns["폐업 관련"].append(addr)

        # 7. 전화번호가 포함된 경우
        elif re.search(r"010-\d{4}-\d{4}", addr):
            patterns["전화번호 포함"].append(addr)

        # 8. 건물명/시설명만 있는 경우
        elif (
            not any(dong in addr for dong in ["동", "리", "가", "로", "길"])
            and len(addr.split()) > 2
        ):
            patterns["건물명만"].append(addr)

        # 9. 존재하지 않는 번지로 추정
        elif re.search(r"\d{3,}-\d{2,}", addr):  # 큰 번지수
            patterns["큰 번지(존재 의심)"].append(addr)

        # 10. 기타
        else:
            patterns["기타"].append(addr)

    return dict(patterns)


def suggest_improvements(patterns: dict[str, list[str]]) -> dict[str, str]:
    """패턴별 개선 방안 제시"""
    return {
        "번지만 있음": "지역 정보가 누락된 불완전한 주소. 원본 데이터 확인 필요",
        "특수문자만": "유효하지 않은 데이터. 원본 데이터에서 제거 필요",
        "공사 설명": "주소가 아닌 작업 설명. 별도 컬럼으로 분리 필요",
        "날짜 포함": "날짜 정보 제거 후 재시도 가능",
        "특수 표기": "동/호수 정보 제거 후 재시도 가능",
        "폐업 관련": "폐업된 장소. 이전 주소나 인근 주소로 대체 필요",
        "전화번호 포함": "전화번호 제거 후 재시도 가능",
        "건물명만": "정확한 주소 정보 추가 필요",
        "큰 번지(존재 의심)": "실제 존재하지 않는 번지일 가능성. 확인 필요",
        "기타": "개별 검토 필요",
    }


def main() -> None:
    """메인 함수"""
    # DB 경로
    db_path = RESULTS_DIR / "geocoding_cache_kakao_v2.db"
    if not db_path.exists():
        print(f"캐시 DB를 찾을 수 없습니다: {db_path}")
        return

    # 실패한 주소들 조회
    failed_addresses = get_failed_addresses(db_path)
    print(f"실패한 주소 총 {len(failed_addresses)}개 분석")
    print("=" * 60)

    # 패턴 분석
    patterns = analyze_patterns(failed_addresses)
    suggestions = suggest_improvements(patterns)

    # 결과 출력
    total_categorized = sum(len(addrs) for addrs in patterns.values())

    print("\n패턴별 분석 결과:")
    print("-" * 60)

    for pattern_name, addresses in sorted(
        patterns.items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(addresses)
        percentage = (count / len(failed_addresses)) * 100

        print(f"\n[{pattern_name}] - {count}개 ({percentage:.1f}%)")
        print(f"개선 방안: {suggestions.get(pattern_name, '분석 필요')}")
        print("예시 (최대 5개):")
        for addr in addresses[:5]:
            print(f"  - {addr}")

    # 통계 요약
    print("\n" + "=" * 60)
    print("요약:")
    print(f"- 전체 실패 주소: {len(failed_addresses)}개")
    print(f"- 분류된 주소: {total_categorized}개")

    # 가장 큰 문제 카테고리
    top_patterns = sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    print("\n주요 문제 패턴 TOP 3:")
    for i, (pattern, addrs) in enumerate(top_patterns, 1):
        print(
            f"{i}. {pattern}: {len(addrs)}개 ({len(addrs)/len(failed_addresses)*100:.1f}%)"
        )

    # 개선 가능한 주소 추정
    improvable = ["날짜 포함", "특수 표기", "전화번호 포함"]
    improvable_count = sum(len(patterns.get(p, [])) for p in improvable)
    print(
        f"\n전처리 개선으로 해결 가능한 주소: 약 {improvable_count}개 ({improvable_count/len(failed_addresses)*100:.1f}%)"
    )

    # 데이터 품질 문제
    quality_issues = ["번지만 있음", "특수문자만", "공사 설명", "건물명만"]
    quality_count = sum(len(patterns.get(p, [])) for p in quality_issues)
    print(
        f"원본 데이터 품질 문제: 약 {quality_count}개 ({quality_count/len(failed_addresses)*100:.1f}%)"
    )


if __name__ == "__main__":
    main()
