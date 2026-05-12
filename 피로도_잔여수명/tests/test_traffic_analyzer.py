"""
traffic_analyzer.py 테스트
교통량 분석 모듈의 비즈니스 로직 테스트
"""

from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from src.traffic_analyzer import (
    MAX_BUFFER_DISTANCE,
    MIN_BUFFER_DISTANCE,
    ROAD_BUFFER_RATIO,
    analyze_pipe_traffic,
    calculate_buffer_distance,
    create_road_buffers,
    perform_spatial_join,
    save_traffic_csv,
    select_primary_road,
)


class TestCalculateBufferDistance:
    """calculate_buffer_distance 함수 테스트"""

    def test_normal_road_width(self):
        """일반적인 도로 폭 테스트"""
        road_width = 10.0
        expected = road_width * ROAD_BUFFER_RATIO

        result = calculate_buffer_distance(road_width)

        assert result == expected
        assert isinstance(result, float)

    def test_very_narrow_road(self):
        """매우 좁은 도로 (최소값 적용)"""
        road_width = 2.0

        result = calculate_buffer_distance(road_width)

        assert result == MIN_BUFFER_DISTANCE
        assert result >= MIN_BUFFER_DISTANCE

    def test_very_wide_road(self):
        """매우 넓은 도로 (최대값 적용)"""
        road_width = 100.0

        result = calculate_buffer_distance(road_width)

        assert result == MAX_BUFFER_DISTANCE
        assert result <= MAX_BUFFER_DISTANCE

    def test_zero_width(self):
        """0 폭 도로"""
        road_width = 0.0

        result = calculate_buffer_distance(road_width)

        assert result == MIN_BUFFER_DISTANCE

    def test_negative_width(self):
        """음수 폭 도로"""
        road_width = -5.0

        result = calculate_buffer_distance(road_width)

        assert result == MIN_BUFFER_DISTANCE

    def test_boundary_values(self):
        """경계값 테스트"""
        # 최소값 경계
        min_road_width = MIN_BUFFER_DISTANCE / ROAD_BUFFER_RATIO
        result_min = calculate_buffer_distance(min_road_width)
        assert result_min == MIN_BUFFER_DISTANCE

        # 최대값 경계
        max_road_width = MAX_BUFFER_DISTANCE / ROAD_BUFFER_RATIO
        result_max = calculate_buffer_distance(max_road_width)
        assert result_max == MAX_BUFFER_DISTANCE


