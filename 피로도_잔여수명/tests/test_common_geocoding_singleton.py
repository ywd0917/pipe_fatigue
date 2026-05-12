"""
싱글톤 패턴 테스트
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from src.common.geocoding_kakao_sqlite_v2 import GeocodingCacheSQLiteV2 as KakaoCache
from src.common.geocoding_naver_sqlite import GeocodingCacheSQLite as NaverCache


class TestGeocodingSingleton(unittest.TestCase):
    """Geocoding 캐시 싱글톤 패턴 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        self.temp_cache_file = Path(self.temp_dir) / "test_cache.json"

        # 싱글톤 리셋
        NaverCache._instance = None
        NaverCache._initialized = False
        KakaoCache._instance = None
        KakaoCache._initialized = False

    def tearDown(self):
        """테스트 정리"""
        # 임시 디렉토리 삭제
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # 싱글톤 리셋
        NaverCache._instance = None
        NaverCache._initialized = False
        KakaoCache._instance = None
        KakaoCache._initialized = False

    def test_naver_cache_singleton(self):
        """Naver 캐시 싱글톤 패턴 테스트"""
        # 첫 번째 인스턴스 생성
        cache1 = NaverCache(self.temp_cache_file)
        cache1.set(
            "테스트주소1", {"status": "success", "latitude": 37.5, "longitude": 127.0}
        )

        # 두 번째 인스턴스 생성 (같은 객체여야 함)
        cache2 = NaverCache(self.temp_cache_file)

        # 같은 인스턴스인지 확인
        self.assertIs(cache1, cache2)

        # 같은 데이터를 참조하는지 확인
        result = cache2.get("테스트주소1")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["latitude"], 37.5)

    def test_kakao_cache_singleton(self):
        """Kakao 캐시 싱글톤 패턴 테스트"""
        # 첫 번째 인스턴스 생성
        cache1 = KakaoCache(self.temp_cache_file)
        cache1.set(
            "테스트주소2", {"status": "success", "latitude": 36.5, "longitude": 126.0}
        )

        # 두 번째 인스턴스 생성 (같은 객체여야 함)
        cache2 = KakaoCache(self.temp_cache_file)

        # 같은 인스턴스인지 확인
        self.assertIs(cache1, cache2)

        # 같은 데이터를 참조하는지 확인
        result = cache2.get("테스트주소2")
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["latitude"], 36.5)

    def test_cache_persistence(self):
        """캐시 영속성 테스트"""
        # Naver 캐시에 데이터 추가
        naver_cache = NaverCache(self.temp_cache_file)
        naver_cache.set(
            "서울시청",
            {"status": "success", "latitude": 37.5663, "longitude": 126.9779},
        )

        # 캐시 파일이 생성되었는지 확인
        self.assertTrue(self.temp_cache_file.exists())

        # 여러 번 인스턴스를 생성해도 데이터가 유지되는지 확인
        for _ in range(5):
            new_cache = NaverCache(self.temp_cache_file)
            result = new_cache.get("서울시청")
            self.assertIsNotNone(result)
            self.assertEqual(result["latitude"], 37.5663)


if __name__ == "__main__":
    unittest.main()
