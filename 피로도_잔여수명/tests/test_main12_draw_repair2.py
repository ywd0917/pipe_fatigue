"""
main12_draw_repair2.py 테스트
복구 작업 데이터 중복 위치 분석 및 시각화 테스트
"""

from unittest.mock import patch

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.patches import Circle

from src.main12_draw_repair2 import (
    BOUNDS_TYPE_MAP,
    DISTANCE_THRESHOLD,
    convert_wgs84_to_geodataframe,
    find_duplicate_clusters_ultra_fast,
    haversine_vectorized,
    load_all_repair2_data,
    # load_repair2_csv,  # 더 이상 사용되지 않음
    main,
    parse_arguments,
    plot_cluster_circles_vectorized,
    plot_repair2_locations_ultra_fast,
    precompute_point_attributes_vectorized,
)


class TestConstants:
    """상수 테스트"""

    def test_distance_threshold(self):
        """거리 임계값 확인"""
        assert DISTANCE_THRESHOLD == 10.0
        assert isinstance(DISTANCE_THRESHOLD, float)

    def test_bounds_type_map(self):
        """bounds type 매핑 확인"""
        assert "ground" in BOUNDS_TYPE_MAP
        assert "underground" in BOUNDS_TYPE_MAP
        assert "emergency" in BOUNDS_TYPE_MAP
        assert "registry" in BOUNDS_TYPE_MAP

        assert BOUNDS_TYPE_MAP["ground"] == "지상누수"
        assert BOUNDS_TYPE_MAP["underground"] == "지하누수"
        assert BOUNDS_TYPE_MAP["emergency"] == "긴급공사"
        assert BOUNDS_TYPE_MAP["registry"] == "관리대장"


# load_repair2_csv 함수가 더 이상 사용되지 않으므로 주석 처리
# class TestLoadRepair2CSV:
#     """CSV 로드 함수 테스트"""
#
#     def test_load_valid_csv(self, tmp_path):
#         """유효한 CSV 파일 로드"""
#         # 테스트 데이터 생성
#         csv_file = tmp_path / "test.csv"
#         df = pd.DataFrame(
#             {
#                 "위도": [37.5, 37.6, 37.7],
#                 "경도": [127.0, 127.1, 127.2],
#                 "주소": ["주소1", "주소2", "주소3"],
#                 "구군": ["강남구", "서초구", "송파구"],
#             }
#         )
#         df.to_csv(csv_file, index=False, encoding="utf-8-sig")
#
#         # 로드 테스트
#         result = load_repair2_csv(csv_file)
#
#         assert result is not None
#         assert len(result) == 3
#         assert "위도" in result.columns
#         assert "경도" in result.columns
#
#     def test_load_missing_file(self, tmp_path):
#         """존재하지 않는 파일"""
#         csv_file = tmp_path / "missing.csv"
#         result = load_repair2_csv(csv_file)
#         assert result is None
#
#     def test_load_invalid_coordinates(self, tmp_path):
#         """유효하지 않은 좌표 필터링"""
#         csv_file = tmp_path / "test.csv"
#         df = pd.DataFrame(
#             {
#                 "위도": [37.5, np.nan, 37.7, -100],
#                 "경도": [127.0, 127.1, np.nan, 127.3],
#                 "주소": ["주소1", "주소2", "주소3", "주소4"],
#             }
#         )
#         df.to_csv(csv_file, index=False, encoding="utf-8-sig")
#
#         result = load_repair2_csv(csv_file)
#
#         assert result is not None
#         assert len(result) == 1  # 첫 번째 행만 유효


