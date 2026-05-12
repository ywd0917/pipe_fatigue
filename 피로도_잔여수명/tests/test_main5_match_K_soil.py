"""
main5_match_K_soil.py 테스트
"""

from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.main5_match_K_soil import (
    get_export_directories,
    main,
    process_pipe_type,
    process_regions,
)


@pytest.fixture
def mock_export_dirs(tmp_path):
    """테스트용 export 디렉토리 생성"""
    # export_shp_20250704(0520) 형식으로 디렉토리 생성
    (tmp_path / "export_shp_20250704(0520)").mkdir()
    (tmp_path / "export_shp_20250901(0903)").mkdir()
    (tmp_path / "export_shp_20251201(1234)").mkdir()

    # 비 export 디렉토리도 생성
    (tmp_path / "other_dir").mkdir()

    return tmp_path


@pytest.fixture
def mock_soil_gdf():
    """테스트용 토양 GeoDataFrame"""
    data = {
        "lithoidx": [1, 2, 3],
        "lithoname": ["화강암", "편마암", "현무암"],
        "geometry": [
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            Polygon([(2, 0), (4, 0), (4, 2), (2, 2)]),
            Polygon([(0, 2), (2, 2), (2, 4), (0, 4)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:4326")


@pytest.fixture
def mock_pipe_gdf():
    """테스트용 파이프 GeoDataFrame"""
    data = {
        "FTR_IDN": [1001, 1002, 1003],
        "PIPE_TYPE": ["PIPE_LM", "PIPE_LM", "PIPE_LM"],
        "geometry": [
            Point(1, 1),  # 첫 번째 토양 영역에 속함
            Point(3, 1),  # 두 번째 토양 영역에 속함
            Point(1, 3),  # 세 번째 토양 영역에 속함
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:4326")


@pytest.fixture
def mock_k_soil_df():
    """테스트용 K_SOIL DataFrame"""
    return pd.DataFrame({"lithoidx": [1, 2, 3], "k_value": [0.8, 1.2, 0.6]})


class TestGetExportDirectories:
    """get_export_directories 함수 테스트"""

    def test_get_export_directories_success(self, mock_export_dirs):
        """export 디렉토리 찾기 성공 테스트"""
        # When: export 디렉토리 검색
        result = get_export_directories(mock_export_dirs)

        # Then: 3개의 export 디렉토리 발견
        assert len(result) == 3

        # 버전 정보가 올바르게 추출되었는지 확인
        versions = [version for _, version in result]
        assert "0520" in versions
        assert "0903" in versions
        assert "1234" in versions

    def test_get_export_directories_empty(self, tmp_path):
        """export 디렉토리가 없는 경우 테스트"""
        # Given: export 디렉토리가 없는 빈 디렉토리
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        # When: export 디렉토리 검색
        result = get_export_directories(empty_dir)

        # Then: 빈 리스트 반환
        assert result == []

    def test_get_export_directories_mixed(self, tmp_path):
        """export와 non-export 디렉토리가 섞여있는 경우 테스트"""
        # Given: export와 일반 디렉토리 혼재
        (tmp_path / "export_shp_20250704(0520)").mkdir()
        (tmp_path / "normal_dir").mkdir()
        (tmp_path / "export_shp_invalid").mkdir()  # 패턴에 맞지 않는 디렉토리

        # When: export 디렉토리 검색
        result = get_export_directories(tmp_path)

        # Then: export_shp_로 시작하는 디렉토리만 반환
        assert len(result) == 2
        versions = [version for _, version in result]
        assert "0520" in versions
        assert "unknown" in versions  # invalid 패턴의 경우


class TestProcessPipeType:
    """process_pipe_type 함수 테스트"""

    @patch("src.main5_match_K_soil.soil_loader.save_soil_matching_result")
    @patch("src.main5_match_K_soil.soil_loader.spatial_join_with_soil")
    @patch("src.main5_match_K_soil.load_pipe_shapefile")
    def test_process_pipe_type_success(
        self,
        mock_load_pipe,
        mock_spatial_join,
        mock_save_result,
        mock_pipe_gdf,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """파이프 타입 처리 성공 테스트"""
        # Given: Mock 설정
        mock_load_pipe.return_value = mock_pipe_gdf
        mock_result = pd.DataFrame({"FTR_IDN": [1001, 1002], "lithoidx": [1, 2]})
        mock_spatial_join.return_value = mock_result

        # When: 파이프 타입 처리
        process_pipe_type("0520", "PIPE_LM", mock_soil_gdf, mock_k_soil_df)

        # Then: 모든 함수가 호출되었는지 확인
        mock_load_pipe.assert_called_once()
        mock_spatial_join.assert_called_once_with(
            mock_pipe_gdf, mock_soil_gdf, mock_k_soil_df
        )
        mock_save_result.assert_called_once()

    @patch("src.main5_match_K_soil.load_pipe_shapefile")
    def test_process_pipe_type_no_pipe_data(
        self, mock_load_pipe, mock_soil_gdf, mock_k_soil_df
    ):
        """파이프 데이터가 없는 경우 테스트"""
        # Given: 파이프 데이터 로드 실패
        mock_load_pipe.return_value = None

        # When: 파이프 타입 처리
        with patch(
            "src.main5_match_K_soil.soil_loader.spatial_join_with_soil"
        ) as mock_spatial_join:
            process_pipe_type("9999", "PIPE_LM", mock_soil_gdf, mock_k_soil_df)

        # Then: spatial_join이 호출되지 않음
        mock_spatial_join.assert_not_called()

    @patch("src.main5_match_K_soil.soil_loader.save_soil_matching_result")
    @patch("src.main5_match_K_soil.soil_loader.spatial_join_with_soil")
    @patch("src.main5_match_K_soil.load_pipe_shapefile")
    def test_process_pipe_type_empty_pipe_data(
        self,
        mock_load_pipe,
        mock_spatial_join,
        mock_save_result,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """빈 파이프 데이터인 경우 테스트"""
        # Given: 빈 파이프 데이터
        empty_gdf = gpd.GeoDataFrame(columns=["FTR_IDN", "geometry"])
        mock_load_pipe.return_value = empty_gdf

        # When: 파이프 타입 처리
        process_pipe_type("0520", "PIPE_LM", mock_soil_gdf, mock_k_soil_df)

        # Then: spatial_join이 호출되지 않음
        mock_spatial_join.assert_not_called()
        mock_save_result.assert_not_called()


class TestProcessRegions:
    """process_regions 함수 테스트"""

    @patch("src.main5_match_K_soil.process_pipe_type")
    @patch("src.main5_match_K_soil.get_export_directories")
    def test_process_regions_both_types(
        self,
        mock_get_dirs,
        mock_process_pipe,
        mock_export_dirs,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """모든 타입 처리 테스트"""
        # Given: Mock 설정
        mock_get_dirs.return_value = [
            (mock_export_dirs / "export_shp_20250704(0520)", "0520")
        ]

        # args 객체 모킹
        args = MagicMock()
        args.version = None
        args.type = "both"

        # When: 지역 처리
        process_regions(args, mock_soil_gdf, mock_k_soil_df)

        # Then: PIPE_LM과 SPLY_LS 모두 처리됨
        assert mock_process_pipe.call_count == 2
        mock_process_pipe.assert_any_call(
            "0520", "PIPE_LM", mock_soil_gdf, mock_k_soil_df
        )
        mock_process_pipe.assert_any_call(
            "0520", "SPLY_LS", mock_soil_gdf, mock_k_soil_df
        )

    @patch("src.main5_match_K_soil.process_pipe_type")
    @patch("src.main5_match_K_soil.get_export_directories")
    def test_process_regions_pipe_only(
        self,
        mock_get_dirs,
        mock_process_pipe,
        mock_export_dirs,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """파이프만 처리 테스트"""
        # Given: Mock 설정
        mock_get_dirs.return_value = [
            (mock_export_dirs / "export_shp_20250704(0520)", "0520")
        ]

        # args 객체 모킹
        args = MagicMock()
        args.version = None
        args.type = "pipe"

        # When: 지역 처리
        process_regions(args, mock_soil_gdf, mock_k_soil_df)

        # Then: PIPE_LM만 처리됨
        mock_process_pipe.assert_called_once_with(
            "0520", "PIPE_LM", mock_soil_gdf, mock_k_soil_df
        )

    @patch("src.main5_match_K_soil.process_pipe_type")
    @patch("src.main5_match_K_soil.get_export_directories")
    def test_process_regions_specific_version(
        self,
        mock_get_dirs,
        mock_process_pipe,
        mock_export_dirs,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """특정 버전만 처리 테스트"""
        # Given: Mock 설정 - 여러 버전이 있지만 하나만 선택
        mock_get_dirs.return_value = [
            (mock_export_dirs / "export_shp_20250704(0520)", "0520"),
            (mock_export_dirs / "export_shp_20250901(0903)", "0903"),
        ]

        # args 객체 모킹
        args = MagicMock()
        args.version = "0520"
        args.type = "both"

        # When: 지역 처리
        process_regions(args, mock_soil_gdf, mock_k_soil_df)

        # Then: 0520 버전만 처리됨
        assert mock_process_pipe.call_count == 2
        mock_process_pipe.assert_any_call(
            "0520", "PIPE_LM", mock_soil_gdf, mock_k_soil_df
        )
        mock_process_pipe.assert_any_call(
            "0520", "SPLY_LS", mock_soil_gdf, mock_k_soil_df
        )

    @patch("src.main5_match_K_soil.get_export_directories")
    def test_process_regions_no_directories(
        self, mock_get_dirs, mock_soil_gdf, mock_k_soil_df, capsys
    ):
        """export 디렉토리가 없는 경우 테스트"""
        # Given: export 디렉토리 없음
        mock_get_dirs.return_value = []

        # args 객체 모킹
        args = MagicMock()
        args.version = None
        args.type = "both"

        # When: 지역 처리
        process_regions(args, mock_soil_gdf, mock_k_soil_df)

        # Then: 오류 메시지 출력
        captured = capsys.readouterr()
        assert "오류: export_shp_ 디렉토리를 찾을 수 없습니다." in captured.out


class TestMain:
    """main 함수 테스트"""

    @patch("src.main5_match_K_soil.process_regions")
    @patch("src.main5_match_K_soil.soil_loader.load_k_soil_data")
    @patch("src.main5_match_K_soil.soil_loader.load_soil_data")
    @patch("pathlib.Path.mkdir")
    @patch("sys.argv", ["main5_match_K_soil.py"])
    def test_main_success(
        self,
        mock_mkdir,
        mock_load_soil,
        mock_load_k_soil,
        mock_process_regions,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """기본 실행 테스트"""
        # Given: Mock 설정
        mock_load_soil.return_value = mock_soil_gdf
        mock_load_k_soil.return_value = mock_k_soil_df

        # When: main 함수 실행
        main()

        # Then: 모든 함수가 호출되었는지 확인
        mock_mkdir.assert_called_once_with(exist_ok=True)
        mock_load_soil.assert_called_once()
        mock_load_k_soil.assert_called_once()
        mock_process_regions.assert_called_once()

    @patch("src.main5_match_K_soil.soil_loader.load_soil_data")
    @patch("pathlib.Path.mkdir")
    @patch("sys.argv", ["main5_match_K_soil.py"])
    def test_main_no_soil_data(self, mock_mkdir, mock_load_soil, capsys):
        """토양 데이터가 없는 경우 테스트"""
        # Given: 토양 데이터 로드 실패
        mock_load_soil.return_value = None

        # When: main 함수 실행
        main()

        # Then: 오류 메시지 출력
        captured = capsys.readouterr()
        assert "오류: 토양 데이터를 로드할 수 없습니다." in captured.out

    @patch("src.main5_match_K_soil.process_regions")
    @patch("src.main5_match_K_soil.soil_loader.load_k_soil_data")
    @patch("src.main5_match_K_soil.soil_loader.load_soil_data")
    @patch("pathlib.Path.mkdir")
    @patch("sys.argv", ["main5_match_K_soil.py", "--version", "0520", "--type", "pipe"])
    def test_main_with_arguments(
        self,
        mock_mkdir,
        mock_load_soil,
        mock_load_k_soil,
        mock_process_regions,
        mock_soil_gdf,
        mock_k_soil_df,
    ):
        """인수가 있는 경우 테스트"""
        # Given: Mock 설정
        mock_load_soil.return_value = mock_soil_gdf
        mock_load_k_soil.return_value = mock_k_soil_df

        # When: main 함수 실행
        main()

        # Then: process_regions가 올바른 args와 함께 호출됨
        mock_process_regions.assert_called_once()

        # args 객체의 속성 확인
        call_args = mock_process_regions.call_args[0]
        args = call_args[0]  # 첫 번째 인수가 args
        assert args.version == "0520"
        assert args.type == "pipe"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
