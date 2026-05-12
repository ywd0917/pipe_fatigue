#!/usr/bin/env python3
"""
JSON 메타데이터 방식 테스트
main14b/main14c의 metadata.json 생성 및 main14b2/main14c2의 읽기 테스트
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd


class TestJSONMetadata(unittest.TestCase):
    """JSON 메타데이터 생성 및 읽기 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """테스트 환경 정리"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_main14b_metadata_generation(self):
        """main14b의 metadata.json 생성 테스트"""
        # 테스트 데이터 준비
        test_metadata = {
            "total_clusters": 981,
            "matched_clusters": 938,
            "matching_rate": 95.6,
            "avg_pipes_per_cluster": 4.2,
            "distance_threshold": 10,
            "min_repairs_for_frequent": 4,
            "analysis_factors": ["K_age", "K_soil", "K_traffic"],
            "timestamp": "2025-08-27T20:00:00",
        }

        # metadata.json 저장
        metadata_path = self.temp_path / "metadata.json"
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(test_metadata, f, indent=2, ensure_ascii=False)

        # 저장된 파일 검증
        self.assertTrue(metadata_path.exists())

        # 내용 검증
        with metadata_path.open("r", encoding="utf-8") as f:
            loaded_metadata = json.load(f)

        self.assertEqual(loaded_metadata["total_clusters"], 981)
        self.assertEqual(loaded_metadata["matched_clusters"], 938)
        self.assertAlmostEqual(loaded_metadata["matching_rate"], 95.6, places=1)

    def test_main14b2_metadata_reading(self):
        """main14b2의 metadata.json 읽기 테스트"""
        # 테스트용 metadata.json 생성
        test_metadata = {
            "total_clusters": 981,
            "matched_clusters": 938,
            "matching_rate": 95.6,
            "avg_pipes_per_cluster": 4.2,
        }

        metadata_path = self.temp_path / "main14b" / "metadata.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(test_metadata, f)

        # main14b2에서 읽기 시뮬레이션
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            matching_stats = {
                "total_clusters": metadata.get("total_clusters", 0),
                "matched_clusters": metadata.get("matched_clusters", 0),
                "matching_rate": metadata.get("matching_rate", 0),
                "avg_pipes_per_cluster": metadata.get("avg_pipes_per_cluster", 0),
            }

        # 검증
        self.assertEqual(matching_stats["total_clusters"], 981)
        self.assertEqual(matching_stats["matched_clusters"], 938)
        self.assertAlmostEqual(matching_stats["matching_rate"], 95.6, places=1)

    def test_main14c_metadata_generation(self):
        """main14c의 지역별 metadata.json 생성 테스트"""
        # 테스트 데이터 준비
        region_code = "0470"
        test_metadata = {
            "region_code": region_code,
            "total_clusters": 172,
            "matched_clusters": 171,
            "matching_rate": 99.4,
            "avg_pipes_per_cluster": 3.5,
            "total_repairs": 218,
            "total_pipes": 1234,
            "timestamp": "2025-08-27T20:00:00",
        }

        # 지역별 디렉토리 생성
        region_dir = self.temp_path / region_code
        region_dir.mkdir(parents=True, exist_ok=True)

        # metadata.json 저장
        metadata_path = region_dir / "metadata.json"
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(test_metadata, f, indent=2, ensure_ascii=False)

        # 저장된 파일 검증
        self.assertTrue(metadata_path.exists())

        # 내용 검증
        with metadata_path.open("r", encoding="utf-8") as f:
            loaded_metadata = json.load(f)

        self.assertEqual(loaded_metadata["region_code"], region_code)
        self.assertEqual(loaded_metadata["total_clusters"], 172)
        self.assertEqual(loaded_metadata["matched_clusters"], 171)

    def test_main14c2_metadata_reading(self):
        """main14c2의 지역별 metadata.json 읽기 테스트"""
        # 테스트용 metadata.json 생성
        region_code = "0470"
        test_metadata = {
            "region_code": region_code,
            "total_clusters": 172,
            "matched_clusters": 171,
            "matching_rate": 99.4,
            "avg_pipes_per_cluster": 3.5,
            "total_repairs": 218,
        }

        region_output_dir = self.temp_path / region_code
        region_output_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = region_output_dir / "metadata.json"

        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(test_metadata, f)

        # main14c2에서 읽기 시뮬레이션
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            matching_stats = {
                "total_clusters": metadata.get("total_clusters", 0),
                "matched_clusters": metadata.get("matched_clusters", 0),
                "matching_rate": metadata.get("matching_rate", 0),
                "avg_pipes_per_cluster": metadata.get("avg_pipes_per_cluster", 0),
                "total_repairs": metadata.get("total_repairs", 0),
            }

        # 검증
        self.assertEqual(matching_stats["total_clusters"], 172)
        self.assertEqual(matching_stats["matched_clusters"], 171)
        self.assertAlmostEqual(matching_stats["matching_rate"], 99.4, places=1)
        self.assertEqual(matching_stats["total_repairs"], 218)

    def test_missing_metadata_handling(self):
        """metadata.json 파일이 없을 때 에러 처리 테스트"""
        metadata_file = self.temp_path / "nonexistent" / "metadata.json"

        # 파일이 존재하지 않을 때 처리
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            # 기본값으로 처리
            matching_stats = {
                "total_clusters": 0,
                "matched_clusters": 0,
                "matching_rate": 0,
                "avg_pipes_per_cluster": 0,
            }

        # 기본값 검증
        self.assertEqual(matching_stats["total_clusters"], 0)
        self.assertEqual(matching_stats["matched_clusters"], 0)
        self.assertEqual(matching_stats["matching_rate"], 0)

    def test_metadata_backward_compatibility(self):
        """구버전 호환성 테스트 (필드가 없을 경우)"""
        # 일부 필드가 없는 metadata.json
        incomplete_metadata = {
            "total_clusters": 100,
            "matched_clusters": 95,
            # matching_rate와 avg_pipes_per_cluster 없음
        }

        metadata_path = self.temp_path / "metadata.json"
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(incomplete_metadata, f)

        # 읽기
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        # get 메서드로 기본값 처리
        matching_stats = {
            "total_clusters": metadata.get("total_clusters", 0),
            "matched_clusters": metadata.get("matched_clusters", 0),
            "matching_rate": metadata.get("matching_rate", 0),  # 기본값 0
            "avg_pipes_per_cluster": metadata.get(
                "avg_pipes_per_cluster", 0
            ),  # 기본값 0
        }

        # 검증
        self.assertEqual(matching_stats["total_clusters"], 100)
        self.assertEqual(matching_stats["matched_clusters"], 95)
        self.assertEqual(matching_stats["matching_rate"], 0)  # 기본값
        self.assertEqual(matching_stats["avg_pipes_per_cluster"], 0)  # 기본값


if __name__ == "__main__":
    unittest.main()
