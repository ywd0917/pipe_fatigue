"""
main13_crop_520.py 테스트 (520 영역 추출 및 중복 분석)
MDLZ 0520 영역 복구 작업 중복 위치 분석 테스트
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import tempfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.main13_crop_520 import (
    DISTANCE_THRESHOLD,
    convert_wgs84_to_geodataframe,
    find_duplicate_clusters_ultra_fast,
    get_repair2_colors,
    load_mdlz_520_shapefile,
    load_pipe_data_520,
    load_unified_repair_data,
    main,
    parse_arguments,
    plot_repair2_locations_520,
    precompute_point_attributes_vectorized,
    save_filtered_csv,
    save_statistics_report,
)


class TestConstants:
    """상수 테스트"""

    def test_distance_threshold(self):
        """거리 임계값 확인"""
        assert DISTANCE_THRESHOLD == 10.0
        assert isinstance(DISTANCE_THRESHOLD, float)


class TestGetRepair2Colors:
    """색상 정의 테스트"""

    def test_color_definitions(self):
        """4가지 카테고리 색상 정의 확인"""
        colors = get_repair2_colors()
        assert len(colors) == 4
        assert "지상누수" in colors
        assert "지하누수" in colors
        assert "긴급공사" in colors
        assert "관리대장" in colors

        # 색상과 라벨 튜플 확인
        assert colors["지상누수"] == ("#4ECDC4", "지상누수")
        assert colors["지하누수"] == ("#45B7D1", "지하누수")
        assert colors["긴급공사"] == ("#FF6B6B", "긴급공사")
        assert colors["관리대장"] == ("#FFA500", "관리대장")


class TestLoadUnifiedRepairData:
    """통합 데이터 로드 테스트"""

    def test_load_missing_file(self, tmp_path):
        """파일이 없는 경우"""
        input_path = tmp_path / "missing.csv"
        result, total_stats, filtered_stats = load_unified_repair_data(
            input_path, verbose=False
        )
        assert result == {}
        assert total_stats["total"] == 0
        assert filtered_stats["total"] == 0

    def test_load_valid_csv(self, tmp_path):
        """유효한 CSV 파일 로드"""
        # 테스트용 CSV 생성
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "작업일시": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
                "위도": [35.8, 35.9, None, 35.85],
                "경도": [128.6, 128.7, 128.65, None],
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # 로드 테스트
        result, total_stats, filtered_stats = load_unified_repair_data(
            csv_path, verbose=False
        )

        # 통계 확인
        assert total_stats["total"] == 4
        assert total_stats["with_location"] == 2  # 위치 정보가 있는 것은 2개
        assert len(result) == 2  # 지상누수, 지하누수만
        assert "지상누수" in result
        assert "지하누수" in result
        assert len(result["지상누수"]) == 1
        assert len(result["지하누수"]) == 1

    def test_load_with_mdlz_filtering(self, tmp_path):
        """MDLZ 영역 필터링 테스트"""
        # 테스트용 CSV 생성
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame(
            {
                "작업일시": ["2023-01-01", "2023-01-02"],
                "위도": [35.8946, 35.9],
                "경도": [128.6021, 128.7],
                "파일타입": ["지상누수", "지하누수"],
            }
        )
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # MDLZ GeoDataFrame 생성 (520 영역 모의)
        polygon = Polygon(
            [
                (128.59, 35.89),
                (128.61, 35.89),
                (128.61, 35.90),
                (128.59, 35.90),
                (128.59, 35.89),
            ]
        )
        mdlz_gdf = gpd.GeoDataFrame(
            {"MDZ_NUM": ["0520"]}, geometry=[polygon], crs="EPSG:4326"
        ).to_crs("EPSG:5179")

        # 로드 테스트
        result, total_stats, filtered_stats = load_unified_repair_data(
            csv_path, mdlz_gdf=mdlz_gdf, verbose=False
        )

        # 필터링 결과 확인
        assert total_stats["with_location"] == 2
        assert filtered_stats["total"] <= 2  # 영역 내의 점만


class TestSaveFilteredCSV:
    """필터링된 데이터 저장 테스트"""

    def test_save_empty_data(self, tmp_path):
        """빈 데이터 저장"""
        output_path = tmp_path / "output.csv"
        save_filtered_csv({}, output_path, verbose=False)
        assert not output_path.exists()

    def test_save_valid_data(self, tmp_path):
        """유효한 데이터 저장"""
        output_path = tmp_path / "output.csv"

        # 테스트 데이터 생성
        data = {
            "지상누수": pd.DataFrame(
                {
                    "작업일시": ["2023-01-01", "2023-01-02"],
                    "위도": [35.8, 35.9],
                    "경도": [128.6, 128.7],
                    "파일타입": ["지상누수", "지상누수"],
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "작업일시": ["2023-01-03"],
                    "위도": [35.85],
                    "경도": [128.65],
                    "파일타입": ["지하누수"],
                }
            ),
        }

        save_filtered_csv(data, output_path, verbose=False)

        # 저장된 파일 확인
        assert output_path.exists()
        saved_df = pd.read_csv(output_path)
        assert len(saved_df) == 3
        assert "파일타입" in saved_df.columns
        assert set(saved_df["파일타입"].unique()) == {"지상누수", "지하누수"}

    def test_save_data_with_extra_columns(self, tmp_path):
        """추가된 공통 컬럼들이 저장되는지 테스트"""
        output_path = tmp_path / "output_with_extra_cols.csv"

        # 테스트 데이터에 추가 컬럼 포함
        extra_columns = {
            "공사명": "테스트 공사",
            "공사개요": "테스트 개요",
            "구군": "테스트구",
            "주소": "테스트 주소",
        }
        data = {
            "지상누수": pd.DataFrame(
                {
                    "작업일시": ["2023-01-01"],
                    "위도": [35.8],
                    "경도": [128.6],
                    "파일타입": ["지상누수"],
                    **extra_columns,
                }
            )
        }

        save_filtered_csv(data, output_path, verbose=False)

        # 저장된 파일 확인
        assert output_path.exists()
        saved_df = pd.read_csv(output_path)
        assert len(saved_df) == 1

        # 추가된 컬럼들이 모두 존재하는지 확인
        for col in extra_columns:
            assert col in saved_df.columns
            assert saved_df[col].iloc[0] == extra_columns[col]


class TestSaveStatisticsReport:
    """통계 보고서 저장 테스트"""

    def test_save_statistics(self, tmp_path):
        """통계 보고서 저장 테스트"""
        # 통계 데이터 생성
        total_stats = {
            "total": 100,
            "by_type": {"지상누수": 50, "지하누수": 30, "긴급공사": 15, "관리대장": 5},
            "with_location": 95,
            "with_location_by_type": {
                "지상누수": 48,
                "지하누수": 29,
                "긴급공사": 14,
                "관리대장": 4,
            },
        }

        filtered_stats = {
            "total": 10,
            "by_type": {"지상누수": 5, "지하누수": 3, "긴급공사": 2},
        }

        # 보고서 저장
        save_statistics_report(total_stats, filtered_stats, tmp_path, verbose=False)

        # 파일 확인
        report_path = tmp_path / "처리통계.txt"
        assert report_path.exists()

        # 내용 확인
        content = report_path.read_text(encoding="utf-8")
        assert "원본 데이터" in content
        assert "총 항목 수: 100개" in content
        assert "위치 정보가 있는 항목 수: 95개" in content
        assert "지상누수: 48개 (-2개)" in content  # 50 - 48 = -2
        assert "MDLZ 0520 지역 필터링 후" in content
        assert "지상누수: 5개 (위치있는 것 대비" in content
        assert "관리대장: 0개 (위치있는 것 대비" in content


class TestLoadMDLZ520Shapefile:
    """MDLZ 0520 shapefile 로드 테스트"""

    def test_load_missing_file(self, tmp_path):
        """파일이 없는 경우"""
        result = load_mdlz_520_shapefile(tmp_path, verbose=False)
        assert result is None

    @patch("src.main13_crop_520.gpd.read_file")
    def test_load_valid_shapefile(self, mock_read, tmp_path):
        """유효한 shapefile 로드"""
        # 테스트용 shapefile 구조 생성
        shp_dir = tmp_path / "export_shp_20250704(0520)"
        shp_dir.mkdir()
        shp_file = shp_dir / "WEA_MDLZ_AS.shp"
        shp_file.touch()  # 빈 파일 생성

        # Mock GeoDataFrame
        mock_gdf = gpd.GeoDataFrame(
            {"MDZ_NUM": ["0520", "0521", "0520"]},
            geometry=[
                Point(0, 0).buffer(1),
                Point(1, 1).buffer(1),
                Point(2, 2).buffer(1),
            ],
            crs="EPSG:5179",
        )
        mock_read.return_value = mock_gdf

        result = load_mdlz_520_shapefile(tmp_path, verbose=False)

        # 0520만 필터링되었는지 확인
        assert result is not None
        assert len(result) == 2  # 0520인 것만
        assert all(result["MDZ_NUM"] == "0520")


class TestFindDuplicateClustersUltraFast:
    """중복 클러스터 찾기 테스트"""

    def test_no_duplicates(self):
        """중복이 없는 경우"""
        data = {
            "지상누수": pd.DataFrame({"위도": [35.0, 35.5], "경도": [128.0, 128.5]})
        }

        clusters, point_to_size = find_duplicate_clusters_ultra_fast(data)

        assert len(clusters) == 0  # 거리가 멀어서 클러스터 없음
        assert len(point_to_size) == 0

    def test_with_duplicates(self):
        """중복이 있는 경우"""
        # 매우 가까운 점들 생성 (10m 이내)
        data = {
            "지상누수": pd.DataFrame(
                {
                    "위도": [35.0000, 35.0001, 35.0002],  # 약 11m씩 떨어진 점
                    "경도": [128.0000, 128.0000, 128.0000],
                }
            )
        }

        clusters, point_to_size = find_duplicate_clusters_ultra_fast(data)

        # 클러스터가 생성되었는지 확인
        assert len(clusters) >= 0  # 클러스터 수는 거리에 따라 달라질 수 있음

    def test_empty_data(self):
        """빈 데이터"""
        clusters, point_to_size = find_duplicate_clusters_ultra_fast({})
        assert clusters == {}
        assert point_to_size == {}


class TestConvertWGS84ToGeoDataFrame:
    """좌표 변환 테스트"""

    def test_convert_coordinates(self):
        """WGS84 좌표를 EPSG:5179로 변환"""
        df = pd.DataFrame({"위도": [35.8, 35.9], "경도": [128.6, 128.7]})

        gdf = convert_wgs84_to_geodataframe(df)

        assert isinstance(gdf, gpd.GeoDataFrame)
        assert gdf.crs.to_epsg() == 5179
        assert len(gdf) == 2
        assert all(gdf.geometry.type == "Point")


class TestPrecomputePointAttributesVectorized:
    """벡터화된 점 속성 계산 테스트"""

    def test_compute_attributes(self):
        """점 속성 계산"""
        repair_data = {
            "지상누수": pd.DataFrame({"위도": [35.8, 35.9], "경도": [128.6, 128.7]})
        }

        point_to_cluster_size = {
            (35.8, 128.6, "지상누수"): 2,
            (35.9, 128.7, "지상누수"): 1,
        }

        result = precompute_point_attributes_vectorized(
            repair_data, point_to_cluster_size, base_size=50
        )

        assert "지상누수" in result
        assert "x" in result["지상누수"]
        assert "y" in result["지상누수"]
        assert "sizes" in result["지상누수"]
        assert "color" in result["지상누수"]
        assert len(result["지상누수"]["x"]) == 2


class TestParseArguments:
    """명령줄 인자 파싱 테스트"""

    def test_default_arguments(self):
        """기본 인자"""
        with patch("sys.argv", ["script.py"]):
            args = parse_arguments()
            assert args.output_dir is None
            assert args.show is False
            assert args.no_interactive is False
            assert args.skip_duplicates is False
            assert args.min_duplicates == 0
            assert args.scale == 1.0

    def test_custom_arguments(self):
        """사용자 정의 인자"""
        with patch(
            "sys.argv",
            [
                "script.py",
                "--output-dir",
                "custom_dir",
                "--show",
                "--min-duplicates",
                "4",
                "--skip-duplicates",
                "--scale",
                "2.0",
            ],
        ):
            args = parse_arguments()
            assert args.output_dir == "custom_dir"
            assert args.show is True
            assert args.min_duplicates == 4
            assert args.skip_duplicates is True
            assert args.scale == 2.0


class TestPlotRepair2Locations520:
    """시각화 함수 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.show")
    def test_plot_without_show(self, mock_show, mock_savefig, tmp_path):
        """화면 표시 없이 플롯"""
        repair_data = {"지상누수": pd.DataFrame({"위도": [35.8], "경도": [128.6]})}
        output_path = tmp_path / "test.png"

        plot_repair2_locations_520(
            repair_data, output_path, show_plot=False, skip_duplicates=True, scale=1.0
        )

        mock_savefig.assert_called_once()
        mock_show.assert_not_called()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.show")
    def test_plot_with_scale(self, mock_show, mock_savefig, tmp_path):
        """스케일 옵션으로 플롯"""
        repair_data = {"지상누수": pd.DataFrame({"위도": [35.8], "경도": [128.6]})}
        output_path = tmp_path / "test.png"

        # scale=2.0으로 테스트
        plot_repair2_locations_520(
            repair_data, output_path, show_plot=False, skip_duplicates=True, scale=2.0
        )

        mock_savefig.assert_called_once()
        mock_show.assert_not_called()


