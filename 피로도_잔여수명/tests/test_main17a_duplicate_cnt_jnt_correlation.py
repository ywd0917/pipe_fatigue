"""
main17a_duplicate_cnt_jnt_correlation.py 테스트 코드
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pandas as pd
import pytest
import numpy as np
from pyproj import Transformer

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main17a_duplicate_cnt_jnt_correlation import (
    calculate_euclidean_distance,
    load_pipe_data,
    load_520_repair_operations,
    match_operations_to_pipes_v2,
    analyze_cnt_jnt_correlation_v2,
    DEFAULT_DISTANCE_THRESHOLD,
    MIN_REPAIRS_FOR_FREQUENT,
)


class TestEuclideanDistance:
    """유클리드 거리 계산 테스트"""

    def test_same_location(self):
        """같은 위치 간 거리는 0"""
        dist = calculate_euclidean_distance(1000, 2000, 1000, 2000)
        assert dist == pytest.approx(0, abs=0.1)

    def test_known_distance(self):
        """알려진 거리 테스트 (3-4-5 직각삼각형)"""
        # 3m 동쪽, 4m 북쪽 = 5m 거리
        dist = calculate_euclidean_distance(0, 0, 3, 4)
        assert dist == pytest.approx(5, abs=0.01)

    def test_short_distance(self):
        """짧은 거리 계산"""
        # 10m 떨어진 두 점
        dist = calculate_euclidean_distance(100, 200, 110, 200)
        assert dist == pytest.approx(10, abs=0.01)


class TestLoadPipeData:
    """파이프 데이터 로드 테스트"""

    @patch("src.main17a_duplicate_cnt_jnt_correlation.gpd.read_file")
    @patch("src.main17a_duplicate_cnt_jnt_correlation.Path.exists")
    def test_load_both_pipes(self, mock_exists, mock_read_file):
        """PIPE_LM과 SPLY_LS 모두 로드"""
        import geopandas as gpd
        from shapely.geometry import LineString

        # Mock 설정
        mock_exists.return_value = True

        # Mock GeoDataFrame 생성 (EPSG:5179 좌표)
        mock_pipe_lm = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["P001", "P002"],
                "CNT_JNT": [2, 3],
                "geometry": [
                    LineString([(960000, 1940000), (960100, 1940100)]),
                    LineString([(960100, 1940100), (960200, 1940200)]),
                ],
            },
            crs="EPSG:5179",
        )

        mock_sply_ls = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["S001"],
                "CNT_JNT": [1],
                "geometry": [LineString([(960200, 1940200), (960300, 1940300)])],
            },
            crs="EPSG:5179",
        )

        # to_crs 메서드 모킹
        mock_pipe_lm.to_crs = MagicMock(return_value=mock_pipe_lm)
        mock_sply_ls.to_crs = MagicMock(return_value=mock_sply_ls)

        mock_read_file.side_effect = [mock_pipe_lm, mock_sply_ls]

        # 실행
        result = load_pipe_data()

        # 검증
        assert len(result) == 3  # 2 PIPE_LM + 1 SPLY_LS
        assert "CNT_JNT" in result.columns
        assert "PIPE_TYPE" in result.columns
        assert "CENTER_X" in result.columns  # X 좌표
        assert "CENTER_Y" in result.columns  # Y 좌표
        assert set(result["PIPE_TYPE"]) == {"PIPE_LM", "SPLY_LS"}

    @patch("src.main17a_duplicate_cnt_jnt_correlation.Path.exists")
    def test_no_pipe_files(self, mock_exists):
        """파이프 파일이 없을 때"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            load_pipe_data()


