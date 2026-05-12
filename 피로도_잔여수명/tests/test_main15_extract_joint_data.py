"""
main15_extract_joint_data.py 테스트
파이프 세그먼트 분리 및 조인트 데이터 추출 테스트
"""

from unittest.mock import Mock, patch

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

from src.main15_extract_joint_data import (
    calculate_joint_counts,
    process_pipe_segments,
    process_pipe_type,
    save_segment_data,
    split_linestring_with_semicircle_detection,
)


class TestSplitLinestringWithSemicircleDetection:
    """split_linestring_with_semicircle_detection 함수 테스트"""

    def test_simple_linestring(self):
        """단순한 LineString 테스트"""
        # 3개 점으로 구성된 직선
        coords = [(0, 0), (1, 0), (2, 0)]
        line = LineString(coords)

        segments, merged_indices = split_linestring_with_semicircle_detection(line)

        # 2개의 세그먼트로 분리되어야 함
        assert len(segments) == 2
        assert isinstance(segments[0], LineString)
        assert isinstance(segments[1], LineString)
        assert isinstance(merged_indices, set)

    def test_semicircular_linestring(self):
        """반원형 패턴이 있는 LineString 테스트"""
        # 반원형 좌표 생성 (짧은 세그먼트들)
        coords = []
        num_points = 8
        radius = 0.3
        for i in range(num_points):
            angle = i * np.pi / (num_points - 1)
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            coords.append((x, y))

        line = LineString(coords)
        segments, merged_indices = split_linestring_with_semicircle_detection(line)

        # 반원형 패턴이 병합되어 세그먼트 수가 줄어들 수 있음
        assert len(segments) > 0
        assert isinstance(merged_indices, set)

    def test_multilinestring(self):
        """MultiLineString 테스트"""
        from shapely.geometry import MultiLineString

        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(2, 0), (3, 0)])
        multi_line = MultiLineString([line1, line2])

        segments, merged_indices = split_linestring_with_semicircle_detection(
            multi_line
        )

        assert len(segments) >= 2  # 최소 2개 세그먼트
        assert isinstance(merged_indices, set)

    def test_empty_geometry(self):
        """빈 geometry 테스트"""
        empty_line = LineString()

        segments, merged_indices = split_linestring_with_semicircle_detection(
            empty_line
        )

        assert len(segments) == 0
        assert isinstance(merged_indices, set)


class TestProcessPipeSegments:
    """process_pipe_segments 함수 테스트"""

    def create_mock_pipe_gdf(self, num_pipes: int = 3) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        data = []
        for i in range(num_pipes):
            # 간단한 LineString 생성
            coords = [(i, 0), (i + 1, 0), (i + 2, 0)]
            geometry = LineString(coords)
            data.append({"FTR_IDN": f"{1000 + i}", "geometry": geometry})

        return gpd.GeoDataFrame(data)

    def test_process_pipe_segments_success(self):
        """정상 처리 테스트"""
        mock_gdf = self.create_mock_pipe_gdf(3)

        result = process_pipe_segments(mock_gdf, "PIPE_LM", verbose=False)

        assert result is not None
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= 3  # 최소 원본만큼의 세그먼트
        assert "FTR_IDN" in result.columns
        assert "SUB_IDN" in result.columns
        assert "ORIG_FTR_IDN" in result.columns

    def test_process_pipe_segments_empty_input(self):
        """빈 입력 데이터 테스트"""
        empty_gdf = gpd.GeoDataFrame()

        result = process_pipe_segments(empty_gdf, "PIPE_LM", verbose=False)

        assert result is None

    def test_process_pipe_segments_no_ftr_idn(self):
        """FTR_IDN 컬럼이 없는 경우"""
        data = [{"geometry": LineString([(0, 0), (1, 0)])}]
        gdf = gpd.GeoDataFrame(data)

        result = process_pipe_segments(gdf, "PIPE_LM", verbose=False)

        assert result is None

    def test_process_pipe_segments_invalid_ftr_idn(self):
        """잘못된 FTR_IDN 값"""
        data = [
            {"FTR_IDN": "invalid", "geometry": LineString([(0, 0), (1, 0)])},
            {"FTR_IDN": "123", "geometry": LineString([(1, 0), (2, 0)])},
        ]
        gdf = gpd.GeoDataFrame(data)

        result = process_pipe_segments(gdf, "PIPE_LM", verbose=False)

        # 유효한 레코드만 처리됨
        assert result is not None
        assert len(result) >= 1