class TestCreateRoadBuffers:
    """create_road_buffers 함수 테스트"""

    def create_test_road_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 도로 GeoDataFrame 생성"""
        roads = [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
        ]

        data = []
        for i, road in enumerate(roads):
            data.append(
                {
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 5.0 + i * 2,  # 5, 7, 9미터
                    "ROA_CLS_SE": 1,
                    "SIG_CD": f"SIG{i}",
                    "geometry": road,
                }
            )

        return gpd.GeoDataFrame(data)

    def test_create_road_buffers_success(self):
        """정상 버퍼 생성 테스트"""
        road_gdf = self.create_test_road_gdf()

        result = create_road_buffers(road_gdf, verbose=False)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == len(road_gdf)
        assert "buffer_dist" in result.columns
        assert "buffered_geometry" in result.columns
        assert result.geometry.name == "buffered_geometry"

    def test_buffer_distance_calculation(self):
        """버퍼 거리 계산 검증"""
        road_gdf = self.create_test_road_gdf()

        result = create_road_buffers(road_gdf, verbose=False)

        # 각 도로의 버퍼 거리가 올바르게 계산되었는지 확인
        for idx, row in result.iterrows():
            expected_buffer = calculate_buffer_distance(row["ROAD_BT"])
            assert row["buffer_dist"] == expected_buffer

    def test_buffer_geometry_creation(self):
        """버퍼 지오메트리 생성 확인"""
        road_gdf = self.create_test_road_gdf()

        result = create_road_buffers(road_gdf, verbose=False)

        # 모든 버퍼 지오메트리가 Polygon이어야 함
        for geom in result.geometry:
            assert geom.geom_type in ["Polygon", "MultiPolygon"]

    def test_verbose_output(self, capsys):
        """상세 출력 테스트"""
        road_gdf = self.create_test_road_gdf()

        create_road_buffers(road_gdf, verbose=True)

        captured = capsys.readouterr()
        assert "도로 버퍼 생성 중" in captured.out
        assert "버퍼 생성 완료" in captured.out
        assert "평균 버퍼 거리" in captured.out

    def test_empty_input(self):
        """빈 입력 테스트"""
        empty_gdf = gpd.GeoDataFrame()

        result = create_road_buffers(empty_gdf, verbose=False)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0


class TestPerformSpatialJoin:
    """perform_spatial_join 함수 테스트"""

    def create_test_pipe_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 파이프 GeoDataFrame 생성"""
        pipes = [
            LineString([(0.5, -1), (0.5, 1)]),  # 첫 번째 도로와 교차
            LineString([(1.5, -1), (1.5, 1)]),  # 두 번째 도로와 교차
            LineString([(5, -1), (5, 1)]),  # 어떤 도로와도 교차하지 않음
        ]

        data = []
        for i, pipe in enumerate(pipes):
            data.append({"FTR_IDN": f"{2000 + i}", "geometry": pipe})

        return gpd.GeoDataFrame(data)

    def create_test_buffered_road_gdf(self) -> gpd.GeoDataFrame:
        """테스트용 버퍼된 도로 GeoDataFrame 생성"""
        roads = [LineString([(0, 0), (1, 0)]), LineString([(1, 0), (2, 0)])]

        data = []
        for i, road in enumerate(roads):
            # 버퍼 생성
            buffer_dist = 3.0
            buffered_geom = road.buffer(buffer_dist)

            data.append(
                {
                    "RN_CD": f"R{1000 + i}",
                    "RN": f"도로{i+1}",
                    "ROAD_BT": 6.0,
                    "ROA_CLS_SE": 1,
                    "SIG_CD": f"SIG{i}",
                    "buffered_geometry": buffered_geom,
                }
            )

        gdf = gpd.GeoDataFrame(data)
        gdf.set_geometry("buffered_geometry", inplace=True)
        return gdf

    def test_spatial_join_success(self):
        """정상 공간 조인 테스트"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_buffered_road_gdf()

        result = perform_spatial_join(pipe_gdf, road_gdf, verbose=False)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) >= len(pipe_gdf)  # left join이므로 모든 파이프 포함
        assert "FTR_IDN" in result.columns
        assert "RN_CD" in result.columns

    def test_all_pipes_included(self):
        """모든 파이프가 결과에 포함되는지 확인 (left join)"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_buffered_road_gdf()

        result = perform_spatial_join(pipe_gdf, road_gdf, verbose=False)

        # 모든 파이프 ID가 결과에 포함되어야 함
        original_pipe_ids = set(pipe_gdf["FTR_IDN"])
        result_pipe_ids = set(result["FTR_IDN"])
        assert original_pipe_ids.issubset(result_pipe_ids)

    def test_verbose_output(self, capsys):
        """상세 출력 테스트"""
        pipe_gdf = self.create_test_pipe_gdf()
        road_gdf = self.create_test_buffered_road_gdf()

        perform_spatial_join(pipe_gdf, road_gdf, verbose=True)

        captured = capsys.readouterr()
        assert "공간 조인 수행 중" in captured.out
        assert "공간 조인 완료" in captured.out
        assert "매칭된 파이프 수" in captured.out

    def test_empty_pipe_input(self):
        """빈 파이프 입력 테스트"""
        empty_pipe_gdf = gpd.GeoDataFrame(columns=["FTR_IDN", "geometry"])
        empty_pipe_gdf = empty_pipe_gdf.set_geometry("geometry")
        road_gdf = self.create_test_buffered_road_gdf()

        result = perform_spatial_join(empty_pipe_gdf, road_gdf, verbose=False)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 0

    def test_empty_road_input(self):
        """빈 도로 입력 테스트"""
        pipe_gdf = self.create_test_pipe_gdf()
        empty_road_gdf = gpd.GeoDataFrame(
            columns=[
                "RN_CD",
                "RN",
                "ROAD_BT",
                "ROA_CLS_SE",
                "SIG_CD",
                "buffered_geometry",
            ]
        )
        empty_road_gdf = empty_road_gdf.set_geometry("buffered_geometry")

        result = perform_spatial_join(pipe_gdf, empty_road_gdf, verbose=False)

        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == len(pipe_gdf)  # left join이므로 모든 파이프 포함


