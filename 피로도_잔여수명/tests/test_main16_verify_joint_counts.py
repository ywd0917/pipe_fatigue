"""
main16_verify_joint_counts.py 테스트
CNT_JNT 검증 시각화 스크립트 테스트
"""

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from src.main16_verify_joint_counts import (
    analyze_connections,
    load_joint_data,
    load_segment_geometries,
    select_diverse_samples,
)


class TestLoadJointData:
    """load_joint_data 함수 테스트"""

    def create_test_csv_content(self) -> str:
        """테스트용 CSV 내용 생성"""
        return """FTR_IDN,SUB_IDN,ORIG_FTR_IDN,CNT_JNT,SEGMENT_LENGTH
1000_1,1,1000,2,1.5
1001_1,1,1001,1,2.0
1002_1,1,1002,3,0.8
1003_1,1,1003,0,1.2
1004_1,1,1004,2,1.8
"""

    @patch("pandas.read_csv")
    def test_load_joint_data_success(self, mock_read_csv):
        """정상 로드 테스트"""
        # Mock 데이터 설정
        test_data = pd.DataFrame(
            {
                "FTR_IDN": ["1000_1", "1001_1", "1002_1"],
                "CNT_JNT": [2, 1, 3],
                "SEGMENT_LENGTH": [1.5, 2.0, 0.8],
            }
        )
        mock_read_csv.return_value = test_data

        result = load_joint_data(Path("/fake/path.csv"))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "CNT_JNT" in result.columns
        mock_read_csv.assert_called_once()

    @patch("pandas.read_csv", side_effect=FileNotFoundError())
    def test_load_joint_data_file_not_found(self, mock_read_csv):
        """파일 없음 예외 테스트"""
        with pytest.raises(FileNotFoundError):
            load_joint_data(Path("/nonexistent/path.csv"))

    @patch("pandas.read_csv")
    def test_load_joint_data_empty_file(self, mock_read_csv):
        """빈 파일 테스트"""
        mock_read_csv.return_value = pd.DataFrame()

        result = load_joint_data(Path("/fake/empty.csv"))

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestSelectDiverseSamples:
    """select_diverse_samples 함수 테스트"""

    def create_test_dataframe(self) -> pd.DataFrame:
        """테스트용 DataFrame 생성"""
        data = []
        # CNT_JNT = 0: 3개
        for i in range(3):
            data.append({"FTR_IDN": f"1000_{i}", "CNT_JNT": 0, "SEGMENT_LENGTH": 1.0})

        # CNT_JNT = 1: 5개
        for i in range(5):
            data.append({"FTR_IDN": f"1010_{i}", "CNT_JNT": 1, "SEGMENT_LENGTH": 1.5})

        # CNT_JNT = 2: 10개
        for i in range(10):
            data.append({"FTR_IDN": f"1020_{i}", "CNT_JNT": 2, "SEGMENT_LENGTH": 2.0})

        return pd.DataFrame(data)

    def test_select_diverse_samples_basic(self):
        """기본 샘플 선택 테스트"""
        df = self.create_test_dataframe()

        result = select_diverse_samples(df, max_per_cnt=3)

        assert isinstance(result, pd.DataFrame)
        assert len(result) <= len(df)

        # 각 CNT_JNT별로 최대 3개씩만 선택되어야 함
        cnt_counts = result["CNT_JNT"].value_counts()
        for cnt, count in cnt_counts.items():
            assert count <= 3

    def test_select_diverse_samples_max_per_cnt(self):
        """max_per_cnt 매개변수 테스트"""
        df = self.create_test_dataframe()

        result = select_diverse_samples(df, max_per_cnt=2)

        # 각 CNT_JNT별로 최대 2개씩만 선택
        cnt_counts = result["CNT_JNT"].value_counts()
        for cnt, count in cnt_counts.items():
            assert count <= 2

    def test_select_diverse_samples_empty_input(self):
        """빈 입력 테스트"""
        empty_df = pd.DataFrame()

        result = select_diverse_samples(empty_df, max_per_cnt=5)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_select_diverse_samples_single_cnt_jnt(self):
        """단일 CNT_JNT 값만 있는 경우"""
        df = pd.DataFrame(
            {
                "FTR_IDN": ["1000_1", "1000_2", "1000_3"],
                "CNT_JNT": [2, 2, 2],
                "SEGMENT_LENGTH": [1.0, 1.5, 2.0],
            }
        )

        result = select_diverse_samples(df, max_per_cnt=2)

        assert len(result) == 2
        assert all(result["CNT_JNT"] == 2)


