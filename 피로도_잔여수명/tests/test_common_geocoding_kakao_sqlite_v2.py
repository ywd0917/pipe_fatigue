"""
geocoding_kakao_sqlite_v2.py 테스트
Kakao Maps API 지오코딩 캐시 시스템 테스트
"""

import os
import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.common.geocoding_kakao_sqlite_v2 import (
    CACHE_DB,
    GeocodingCacheSQLiteV2,
    GeocodingError,
    check_api_credentials,
    geocode_address,
    get_cache_stats,
    preprocess_address_for_api,
)


class TestGeocodingCacheSQLiteV2:
    """GeocodingCacheSQLiteV2 클래스 테스트"""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋"""
        GeocodingCacheSQLiteV2._instance = None
        GeocodingCacheSQLiteV2._initialized = False

    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        cache1 = GeocodingCacheSQLiteV2()
        cache2 = GeocodingCacheSQLiteV2()

        assert cache1 is cache2
        assert GeocodingCacheSQLiteV2._instance is not None

    @patch("sqlite3.connect")
    def test_init_database_creation(self, mock_connect):
        """데이터베이스 초기화 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_connect.return_value = mock_conn

        GeocodingCacheSQLiteV2()

        # 데이터베이스 연결이 시도되었는지 확인
        mock_connect.assert_called()
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_cache_initialization(self):
        """캐시 초기화 테스트"""
        cache = GeocodingCacheSQLiteV2()

        # 캐시 인스턴스가 정상적으로 생성되었는지 확인
        assert cache is not None
        assert isinstance(cache, GeocodingCacheSQLiteV2)

        # 싱글톤 패턴 확인
        cache2 = GeocodingCacheSQLiteV2()
        assert cache is cache2

    @patch("sqlite3.connect")
    def test_get_cache_hit(self, mock_connect):
        """캐시 히트 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)

        # 성공 결과 모킹
        mock_cursor.fetchone.return_value = (
            "서울특별시 강남구 테헤란로 123",  # jibun_address
            "서울특별시 강남구 테헤란로 123길 456",  # road_address
            37.123456,  # lat
            127.123456,  # lon
            "success",  # status
            None,  # error
            time.time(),  # cached_at
        )

        cache = GeocodingCacheSQLiteV2()
        result = cache.get("서울특별시 강남구 테헤란로 123")

        assert result is not None
        assert result["status"] == "success"
        assert "latitude" in result
        assert "longitude" in result
        assert "jibun_address" in result
        assert "road_address" in result

    @patch("sqlite3.connect")
    def test_get_cache_miss(self, mock_connect):
        """캐시 미스 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)

        mock_cursor.fetchone.return_value = None

        cache = GeocodingCacheSQLiteV2()
        result = cache.get("존재하지 않는 주소")

        assert result is None

    @patch("sqlite3.connect")
    def test_set_success_result(self, mock_connect):
        """성공 결과 캐시 저장 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)

        cache = GeocodingCacheSQLiteV2()

        success_data = {
            "status": "success",
            "jibun_address": "서울특별시 강남구 테헤란로 123",
            "road_address": "서울특별시 강남구 테헤란로 123길 456",
            "latitude": 37.123456,
            "longitude": 127.123456,
        }

        cache.set("테스트 주소", success_data)

        # INSERT 쿼리가 실행되었는지 확인
        mock_cursor.execute.assert_called()
        args = mock_cursor.execute.call_args[0]
        assert "INSERT OR REPLACE" in args[0]

    @patch("sqlite3.connect")
    def test_set_not_found_result(self, mock_connect):
        """주소 찾을 수 없음 결과 캐시 저장 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)

        cache = GeocodingCacheSQLiteV2()

        not_found_data = {"status": "not_found"}

        cache.set("존재하지 않는 주소", not_found_data)

        mock_cursor.execute.assert_called()

    @patch("sqlite3.connect")
    def test_set_error_result(self, mock_connect):
        """오류 결과 캐시 저장 테스트"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_connect.return_value.__exit__ = Mock(return_value=None)

        cache = GeocodingCacheSQLiteV2()

        error_data = {"status": "error", "error": "API 오류"}

        cache.set("테스트 주소", error_data)

        mock_cursor.execute.assert_called()


class TestPreprocessAddressForApi:
    """preprocess_address_for_api 함수 테스트"""

    def test_basic_preprocessing(self):
        """기본 전처리 테스트"""
        address = "서울특별시 강남구 테헤란로 123"
        processed = preprocess_address_for_api(address)

        assert isinstance(processed, str)
        assert len(processed) > 0

    def test_slash_removal(self):
        """슬래시 제거 테스트"""
        address = "서울특별시 강남구 테헤란로 123/추가정보"
        processed = preprocess_address_for_api(address)

        assert "추가정보" not in processed
        assert "서울특별시 강남구 테헤란로 123" in processed

    def test_parentheses_removal(self):
        """괄호 제거 테스트"""
        address = "서울특별시 강남구 테헤란로 123 (신사동)"
        processed = preprocess_address_for_api(address)

        assert "(신사동)" not in processed
        assert "서울특별시 강남구 테헤란로 123" in processed

    def test_empty_address(self):
        """빈 주소 테스트"""
        empty_addresses = ["", "   ", None]

        for addr in empty_addresses:
            processed = preprocess_address_for_api(addr)
            if addr is None:
                assert processed is None
            else:
                assert isinstance(processed, str)

    def test_daegu_city_addition(self):
        """대구 시도명 추가 테스트"""
        address = "남구 대명로 123"
        processed = preprocess_address_for_api(address)

        # 대구가 추가되었는지 확인
        assert "대구" in processed


class TestGeocodeAddress:
    """geocode_address 함수 테스트"""

    @patch("src.common.geocoding_kakao_sqlite_v2._get_cache")
    @patch("requests.get")
    def test_successful_geocoding(self, mock_get, mock_get_cache):
        """성공적인 지오코딩 테스트"""
        # Cache mock
        mock_cache = Mock()
        mock_cache.get.return_value = None  # 캐시 미스
        mock_get_cache.return_value = mock_cache

        # 성공 응답 모킹
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "documents": [
                {
                    "address": {
                        "address_name": "서울특별시 강남구 테헤란로 123",
                        "y": "37.123456",
                        "x": "127.123456",
                    },
                    "road_address": {
                        "address_name": "서울특별시 강남구 테헤란로 123길 456",
                        "y": "37.123456",
                        "x": "127.123456",
                    },
                }
            ]
        }
        mock_get.return_value = mock_response

        result = geocode_address("서울특별시 강남구 테헤란로 123")

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)  # latitude
        assert isinstance(result[1], float)  # longitude

    @patch("src.common.geocoding_kakao_sqlite_v2._get_cache")
    def test_cache_hit(self, mock_get_cache):
        """캐시 히트 테스트"""
        mock_cache = Mock()
        mock_cache.get.return_value = {
            "status": "success",
            "latitude": 37.123456,
            "longitude": 127.123456,
        }
        mock_get_cache.return_value = mock_cache

        result = geocode_address("서울특별시 강남구 테헤란로 123")

        assert result == (37.123456, 127.123456)

    @patch("src.common.geocoding_kakao_sqlite_v2._get_cache")
    @patch("requests.get")
    def test_address_not_found(self, mock_get, mock_get_cache):
        """주소 찾을 수 없음 테스트"""
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"documents": []}
        mock_get.return_value = mock_response

        result = geocode_address("존재하지 않는 주소")

        assert result is None

    def test_empty_address(self):
        """빈 주소 테스트"""
        result = geocode_address("")
        assert result is None

        result = geocode_address(None)
        assert result is None

    @patch("src.common.geocoding_kakao_sqlite_v2.KAKAO_API_KEY", None)
    def test_missing_api_key(self):
        """API 키 없음 테스트"""
        result = geocode_address("테스트 주소")
        assert result is None


class TestGetCacheStats:
    """get_cache_stats 함수 테스트"""

    @patch("src.common.geocoding_kakao_sqlite_v2._get_cache")
    def test_get_cache_stats(self, mock_get_cache):
        """캐시 통계 조회 테스트"""
        mock_cache = Mock()
        mock_cache.get_stats.return_value = {
            "total": 100,
            "success": 80,
            "not_found": 15,
            "error": 5,
            "success_rate": 80.0,
        }
        mock_get_cache.return_value = mock_cache

        stats = get_cache_stats()

        assert isinstance(stats, dict)
        assert "total" in stats
        assert "success" in stats
        assert "success_rate" in stats
        assert stats["total"] == 100
        assert stats["success_rate"] == 80.0


class TestCheckApiCredentials:
    """check_api_credentials 함수 테스트"""

    @patch("src.common.geocoding_kakao_sqlite_v2.KAKAO_API_KEY", "test_key")
    def test_api_credentials_available(self):
        """API 키가 있는 경우"""
        result = check_api_credentials()
        assert result is True

    @patch("src.common.geocoding_kakao_sqlite_v2.KAKAO_API_KEY", None)
    def test_api_credentials_missing(self):
        """API 키가 없는 경우"""
        result = check_api_credentials()
        assert result is False

    @patch("src.common.geocoding_kakao_sqlite_v2.KAKAO_API_KEY", "")
    def test_api_credentials_empty(self):
        """API 키가 빈 문자열인 경우"""
        result = check_api_credentials()
        assert result is False


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_imports(self):
        """모듈 import 테스트"""
        from src.common.geocoding_kakao_sqlite_v2 import (
            GeocodingCacheSQLiteV2,
            GeocodingError,
            geocode_address,
            preprocess_address_for_api,
        )

        assert GeocodingCacheSQLiteV2 is not None
        assert GeocodingError is not None
        assert callable(preprocess_address_for_api)
        assert callable(geocode_address)

    def test_constants(self):
        """상수 테스트"""
        assert isinstance(CACHE_DB, Path)

    def test_environment_variables(self):
        """환경 변수 테스트"""
        # API 키 환경 변수 확인 (실제 값이 아닌 존재 여부만)
        api_key = os.getenv("KAKAO_API_KEY")
        # API 키가 있든 없든 문자열이거나 None이어야 함
        assert api_key is None or isinstance(api_key, str)


class TestErrorHandling:
    """오류 처리 테스트"""

    def test_geocoding_error_creation(self):
        """GeocodingError 생성 테스트"""
        error = GeocodingError("테스트 오류")
        assert isinstance(error, Exception)
        assert str(error) == "테스트 오류"

    @patch("sqlite3.connect")
    def test_database_connection_error(self, mock_connect):
        """데이터베이스 연결 오류 테스트"""
        # 싱글톤 리셋 (이미 초기화된 경우를 대비)
        GeocodingCacheSQLiteV2._instance = None
        GeocodingCacheSQLiteV2._initialized = False

        mock_connect.side_effect = sqlite3.Error("DB 연결 실패")

        # 연결 오류가 발생해도 예외가 전파되지 않아야 함
        try:
            cache = GeocodingCacheSQLiteV2()
            # 캐시 초기화가 실패했지만 인스턴스는 생성됨
            assert cache is not None

            # get 메서드에서도 DB 오류가 발생하도록 설정
            mock_conn = Mock()
            mock_conn.__enter__ = Mock(side_effect=sqlite3.Error("DB 연결 실패"))
            mock_conn.__exit__ = Mock(return_value=None)
            mock_connect.return_value = mock_conn

            result = cache.get("테스트 주소")
            # DB 오류 시 None을 반환해야 함
            assert result is None
        except Exception as e:
            # 예상치 못한 예외가 발생하면 테스트 실패
            pytest.fail(f"Unexpected exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
