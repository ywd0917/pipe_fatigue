"""
Kakao Maps API를 사용한 Geocoding (개선된 SQLite 캐시 버전)
- 원본 쿼리 주소를 키로 사용
- 지번/도로명 주소 모두 저장
"""

import logging
import os
import sqlite3
import time
import unicodedata
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from src.common.config import RESULTS_DIR
from src.common.geocoding_constants import (
    API_TIMEOUT,
    CACHE_RETRY_DAYS,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_RETRIES,
    calculate_retry_wait_time,
)

# 환경 변수 로드
load_dotenv()

# API 설정
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")
KAKAO_GEOCODING_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# 캐시 설정
CACHE_DB = RESULTS_DIR / "geocoding_cache_kakao_v2.db"

# 로거 설정
logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Geocoding 관련 오류"""


class GeocodingCacheSQLiteV2:
    """개선된 SQLite 기반 Geocoding 캐시 (싱글톤 패턴)"""

    _instance: "GeocodingCacheSQLiteV2 | None" = None
    _initialized: bool = False

    def __new__(cls, db_file: Path = CACHE_DB) -> "GeocodingCacheSQLiteV2":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_file: Path = CACHE_DB):
        if GeocodingCacheSQLiteV2._initialized:
            return

        self.db_file = db_file
        self._ensure_table()
        GeocodingCacheSQLiteV2._initialized = True
        logger.info("SQLite 캐시 v2 초기화 완료: %s", self.db_file)

    def _ensure_table(self) -> None:
        """테이블이 없으면 생성"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS geocoding_cache (
                        query_address TEXT PRIMARY KEY,
                        jibun_address TEXT,
                        road_address TEXT,
                        lat REAL,
                        lon REAL,
                        status TEXT,
                        error TEXT,
                        cached_at REAL
                    )
                """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jibun_address ON geocoding_cache(jibun_address)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_road_address ON geocoding_cache(road_address)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_status ON geocoding_cache(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_cached_at ON geocoding_cache(cached_at)"
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("데이터베이스 초기화 실패: %s", e)

    def get(self, query_address: str) -> dict[str, Any] | None:
        """원본 쿼리 주소로 캐시에서 조회"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT jibun_address, road_address, lat, lon, status, error, cached_at
                    FROM geocoding_cache
                    WHERE query_address = ?
                """,
                    (query_address,),
                )

                result = cursor.fetchone()
                if result:
                    jibun_address, road_address, lat, lon, status, error, cached_at = (
                        result
                    )
                    if status == "success":
                        return {
                            "status": "success",
                            "jibun_address": jibun_address,
                            "road_address": road_address,
                            "latitude": lat,
                            "longitude": lon,
                            "cached_at": cached_at,
                        }
                    if status == "not_found":
                        return {"status": "not_found", "cached_at": cached_at}
                    return {"status": "error", "error": error, "cached_at": cached_at}

                return None
        except sqlite3.Error as e:
            logger.error("데이터베이스 조회 실패: %s", e)
            return None

    def set(self, query_address: str, data: dict[str, Any]) -> None:
        """원본 쿼리 주소를 키로 캐시에 저장"""
        cached_at = time.time()

        if data["status"] == "success":
            jibun_address = data.get("jibun_address")
            road_address = data.get("road_address")
            lat = data.get("latitude")
            lon = data.get("longitude")
            status = "success"
            error = None
        elif data["status"] == "not_found":
            jibun_address = None
            road_address = None
            lat = None
            lon = None
            status = "not_found"
            error = None
        else:
            jibun_address = None
            road_address = None
            lat = None
            lon = None
            status = "error"
            error = data.get("error", "Unknown error")

        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO geocoding_cache
                    (query_address, jibun_address, road_address, lat, lon, status, error, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        query_address,
                        jibun_address,
                        road_address,
                        lat,
                        lon,
                        status,
                        error,
                        cached_at,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("데이터베이스 저장 실패: %s", e)

    def get_stats(self) -> dict[str, Any]:
        """캐시 통계"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()

                # 전체 개수
                cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
                total = cursor.fetchone()[0]

                # 상태별 개수
                cursor.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM geocoding_cache
                    GROUP BY status
                """
                )

                stats = {"total": total}
                for status, count in cursor.fetchall():
                    if status == "success":
                        stats["success"] = count
                    elif status == "not_found":
                        stats["not_found"] = count
                    elif status == "error":
                        stats["error"] = count

                # 기본값 설정
                stats["success"] = stats.get("success", 0)
                stats["not_found"] = stats.get("not_found", 0)
                stats["error"] = stats.get("error", 0)
                stats["success_rate"] = (
                    (stats["success"] / total * 100) if total > 0 else 0
                )

                return stats
        except sqlite3.Error as e:
            logger.error("데이터베이스 통계 조회 실패: %s", e)
            return {
                "total": 0,
                "success": 0,
                "not_found": 0,
                "error": 0,
                "success_rate": 0,
            }


# 전역 캐시 인스턴스
_cache = None


def _get_cache() -> GeocodingCacheSQLiteV2:
    """캐시 인스턴스 반환"""
    global _cache
    if _cache is None:
        _cache = GeocodingCacheSQLiteV2()
    return _cache


def check_api_credentials() -> bool:
    """API 자격 증명 확인"""
    return bool(KAKAO_API_KEY)


def preprocess_address_for_api(address: str) -> str:
    """
    API 호출을 위한 주소 전처리

    Args:
        address: 원본 주소

    Returns:
        전처리된 주소
    """
    if not address or not isinstance(address, str):
        return address

    # 기본 정리 및 Unicode NFC 정규화
    addr = unicodedata.normalize("NFC", address.strip())

    # 슬래시가 있으면 슬래시 전까지만 사용
    if "/" in addr:
        addr = addr.split("/")[0].strip()

    # 괄호가 있으면 괄호 전까지만 사용
    if "(" in addr:
        addr = addr.split("(")[0].strip()

    # 특수 표기 제거 (B동, 79B 13L, 외91필지 등)
    import re

    # 동/호수 표기 정리
    addr = re.sub(r"\s+\d+[A-Z]\s+\d+L", "", addr)  # "79B 13L" 같은 패턴
    addr = re.sub(r"\s+[A-Z]동(?:\s|$)", "", addr)  # "B동" 같은 패턴
    addr = re.sub(r"\s+외\d+필지.*$", "", addr)  # "외91필지 302동" 같은 패턴
    addr = re.sub(r"\s+\d+동(?:\s|$)", "", addr)  # "302동" 같은 패턴

    # 날짜 패턴 제거 (예: (06.04.06), [2021.01.01] 등)
    addr = re.sub(r"[\(\[]?\d{2,4}[.\-/]\d{1,2}[.\-/]\d{1,2}[\)\]]?", "", addr)

    # 부가 정보 제거 (건물명, 시설명 등은 주소 뒤쪽에 오므로 번지 뒤의 내용 제거)
    match = re.search(r"^(.+?(?:리|동|가)\s+\d+(?:-\d+)?)", addr)
    if match:
        addr = match.group(1)

    # 특수 키워드 제거 (폐전, 폐지 등)
    remove_keywords = ["폐전", "폐지", "폐업", "철거", "이전", "없음"]
    for keyword in remove_keywords:
        if keyword in addr:
            addr = addr.replace(keyword, "").strip()

    # 시도명이 없으면 추가 (대구 지역 가정)
    if not any(
        city in addr
        for city in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
    ) and any(
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
    ):
        addr = "대구 " + addr

    return addr


def geocode_address(
    address: str,
    use_cache: bool = True,
    no_api: bool = False,
    max_retries: int = MAX_RETRIES,
) -> tuple[float, float] | None:
    """
    주소를 위도/경도로 변환 (Kakao Maps API)
    원본 주소를 그대로 캐싱하고, API 호출 시에만 전처리

    Args:
        address: 변환할 주소 (원본 그대로)
        use_cache: 캐시 사용 여부
        no_api: API 호출 없이 캐시만 사용 (오프라인 모드)
        max_retries: API 연결 오류시 최대 재시도 횟수

    Returns:
        (위도, 경도) 튜플 또는 None
    """
    if not address or not isinstance(address, str):
        return None

    # 원본 주소를 그대로 키로 사용 (Unicode NFC 정규화 적용)
    query_address = unicodedata.normalize("NFC", address.strip())

    # 캐시 확인
    cache = _get_cache()
    if use_cache:
        cached = cache.get(query_address)
        if cached:
            if cached["status"] == "success":
                logger.debug("캐시에서 찾음: %s", query_address)
                return (cached["latitude"], cached["longitude"])
            # not_found인 경우 시간 체크
            if cached["status"] == "not_found":
                current_time = time.time()
                cached_time = cached.get("cached_at", 0)
                days_passed = (current_time - cached_time) / (60 * 60 * 24)

                if days_passed >= CACHE_RETRY_DAYS:
                    logger.debug(
                        "캐시에 실패 기록 있음, %.1f일 경과하여 재시도: %s",
                        days_passed,
                        query_address,
                    )
                    # 1일 이상 지났으므로 다시 API 호출하도록 계속 진행
                else:
                    logger.debug(
                        "캐시에 실패 기록 있음, %.1f일 경과 (재시도 안함): %s",
                        days_passed,
                        query_address,
                    )
                    return None  # 1일이 지나지 않았으므로 패스
            # error 상태인 경우도 재시도를 위해 계속 진행

    # no_api 모드에서는 캐시에 없으면 None 반환
    if no_api:
        logger.debug("오프라인 모드: 캐시에 없음 - %s", query_address)
        return None

    # API 키 확인
    if not KAKAO_API_KEY:
        logger.error("Kakao API 키가 설정되지 않았습니다")
        return None

    # API 호출을 위해 주소 전처리
    preprocessed_address = preprocess_address_for_api(query_address)
    logger.debug("API 호출: '%s' → '%s'", query_address, preprocessed_address)

    # API 호출 (재시도 로직 포함)
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": preprocessed_address}

    for attempt in range(max_retries):
        try:
            # 재시도시 지수 백오프
            if attempt > 0:
                wait_time = calculate_retry_wait_time(attempt)
                logger.info(
                    "재시도 %d/%d: %s초 대기 중...", attempt, max_retries - 1, wait_time
                )
                time.sleep(wait_time)

            response = requests.get(
                KAKAO_GEOCODING_URL, headers=headers, params=params, timeout=API_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            if data.get("documents"):
                # 첫 번째 결과 사용
                first_result = data["documents"][0]

                # 도로명 주소 우선, 없으면 지번 주소
                if first_result.get("road_address"):
                    address_info = first_result["road_address"]
                    road_address = address_info.get("address_name", "")
                    jibun_address = ""
                    # 지번 주소 정보가 있으면 추가
                    if first_result.get("address"):
                        jibun_address = first_result["address"].get("address_name", "")
                else:
                    address_info = first_result["address"]
                    jibun_address = address_info.get("address_name", "")
                    road_address = ""

                # 좌표
                lat = float(address_info["y"])
                lon = float(address_info["x"])

                # 캐시에 저장 (원본 쿼리 주소를 키로)
                if use_cache:
                    cache.set(
                        query_address,
                        {
                            "status": "success",
                            "jibun_address": jibun_address,
                            "road_address": road_address,
                            "latitude": lat,
                            "longitude": lon,
                        },
                    )

                # 성공 로그는 debug 레벨로 (기본적으로 표시 안됨)
                logger.debug(
                    "API 성공: %s → %s", query_address, road_address or jibun_address
                )
                return (lat, lon)
            logger.warning(
                "Kakao: 검색 결과 없음 - %s (전처리: %s)",
                query_address,
                preprocessed_address,
            )
            # 캐시에 저장
            if use_cache:
                cache.set(query_address, {"status": "not_found"})
            return None

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # 연결 오류나 타임아웃은 재시도
            if attempt < max_retries - 1:
                logger.warning(
                    "Kakao API 연결 오류 (시도 %d/%d): %s", attempt + 1, max_retries, e
                )
                continue
            logger.error("Kakao API 연결 실패 (모든 재시도 실패): %s", e)
            if use_cache:
                cache.set(
                    query_address,
                    {
                        "status": "error",
                        "error": f"Connection failed after {max_retries} attempts: {e!s}",
                    },
                )
            return None

        except requests.exceptions.HTTPError as e:
            # HTTP 오류 (4xx, 5xx)
            if (
                e.response.status_code >= HTTP_SERVER_ERROR_THRESHOLD
                and attempt < max_retries - 1
            ):
                # 서버 오류는 재시도
                logger.warning(
                    "Kakao API 서버 오류 %s (시도 %d/%d)",
                    e.response.status_code,
                    attempt + 1,
                    max_retries,
                )
                continue
            # 클라이언트 오류(4xx)나 마지막 시도 실패
            logger.error("Kakao API HTTP 오류: %s", e)
            if use_cache:
                cache.set(query_address, {"status": "error", "error": str(e)})
            return None

        except requests.exceptions.RequestException as e:
            # 기타 요청 오류
            logger.error("Kakao API 요청 오류: %s", e)
            if use_cache:
                cache.set(query_address, {"status": "error", "error": str(e)})
            return None

        except Exception as e:
            # 기타 오류
            logger.error("Kakao geocoding 오류: %s", e)
            if use_cache:
                cache.set(query_address, {"status": "error", "error": str(e)})
            return None

    # 모든 재시도 실패 (이미 처리됨)
    return None


def get_cache_stats() -> dict[str, Any]:
    """캐시 통계 반환"""
    cache = _get_cache()
    return cache.get_stats()
