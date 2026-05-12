"""
Geocoding 기능 테스트
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src.common.geocoding_constants import MAX_RETRIES
from src.common.geocoding_naver_sqlite import (
    GeocodingCacheSQLite,
    check_api_credentials,
    geocode_address,
)


class TestGeocodingCacheSQLite:
    """GeocodingCacheSQLite 클래스 테스트"""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋"""
        GeocodingCacheSQLite._instance = None
        GeocodingCacheSQLite._initialized = False

    def test_init_with_empty_cache(self):
        """빈 캐시로 초기화"""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            cache = GeocodingCacheSQLite(Path(tmp.name))
            # SQLite는 테이블이 자동 생성됨
            assert cache.db_file.exists()

    def test_get_and_set(self):
        """캐시 저장 및 조회"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            cache = GeocodingCacheSQLite(Path(tmp.name))

            address = "대구광역시 달서구 성당로 123"
            result = {
                "status": "success",
                "latitude": 35.8,
                "longitude": 128.5,
                "jibun_address": "대구광역시 달서구 성당동 123-4",
                "road_address": "대구광역시 달서구 성당로 123",
            }

            # 캐시에 저장
            cache.set(address, result)

            # 캐시에서 조회
            cached = cache.get(address)
            assert cached is not None
            assert cached["status"] == "success"
            assert cached["latitude"] == 35.8
            assert cached["longitude"] == 128.5
            assert "cached_at" in cached

            # 파일 삭제
            Path(tmp.name).unlink(missing_ok=True)

    def test_get_nonexistent(self):
        """존재하지 않는 주소 조회"""
        with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
            cache = GeocodingCacheSQLite(Path(tmp.name))

            result = cache.get("존재하지 않는 주소")
            assert result is None


class TestAPIFunctions:
    """API 관련 함수 테스트"""

    @patch.dict(
        os.environ, {"NAVER_API_KEY_ID": "test_id", "NAVER_API_KEY": "test_key"}
    )
    def test_check_api_credentials_success(self):
        """API 자격 증명 확인 - 성공"""
        # 모듈을 다시 import하여 환경 변수 반영
        import src.common.geocoding_naver_sqlite

        src.common.geocoding_naver_sqlite.API_KEY_ID = "test_id"
        src.common.geocoding_naver_sqlite.API_KEY = "test_key"

        assert check_api_credentials() is True

    def test_check_api_credentials_missing(self):
        """API 자격 증명 확인 - 실패"""
        # 원래 값 백업
        import src.common.geocoding_naver_sqlite

        original_key_id = src.common.geocoding_naver_sqlite.NAVER_API_KEY_ID
        original_key = src.common.geocoding_naver_sqlite.NAVER_API_KEY

        try:
            # 임시로 None으로 설정
            src.common.geocoding_naver_sqlite.NAVER_API_KEY_ID = None
            src.common.geocoding_naver_sqlite.NAVER_API_KEY = None

            assert check_api_credentials() is False
        finally:
            # 원래 값 복원
            src.common.geocoding_naver_sqlite.NAVER_API_KEY_ID = original_key_id
            src.common.geocoding_naver_sqlite.NAVER_API_KEY = original_key


class TestGeocodeAddress:
    """geocode_address 함수 테스트"""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋"""
        GeocodingCacheSQLite._instance = None
        GeocodingCacheSQLite._initialized = False
        # 모듈 레벨 _cache 변수도 리셋
        import src.common.geocoding_naver_sqlite

        src.common.geocoding_naver_sqlite._cache = None

    @patch(
        "src.common.geocoding_naver_sqlite.check_api_credentials", return_value=False
    )
    def test_geocode_without_credentials(self, mock_check):
        """API 자격 증명 없이 geocoding 시도"""
        # 싱글톤 초기화
        GeocodingCacheSQLite._instance = None
        GeocodingCacheSQLite._initialized = False

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            with patch("src.common.geocoding_naver_sqlite.CACHE_DB", Path(tmp.name)):
                # 새로운 빈 캐시 파일 사용
                import src.common.geocoding_naver_sqlite

                src.common.geocoding_naver_sqlite._cache = None

                # 캐시를 사용하지 않고 테스트
                result = geocode_address(
                    "대구광역시 달서구 성당로 123", use_cache=False
                )
                assert result is None

            # 정리
            Path(tmp.name).unlink(missing_ok=True)

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    def test_geocode_with_cache_hit(self, mock_check):
        """캐시 히트 시 API 호출 안함"""
        # 캐시를 mock하여 데이터 반환
        mock_cache = Mock()
        mock_cache.get.return_value = {
            "status": "success",
            "latitude": 35.8,
            "longitude": 128.5,
            "jibun_address": "대구광역시 달서구 성당동 123-4",
            "road_address": "대구광역시 달서구 성당로 123",
        }

        with (
            patch(
                "src.common.geocoding_naver_sqlite.GeocodingCacheSQLite",
                return_value=mock_cache,
            ),
            patch("requests.get") as mock_get,
        ):
            result = geocode_address("대구광역시 달서구 성당로 123", use_cache=True)

            # API가 호출되지 않았는지 확인
            mock_get.assert_not_called()

            # 캐시된 결과 반환
            assert result == (35.8, 128.5)

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    @patch("requests.get")
    def test_geocode_without_cache(self, mock_get, mock_check):
        """캐시 없이 geocoding"""
        # 성공적인 API 응답 모의
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "OK",
            "addresses": [
                {
                    "y": "35.8",
                    "x": "128.5",
                    "jibunAddress": "대구광역시 달서구 성당동 123-4",
                    "roadAddress": "대구광역시 달서구 성당로 123",
                }
            ],
        }
        mock_get.return_value = mock_response

        address = "대구광역시 달서구 성당로 123"
        result = geocode_address(address, use_cache=False)

        # API 호출됨
        mock_get.assert_called_once()

        # 결과 확인
        assert result == (35.8, 128.5)

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    @patch("requests.get")
    def test_geocode_address_not_found(self, mock_get, mock_check):
        """주소를 찾을 수 없는 경우"""
        # 결과 없음 응답 모의
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "OK", "addresses": []}
        mock_get.return_value = mock_response

        address = "존재하지 않는 주소"
        result = geocode_address(address, use_cache=False)

        # API 호출됨
        mock_get.assert_called_once()

        # None 반환
        assert result is None

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    @patch("requests.get")
    def test_geocode_with_connection_error_retry(self, mock_get, mock_check):
        """연결 오류시 재시도"""
        # 처음 두 번은 연결 오류, 세 번째는 성공
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.Timeout("Timeout"),
            Mock(
                raise_for_status=Mock(return_value=None),
                json=Mock(
                    return_value={
                        "status": "OK",
                        "addresses": [
                            {
                                "y": "35.8",
                                "x": "128.5",
                                "jibunAddress": "대구광역시 달서구 성당동 123-4",
                                "roadAddress": "대구광역시 달서구 성당로 123",
                            }
                        ],
                    }
                ),
            ),
        ]

        with patch("time.sleep"):  # sleep 호출 무시
            address = "대구광역시 달서구 성당로 123"
            result = geocode_address(address, use_cache=False, max_retries=MAX_RETRIES)

        # 3번 호출됨
        assert mock_get.call_count == 3

        # 성공 결과 반환
        assert result == (35.8, 128.5)

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    @patch("requests.get")
    def test_geocode_with_server_error_retry(self, mock_get, mock_check):
        """서버 오류시 재시도"""
        # 처음은 500 오류, 두 번째는 성공
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError(response=mock_error_response)
        )

        mock_success_response = Mock()
        mock_success_response.raise_for_status.return_value = None
        mock_success_response.json.return_value = {
            "status": "OK",
            "addresses": [
                {
                    "y": "35.8",
                    "x": "128.5",
                    "jibunAddress": "대구광역시 달서구 성당동 123-4",
                    "roadAddress": "대구광역시 달서구 성당로 123",
                }
            ],
        }

        mock_get.side_effect = [mock_error_response, mock_success_response]

        with patch("time.sleep"):  # sleep 호출 무시
            address = "대구광역시 달서구 성당로 123"
            result = geocode_address(address, use_cache=False, max_retries=2)

        # 2번 호출됨
        assert mock_get.call_count == 2

        # 성공 결과 반환
        assert result == (35.8, 128.5)

    @patch("src.common.geocoding_naver_sqlite.check_api_credentials", return_value=True)
    @patch("requests.get")
    def test_geocode_with_all_retries_failed(self, mock_get, mock_check):
        """모든 재시도 실패"""
        # 모든 시도가 연결 오류
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with patch("time.sleep"):  # sleep 호출 무시
            address = "대구광역시 달서구 성당로 123"
            result = geocode_address(address, use_cache=False, max_retries=2)

        # 2번 호출됨
        assert mock_get.call_count == 2

        # None 반환
        assert result is None
