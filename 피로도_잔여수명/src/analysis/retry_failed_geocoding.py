#!/usr/bin/env python
"""
실패한 geocoding 주소들을 Unicode NFC 정규화 및 추가 전처리 후 재시도
"""

import logging
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

from src.common.config import RESULTS_DIR
from src.common.geocoding_kakao_sqlite_v2 import (
    _get_cache,
    check_api_credentials,
    geocode_address,
    preprocess_address_for_api,
)

# 로거 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def normalize_unicode(text: str) -> str:
    """
    Unicode NFC 정규화 적용

    Args:
        text: 정규화할 텍스트

    Returns:
        NFC 정규화된 텍스트
    """
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


def enhanced_preprocess_address(address: str) -> str | None:
    """
    향상된 주소 전처리

    Args:
        address: 원본 주소

    Returns:
        전처리된 주소
    """
    if not address or not isinstance(address, str):
        return address

    # Unicode NFC 정규화
    addr = normalize_unicode(address.strip())

    # 특수한 경우 처리
    # 1. 숫자만 있거나 하이픈만 있는 경우
    if re.match(r"^[\d\-]+$", addr) or addr == "-":
        return None  # 유효하지 않은 주소

    # 2. 날짜 패턴 제거 (예: (06.04.06), [2021.01.01] 등)
    addr = re.sub(r"[\(\[]?\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}[\)\]]?", "", addr)

    # 3. 특수 표기 제거 (B동, 79B 13L, 외91필지 등)
    # 동/호수 표기 정리
    addr = re.sub(r"\s+\d+[A-Z]\s+\d+L", "", addr)  # "79B 13L" 같은 패턴
    addr = re.sub(r"\s+[A-Z]동(?:\s|$)", "", addr)  # "B동" 같은 패턴
    addr = re.sub(r"\s+외\d+필지.*$", "", addr)  # "외91필지 302동" 같은 패턴
    addr = re.sub(r"\s+\d+동(?:\s|$)", "", addr)  # "302동" 같은 패턴

    # 4. 부가 정보 제거
    # 건물명, 시설명 등은 주소 뒤쪽에 오므로 번지 뒤의 내용 제거
    match = re.search(r"^(.+?(?:리|동|가)\s+\d+(?:-\d+)?)", addr)
    if match:
        addr = match.group(1)

    # 5. 특수 키워드와 그 뒤의 내용 제거
    keywords_with_tail = [
        "폐전",
        "폐지",
        "폐업",
        "철거",
        "이전",
        "없음",
        "고:",
        "산마루",
        "무산",
    ]
    for keyword in keywords_with_tail:
        if keyword in addr:
            # 키워드가 포함된 부분부터 제거
            idx = addr.find(keyword)
            if idx > 0:
                addr = addr[:idx].strip()

    # 6. 특수문자 제거
    addr = re.sub(r"[:]", "", addr)

    # 7. 불필요한 공백 정리
    addr = " ".join(addr.split())

    # 8. 기본 전처리 적용 (시도명 추가 등)
    if addr:
        addr = preprocess_address_for_api(addr)

    return addr


def get_failed_addresses(db_path: Path) -> list[tuple[str, str]]:
    """
    실패한 주소들을 조회

    Returns:
        [(query_address, created_at), ...] 리스트
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT query_address, created_at
            FROM geocoding_cache
            WHERE status = 'not_found'
            ORDER BY created_at DESC
        """
        )
        return cursor.fetchall()


