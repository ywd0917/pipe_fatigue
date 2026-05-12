"""
main8_verify_overlap_samples.py 테스트
"""

import random
from unittest.mock import MagicMock, patch

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from shapely.geometry import LineString

from src.main8_verify_overlap_samples import (
    load_all_data,
    load_traffic_results,
    main,
    setup_plot_style,
)
from src.overlap_verifier import (
    select_sample_pipes,
    visualize_pipe_sample,
)


@pytest.fixture
def mock_pipe_gdf():
    """테스트용 파이프 GeoDataFrame"""
    data = {
        "FTR_IDN": [1.0, 2.0, 3.0, 4.0, 5.0],
        "geometry": [
            LineString([(0, 0), (10, 0)]),
            LineString([(10, 10), (20, 10)]),
            LineString([(20, 20), (30, 20)]),
            LineString([(30, 30), (40, 30)]),
            LineString([(40, 40), (50, 40)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def mock_road_gdf():
    """테스트용 도로 GeoDataFrame"""
    data = {
        "RN_CD": ["1234001", "1234002", "1234003"],
        "RN": ["테스트로1", "테스트로2", "테스트로3"],
        "ROAD_BT": [20.0, 15.0, 10.0],
        "geometry": [
            LineString([(0, 5), (10, 5)]),
            LineString([(10, 15), (20, 15)]),
            LineString([(20, 25), (30, 25)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


@pytest.fixture
def mock_traffic_df():
    """테스트용 교통 분석 결과 DataFrame"""
    data = {
        "FTR_IDN": [1.0, 2.0, 3.0, 4.0, 5.0],
        "RN_CD": ["1234001", "1234002", None, None, "1234003"],
        "RN": ["테스트로1", "테스트로2", None, None, "테스트로3"],
        "ROAD_BT": [20.0, 15.0, None, None, 10.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_data_dir(tmp_path):
    """테스트용 데이터 디렉토리 생성"""
    # 디렉토리 구조 생성
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    # export 디렉토리 생성
    export_dir = raw_dir / "export_shp_20231201(0520)"
    export_dir.mkdir()

    # 도로 디렉토리 생성
    road_dir = raw_dir / "road"
    road_dir.mkdir()

    return raw_dir


class TestSetupPlotStyle:
    """setup_plot_style 함수 테스트"""

    @patch("src.main8_verify_overlap_samples.korean_font_utils.setup_korean_font")
    @patch("matplotlib.pyplot.style.use")
    def test_setup_plot_style(self, mock_style_use, mock_setup_font):
        """플롯 스타일 설정 테스트"""
        mock_setup_font.return_value = "AppleGothic"

        setup_plot_style()

        mock_style_use.assert_called_once_with("default")
        mock_setup_font.assert_called_once()


class TestLoadAllData:
    """load_all_data 함수 테스트"""

    @patch("src.main8_verify_overlap_samples.load_road_data")
    @patch("src.main8_verify_overlap_samples.load_pipe_shapefile")
    @patch("src.main8_verify_overlap_samples.load_traffic_results")
    def test_load_all_data_success(
        self, mock_load_traffic, mock_load_pipe, mock_load_road
    ):
        """정상적인 모든 데이터 로드"""
        mock_road_gdf = MagicMock()
        mock_pipe_gdf = MagicMock()
        mock_traffic_df = MagicMock()

        mock_load_road.return_value = mock_road_gdf
        mock_load_pipe.return_value = mock_pipe_gdf
        mock_load_traffic.return_value = mock_traffic_df

        road_gdf, pipe_gdf, traffic_df = load_all_data("0520", "pipe")

        assert road_gdf is not None
        assert pipe_gdf is not None
        assert traffic_df is not None

    @patch("src.main8_verify_overlap_samples.load_road_data")
    def test_load_all_data_no_road_data(self, mock_load_road):
        """도로 데이터가 없는 경우"""
        mock_load_road.return_value = None

        result = load_all_data("0520", "pipe")

        assert result is None


class TestLoadTrafficResults:
    """load_traffic_results 함수 테스트"""

    def test_load_traffic_results_success(self, tmp_path):
        """정상적인 CSV 로드"""
        # traffic 디렉토리 생성
        traffic_dir = tmp_path / "results" / "traffic"
        traffic_dir.mkdir(parents=True)

        # CSV 파일 생성
        csv_path = traffic_dir / "0520_pipe_traffic.csv"
        test_df = pd.DataFrame(
            {"FTR_IDN": [1, 2, 3], "RN_CD": ["1234001", "1234002", None]}
        )
        test_df.to_csv(csv_path, index=False)

        results_path = tmp_path / "results"
        with patch("src.main8_verify_overlap_samples.RESULTS_DIR", results_path):
            result = load_traffic_results("0520", "pipe")

        assert result is not None
        assert len(result) == 3
        assert result["RN_CD"].dtype == object  # 문자열로 읽혔는지 확인

    def test_load_traffic_results_file_not_found(self, tmp_path):
        """CSV 파일이 없는 경우"""
        results_path = tmp_path / "results"
        with (
            patch("src.main8_verify_overlap_samples.RESULTS_DIR", results_path),
            patch("builtins.print"),
        ):
            result = load_traffic_results("0520", "pipe")

        assert result is None


class TestSelectSamplePipes:
    """select_sample_pipes 함수 테스트"""

    def test_select_sample_pipes_balanced(self, mock_pipe_gdf, mock_traffic_df):
        """균형잡힌 샘플 선택"""
        # 시드 고정
        random.seed(42)

        sample_ids, matching_info = select_sample_pipes(
            mock_pipe_gdf, mock_traffic_df, sample_size=4
        )

        assert len(sample_ids) == 4
        assert len(matching_info) == 4

        # 매칭된 것과 안된 것이 섞여있는지 확인
        matched_count = sum(1 for v in matching_info.values() if v is not None)
        assert matched_count == 2  # 절반씩

    def test_select_sample_pipes_all_matched(self, mock_pipe_gdf):
        """모두 매칭된 경우"""
        traffic_df = pd.DataFrame(
            {
                "FTR_IDN": [1.0, 2.0, 3.0, 4.0, 5.0],
                "RN_CD": ["1234001", "1234002", "1234003", "1234004", "1234005"],
            }
        )

        sample_ids, matching_info = select_sample_pipes(
            mock_pipe_gdf, traffic_df, sample_size=4
        )

        # 모두 매칭된 경우에도 요청한 샘플 수만큼 선택됨
        assert len(sample_ids) == 4
        assert all(v is not None for v in matching_info.values())

    def test_select_sample_pipes_empty(self, mock_pipe_gdf):
        """빈 데이터프레임"""
        empty_df = pd.DataFrame(columns=["FTR_IDN", "RN_CD"])

        sample_ids, matching_info = select_sample_pipes(
            mock_pipe_gdf, empty_df, sample_size=4
        )

        assert len(sample_ids) == 0
        assert len(matching_info) == 0


class TestVisualizePipeSample:
    """visualize_pipe_sample 함수 테스트"""

    def test_visualize_pipe_sample_matched(self, mock_pipe_gdf, mock_road_gdf):
        """매칭된 파이프 시각화"""
        fig, ax = plt.subplots()

        visualize_pipe_sample(
            mock_pipe_gdf, mock_road_gdf, 1.0, "1234001", ax, "Test Sample"
        )

        # 제목 확인
        assert ax.get_title() == "Test Sample"

        # 범례 요소들이 그려졌는지 확인
        assert len(ax.lines) > 0 or len(ax.collections) > 0

        plt.close(fig)

    def test_visualize_pipe_sample_unmatched(self, mock_pipe_gdf, mock_road_gdf):
        """매칭 안된 파이프 시각화"""
        fig, ax = plt.subplots()

        visualize_pipe_sample(
            mock_pipe_gdf, mock_road_gdf, 3.0, None, ax, "Test Sample"
        )

        assert ax.get_title() == "Test Sample"
        plt.close(fig)

    def test_visualize_pipe_sample_not_found(self, mock_pipe_gdf, mock_road_gdf):
        """존재하지 않는 파이프"""
        fig, ax = plt.subplots()

        visualize_pipe_sample(
            mock_pipe_gdf, mock_road_gdf, 999.0, None, ax, "Test Sample"
        )

        # 텍스트가 표시되었는지 확인
        assert len(ax.texts) > 0
        assert "파이프 999" in ax.texts[0].get_text()

        plt.close(fig)


class TestMainFunction:
    """main 함수 통합 테스트"""

    @patch("src.main8_verify_overlap_samples.load_road_data")
    @patch("src.main8_verify_overlap_samples.load_pipe_shapefile")
    @patch("src.main8_verify_overlap_samples.load_traffic_results")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("sys.argv", ["test", "0520", "--output-dir", "/tmp/test"])
    def test_main_with_region_code(
        self,
        mock_close,
        mock_savefig,
        mock_load_traffic,
        mock_load_pipe,
        mock_load_road,
        mock_pipe_gdf,
        mock_road_gdf,
        mock_traffic_df,
        tmp_path,
    ):
        """지역 코드 지정하여 실행"""
        mock_load_road.return_value = mock_road_gdf
        mock_load_pipe.return_value = mock_pipe_gdf
        mock_load_traffic.return_value = mock_traffic_df

        with patch(
            "sys.argv", ["test", "0520", "--output-dir", str(tmp_path / "output")]
        ):
            main()

        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("src.main8_verify_overlap_samples.load_road_data")
    @patch("src.main8_verify_overlap_samples.load_pipe_shapefile")
    @patch("src.main8_verify_overlap_samples.load_traffic_results")
    def test_main_no_region_code(
        self, mock_load_traffic, mock_load_pipe, mock_load_road, tmp_path
    ):
        """지역 코드 미지정시 자동 선택"""
        # traffic 디렉토리와 CSV 파일 생성
        traffic_dir = tmp_path / "results" / "traffic"
        traffic_dir.mkdir(parents=True)
        (traffic_dir / "0520_pipe_traffic.csv").touch()
        (traffic_dir / "0903_sply_traffic.csv").touch()

        mock_load_road.return_value = None  # 도로 데이터 로드 실패로 종료

        results_path = tmp_path / "results"
        with (
            patch("src.main8_verify_overlap_samples.RESULTS_DIR", results_path),
            patch("builtins.print") as mock_print,
            patch("sys.argv", ["test"]),
        ):
            main()

        # 지역 코드가 자동으로 선택되었는지 확인
        printed_messages = [call[0][0] for call in mock_print.call_args_list]
        assert any("발견된 지역 코드" in msg for msg in printed_messages)

    @patch("src.main8_verify_overlap_samples.load_road_data")
    def test_main_no_traffic_dir(self, mock_load_road, tmp_path):
        """traffic 디렉토리가 없는 경우"""
        results_path = tmp_path / "results"
        with (
            patch("src.main8_verify_overlap_samples.RESULTS_DIR", results_path),
            patch("builtins.print") as mock_print,
            patch("sys.argv", ["test"]),
            pytest.raises(ValueError, match="사용 가능한 지역 코드를 찾을 수 없습니다"),
        ):
            main()

        mock_print.assert_any_call("오류: traffic 디렉토리를 찾을 수 없습니다.")

    @patch("src.main8_verify_overlap_samples.load_road_data")
    @patch("src.main8_verify_overlap_samples.load_pipe_shapefile")
    def test_main_data_load_failure(self, mock_load_pipe, mock_load_road):
        """데이터 로드 실패"""
        mock_load_road.return_value = None

        with patch("sys.argv", ["test", "0520"]):
            main()

        # 파이프 데이터 로드까지 가지 않음
        mock_load_pipe.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
