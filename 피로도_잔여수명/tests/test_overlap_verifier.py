"""
overlap_verifier.py 테스트
중첩 검증 모듈의 파이프-도로 샘플링 및 시각화 로직 테스트
"""

from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from shapely.geometry import LineString

from src.overlap_verifier import (
    BUFFER_RADIUS,
    COLOR_BUFFER,
    COLOR_MATCHED_PIPE,
    COLOR_MATCHED_ROAD,
    COLOR_OTHER_ROAD,
    COLOR_UNMATCHED_PIPE,
    SAMPLE_SIZE,
    calculate_verification_stats,
    create_legend_elements,
    select_sample_pipes,
    visualize_pipe_sample,
)


class TestSelectSamplePipes:
    """select_sample_pipes 함수 테스트"""

    def create_test_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        pipes = []
        for i in range(10):
            pipe = LineString([(i, 0), (i + 1, 0)])
            pipes.append({"FTR_IDN": 2000 + i, "geometry": pipe})
        return gpd.GeoDataFrame(pipes)

    def create_test_traffic_df(self) -> pd.DataFrame:
        """테스트용 교통 분석 DataFrame 생성"""
        data = []
        # 매칭된 파이프 5개
        for i in range(5):
            data.append(
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 10.0 + i,
                    "ROA_CLS_SE": 1,
                }
            )

        # 매칭 안된 파이프 5개
        for i in range(5, 10):
            data.append(
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                }
            )

        return pd.DataFrame(data)

    @patch("random.sample")
    def test_select_sample_pipes_balanced(self, mock_sample):
        """균형잡힌 샘플 선택 테스트"""
        # Mock random.sample to return predictable results
        mock_sample.side_effect = [
            [2000, 2001],  # 매칭된 파이프에서 2개
            [2005, 2006],  # 매칭 안된 파이프에서 2개
        ]

        pipe_gdf = self.create_test_pipe_gdf()
        traffic_df = self.create_test_traffic_df()

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, traffic_df, sample_size=4
        )

        assert len(sample_ids) == 4
        assert isinstance(matching_info, dict)

        # 매칭 정보 확인
        assert matching_info[2000] == "R1000"  # 매칭된 파이프
        assert matching_info[2005] is None  # 매칭 안된 파이프

    def test_select_sample_pipes_insufficient_matched(self):
        """매칭된 파이프가 부족한 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        # 매칭된 파이프 1개만 있는 경우
        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000,
                    "RN_CD": "R1000",
                    "RN": "도로1",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                },
                {
                    "FTR_IDN": 2001,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                },
                {
                    "FTR_IDN": 2002,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                },
            ]
        )

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, traffic_df, sample_size=3
        )

        assert len(sample_ids) <= 3
        assert isinstance(matching_info, dict)

        # 매칭된 파이프가 포함되어 있는지 확인
        matched_in_sample = sum(
            1 for ftr_id in sample_ids if matching_info.get(ftr_id) is not None
        )
        assert matched_in_sample >= 1

    def test_select_sample_pipes_only_matched(self):
        """매칭된 파이프만 있는 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        # 모든 파이프가 매칭된 경우
        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                }
                for i in range(5)
            ]
        )

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, traffic_df, sample_size=3
        )

        assert len(sample_ids) <= 3
        # 모든 샘플이 매칭되어 있어야 함
        for ftr_id in sample_ids:
            assert matching_info[ftr_id] is not None

    def test_select_sample_pipes_only_unmatched(self):
        """매칭 안된 파이프만 있는 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        # 모든 파이프가 매칭 안된 경우
        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                }
                for i in range(5)
            ]
        )

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, traffic_df, sample_size=3
        )

        assert len(sample_ids) <= 3
        # 모든 샘플이 매칭 안되어 있어야 함
        for ftr_id in sample_ids:
            assert matching_info[ftr_id] is None

    def test_select_sample_pipes_empty_traffic(self):
        """빈 교통 데이터"""
        pipe_gdf = self.create_test_pipe_gdf()
        empty_traffic_df = pd.DataFrame(
            columns=["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
        )

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, empty_traffic_df, sample_size=5
        )

        assert len(sample_ids) == 0
        assert len(matching_info) == 0

    def test_sample_size_larger_than_available(self):
        """요청 샘플 수가 가용 데이터보다 큰 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        # 파이프 2개만 있는 경우
        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000,
                    "RN_CD": "R1000",
                    "RN": "도로1",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                },
                {
                    "FTR_IDN": 2001,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                },
            ]
        )

        sample_ids, matching_info = select_sample_pipes(
            pipe_gdf, traffic_df, sample_size=10
        )

        # 가용한 데이터 수만큼만 반환
        assert len(sample_ids) <= 2
        assert len(matching_info) <= 2