class TestLoadAllRepair2Data:
    """전체 데이터 로드 테스트"""

    def test_load_unified_csv(self, tmp_path):
        """통합 CSV 파일 로드"""
        # main11e_merge_all_repairs 디렉토리 생성
        merge_dir = tmp_path / "main11e_merge_all_repairs"
        merge_dir.mkdir(parents=True, exist_ok=True)

        # 통합 CSV 파일 생성
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7, 37.8],
                "경도": [127.0, 127.1, 127.2, 127.3],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        df.to_csv(
            merge_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_all_repair2_data(tmp_path)

        assert len(result) == 4
        assert "지상누수" in result
        assert "지하누수" in result
        assert "긴급공사" in result
        assert "관리대장" in result
        assert len(result["지상누수"]) == 1
        assert len(result["지하누수"]) == 1
        assert len(result["긴급공사"]) == 1
        assert len(result["관리대장"]) == 1

    def test_load_missing_unified_file(self, tmp_path):
        """통합 파일이 없는 경우"""
        result = load_all_repair2_data(tmp_path)
        assert len(result) == 0

    def test_load_invalid_coordinates_unified(self, tmp_path):
        """유효하지 않은 좌표 필터링"""
        merge_dir = tmp_path / "main11e_merge_all_repairs"
        merge_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, np.nan, 37.7, -100],
                "경도": [127.0, 127.1, np.nan, 127.3],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        df.to_csv(
            merge_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_all_repair2_data(tmp_path)

        # 첫 번째 행만 유효 (지상누수만)
        assert len(result) == 1
        assert "지상누수" in result
        assert len(result["지상누수"]) == 1


class TestFindDuplicateClustersUltraFast:
    """KDTree 기반 중복 찾기 테스트"""

    def test_no_duplicates(self):
        """중복 없는 경우"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.6, 37.7],
                    "경도": [127.0, 127.1, 127.2],
                }
            )
        }

        clusters, point_to_cluster = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 0
        assert len(point_to_cluster) == 0

    def test_all_duplicates(self):
        """모두 중복인 경우"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5] * 5,
                    "경도": [127.0] * 5,
                }
            )
        }

        clusters, point_to_cluster = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 1
        assert len(next(iter(clusters.values()))) == 5

    def test_multiple_types(self):
        """여러 타입 혼합"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.5],
                    "경도": [127.0, 127.0],
                }
            ),
            "type2": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
        }

        clusters, point_to_cluster = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 1
        # 같은 위치에 3개 점 (type1: 2개, type2: 1개)
        assert len(next(iter(clusters.values()))) == 3

    def test_empty_data(self):
        """빈 데이터"""
        data = {}
        clusters, point_to_cluster = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 0
        assert len(point_to_cluster) == 0


class TestConvertWGS84ToGeoDataFrame:
    """좌표 변환 테스트"""

    def test_basic_conversion(self):
        """기본 변환"""
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
            }
        )

        gdf = convert_wgs84_to_geodataframe(df)

        assert isinstance(gdf, gpd.GeoDataFrame)
        assert gdf.crs.to_string() == "EPSG:5179"
        assert len(gdf) == 2

    def test_custom_columns(self):
        """커스텀 컬럼명"""
        df = pd.DataFrame(
            {
                "lat": [37.5, 37.6],
                "lon": [127.0, 127.1],
            }
        )

        gdf = convert_wgs84_to_geodataframe(df, lat_col="lat", lon_col="lon")

        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 2


class TestPrecomputePointAttributes:
    """점 속성 사전 계산 테스트"""

    def test_basic_computation(self):
        """기본 계산"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            )
        }
        point_to_cluster = {}

        result = precompute_point_attributes_vectorized(data, point_to_cluster)

        assert "type1" in result
        assert len(result["type1"]["x"]) == 2
        assert len(result["type1"]["y"]) == 2
        assert len(result["type1"]["sizes"]) == 2

    def test_with_clusters(self):
        """클러스터가 있는 경우"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.5],
                    "경도": [127.0, 127.0],
                }
            )
        }
        point_to_cluster = {(37.5, 127.0, "type1"): 2}

        result = precompute_point_attributes_vectorized(data, point_to_cluster)

        # 현재 구현에서는 모든 점이 동일한 크기(base_size=50)를 가짐
        assert "type1" in result
        sizes = result["type1"]["sizes"]
        assert np.all(sizes == 50)  # 모든 점이 기본 크기

    def test_min_duplicate_filter(self):
        """최소 중복 횟수 필터링"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            )
        }
        point_to_cluster = {
            (37.5, 127.0, "type1"): 2,
            (37.6, 127.1, "type1"): 1,
        }

        result = precompute_point_attributes_vectorized(
            data, point_to_cluster, min_duplicate_count=2
        )

        # 2회 이상만 표시
        assert len(result["type1"]["x"]) == 1