def update_cache_status(address: str, result: tuple[float, float] | None) -> None:
    """
    캐시 상태 업데이트

    Args:
        address: 원본 주소
        result: geocoding 결과 (lat, lon) 또는 None
    """
    cache = _get_cache()
    if result:
        lat, lon = result
        # 기존 not_found를 success로 업데이트
        with sqlite3.connect(cache.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE geocoding_cache
                SET status = 'success',
                    lat = ?,
                    lon = ?,
                    cached_at = ?
                WHERE query_address = ?
            """,
                (lat, lon, time.time(), address),
            )
            conn.commit()
            logger.info("캐시 업데이트 성공: %s", address)
    else:
        logger.debug("여전히 실패: %s", address)


def retry_failed_geocoding(limit: int | None = None, delay: float = 0.1) -> None:
    """
    실패한 주소들을 재시도

    Args:
        limit: 처리할 최대 개수 (None이면 전체)
        delay: API 호출 간 지연 시간
    """
    # API 자격 증명 확인
    if not check_api_credentials():
        logger.error("Kakao API 키가 설정되지 않았습니다.")
        return

    # DB 경로
    db_path = RESULTS_DIR / "geocoding_cache_kakao_v2.db"
    if not db_path.exists():
        logger.error("캐시 DB를 찾을 수 없습니다: %s", db_path)
        return

    # 실패한 주소들 조회
    failed_addresses = get_failed_addresses(db_path)
    total_failed = len(failed_addresses)

    if limit:
        failed_addresses = failed_addresses[:limit]

    logger.info(
        "실패한 주소 %d개 중 %d개 재처리 시작", total_failed, len(failed_addresses)
    )

    success_count = 0
    still_failed = []
    improved_examples = []

    for i, (address, created_at) in enumerate(failed_addresses, 1):
        logger.info("\n[%d/%d] 처리 중: %s", i, len(failed_addresses), address)

        # 향상된 전처리 적용
        processed = enhanced_preprocess_address(address)

        # 원본과 다른 경우만 재시도
        if processed != address:
            logger.info("  전처리 후: %s", processed)

            # geocoding 재시도 (캐시 무시)
            result = geocode_address(address, use_cache=False)

            if result:
                success_count += 1
                improved_examples.append((address, processed))
                logger.info("  ✓ 성공! 좌표: %s", result)
            else:
                still_failed.append(address)
                logger.warning("  ✗ 여전히 실패")
        else:
            # 전처리 후에도 동일하면 Unicode 문제일 수 있음
            normalized = normalize_unicode(address)
            if normalized != address:
                logger.info("  Unicode 정규화 적용됨")
                result = geocode_address(address, use_cache=False)

                if result:
                    success_count += 1
                    improved_examples.append((address, f"{address} (NFC 정규화)"))
                    logger.info("  ✓ 성공! 좌표: %s", result)
                else:
                    still_failed.append(address)
                    logger.warning("  ✗ 여전히 실패")
            else:
                still_failed.append(address)
                logger.debug("  전처리 변화 없음, 건너뜀")

        # API 호출 간 지연
        if i < len(failed_addresses):
            time.sleep(delay)

    # 결과 요약
    print("\n" + "=" * 60)
    print("재처리 결과 요약")
    print("=" * 60)
    print(f"전체 실패 주소: {total_failed}개")
    print(f"재처리 시도: {len(failed_addresses)}개")
    print(f"재처리 성공: {success_count}개")
    print(f"여전히 실패: {len(still_failed)}개")

    if improved_examples:
        print("\n개선된 주소 예시 (최대 10개):")
        for orig, improved in improved_examples[:10]:
            print(f"  원본: {orig}")
            print(f"  개선: {improved}")
            print()

    if still_failed:
        print("\n여전히 실패한 주소 예시 (최대 10개):")
        for addr in still_failed[:10]:
            print(f"  - {addr}")


def main() -> None:
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="실패한 geocoding 주소들을 재처리")
    parser.add_argument("--limit", type=int, help="처리할 최대 개수 (기본값: 전체)")
    parser.add_argument(
        "--delay", type=float, default=0.1, help="API 호출 간 지연 시간 (초)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="실패한 주소만 확인하고 재처리하지 않음",
    )

    args = parser.parse_args()

    if args.check_only:
        # 실패한 주소만 확인
        db_path = RESULTS_DIR / "geocoding_cache_kakao_v2.db"
        failed = get_failed_addresses(db_path)
        print(f"실패한 주소 총 {len(failed)}개")
        print("\n처음 20개:")
        for addr, created in failed[:20]:
            print(f"  - {addr}")
    else:
        # 재처리 실행
        retry_failed_geocoding(limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
