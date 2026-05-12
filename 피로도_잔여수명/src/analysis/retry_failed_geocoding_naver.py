#!/usr/bin/env python
"""
실패한 geocoding 주소들을 Naver API로 재시도
"""

import logging
import os
import sqlite3
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.common.config import RESULTS_DIR

# 환경 변수 로드
load_dotenv()

# Naver API 설정
NAVER_API_KEY_ID = os.getenv("NAVER_API_KEY_ID")
NAVER_API_KEY = os.getenv("NAVER_API_KEY")
NAVER_GEOCODING_URL = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"

# 로거 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_naver_api_credentials() -> bool:
    """Naver API 자격 증명 확인"""
    return bool(NAVER_API_KEY_ID and NAVER_API_KEY)


def geocode_with_naver(address: str) -> tuple[float, float] | None:
    """
    Naver Maps API로 주소를 좌표로 변환

    Args:
        address: 변환할 주소

    Returns:
        (위도, 경도) 튜플 또는 None
    """
    if not address or not isinstance(address, str):
        return None

    # API 키 확인
    if not check_naver_api_credentials():
        logger.error("Naver API 키가 설정되지 않았습니다")
        return None

    # API 호출
    try:
        headers = {
            "x-ncp-apigw-api-key-id": NAVER_API_KEY_ID,
            "x-ncp-apigw-api-key": NAVER_API_KEY,
            "Accept": "application/json",
        }
        params = {"query": address}

        response = requests.get(
            NAVER_GEOCODING_URL, headers=headers, params=params, timeout=5
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") == "OK" and data.get("addresses"):
            # 첫 번째 결과 사용
            first_result = data["addresses"][0]
            lat = float(first_result["y"])
            lon = float(first_result["x"])

            # 주소 정보
            jibun_address = first_result.get("jibunAddress", "")
            road_address = first_result.get("roadAddress", "")

            logger.info(
                "Naver API 성공: %s → %s", address, jibun_address or road_address
            )
            return (lat, lon)
        logger.warning("Naver: 검색 결과 없음 - %s", address)
        return None

    except requests.exceptions.RequestException as e:
        logger.error("Naver API 요청 오류: %s", e)
        return None
    except Exception as e:
        logger.error("Naver geocoding 오류: %s", e)
        return None


def get_failed_addresses(
    db_path: Path, limit: int | None = None
) -> list[tuple[str, str]]:
    """
    실패한 주소들을 조회

    Returns:
        [(query_address, created_at), ...] 리스트
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        if limit:
            query = """
                SELECT query_address, created_at
                FROM geocoding_cache
                WHERE status = 'not_found'
                ORDER BY created_at DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
        else:
            query = """
                SELECT query_address, created_at
                FROM geocoding_cache
                WHERE status = 'not_found'
                ORDER BY created_at DESC
            """
            cursor.execute(query)

        return cursor.fetchall()


def preprocess_address_for_naver(address: str) -> str | None:
    """
    Naver API를 위한 주소 전처리

    Args:
        address: 원본 주소

    Returns:
        전처리된 주소
    """
    if not address or not isinstance(address, str):
        return address

    # 기본 정리
    addr = address.strip()

    # 특수한 경우 처리
    # 1. 숫자만 있거나 하이픈만 있는 경우 - 처리 불가
    import re

    if re.match(r"^[\d\-]+$", addr) or addr == "-":
        return None  # 유효하지 않은 주소

    # 2. 슬래시가 있으면 슬래시 전까지만 사용
    if "/" in addr:
        addr = addr.split("/")[0].strip()

    # 3. 괄호가 있으면 괄호 전까지만 사용
    if "(" in addr:
        addr = addr.split("(")[0].strip()

    # 4. 특수 표기 제거 (B동, 79B 13L, 외91필지 등)
    # 동/호수 표기 정리
    addr = re.sub(r"\s+\d+[A-Z]\s+\d+L", "", addr)  # "79B 13L" 같은 패턴
    addr = re.sub(r"\s+[A-Z]동(?:\s|$)", "", addr)  # "B동" 같은 패턴
    addr = re.sub(r"\s+외\d+필지.*$", "", addr)  # "외91필지 302동" 같은 패턴
    addr = re.sub(r"\s+\d+동(?:\s|$)", "", addr)  # "302동" 같은 패턴

    # 5. 부가 정보 제거
    # 건물명, 시설명 등은 주소 뒤쪽에 오므로 번지 뒤의 내용 제거
    match = re.search(r"^(.+?(?:리|동|가)\s+\d+(?:-\d+)?)", addr)
    if match:
        addr = match.group(1)

    # 6. 특수 키워드와 그 뒤의 내용 제거
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

    # 7. 날짜 패턴 제거 (예: (06.04.06), [2021.01.01] 등)
    addr = re.sub(r"[\(\[]?\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}[\)\]]?", "", addr)

    # 8. 특수문자 제거
    addr = re.sub(r"[:]", "", addr)

    # 9. 불필요한 공백 정리
    addr = " ".join(addr.split())

    # 10. 시도명이 없으면 추가 (대구 지역 가정)
    if (
        addr
        and not any(
            city in addr
            for city in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
        )
        and any(
            gu in addr
            for gu in [
                "남구",
                "북구",
                "동구",
                "서구",
                "중구",
                "수성구",
                "달서구",
                "달성군",
            ]
        )
    ):
        addr = "대구 " + addr

    return addr


def retry_with_naver(limit: int | None = None, delay: float = 0.2) -> None:
    """
    실패한 주소들을 Naver API로 재시도

    Args:
        limit: 처리할 최대 개수 (None이면 전체)
        delay: API 호출 간 지연 시간
    """
    # API 자격 증명 확인
    if not check_naver_api_credentials():
        logger.error("Naver API 키가 설정되지 않았습니다.")
        logger.info(".env 파일에 NAVER_API_KEY_ID와 NAVER_API_KEY를 설정해주세요.")
        return

    # DB 경로
    db_path = RESULTS_DIR / "geocoding_cache_kakao_v2.db"
    if not db_path.exists():
        logger.error("캐시 DB를 찾을 수 없습니다: %s", db_path)
        return

    # 실패한 주소들 조회
    failed_addresses = get_failed_addresses(db_path, limit)
    total_failed = len(get_failed_addresses(db_path))  # 전체 개수

    logger.info(
        "실패한 주소 %d개 중 %d개를 Naver API로 재처리",
        total_failed,
        len(failed_addresses),
    )

    success_count = 0
    still_failed = []
    success_examples = []

    for i, (address, created_at) in enumerate(failed_addresses, 1):
        logger.info("\n[%d/%d] 처리 중: %s", i, len(failed_addresses), address)

        # 전처리 적용
        processed = preprocess_address_for_naver(address)

        if processed is None:
            logger.info("  유효하지 않은 주소 형식, 건너뜀")
            still_failed.append(address)
            continue

        if processed != address:
            logger.info("  전처리 후: %s", processed)

        # Naver API로 geocoding 시도
        result = geocode_with_naver(processed)

        if result:
            success_count += 1
            success_examples.append((address, processed, result))
            logger.info("  ✓ Naver API 성공! 좌표: %s", result)

            # Kakao 캐시 DB에 업데이트
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE geocoding_cache
                    SET status = 'success',
                        lat = ?,
                        lon = ?,
                        cached_at = ?,
                        jibun_address = ?
                    WHERE query_address = ?
                """,
                    (result[0], result[1], time.time(), f"Naver: {processed}", address),
                )
                conn.commit()
        else:
            still_failed.append(address)
            logger.warning("  ✗ Naver API도 실패")

        # API 호출 간 지연
        if i < len(failed_addresses):
            time.sleep(delay)

    # 결과 요약
    print("\n" + "=" * 60)
    print("Naver API 재처리 결과 요약")
    print("=" * 60)
    print(f"전체 실패 주소: {total_failed}개")
    print(f"재처리 시도: {len(failed_addresses)}개")
    print(f"Naver API 성공: {success_count}개")
    print(f"여전히 실패: {len(still_failed)}개")

    if success_examples:
        print("\nNaver API로 성공한 주소 예시 (최대 10개):")
        for orig, processed, (lat, lon) in success_examples[:10]:
            print(f"  원본: {orig}")
            if processed != orig:
                print(f"  전처리: {processed}")
            print(f"  좌표: ({lat}, {lon})")
            print()

    if still_failed:
        print("\nNaver API도 실패한 주소 예시 (최대 10개):")
        for addr in still_failed[:10]:
            print(f"  - {addr}")


def main() -> None:
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="실패한 geocoding 주소들을 Naver API로 재처리"
    )
    parser.add_argument(
        "--limit", type=int, default=30, help="처리할 최대 개수 (기본값: 30)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="API 호출 간 지연 시간 (초, 기본값: 0.2)",
    )

    args = parser.parse_args()

    retry_with_naver(limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