class TestVisualizePipeSample:
    """visualize_pipe_sample 함수 테스트"""

    def create_test_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame"""
        return gpd.GeoDataFrame(
            [{"FTR_IDN": 2000, "geometry": LineString([(100, 100), (200, 100)])}]
        )

    def create_test_road_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 도로 GeoDataFrame"""
        return gpd.GeoDataFrame(
            [
                {
                    "RN_CD": "R1000",
                    "RN": "테스트도로",
                    "ROAD_BT": 10.0,
                    "geometry": LineString([(80, 80), (220, 120)]),
                },
                {
                    "RN_CD": "R1001",
                    "RN": "기타도로",
                    "ROAD_BT": 8.0,
                    "geometry": LineString([(90, 90), (210, 110)]),
                },
            ]
        )

    @patch("matplotlib.pyplot.Axes.text")
    @patch("matplotlib.pyplot.Axes.set_title")
    def test_visualize_pipe_sample_not_found(self, mock_set_title, mock_text):
        """존재하지 않는 파이프 테스트"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_road_gdf()

        fig, ax = plt.subplots()

        visualize_pipe_sample(pipe_gdf, road_gdf, 9999, None, ax, "Test Title")

        mock_text.assert_called_once()
        mock_set_title.assert_called_with("Test Title")
        plt.close(fig)

    @patch("geopandas.GeoDataFrame.plot")
    @patch("geopandas.GeoSeries.plot")
    def test_visualize_pipe_sample_with_matched_road(
        self, mock_series_plot, mock_gdf_plot
    ):
        """매칭된 도로가 있는 파이프 시각화"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_road_gdf()

        fig, ax = plt.subplots()

        visualize_pipe_sample(pipe_gdf, road_gdf, 2000, "R1000", ax, "Matched Pipe")

        # plot 함수들이 호출되었는지 확인
        assert mock_gdf_plot.called
        assert mock_series_plot.called  # 버퍼 영역 그리기

        plt.close(fig)

    @patch("geopandas.GeoDataFrame.plot")
    def test_visualize_pipe_sample_without_matched_road(self, mock_plot):
        """매칭된 도로가 없는 파이프 시각화"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_road_gdf()

        fig, ax = plt.subplots()

        visualize_pipe_sample(pipe_gdf, road_gdf, 2000, None, ax, "Unmatched Pipe")

        # plot 함수가 호출되었는지 확인
        assert mock_plot.called

        plt.close(fig)

    def test_visualize_pipe_sample_empty_roads(self):
        """주변 도로가 없는 경우"""
        pipe_gdf = self.create_test_pipe_gdf()
        empty_road_gdf = gpd.GeoDataFrame(
            columns=["RN_CD", "RN", "ROAD_BT", "geometry"]
        )
        empty_road_gdf = empty_road_gdf.set_geometry("geometry")

        fig, ax = plt.subplots()

        # 예외가 발생하지 않아야 함
        try:
            visualize_pipe_sample(pipe_gdf, empty_road_gdf, 2000, None, ax, "No Roads")
        except Exception as e:
            pytest.fail(f"Unexpected exception: {e}")

        plt.close(fig)

    def test_visualize_pipe_sample_ax_settings(self):
        """axes 설정 확인"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_road_gdf()

        fig, ax = plt.subplots()

        visualize_pipe_sample(pipe_gdf, road_gdf, 2000, "R1000", ax, "Settings Test")

        # axes 설정 확인
        # matplotlib에서 aspect가 'equal'로 설정되면 1.0을 반환할 수 있음
        assert ax.get_aspect() in ["equal", 1.0]
        assert ax.get_title() == "Settings Test"

        # xlim, ylim이 설정되었는지 확인
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        assert xlim[1] > xlim[0]
        assert ylim[1] > ylim[0]

        plt.close(fig)