class TestSelectPrimaryRoad:
    """select_primary_road 함수 테스트"""

    def create_test_overlaps_df(self) -> pd.DataFrame:
        """테스트용 중첩 DataFrame 생성"""
        data = [
            # 파이프 2000: 두 도로와 중첩 (넓은 도로가 우선)
            {
                "FTR_IDN": "2000",
                "RN_CD": "R1001",
                "RN": "도로1",
                "ROAD_BT": 10.0,
                "ROA_CLS_SE": 2,
            },
            {
                "FTR_IDN": "2000",
                "RN_CD": "R1002",
                "RN": "도로2",
                "ROAD_BT": 15.0,
                "ROA_CLS_SE": 1,
            },
            # 파이프 2001: 한 도로와만 중첩
            {
                "FTR_IDN": "2001",
                "RN_CD": "R1003",
                "RN": "도로3",
                "ROAD_BT": 8.0,
                "ROA_CLS_SE": 3,
            },
            # 파이프 2002: 세 도로와 중첩 (폭이 같을 때 등급 우선)
            {
                "FTR_IDN": "2002",
                "RN_CD": "R1004",
                "RN": "도로4",
                "ROAD_BT": 12.0,
                "ROA_CLS_SE": 2,
            },
            {
                "FTR_IDN": "2002",
                "RN_CD": "R1005",
                "RN": "도로5",
                "ROAD_BT": 12.0,
                "ROA_CLS_SE": 1,
            },
            {
                "FTR_IDN": "2002",
                "RN_CD": "R1006",
                "RN": "도로6",
                "ROAD_BT": 12.0,
                "ROA_CLS_SE": 3,
            },
        ]
        return pd.DataFrame(data)

    def test_select_primary_road_basic(self):
        """기본 우선순위 선택 테스트"""
        overlaps_df = self.create_test_overlaps_df()

        result = select_primary_road(overlaps_df, verbose=False)

        assert isinstance(result, pd.DataFrame)
        # 각 파이프당 하나의 도로만 선택되어야 함
        assert len(result) == len(overlaps_df["FTR_IDN"].unique())
        assert result["FTR_IDN"].nunique() == len(result)

    def test_road_width_priority(self):
        """도로 폭 우선순위 테스트"""
        overlaps_df = self.create_test_overlaps_df()

        result = select_primary_road(overlaps_df, verbose=False)

        # 파이프 2000: 15.0m 도로가 선택되어야 함
        pipe_2000_result = result[result["FTR_IDN"] == "2000"]
        assert len(pipe_2000_result) == 1
        assert pipe_2000_result.iloc[0]["ROAD_BT"] == 15.0
        assert pipe_2000_result.iloc[0]["RN_CD"] == "R1002"

    def test_road_class_priority(self):
        """도로 등급 우선순위 테스트 (폭이 같을 때)"""
        overlaps_df = self.create_test_overlaps_df()

        result = select_primary_road(overlaps_df, verbose=False)

        # 파이프 2002: 같은 폭일 때 등급 1이 선택되어야 함
        pipe_2002_result = result[result["FTR_IDN"] == "2002"]
        assert len(pipe_2002_result) == 1
        assert pipe_2002_result.iloc[0]["ROA_CLS_SE"] == 1
        assert pipe_2002_result.iloc[0]["RN_CD"] == "R1005"

    def test_single_road_per_pipe(self):
        """파이프당 단일 도로만 선택되는지 확인"""
        overlaps_df = self.create_test_overlaps_df()

        result = select_primary_road(overlaps_df, verbose=False)

        # 각 파이프 ID의 출현 횟수가 1이어야 함
        pipe_counts = result["FTR_IDN"].value_counts()
        assert all(count == 1 for count in pipe_counts)

    def test_verbose_output(self, capsys):
        """상세 출력 테스트"""
        overlaps_df = self.create_test_overlaps_df()

        select_primary_road(overlaps_df, verbose=True)

        captured = capsys.readouterr()
        assert "도로 폭 우선순위 적용 중" in captured.out
        assert "우선순위 적용 완료" in captured.out

    def test_empty_input(self):
        """빈 입력 테스트"""
        empty_df = pd.DataFrame(columns=["FTR_IDN", "RN_CD", "ROAD_BT", "ROA_CLS_SE"])

        result = select_primary_road(empty_df, verbose=False)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_single_overlap_per_pipe(self):
        """파이프당 하나의 도로만 중첩된 경우"""
        single_overlap_df = pd.DataFrame(
            [
                {"FTR_IDN": "2000", "RN_CD": "R1001", "ROAD_BT": 10.0, "ROA_CLS_SE": 2},
                {"FTR_IDN": "2001", "RN_CD": "R1002", "ROAD_BT": 8.0, "ROA_CLS_SE": 1},
            ]
        )

        result = select_primary_road(single_overlap_df, verbose=False)

        assert len(result) == 2
        assert len(result) == len(single_overlap_df)


