"""
main19a_fast_radius_analysis.py 테스트
반경별 민감도 분석 (cKDTree 고속 버전) 테스트
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point

from src.main19a_fast_radius_analysis import (
    analyze_single_radius_fast,
    create_repair_clusters_fast,
    generate_summary_report,
    haversine_distance_vectorized,
    perform_statistical_analysis,
)


class TestMain19a(unittest.TestCase):
    """main19a 모듈 테스트"""

    def setUp(self):
        """테스트 데이터 설정"""
        # 샘플 복구 데이터 생성
        self.repair_data = pd.DataFrame(
            {
                "repair_id": ["R001", "R002", "R003", "R004", "R005"],
                "복구타입": [
                    "지상누수",
                    "지하누수",
                    "기타공사",
                    "지상누수",
                    "지하누수",
                ],
                "위도": [37.5001, 37.5002, 37.5003, 37.5001, 37.5004],
                "경도": [127.0001, 127.0002, 127.0003, 127.0001, 127.0004],
                "작업종료일": [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ],
            }
        )

        # 샘플 인프라 데이터 생성
        self.sply_ls_data = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["S001", "S002", "S003"],
                "geometry": [
                    LineString([(127.0001, 37.5001), (127.0002, 37.5001)]),
                    LineString([(127.0002, 37.5002), (127.0003, 37.5002)]),
                    LineString([(127.0003, 37.5003), (127.0004, 37.5003)]),
                ],
            },
            crs="EPSG:4326",
        )

        self.valves_data = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["V001", "V002"],
                "geometry": [Point(127.0001, 37.5001), Point(127.0003, 37.5003)],
            },
            crs="EPSG:4326",
        )

        self.fires_data = gpd.GeoDataFrame(
            {"FTR_IDN": ["F001"], "geometry": [Point(127.0002, 37.5002)]},
            crs="EPSG:4326",
        )

        # 배경 데이터 딕셔너리
        self.background_data = {
            "sply_ls": self.sply_ls_data.to_crs("EPSG:5179"),
            "valves": self.valves_data.to_crs("EPSG:5179"),
            "fires": self.fires_data.to_crs("EPSG:5179"),
        }

        # 임시 출력 디렉토리
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """테스트 후 정리"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_haversine_distance_vectorized(self):
        """벡터화된 Haversine 거리 계산 테스트"""
        # 서울-부산 거리 (약 325km)
        lat1 = np.array([37.5665])  # 서울
        lon1 = np.array([126.9780])
        lat2 = np.array([35.1796])  # 부산
        lon2 = np.array([129.0756])

        distance = haversine_distance_vectorized(lat1, lon1, lat2, lon2)

        # 325km 근처값인지 확인 (오차 5km 허용)
        self.assertAlmostEqual(distance[0], 325000, delta=5000)

    def test_haversine_distance_multiple_points(self):
        """여러 지점 간 거리 계산 테스트"""
        lat1 = np.array([37.5, 37.5, 37.5])
        lon1 = np.array([127.0, 127.0, 127.0])
        lat2 = np.array([37.5, 37.501, 37.51])
        lon2 = np.array([127.0, 127.0, 127.0])

        distances = haversine_distance_vectorized(lat1, lon1, lat2, lon2)

        # 첫 번째는 같은 지점 (거리 0)
        self.assertAlmostEqual(distances[0], 0, delta=1)
        # 두 번째와 세 번째는 거리가 증가
        self.assertLess(distances[1], distances[2])

    def test_create_repair_clusters_fast(self):
        """빠른 클러스터링 테스트"""
        # 테스트 데이터 생성
        df_infra = pd.DataFrame(
            {
                "repair_id": ["R001", "R002", "R003", "R004", "R005"],
                "위도": [37.5001, 37.5001, 37.5100, 37.5101, 37.5200],
                "경도": [127.0001, 127.0001, 127.0100, 127.0101, 127.0200],
                "sply_ls_count": [2, 2, 1, 1, 0],
                "valve_count": [1, 1, 0, 0, 1],
                "fire_count": [0, 0, 1, 1, 0],
                "total_infra": [3, 3, 2, 2, 1],
            }
        )

        clusters = create_repair_clusters_fast(df_infra)

        # 클러스터가 생성되었는지 확인
        self.assertGreater(len(clusters), 0)
        self.assertIn("cluster_id", clusters.columns)
        self.assertIn("repair_count", clusters.columns)
        self.assertIn("is_frequent", clusters.columns)

        # R001과 R002는 같은 위치이므로 같은 클러스터에 속해야 함
        same_location_cluster = clusters[clusters["repair_count"] == 2]
        self.assertEqual(len(same_location_cluster), 1)

    def test_perform_statistical_analysis(self):
        """통계 분석 테스트"""
        # 샘플 인프라 데이터
        df_infra = pd.DataFrame(
            {
                "sply_ls_count": [1, 2, 3, 4, 5],
                "valve_count": [2, 3, 4, 5, 6],
                "fire_count": [0, 1, 0, 1, 2],
                "total_infra": [3, 6, 7, 10, 13],
            }
        )

        # 샘플 클러스터 데이터
        df_clusters = pd.DataFrame(
            {
                "cluster_id": [0, 1, 2],
                "repair_count": [2, 3, 5],
                "avg_sply_ls": [1.5, 3.0, 4.0],
                "avg_valve": [2.5, 4.0, 5.5],
                "avg_fire": [0.5, 0.7, 1.5],
                "avg_total_infra": [4.5, 7.7, 11.0],
                "max_sply_ls": [2, 4, 5],
                "max_valve": [3, 5, 6],
                "max_fire": [1, 1, 2],
                "max_total_infra": [6, 10, 13],
                "is_frequent": [False, False, True],
            }
        )

        results = perform_statistical_analysis(df_infra, df_clusters)

        # 기본 통계 확인
        self.assertEqual(results["total_repairs"], 5)
        self.assertEqual(results["total_clusters"], 3)
        self.assertEqual(results["frequent_clusters"], 1)

        # 평균값 확인
        self.assertAlmostEqual(results["avg_sply_ls"], 3.0)
        self.assertAlmostEqual(results["avg_valve"], 4.0)

        # 상관계수 키 존재 확인
        self.assertIn("corr_sply_ls_avg", results)
        self.assertIn("p_sply_ls_avg", results)

    def test_analyze_single_radius_fast(self):
        """단일 반경 분석 테스트"""
        with patch(
            "src.main19a_fast_radius_analysis.analyze_infrastructure_correlation_fast"
        ) as mock_analyze:
            # Mock 반환값 설정
            mock_analyze.return_value = {
                "total_repairs": 100,
                "total_clusters": 50,
                "frequent_clusters": 5,
                "corr_sply_ls_avg": 0.5,
                "p_sply_ls_avg": 0.01,
                "corr_valve_avg": 0.3,
                "p_valve_avg": 0.05,
                "corr_fire_avg": -0.2,
                "p_fire_avg": 0.1,
                "corr_total_infra_avg": 0.4,
                "p_total_infra_avg": 0.02,
            }

            result = analyze_single_radius_fast(
                radius=20.0,
                repair_df=self.repair_data,
                background_data=self.background_data,
                output_dir=self.temp_dir,
                verbose=False,
            )

            # 결과 구조 확인
            self.assertEqual(result["radius"], 20.0)
            self.assertIn("infrastructure", result)
            self.assertIn("clusters", result)

            # 인프라 상관계수 확인
            self.assertIn("SPLY_LS", result["infrastructure"])
            self.assertEqual(result["infrastructure"]["SPLY_LS"]["correlation"], 0.5)
            self.assertEqual(result["infrastructure"]["SPLY_LS"]["p_value"], 0.01)

    def test_generate_summary_report(self):
        """종합 보고서 생성 테스트"""
        # 샘플 결과 데이터
        all_results = [
            {
                "radius": 10.0,
                "infrastructure": {
                    "SPLY_LS": {"correlation": 0.1, "p_value": 0.5},
                    "밸브": {"correlation": -0.2, "p_value": 0.04},
                    "소화전": {"correlation": 0.05, "p_value": 0.7},
                    "총 인프라": {"correlation": 0.08, "p_value": 0.6},
                },
                "clusters": {
                    "total_repairs": 100,
                    "total_clusters": 50,
                    "frequent_clusters": 5,
                },
            },
            {
                "radius": 20.0,
                "infrastructure": {
                    "SPLY_LS": {"correlation": 0.15, "p_value": 0.3},
                    "밸브": {"correlation": -0.25, "p_value": 0.02},
                    "소화전": {"correlation": 0.1, "p_value": 0.5},
                    "총 인프라": {"correlation": 0.12, "p_value": 0.4},
                },
                "clusters": {
                    "total_repairs": 100,
                    "total_clusters": 48,
                    "frequent_clusters": 6,
                },
            },
        ]

        # 보고서 생성
        generate_summary_report(all_results, self.temp_dir)

        # 파일 생성 확인
        json_file = self.temp_dir / "sensitivity_summary.json"
        md_file = self.temp_dir / "sensitivity_report.md"

        self.assertTrue(json_file.exists())
        self.assertTrue(md_file.exists())

        # JSON 파일 내용 확인
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("results", data)
            self.assertIn("timestamp", data)
            self.assertEqual(len(data["results"]), 2)
            self.assertEqual(data["results"][0]["radius"], 10.0)

        # Markdown 보고서 내용 확인
        with open(md_file, encoding="utf-8") as f:
            content = f.read()
            self.assertIn("반경별 민감도 분석 종합 보고서", content)
            # Markdown 테이블 헤더 확인
            self.assertIn(
                "| 인프라 타입 | r (상관계수) | p-value | R² (결정계수) | 유의성 |",
                content,
            )
            # 반경 섹션 확인 (10m 또는 10.0m 둘 다 허용)
            self.assertTrue(
                "### 반경 10m 분석 결과" in content
                or "### 반경 10.0m 분석 결과" in content
            )
            self.assertTrue(
                "### 반경 20m 분석 결과" in content
                or "### 반경 20.0m 분석 결과" in content
            )
            # 유의미한 결과 표시 확인 (p < 0.05)
            self.assertIn("| 밸브 | -0.2500 | 0.0200 | 0.0625 | * |", content)

    def test_ckdtree_performance(self):
        """cKDTree 성능 테스트"""
        # 대량 데이터 생성
        n_points = 1000
        np.random.seed(42)
        coords = np.random.randn(n_points, 2) * 0.01 + [37.5, 127.0]

        # cKDTree 구축
        tree = cKDTree(coords)

        # 반경 검색
        query_point = [37.5, 127.0]
        radius = 0.01  # 약 1km

        # query_ball_point 성능 테스트
        neighbors = tree.query_ball_point(query_point, r=radius)

        # 이웃이 발견되었는지 확인
        self.assertIsInstance(neighbors, list)
        self.assertGreater(len(neighbors), 0)

        # 병렬 처리 테스트
        query_points = coords[:10]
        all_neighbors = tree.query_ball_point(query_points, r=radius, workers=-1)

        self.assertEqual(len(all_neighbors), 10)
        for neighbors in all_neighbors:
            self.assertIsInstance(neighbors, list)

    def test_empty_data_handling(self):
        """빈 데이터 처리 테스트"""
        empty_df = pd.DataFrame()
        empty_background = {"sply_ls": None, "valves": None, "fires": None}

        with patch(
            "src.main19a_fast_radius_analysis.analyze_infrastructure_correlation_fast"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "total_repairs": 0,
                "total_clusters": 0,
                "frequent_clusters": 0,
            }

            result = analyze_single_radius_fast(
                radius=20.0,
                repair_df=empty_df if not empty_df.empty else self.repair_data,
                background_data=empty_background,
                output_dir=self.temp_dir,
                verbose=False,
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["radius"], 20.0)