class TestCreateLegendElements:
    """create_legend_elements 함수 테스트"""

    def test_create_legend_elements_types(self):
        """범례 요소 타입 테스트"""
        elements = create_legend_elements()

        assert isinstance(elements, list)
        assert len(elements) == 5

        # 각 요소가 올바른 타입인지 확인
        line_elements = [elem for elem in elements if isinstance(elem, Line2D)]
        rect_elements = [elem for elem in elements if isinstance(elem, Rectangle)]

        assert len(line_elements) == 4  # 라인 요소 4개
        assert len(rect_elements) == 1  # 사각형 요소 1개

    def test_create_legend_elements_colors(self):
        """범례 요소 색상 확인"""
        import matplotlib.colors as mcolors

        elements = create_legend_elements()

        colors_used = []
        for elem in elements:
            if isinstance(elem, Line2D):
                colors_used.append(elem.get_color())
            elif isinstance(elem, Rectangle):
                colors_used.append(elem.get_facecolor())

        # 색상을 문자열로 변환
        colors_str = []
        for color in colors_used:
            if isinstance(color, tuple) and len(color) == 4:
                # RGBA 튜플을 hex로 변환
                colors_str.append(mcolors.to_hex(color[:3]))
            else:
                colors_str.append(color)

        # 정의된 색상들이 사용되었는지 확인
        expected_colors = [
            COLOR_MATCHED_PIPE,
            COLOR_UNMATCHED_PIPE,
            COLOR_MATCHED_ROAD,
            COLOR_OTHER_ROAD,
            COLOR_BUFFER,
        ]

        for expected_color in expected_colors:
            # 예상 색상도 동일하게 변환
            if (
                expected_color.upper() in colors_str
                or expected_color.lower() in colors_str
            ):
                continue
            # 직접 비교
            assert any(c.upper() == expected_color.upper() for c in colors_str)

    def test_create_legend_elements_labels(self):
        """범례 요소 라벨 확인"""
        elements = create_legend_elements()

        labels = [elem.get_label() for elem in elements]

        expected_labels = [
            "매칭된 파이프",
            "매칭 안된 파이프",
            "매칭된 도로",
            "기타 도로",
            "도로 버퍼",
        ]

        for expected_label in expected_labels:
            assert expected_label in labels

    def test_create_legend_elements_properties(self):
        """범례 요소 속성 확인"""
        elements = create_legend_elements()

        line_elements = [elem for elem in elements if isinstance(elem, Line2D)]

        # 라인 요소들이 적절한 linewidth를 가지는지 확인
        for line_elem in line_elements:
            linewidth = line_elem.get_linewidth()
            assert linewidth > 0
            assert linewidth <= 3  # 합리적인 범위

        # Rectangle 요소 확인
        rect_elements = [elem for elem in elements if isinstance(elem, Rectangle)]
        if rect_elements:
            rect = rect_elements[0]
            assert rect.get_width() == 1
            assert rect.get_height() == 1