class TestAnalyzeConnections:
    """analyze_connections 함수 테스트"""

    def create_test_segments(self) -> list:
        """테스트용 세그먼트 리스트 생성"""
        return [
            LineString([(1, 0), (2, 0)]),  # 연결된 세그먼트 1
            LineString([(0, 0), (0, 1)]),  # 연결된 세그먼트 2
            LineString([(10, 10), (11, 10)]),  # 고립된 세그먼트
        ]

    def test_analyze_connections_basic(self):
        """기본 연결 분석 테스트"""
        target_segment = LineString([(0, 0), (1, 0)])
        nearby_segments = self.create_test_segments()

        connections = analyze_connections(
            target_segment, nearby_segments, tolerance=0.001
        )

        assert isinstance(connections, dict)
        assert "end_to_end" in connections
        assert "t_junction" in connections
        assert "cross" in connections

        # 모든 값이 음이 아닌 정수여야 함
        for key, value in connections.items():
            assert isinstance(value, int)
            assert value >= 0

    def test_analyze_connections_no_nearby(self):
        """주변 세그먼트가 없는 경우"""
        target_segment = LineString([(0, 0), (1, 0)])
        empty_segments = []

        connections = analyze_connections(target_segment, empty_segments)

        assert connections["end_to_end"] == 0
        assert connections["t_junction"] == 0
        assert connections["cross"] == 0

    def test_analyze_connections_tolerance(self):
        """tolerance 매개변수 테스트"""
        target_segment = LineString([(0, 0), (1, 0)])
        nearby_segments = [LineString([(1.001, 0), (2, 0)])]  # 약간 떨어진 세그먼트

        # 작은 tolerance
        connections1 = analyze_connections(
            target_segment, nearby_segments, tolerance=0.0001
        )

        # 큰 tolerance
        connections2 = analyze_connections(
            target_segment, nearby_segments, tolerance=0.01
        )

        # 큰 tolerance에서 더 많은 연결을 찾을 수 있음
        total1 = sum(connections1.values())
        total2 = sum(connections2.values())
        assert total2 >= total1


class TestLoadSegmentGeometries:
    """load_segment_geometries 함수 테스트"""

    def create_test_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        return gpd.GeoDataFrame(
            [{"FTR_IDN": "1000", "geometry": LineString([(0, 0), (1, 0), (2, 0)])}]
        )

    def create_test_joint_df(self) -> pd.DataFrame:
        """테스트용 joint DataFrame 생성"""
        return pd.DataFrame(
            [
                {
                    "FTR_IDN": "1000_1",
                    "ORIG_FTR_IDN": 1000,
                    "SUB_IDN": 1,
                    "CNT_JNT": 2,
                    "SEGMENT_LENGTH": 1.0,
                }
            ]
        )

    def test_load_segment_geometries_success(self):
        """정상 geometry 로드 테스트"""
        pipe_gdf = self.create_test_pipe_gdf()
        joint_df = self.create_test_joint_df()

        result = load_segment_geometries(pipe_gdf, joint_df)

        assert isinstance(result, dict)
        # 결과가 있는지 확인 (실제 geometry 생성 로직에 따라 달라질 수 있음)

    def test_load_segment_geometries_empty_input(self):
        """빈 입력 테스트"""
        empty_pipe_gdf = gpd.GeoDataFrame(columns=["FTR_IDN", "geometry"])
        empty_joint_df = pd.DataFrame(
            columns=["FTR_IDN", "ORIG_FTR_IDN", "SUB_IDN", "CNT_JNT", "SEGMENT_LENGTH"]
        )

        result = load_segment_geometries(empty_pipe_gdf, empty_joint_df)

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_load_segment_geometries_no_matching_pipe(self):
        """매칭되는 파이프가 없는 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        joint_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": "9999_1",  # 존재하지 않는 원본 파이프
                    "ORIG_FTR_IDN": 9999,
                    "SUB_IDN": 1,
                    "CNT_JNT": 0,
                    "SEGMENT_LENGTH": 1.0,
                }
            ]
        )

        result = load_segment_geometries(pipe_gdf, joint_df)

        assert isinstance(result, dict)
        assert len(result) == 0


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_function_imports(self):
        """함수 import 테스트"""
        from src.main16_verify_joint_counts import (
            analyze_connections,
            load_joint_data,
            load_segment_geometries,
            select_diverse_samples,
        )

        assert callable(load_joint_data)
        assert callable(select_diverse_samples)
        assert callable(analyze_connections)
        assert callable(load_segment_geometries)

    def test_dependency_imports(self):
        """의존성 모듈 import 테스트"""
        import geopandas
        import matplotlib.pyplot
        import pandas
        from shapely.geometry import LineString

        assert hasattr(pandas, "read_csv")
        assert hasattr(geopandas, "GeoDataFrame")
        assert hasattr(matplotlib.pyplot, "savefig")
        assert LineString is not None
        assert Point is not None

    def test_path_handling(self):
        """Path 객체 처리 테스트"""
        from pathlib import Path

        test_path = Path("/fake/test.csv")
        assert isinstance(test_path, Path)
        assert str(test_path) == "/fake/test.csv"


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_very_small_segments(self):
        """매우 작은 세그먼트 테스트"""
        target_segment = LineString([(0, 0), (0.001, 0)])
        nearby_segments = [LineString([(0.001, 0), (0.002, 0)])]

        connections = analyze_connections(
            target_segment, nearby_segments, tolerance=0.001
        )

        # 매우 작은 세그먼트도 처리 가능해야 함
        assert isinstance(connections, dict)
        assert "end_to_end" in connections

    def test_duplicate_segments(self):
        """중복된 세그먼트 테스트"""
        target_segment = LineString([(0, 0), (1, 0)])
        nearby_segments = [LineString([(0, 0), (1, 0)])]  # 같은 geometry

        connections = analyze_connections(
            target_segment, nearby_segments, tolerance=0.001
        )

        # 중복 세그먼트도 연결로 감지될 수 있음
        assert isinstance(connections, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