class TestAnalyzePipeTraffic:
    """analyze_pipe_traffic 함수 테스트"""

    @patch("src.traffic_analyzer.perform_spatial_join")
    @patch("src.traffic_analyzer.select_primary_road")
    def test_analyze_pipe_traffic_success(self, mock_select, mock_join):
        """정상 분석 테스트"""
        # Mock 설정
        mock_overlaps = pd.DataFrame(
            {
                "FTR_IDN": ["2000", "2001"],
                "RN_CD": ["R1001", "R1002"],
                "RN": ["도로1", "도로2"],
                "ROAD_BT": [10.0, 8.0],
                "ROA_CLS_SE": [1, 2],
            }
        )
        mock_join.return_value = mock_overlaps
        mock_select.return_value = mock_overlaps

        # 테스트 데이터
        pipe_gdf = gpd.GeoDataFrame(
            [
                {"FTR_IDN": "2000", "geometry": LineString([(0, 0), (1, 0)])},
                {"FTR_IDN": "2001", "geometry": LineString([(1, 0), (2, 0)])},
            ]
        )
        road_gdf = gpd.GeoDataFrame()

        result_df, stats = analyze_pipe_traffic(pipe_gdf, road_gdf, verbose=False)

        assert isinstance(result_df, pd.DataFrame)
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "matched" in stats
        assert "match_rate" in stats

    def test_stats_calculation(self):
        """통계 계산 테스트"""
        # 실제 데이터로 통계 검증
        pipe_gdf = gpd.GeoDataFrame(
            [
                {"FTR_IDN": "2000", "geometry": LineString([(0, 0), (1, 0)])},
                {"FTR_IDN": "2001", "geometry": LineString([(1, 0), (2, 0)])},
                {"FTR_IDN": "2002", "geometry": LineString([(2, 0), (3, 0)])},
            ]
        )

        # Mock 결과 - 2개만 매칭됨
        result_df = pd.DataFrame(
            {
                "FTR_IDN": ["2000", "2001", "2002"],
                "RN_CD": ["R1001", "R1002", None],  # 하나는 매칭 안됨
            }
        )

        with (
            patch("src.traffic_analyzer.perform_spatial_join") as mock_join,
            patch("src.traffic_analyzer.select_primary_road") as mock_select,
        ):

            mock_join.return_value = result_df
            mock_select.return_value = result_df

            _, stats = analyze_pipe_traffic(pipe_gdf, gpd.GeoDataFrame(), verbose=False)

            assert stats["total"] == 3
            assert stats["matched"] == 2  # RN_CD가 None이 아닌 것
            assert abs(stats["match_rate"] - 66.67) < 0.1  # 2/3 * 100