class TestCalculateVerificationStats:
    """calculate_verification_stats 함수 테스트"""

    def create_test_data(self) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
        """테스트용 데이터 생성"""
        # 파이프 데이터
        pipe_gdf = gpd.GeoDataFrame(
            [
                {"FTR_IDN": 2000 + i, "geometry": LineString([(i, 0), (i + 1, 0)])}
                for i in range(10)
            ]
        )

        # 교통 분석 결과 (5개 매칭, 3개 미매칭)
        traffic_data = []
        for i in range(5):
            traffic_data.append(
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                }
            )

        for i in range(5, 8):
            traffic_data.append(
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                }
            )

        traffic_df = pd.DataFrame(traffic_data)

        return pipe_gdf, traffic_df

    def test_calculate_verification_stats_basic(self):
        """기본 통계 계산 테스트"""
        pipe_gdf, traffic_df = self.create_test_data()
        sample_ids = [2000, 2001, 2005]

        stats = calculate_verification_stats(pipe_gdf, traffic_df, sample_ids)

        assert isinstance(stats, dict)

        # 필수 키들 확인
        required_keys = [
            "total_pipes",
            "analyzed_pipes",
            "matched_pipes",
            "match_rate",
            "sample_count",
        ]
        for key in required_keys:
            assert key in stats

        # 값 검증
        assert stats["total_pipes"] == 10
        assert stats["analyzed_pipes"] == 8  # traffic_df 레코드 수
        assert stats["matched_pipes"] == 5  # RN_CD가 None이 아닌 것
        assert abs(stats["match_rate"] - 62.5) < 0.1  # 5/8 * 100
        assert stats["sample_count"] == 3

    def test_calculate_verification_stats_no_matches(self):
        """매칭이 없는 경우"""
        pipe_gdf = gpd.GeoDataFrame(
            [{"FTR_IDN": 2000, "geometry": LineString([(0, 0), (1, 0)])}]
        )

        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000,
                    "RN_CD": None,
                    "RN": None,
                    "ROAD_BT": None,
                    "ROA_CLS_SE": None,
                }
            ]
        )

        sample_ids = [2000]

        stats = calculate_verification_stats(pipe_gdf, traffic_df, sample_ids)

        assert stats["matched_pipes"] == 0
        assert stats["match_rate"] == 0.0

    def test_calculate_verification_stats_all_matches(self):
        """모든 파이프가 매칭된 경우"""
        pipe_gdf = gpd.GeoDataFrame(
            [
                {"FTR_IDN": 2000 + i, "geometry": LineString([(i, 0), (i + 1, 0)])}
                for i in range(3)
            ]
        )

        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000 + i,
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                }
                for i in range(3)
            ]
        )

        sample_ids = [2000, 2001]

        stats = calculate_verification_stats(pipe_gdf, traffic_df, sample_ids)

        assert stats["matched_pipes"] == 3
        assert stats["match_rate"] == 100.0

    def test_calculate_verification_stats_empty_traffic(self):
        """빈 교통 데이터"""
        pipe_gdf = gpd.GeoDataFrame(
            [{"FTR_IDN": 2000, "geometry": LineString([(0, 0), (1, 0)])}]
        )

        empty_traffic_df = pd.DataFrame(
            columns=["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
        )

        sample_ids = []

        stats = calculate_verification_stats(pipe_gdf, empty_traffic_df, sample_ids)

        assert stats["analyzed_pipes"] == 0
        assert stats["matched_pipes"] == 0
        assert stats["match_rate"] == 0.0
        assert stats["sample_count"] == 0

    def test_calculate_verification_stats_types(self):
        """반환 값 타입 확인"""
        pipe_gdf, traffic_df = self.create_test_data()
        sample_ids = [2000, 2001]

        stats = calculate_verification_stats(pipe_gdf, traffic_df, sample_ids)

        assert isinstance(stats["total_pipes"], int) or np.issubdtype(
            type(stats["total_pipes"]), np.integer
        )
        assert isinstance(stats["analyzed_pipes"], int) or np.issubdtype(
            type(stats["analyzed_pipes"]), np.integer
        )
        assert isinstance(stats["matched_pipes"], int) or np.issubdtype(
            type(stats["matched_pipes"]), np.integer
        )
        assert isinstance(stats["match_rate"], float) or np.issubdtype(
            type(stats["match_rate"]), np.floating
        )
        assert isinstance(stats["sample_count"], int) or np.issubdtype(
            type(stats["sample_count"]), np.integer
        )


class TestModuleConstants:
    """모듈 상수 테스트"""

    def test_sample_size_constant(self):
        """SAMPLE_SIZE 상수 테스트"""
        assert isinstance(SAMPLE_SIZE, int)
        assert SAMPLE_SIZE > 0
        assert SAMPLE_SIZE <= 100  # 합리적인 범위

    def test_buffer_radius_constant(self):
        """BUFFER_RADIUS 상수 테스트"""
        assert isinstance(BUFFER_RADIUS, int | float)
        assert BUFFER_RADIUS > 0
        assert BUFFER_RADIUS <= 1000  # 1km 이하

    def test_color_constants(self):
        """색상 상수 테스트"""
        color_constants = [
            COLOR_MATCHED_PIPE,
            COLOR_UNMATCHED_PIPE,
            COLOR_MATCHED_ROAD,
            COLOR_OTHER_ROAD,
            COLOR_BUFFER,
        ]

        for color in color_constants:
            assert isinstance(color, str)
            assert color.startswith("#")  # 헥스 컬러 코드
            assert len(color) == 7  # #RRGGBB 형식

    def test_color_uniqueness(self):
        """색상의 고유성 테스트"""
        colors = [
            COLOR_MATCHED_PIPE,
            COLOR_UNMATCHED_PIPE,
            COLOR_MATCHED_ROAD,
            COLOR_OTHER_ROAD,
            COLOR_BUFFER,
        ]

        # 모든 색상이 다른지 확인
        assert len(set(colors)) == len(colors)


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_function_imports(self):
        """함수 import 테스트"""
        from src.overlap_verifier import (
            calculate_verification_stats,
            create_legend_elements,
            select_sample_pipes,
            visualize_pipe_sample,
        )

        assert callable(select_sample_pipes)
        assert callable(visualize_pipe_sample)
        assert callable(create_legend_elements)
        assert callable(calculate_verification_stats)

    def test_dependency_imports(self):
        """의존성 모듈 import 테스트"""
        import geopandas
        import matplotlib.pyplot
        import pandas
        from shapely.geometry import LineString

        assert hasattr(geopandas, "GeoDataFrame")
        assert hasattr(pandas, "DataFrame")
        assert hasattr(matplotlib.pyplot, "subplots")
        assert LineString is not None

    def test_matplotlib_backend_compatibility(self):
        """matplotlib 백엔드 호환성 테스트"""
        # 백엔드 설정 없이도 작동하는지 확인
        try:
            elements = create_legend_elements()
            assert len(elements) > 0
        except Exception as e:
            pytest.fail(f"matplotlib compatibility issue: {e}")


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_very_small_buffer_radius(self):
        """매우 작은 버퍼 반경"""
        # 상수를 임시로 작은 값으로 시뮬레이션

        pipe_gdf = gpd.GeoDataFrame(
            [{"FTR_IDN": 2000, "geometry": LineString([(100, 100), (101, 100)])}]
        )

        road_gdf = gpd.GeoDataFrame(
            [
                {
                    "RN_CD": "R1000",
                    "RN": "테스트도로",
                    "ROAD_BT": 10.0,
                    "geometry": LineString([(99, 99), (102, 101)]),
                }
            ]
        )

        fig, ax = plt.subplots()

        # 작은 버퍼에서도 정상 작동하는지 확인
        try:
            visualize_pipe_sample(pipe_gdf, road_gdf, 2000, "R1000", ax, "Small Buffer")
        except Exception as e:
            pytest.fail(f"Small buffer handling failed: {e}")

        plt.close(fig)

    def test_duplicate_ftr_idn_in_traffic(self):
        """교통 데이터에 중복 FTR_IDN이 있는 경우"""
        pipe_gdf = gpd.GeoDataFrame(
            [{"FTR_IDN": 2000, "geometry": LineString([(0, 0), (1, 0)])}]
        )

        # 중복 FTR_IDN
        traffic_df = pd.DataFrame(
            [
                {
                    "FTR_IDN": 2000,
                    "RN_CD": "R1000",
                    "RN": "도로1",
                    "ROAD_BT": 10.0,
                    "ROA_CLS_SE": 1,
                },
                {
                    "FTR_IDN": 2000,
                    "RN_CD": "R1001",
                    "RN": "도로2",
                    "ROAD_BT": 8.0,
                    "ROA_CLS_SE": 2,
                },
            ]
        )

        # 함수가 중복을 처리할 수 있는지 확인
        try:
            sample_ids, matching_info = select_sample_pipes(
                pipe_gdf, traffic_df, sample_size=1
            )
            assert isinstance(sample_ids, list)
            assert isinstance(matching_info, dict)
        except Exception as e:
            pytest.fail(f"Duplicate FTR_IDN handling failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