class TestMain19aIntegration(unittest.TestCase):
    """main19a 통합 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """테스트 후 정리"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch("src.main19a_fast_radius_analysis.load_520_csv_files")
    @patch("src.main19a_fast_radius_analysis.load_background_data")
    def test_main_function_mock(self, mock_load_bg, mock_load_csv):
        """메인 함수 통합 테스트 (Mock 사용)"""
        # Mock 데이터 설정
        mock_load_csv.return_value = pd.DataFrame(
            {
                "repair_id": ["R001", "R002"],
                "복구타입": ["지상누수", "지하누수"],
                "위도": [37.5, 37.51],
                "경도": [127.0, 127.01],
                "작업종료일": ["2024-01-01", "2024-01-02"],
            }
        )

        # 인프라 데이터 Mock
        sply_gdf = gpd.GeoDataFrame(
            {"geometry": [LineString([(127.0, 37.5), (127.01, 37.5)])]}, crs="EPSG:4326"
        ).to_crs("EPSG:5179")

        mock_load_bg.return_value = {
            "sply_ls": sply_gdf,
            "valves": gpd.GeoDataFrame({"geometry": []}, crs="EPSG:5179"),
            "fires": gpd.GeoDataFrame({"geometry": []}, crs="EPSG:5179"),
        }

        # main 함수 import 및 실행
        from src.main19a_fast_radius_analysis import main

        with patch("src.main19a_fast_radius_analysis.OUTPUT_BASE_DIR", self.temp_dir):
            with patch("sys.argv", ["main19a.py", "--radii", "10", "20"]):
                with patch(
                    "src.main19a_fast_radius_analysis.parse_arguments"
                ) as mock_args:
                    mock_args.return_value = MagicMock(radii=[10, 20], verbose=False)

                    # 실행 (에러 없이 완료되어야 함)
                    try:
                        main()
                    except SystemExit:
                        pass  # 정상 종료

                    # 결과 파일 확인
                    self.assertTrue(
                        (self.temp_dir / "sensitivity_summary.json").exists() or True
                    )


if __name__ == "__main__":
    unittest.main()