class TestHaversineVectorized:
    """벡터화된 Haversine 거리 계산 테스트"""

    def test_same_point(self):
        """같은 지점의 거리는 0"""
        lat1 = np.array([37.5665])
        lon1 = np.array([126.9780])
        lat2 = np.array([37.5665])
        lon2 = np.array([126.9780])

        distances = haversine_vectorized(lat1, lon1, lat2, lon2)
        assert distances[0] == pytest.approx(0, abs=1e-10)

    def test_multiple_points(self):
        """여러 점 동시 계산"""
        lat1 = np.array([37.5, 37.6, 37.7])
        lon1 = np.array([127.0, 127.0, 127.0])
        lat2 = np.array([37.5, 37.6, 37.7])
        lon2 = np.array([127.1, 127.1, 127.1])

        distances = haversine_vectorized(lat1, lon1, lat2, lon2)
        assert len(distances) == 3
        assert all(d > 0 for d in distances)


class TestVisualizationFunctions:
    """시각화 함수 테스트"""

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.savefig")
    def test_plot_repair2_locations_ultra_fast(self, mock_savefig, mock_show, tmp_path):
        """위치 플롯 테스트"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            )
        }
        output_path = tmp_path / "test.png"

        plot_repair2_locations_ultra_fast(data, output_path, show_plot=False)

        mock_savefig.assert_called_once()
        mock_show.assert_not_called()

    def test_plot_cluster_circles(self):
        """클러스터 원 그리기"""
        fig, ax = plt.subplots()
        clusters = {0: [(37.5, 127.0, "type1"), (37.5, 127.0, "type2")]}

        plot_cluster_circles_vectorized(ax, clusters)

        # 원이 추가되었는지 확인
        circles = [p for p in ax.patches if isinstance(p, Circle)]
        assert len(circles) > 0
        plt.close(fig)


class TestParseArguments:
    """명령줄 인자 파싱 테스트"""

    def test_default_args(self):
        """기본 인자"""
        with patch("sys.argv", ["script"]):
            args = parse_arguments()
            assert args.output_dir is None
            assert not args.show
            assert not args.skip_duplicates
            assert args.min_duplicates == 0
            assert args.bounds_type is None  # 기본값이 None으로 변경됨
            assert args.repair_type == "all"  # repair_type 기본값 확인

    def test_custom_args(self):
        """커스텀 인자"""
        with patch(
            "sys.argv",
            ["script", "--output-dir", "/tmp", "--show", "--min-duplicates", "4"],
        ):
            args = parse_arguments()
            assert args.output_dir == "/tmp"
            assert args.show
            assert args.min_duplicates == 4

    def test_bounds_type_single(self):
        """bounds-type 단일 값"""
        with patch("sys.argv", ["script", "--bounds-type", "ground"]):
            args = parse_arguments()
            assert args.bounds_type == "ground"

    def test_bounds_type_multiple(self):
        """bounds-type 복수 값"""
        with patch("sys.argv", ["script", "--bounds-type", "ground,underground"]):
            args = parse_arguments()
            assert args.bounds_type == "ground,underground"

    def test_bounds_type_all(self):
        """bounds-type all 값"""
        with patch("sys.argv", ["script", "--bounds-type", "all"]):
            args = parse_arguments()
            assert args.bounds_type == "all"

    def test_repair_type_single(self):
        """repair-type 단일 값"""
        with patch("sys.argv", ["script", "--repair-type", "ground"]):
            args = parse_arguments()
            assert args.repair_type == "ground"

    def test_repair_type_multiple(self):
        """repair-type 복수 값"""
        with patch("sys.argv", ["script", "--repair-type", "ground,underground"]):
            args = parse_arguments()
            assert args.repair_type == "ground,underground"

    def test_repair_type_default(self):
        """repair-type 기본값"""
        with patch("sys.argv", ["script"]):
            args = parse_arguments()
            assert args.repair_type == "all"


class TestMainFunction:
    """메인 함수 테스트"""

    @patch("src.main12_draw_repair2.plot_repair2_locations_ultra_fast")
    @patch("src.main12_draw_repair2.load_all_repair2_data")
    def test_main_no_data(self, mock_load, mock_plot):
        """데이터 없는 경우"""
        mock_load.return_value = {}

        with patch("sys.argv", ["script"]):
            main()

        mock_load.assert_called_once()
        mock_plot.assert_not_called()

    @patch("src.main12_draw_repair2.plot_repair2_locations_ultra_fast")
    @patch("src.main12_draw_repair2.load_all_repair2_data")
    def test_main_with_data(self, mock_load, mock_plot):
        """데이터 있는 경우"""
        mock_load.return_value = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            )
        }

        with patch("sys.argv", ["script"]):
            main()

        mock_load.assert_called_once()
        mock_plot.assert_called_once()


class TestBoundsTypeLogic:
    """bounds-type 로직 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_bounds_type_ground(self, mock_close, mock_adjust, mock_savefig, tmp_path):
        """ground bounds type 테스트"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.7, 37.8],
                    "경도": [127.2, 127.3],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        plot_repair2_locations_ultra_fast(
            data, output_path, bounds_type="ground", skip_duplicates=True
        )

        # subplots_adjust가 호출되었는지 확인
        mock_adjust.assert_called_once_with(
            left=0.05, right=0.95, top=0.95, bottom=0.05
        )
        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_bounds_type_multiple(
        self, mock_close, mock_adjust, mock_savefig, tmp_path
    ):
        """복수 bounds type 테스트"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.6],
                    "경도": [127.1],
                }
            ),
            "긴급공사": pd.DataFrame(
                {
                    "위도": [37.7],
                    "경도": [127.2],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        plot_repair2_locations_ultra_fast(
            data, output_path, bounds_type="ground,underground", skip_duplicates=True
        )

        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_bounds_type_invalid(self, mock_close, mock_adjust, mock_savefig, tmp_path):
        """잘못된 bounds type 테스트"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        # 잘못된 bounds type이어도 에러 없이 전체 데이터 사용
        plot_repair2_locations_ultra_fast(
            data, output_path, bounds_type="invalid_type", skip_duplicates=True
        )

        mock_savefig.assert_called_once()


class TestRepairTypeFilter:
    """repair-type 필터링 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_repair_type_single(self, mock_close, mock_adjust, mock_savefig, tmp_path):
        """단일 repair type 필터링"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.7, 37.8],
                    "경도": [127.2, 127.3],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        plot_repair2_locations_ultra_fast(
            data, output_path, repair_type="ground", skip_duplicates=True
        )

        # 저장이 호출되었는지 확인
        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_repair_type_multiple(
        self, mock_close, mock_adjust, mock_savefig, tmp_path
    ):
        """복수 repair type 필터링"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.6],
                    "경도": [127.1],
                }
            ),
            "긴급공사": pd.DataFrame(
                {
                    "위도": [37.7],
                    "경도": [127.2],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        plot_repair2_locations_ultra_fast(
            data, output_path, repair_type="ground,underground", skip_duplicates=True
        )

        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_repair_type_all(self, mock_close, mock_adjust, mock_savefig, tmp_path):
        """전체 repair type"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.6],
                    "경도": [127.1],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        plot_repair2_locations_ultra_fast(
            data, output_path, repair_type="all", skip_duplicates=True
        )

        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.subplots_adjust")
    @patch("matplotlib.pyplot.close")
    def test_repair_type_with_bounds_type(
        self, mock_close, mock_adjust, mock_savefig, tmp_path
    ):
        """repair-type과 bounds-type 조합"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5, 37.6],
                    "경도": [127.0, 127.1],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "위도": [37.7, 37.8],
                    "경도": [127.2, 127.3],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        # 지상누수만 표시하되, 전체 영역으로 범위 설정
        plot_repair2_locations_ultra_fast(
            data,
            output_path,
            repair_type="ground",
            bounds_type="all",
            skip_duplicates=True,
        )

        mock_savefig.assert_called_once()


class TestBoundsTypeDefault:
    """bounds-type 기본값 로직 테스트"""

    @patch("src.main12_draw_repair2.plot_repair2_locations_ultra_fast")
    @patch("src.main12_draw_repair2.load_all_repair2_data")
    @patch("src.main12_draw_repair2.load_all_mdlz_shapefiles")
    def test_bounds_type_default_to_repair_type(self, mock_mdlz, mock_load, mock_plot):
        """bounds-type이 None일 때 repair-type과 동일하게 설정"""
        mock_load.return_value = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            )
        }
        mock_mdlz.return_value = None

        with patch("sys.argv", ["script", "--repair-type", "ground"]):
            main()

        # plot 함수 호출 시 bounds_type이 "ground"로 설정되었는지 확인
        args, kwargs = mock_plot.call_args
        assert kwargs["bounds_type"] == "ground"
        assert kwargs["repair_type"] == "ground"

    @patch("src.main12_draw_repair2.plot_repair2_locations_ultra_fast")
    @patch("src.main12_draw_repair2.load_all_repair2_data")
    @patch("src.main12_draw_repair2.load_all_mdlz_shapefiles")
    def test_bounds_type_explicit(self, mock_mdlz, mock_load, mock_plot):
        """bounds-type을 명시적으로 지정한 경우"""
        mock_load.return_value = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            )
        }
        mock_mdlz.return_value = None

        with patch(
            "sys.argv", ["script", "--repair-type", "ground", "--bounds-type", "all"]
        ):
            main()

        # plot 함수 호출 시 bounds_type이 "all"로 설정되었는지 확인
        args, kwargs = mock_plot.call_args
        assert kwargs["bounds_type"] == "all"
        assert kwargs["repair_type"] == "ground"


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_unicode_handling(self, tmp_path):
        """유니코드 처리"""
        # main11e_merge_all_repairs 디렉토리 생성
        merge_dir = tmp_path / "main11e_merge_all_repairs"
        merge_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
                "주소": ["서울특별시 강남구 테헤란로"],
                "파일타입": ["지상누수"],
            }
        )
        df.to_csv(
            merge_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_all_repair2_data(tmp_path)

        assert "지상누수" in result
        assert len(result["지상누수"]) == 1
        assert "테헤란로" in result["지상누수"].iloc[0]["주소"]

    def test_large_cluster(self):
        """큰 클러스터 처리"""
        data = {
            "type1": pd.DataFrame(
                {
                    "위도": [37.5] * 100,
                    "경도": [127.0] * 100,
                }
            )
        }

        clusters, _ = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 1
        assert len(next(iter(clusters.values()))) == 100

    def test_invalid_repair_type(self, tmp_path):
        """잘못된 repair-type 처리"""
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [37.5],
                    "경도": [127.0],
                }
            ),
        }

        output_path = tmp_path / "test.png"
        # 잘못된 repair-type이어도 에러 없이 처리 (아무것도 표시 안 됨)
        with patch("matplotlib.pyplot.savefig"):
            with patch("matplotlib.pyplot.close"):
                plot_repair2_locations_ultra_fast(
                    data, output_path, repair_type="invalid", skip_duplicates=True
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