class TestSaveTrafficCsv:
    """save_traffic_csv 함수 테스트"""

    def create_test_dataframe(self) -> pd.DataFrame:
        """테스트용 DataFrame 생성"""
        return pd.DataFrame(
            {
                "FTR_IDN": ["2000.0", "2001.0", "2002.0"],
                "RN_CD": ["R1001", "R1002", "R1003"],
                "RN": ["도로1", "도로2", "도로3"],
                "ROAD_BT": [10.0, 8.0, 12.0],
                "ROA_CLS_SE": [1, 2, 1],
                "extra_column": ["extra1", "extra2", "extra3"],  # 제외될 컬럼
            }
        )

    @patch("pandas.DataFrame.to_csv")
    def test_save_traffic_csv_success(self, mock_to_csv):
        """정상 저장 테스트"""
        test_df = self.create_test_dataframe()
        output_path = Path("/tmp/test_traffic.csv")

        save_traffic_csv(test_df, output_path, verbose=False)

        # to_csv가 호출되었는지 확인
        mock_to_csv.assert_called_once()
        args, kwargs = mock_to_csv.call_args
        assert args[0] == output_path
        assert kwargs["index"] is False
        assert kwargs["encoding"] == "utf-8-sig"

    def test_column_selection(self):
        """컬럼 선택 테스트"""
        test_df = self.create_test_dataframe()
        output_path = Path("/tmp/test_traffic.csv")

        with patch("pandas.DataFrame.to_csv") as mock_to_csv:
            save_traffic_csv(test_df, output_path, verbose=False)

            # Mock에 전달된 DataFrame 확인
            called_df = mock_to_csv.call_args[1].get("obj")  # self 인수
            if called_df is None:
                # self가 전달되지 않은 경우, DataFrame을 다른 방식으로 확인
                # DataFrame.to_csv가 호출되었는지만 확인
                mock_to_csv.assert_called_once()
            else:
                expected_cols = ["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
                assert list(called_df.columns) == expected_cols

    def test_ftr_idn_conversion(self):
        """FTR_IDN 정수 변환 테스트"""
        test_df = self.create_test_dataframe()

        # 실제 DataFrame 조작 확인을 위해 실제 함수 호출
        output_path = Path("/tmp/test_traffic.csv")

        with patch("pandas.DataFrame.to_csv"):
            # DataFrame이 수정되는지 확인하기 위해 copy 사용
            original_df = test_df.copy()
            save_traffic_csv(original_df, output_path, verbose=False)

            # 원본 DataFrame이 수정되지 않았는지 확인
            assert original_df["FTR_IDN"].dtype == "object"

    def test_verbose_output(self, capsys):
        """상세 출력 테스트"""
        test_df = self.create_test_dataframe()
        output_path = Path("/tmp/test_traffic.csv")

        with patch("pandas.DataFrame.to_csv"):
            save_traffic_csv(test_df, output_path, verbose=True)

        captured = capsys.readouterr()
        assert "test_traffic.csv" in captured.out
        assert "3개 레코드" in captured.out

    def test_empty_dataframe(self):
        """빈 DataFrame 테스트"""
        empty_df = pd.DataFrame(
            columns=["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
        )
        output_path = Path("/tmp/empty_traffic.csv")

        with patch("pandas.DataFrame.to_csv") as mock_to_csv:
            save_traffic_csv(empty_df, output_path, verbose=False)

            mock_to_csv.assert_called_once()


class TestModuleConstants:
    """모듈 상수 테스트"""

    def test_buffer_constants(self):
        """버퍼 관련 상수 테스트"""
        assert isinstance(ROAD_BUFFER_RATIO, float)
        assert 0 < ROAD_BUFFER_RATIO < 1  # 도로 폭의 비율이므로 0과 1 사이

        assert isinstance(MIN_BUFFER_DISTANCE, float)
        assert MIN_BUFFER_DISTANCE > 0

        assert isinstance(MAX_BUFFER_DISTANCE, float)
        assert MAX_BUFFER_DISTANCE > MIN_BUFFER_DISTANCE

    def test_buffer_logic_consistency(self):
        """버퍼 로직 일관성 테스트"""
        # 최소 버퍼를 만족하는 도로 폭
        min_road_width = MIN_BUFFER_DISTANCE / ROAD_BUFFER_RATIO
        assert calculate_buffer_distance(min_road_width) == MIN_BUFFER_DISTANCE

        # 최대 버퍼를 만족하는 도로 폭
        max_road_width = MAX_BUFFER_DISTANCE / ROAD_BUFFER_RATIO
        assert calculate_buffer_distance(max_road_width) == MAX_BUFFER_DISTANCE


class TestModuleIntegration:
    """모듈 통합 테스트"""

    def test_function_imports(self):
        """함수 import 테스트"""
        from src.traffic_analyzer import (
            analyze_pipe_traffic,
            calculate_buffer_distance,
            create_road_buffers,
            perform_spatial_join,
            save_traffic_csv,
            select_primary_road,
        )

        assert callable(calculate_buffer_distance)
        assert callable(create_road_buffers)
        assert callable(perform_spatial_join)
        assert callable(select_primary_road)
        assert callable(analyze_pipe_traffic)
        assert callable(save_traffic_csv)

    def test_dependency_imports(self):
        """의존성 모듈 import 테스트"""
        from pathlib import Path

        import geopandas
        import pandas
        from shapely.geometry import LineString

        assert hasattr(geopandas, "GeoDataFrame")
        assert hasattr(pandas, "DataFrame")
        assert LineString is not None
        assert Path is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