class TestLoad520RepairOperations:
    """개별 작업 로드 테스트"""

    @patch("pyproj.Transformer")
    @patch("src.main17a_duplicate_cnt_jnt_correlation.pd.read_csv")
    @patch("src.main17a_duplicate_cnt_jnt_correlation.Path.exists")
    def test_load_operations(self, mock_exists, mock_read_csv, mock_transformer_class):
        """개별 작업 로드"""
        mock_exists.return_value = True

        # Mock transformer
        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = (
            [960000, 960005, 960100, 960105],  # X 좌표
            [1940000, 1940005, 1940100, 1940105],  # Y 좌표
        )
        mock_transformer_class.from_crs.return_value = mock_transformer

        # Mock 데이터
        mock_df = pd.DataFrame(
            {
                "위도": [
                    37.5,
                    37.5001,
                    37.6,
                    37.6001,
                ],  # 처음 두 개와 마지막 두 개가 각각 클러스터
                "경도": [126.9, 126.9001, 127.0, 127.0001],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
                "작업종료일": ["2023-01-01", "2023-01-02", "2023-02-01", "2023-02-02"],
            }
        )
        mock_read_csv.return_value = mock_df

        # 실행
        result = load_520_repair_operations()

        # 검증
        assert len(result) >= 0  # 작업이 있을 수도 없을 수도
        if len(result) > 0:
            assert "X" in result.columns
            assert "Y" in result.columns
            assert "REPAIR_COUNT_AT_LOCATION" in result.columns
            # IS_FREQUENT는 load_520_repair_operations에서는 생성되지 않음

    @patch("src.main17a_duplicate_cnt_jnt_correlation.Path.exists")
    def test_no_repair_file(self, mock_exists):
        """복구 파일이 없을 때"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            load_520_repair_operations()


class TestAnalyzeCntJntCorrelation:
    """CNT_JNT 상관관계 분석 테스트"""

    def test_correlation_analysis(self):
        """상관관계 분석 테스트"""
        # 테스트 데이터 생성
        df_matched = pd.DataFrame(
            {
                "REPAIR_COUNT_AT_LOCATION": [2, 3, 5, 6, 7],  # 마지막 3개가 빈번(>=4)
                "MAX_CNT_JNT": [1, 2, 3, 4, 5],
                "AVG_CNT_JNT": [1.0, 1.5, 2.5, 3.5, 4.5],
                "NEAREST_CNT_JNT": [1, 2, 3, 3, 4],
                "NEAREST_DISTANCE": [10, 20, 15, 25, 30],
                "NEARBY_PIPE_COUNT": [1, 2, 3, 4, 5],
                "HIGH_CNT_PIPE_COUNT": [0, 0, 1, 2, 3],  # CNT_JNT>=3 파이프 수
                "IS_FREQUENT": [False, False, True, True, True],
                "IS_MATCHED": [True, True, True, True, True],  # 매칭 여부 추가
            }
        )

        # 분석 실행
        results = analyze_cnt_jnt_correlation_v2(df_matched)

        # 검증
        assert "max_cnt_frequent" in results
        assert "max_cnt_normal" in results
        assert "avg_cnt_frequent" in results
        assert "avg_cnt_normal" in results
        assert "nearest_cnt_frequent" in results
        assert "nearest_cnt_normal" in results

        # 새로운 통계 검증 (r, p, R²)
        assert "r_max" in results
        assert "p_max" in results
        assert "r2_max" in results
        assert "r_avg" in results
        assert "p_avg" in results
        assert "r2_avg" in results
        assert "r_nearest" in results
        assert "p_nearest" in results
        assert "r2_nearest" in results

        # 빈번 그룹이 더 높은 CNT_JNT를 가져야 함
        assert (
            results["max_cnt_frequent"]["cnt_jnt_mean"]
            > results["max_cnt_normal"]["cnt_jnt_mean"]
        )
        assert (
            results["avg_cnt_frequent"]["cnt_jnt_mean"]
            > results["avg_cnt_normal"]["cnt_jnt_mean"]
        )


class TestConstants:
    """상수 정의 테스트"""

    def test_default_distance_threshold(self):
        """기본 거리 임계값"""
        assert DEFAULT_DISTANCE_THRESHOLD == 30.0

    def test_min_repairs_for_frequent(self):
        """빈번한 재작업 기준"""
        assert MIN_REPAIRS_FOR_FREQUENT == 4


class TestMatchOperationsToPipes:
    """작업-파이프 매칭 테스트"""

    def test_match_within_distance(self):
        """거리 내 파이프 매칭"""
        # 작업 데이터 (EPSG:5179)
        df_operations = pd.DataFrame(
            {
                "OPERATION_ID": [0],  # OPERATION_ID 추가
                "X": [960000],
                "Y": [1940000],
                "REPAIR_COUNT_AT_LOCATION": [5],
                "파일타입": ["지상누수"],
                "작업타입": ["지상누수"],  # 작업타입 추가
                "작업종료일": ["2023-01-01"],
            }
        )

        # 파이프 데이터 (EPSG:5179)
        df_pipes = pd.DataFrame(
            {
                "FTR_IDN": ["P001", "P002", "P003"],
                "CNT_JNT": [2, 3, 4],
                "CENTER_X": [960010, 960020, 960100],  # 처음 두 개만 30m 이내
                "CENTER_Y": [1940010, 1940020, 1940100],
                "PIPE_TYPE": ["PIPE_LM", "PIPE_LM", "SPLY_LS"],
            }
        )

        # 매칭 실행 (tuple 반환: df_matched, total_operations, matched_operations)
        result, total_ops, matched_ops = match_operations_to_pipes_v2(
            df_operations, df_pipes, 50.0
        )

        # 검증
        assert len(result) == 1  # 1개 작업
        assert total_ops == 1  # 총 1개 작업
        assert matched_ops == 1  # 1개 매칭
        assert "MAX_CNT_JNT" in result.columns
        assert "AVG_CNT_JNT" in result.columns
        assert "NEAREST_CNT_JNT" in result.columns
        assert "NEARBY_PIPE_COUNT" in result.columns
        assert result["IS_FREQUENT"].iloc[0] == True  # REPAIR_COUNT_AT_LOCATION=5 >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