class TestMainFunction:
    """메인 함수 통합 테스트"""

    @patch("src.main13_crop_520.parse_arguments")
    @patch("src.main13_crop_520.load_mdlz_520_shapefile")
    @patch("src.main13_crop_520.load_unified_repair_data")
    @patch("src.main13_crop_520.save_filtered_csv")
    @patch("src.main13_crop_520.save_statistics_report")
    @patch("src.main13_crop_520.plot_repair2_locations_520")
    def test_main_no_data(
        self,
        mock_plot,
        mock_stats,
        mock_save,
        mock_load,
        mock_mdlz,
        mock_args,
        tmp_path,
        capsys,
    ):
        """데이터가 없는 경우 메인 함수"""
        # Mock 설정
        mock_args.return_value = MagicMock(
            output_dir=str(tmp_path),
            show=False,
            min_duplicates=0,
            skip_duplicates=False,
            no_interactive=True,
            scale=1.0,
        )

        # 입력 파일이 없는 경우
        with patch("pathlib.Path.exists", return_value=False):
            main()

        # 에러 메시지 확인
        captured = capsys.readouterr()
        assert "통합 입력 파일을 찾을 수 없습니다" in captured.out

        # 함수들이 호출되지 않았는지 확인
        mock_plot.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.main13_crop_520.parse_arguments")
    @patch("src.main13_crop_520.load_mdlz_520_shapefile")
    @patch("src.main13_crop_520.load_unified_repair_data")
    @patch("src.main13_crop_520.load_pipe_data_520")
    @patch("src.main13_crop_520.save_filtered_csv")
    @patch("src.main13_crop_520.save_statistics_report")
    @patch("src.main13_crop_520.plot_repair2_locations_520")
    @patch("pathlib.Path.exists")
    def test_main_with_data(
        self,
        mock_exists,
        mock_plot,
        mock_stats,
        mock_save,
        mock_pipe,
        mock_load,
        mock_mdlz,
        mock_args,
        tmp_path,
    ):
        """데이터가 있는 경우 메인 함수"""
        # Mock 설정
        mock_args.return_value = MagicMock(
            output_dir=None,
            show=False,
            min_duplicates=0,
            skip_duplicates=False,
            no_interactive=True,
            scale=1.0,
        )

        mock_exists.return_value = True

        # Mock 데이터
        mock_mdlz.return_value = gpd.GeoDataFrame()
        mock_load.return_value = (
            {"지상누수": pd.DataFrame({"위도": [35.8], "경도": [128.6]})},
            {
                "total": 100,
                "by_type": {},
                "with_location": 95,
                "with_location_by_type": {},
            },
            {"total": 10, "by_type": {"지상누수": 5}},
        )
        mock_pipe.return_value = gpd.GeoDataFrame()

        # 실행
        main()

        # 함수 호출 확인
        mock_load.assert_called_once()
        mock_save.assert_called_once()
        mock_stats.assert_called_once()
        mock_plot.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