class TestCalculateJointCounts:
    """calculate_joint_counts 함수 테스트"""

    def create_test_segments_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 세그먼트 GeoDataFrame 생성"""
        segments = [
            # 연결된 세그먼트들
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),  # 첫 번째와 연결
            LineString([(0, 0), (0, 1)]),  # 첫 번째와 연결 (같은 시작점)
            # 고립된 세그먼트
            LineString([(10, 10), (11, 10)]),
        ]

        data = []
        for i, seg in enumerate(segments):
            data.append(
                {
                    "FTR_IDN": f"{1000 + i}_1",
                    "SUB_IDN": 1,
                    "ORIG_FTR_IDN": 1000 + i,
                    "geometry": seg,
                }
            )

        return gpd.GeoDataFrame(data)

    def test_calculate_joint_counts_basic(self):
        """기본 연결 계산 테스트"""
        segments_gdf = self.create_test_segments_gdf()

        result = calculate_joint_counts(segments_gdf, verbose=False)

        assert result is not None
        assert isinstance(result, gpd.GeoDataFrame)
        assert "CNT_JNT" in result.columns

        # 첫 번째 세그먼트는 2개와 연결되어야 함
        first_segment = result.iloc[0]
        assert first_segment["CNT_JNT"] >= 1

    def test_calculate_joint_counts_empty_input(self):
        """빈 입력 테스트"""
        empty_gdf = gpd.GeoDataFrame()

        result = calculate_joint_counts(empty_gdf, verbose=False)

        assert result is not None
        assert len(result) == 0

    def test_calculate_joint_counts_single_segment(self):
        """단일 세그먼트 테스트"""
        single_segment = gpd.GeoDataFrame(
            [
                {
                    "FTR_IDN": "1000_1",
                    "SUB_IDN": 1,
                    "ORIG_FTR_IDN": 1000,
                    "geometry": LineString([(0, 0), (1, 0)]),
                }
            ]
        )

        result = calculate_joint_counts(single_segment, verbose=False)

        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["CNT_JNT"] == 0  # 연결된 것이 없음


class TestSaveSegmentData:
    """save_segment_data 함수 테스트"""

    def create_test_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 GeoDataFrame 생성"""
        data = [
            {
                "FTR_IDN": "1000_1",
                "SUB_IDN": 1,
                "ORIG_FTR_IDN": 1000,
                "CNT_JNT": 2,
                "SEGMENT_LENGTH": 1.5,
                "IS_SEMICIRCULAR": False,
                "geometry": LineString([(0, 0), (1, 0)]),
            }
        ]
        return gpd.GeoDataFrame(data)

    @patch("pathlib.Path.mkdir")
    @patch("pandas.DataFrame.to_csv")
    @patch("geopandas.GeoDataFrame.to_file")
    def test_save_segment_data_success(self, mock_to_file, mock_to_csv, mock_mkdir):
        """정상 저장 테스트"""
        from pathlib import Path

        test_gdf = self.create_test_gdf()
        results_dir = Path("/tmp/test_results")

        result = save_segment_data(test_gdf, "PIPE_LM", results_dir, verbose=False)

        assert result is True
        mock_mkdir.assert_called()
        mock_to_csv.assert_called_once()
        mock_to_file.assert_called_once()

    def test_save_segment_data_empty_input(self):
        """빈 입력 테스트"""
        from pathlib import Path

        empty_gdf = gpd.GeoDataFrame()
        results_dir = Path("/tmp/test_results")

        result = save_segment_data(empty_gdf, "PIPE_LM", results_dir, verbose=False)

        assert result is False

    @patch("pathlib.Path.mkdir")
    @patch("pandas.DataFrame.to_csv", side_effect=Exception("CSV 저장 실패"))
    def test_save_segment_data_csv_error(self, mock_to_csv, mock_mkdir):
        """CSV 저장 실패 테스트"""
        from pathlib import Path

        test_gdf = self.create_test_gdf()
        results_dir = Path("/tmp/test_results")

        result = save_segment_data(test_gdf, "PIPE_LM", results_dir, verbose=False)

        assert result is False


class TestProcessPipeType:
    """process_pipe_type 함수 테스트"""

    @patch("src.main15_extract_joint_data.RESULTS_DIR")
    @patch("src.main15_extract_joint_data.load_pipe_shapefile")
    @patch("src.main15_extract_joint_data.process_pipe_segments")
    @patch("src.main15_extract_joint_data.save_segment_data")
    def test_process_pipe_type_success(
        self, mock_save, mock_process, mock_load, mock_results_dir
    ):
        """정상 처리 테스트"""
        # Mock 설정
        from pathlib import Path

        mock_results_dir.__truediv__.return_value = Path(
            "/tmp/results/main15_extract_joint_data"
        )
        mock_gdf = Mock(spec=gpd.GeoDataFrame)
        mock_load.return_value = mock_gdf
        mock_process.return_value = mock_gdf
        mock_save.return_value = True

        result = process_pipe_type("PIPE_LM", "0520", verbose=False)

        assert result is True
        mock_load.assert_called_once()
        mock_process.assert_called_once()
        mock_save.assert_called_once()

    @patch("src.main15_extract_joint_data.load_pipe_shapefile")
    def test_process_pipe_type_load_failure(self, mock_load):
        """shapefile 로드 실패 테스트"""
        mock_load.return_value = None

        result = process_pipe_type("PIPE_LM", "0520", verbose=False)

        assert result is False

    @patch("src.main15_extract_joint_data.load_pipe_shapefile")
    @patch("src.main15_extract_joint_data.process_pipe_segments")
    def test_process_pipe_type_process_failure(self, mock_process, mock_load):
        """세그먼트 처리 실패 테스트"""
        mock_load.return_value = Mock(spec=gpd.GeoDataFrame)
        mock_process.return_value = None

        result = process_pipe_type("PIPE_LM", "0520", verbose=False)

        assert result is False


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_constants_import(self):
        """상수 import 테스트"""
        from src.main15_extract_joint_data import (
            calculate_joint_counts,
            process_pipe_segments,
            split_linestring_with_semicircle_detection,
        )

        # 함수들이 정상적으로 import 되는지 확인
        assert callable(split_linestring_with_semicircle_detection)
        assert callable(process_pipe_segments)
        assert callable(calculate_joint_counts)

    def test_dependency_imports(self):
        """의존성 모듈 import 테스트"""
        # 외부 의존성 확인
        import geopandas
        import numpy
        import pandas
        from shapely.geometry import LineString

        assert hasattr(geopandas, "GeoDataFrame")
        assert hasattr(pandas, "DataFrame")
        assert hasattr(numpy, "array")
        assert LineString is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
