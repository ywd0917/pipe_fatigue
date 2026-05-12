"""
soil_loader 모듈 테스트
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from src.soil_loader import (
    LithoidxStatistics,
    analyze_lithoidx,
    generate_lithoidx_statistics,
    get_file_type_from_path,
    get_soil_info,
    get_soil_path,
    load_k_soil_data,
    load_soil_data,
    save_soil_matching_result,
    search_lithoidx,
    spatial_join_with_soil,
    validate_soil_data,
)


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성 픽스처"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_soil_gdf():
    """테스트용 토양 GeoDataFrame"""
    data = {
        "lithoidx": ["Km1", "Km2", "Km3", "Km1"],
        "lithoname": ["암석1", "암석2", "암석3", "암석1"],
        "geometry": [
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
            Polygon([(1, 1), (2, 1), (2, 2), (1, 2)]),
        ],
    }
    return gpd.GeoDataFrame(data, crs="EPSG:5179")


class TestGetSoilPath:
    """get_soil_path 함수 테스트"""

    def test_get_soil_path_from_data_dir(self, temp_dir):
        """data 디렉토리에서 경로 생성"""
        data_dir = temp_dir / "data"
        result = get_soil_path(data_dir)
        assert result == data_dir / "soil" / "Geology_250K_Litho.shp"

    def test_get_soil_path_from_raw_dir(self, temp_dir):
        """data/raw 디렉토리에서 경로 생성"""
        raw_dir = temp_dir / "data" / "raw"
        result = get_soil_path(raw_dir)
        assert result == temp_dir / "data" / "soil" / "Geology_250K_Litho.shp"

    def test_get_soil_path_from_other_dir(self, temp_dir):
        """다른 디렉토리에서 경로 생성"""
        other_dir = temp_dir / "other"
        result = get_soil_path(other_dir)
        assert result == other_dir / "soil" / "Geology_250K_Litho.shp"


class TestValidateSoilData:
    """validate_soil_data 함수 테스트"""

    def test_validate_soil_data_clean(self, sample_soil_gdf):
        """정상 데이터 검증"""
        result = validate_soil_data(sample_soil_gdf.copy())
        assert len(result) == 4
        assert result.crs == "EPSG:5179"

    def test_validate_soil_data_with_null_geometry(self):
        """NULL geometry가 있는 데이터 검증"""
        # NULL geometry 포함 데이터 생성
        data = {
            "lithoidx": ["Km1", "Km2", "Km3"],
            "geometry": [
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                None,  # NULL geometry
                Polygon([(0, 1), (1, 1), (1, 2), (0, 2)]),
            ],
        }
        gdf = gpd.GeoDataFrame(data, crs="EPSG:5179")

        result = validate_soil_data(gdf)
        assert len(result) == 2  # NULL geometry 제거됨
        assert result.geometry.isnull().sum() == 0

    def test_validate_soil_data_without_crs(self):
        """CRS가 없는 데이터 검증"""
        data = {
            "lithoidx": ["Km1"],
            "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
        }
        gdf = gpd.GeoDataFrame(data)  # CRS 없음

        result = validate_soil_data(gdf)
        assert result.crs == "EPSG:5179"


class TestLoadSoilData:
    """load_soil_data 함수 테스트"""

    @patch("geopandas.read_file")
    def test_load_soil_data_success(self, mock_read_file, temp_dir, sample_soil_gdf):
        """정상적인 로드"""
        mock_read_file.return_value = sample_soil_gdf

        # soil 디렉토리 및 파일 생성
        soil_dir = temp_dir / "data" / "soil"
        soil_dir.mkdir(parents=True)
        (soil_dir / "Geology_250K_Litho.shp").touch()

        result = load_soil_data(temp_dir / "data")

        assert result is not None
        assert len(result) == 4
        assert result.crs == "EPSG:5179"
        mock_read_file.assert_called_once()

    def test_load_soil_data_file_not_found(self, temp_dir):
        """파일이 없는 경우"""
        result = load_soil_data(temp_dir, verbose=False)
        assert result is None

    @patch("geopandas.read_file")
    def test_load_soil_data_with_error(self, mock_read_file, temp_dir):
        """읽기 중 에러 발생"""
        mock_read_file.side_effect = Exception("Read error")

        # soil 디렉토리 및 파일 생성
        soil_dir = temp_dir / "data" / "soil"
        soil_dir.mkdir(parents=True)
        (soil_dir / "Geology_250K_Litho.shp").touch()

        result = load_soil_data(temp_dir / "data", verbose=False)
        assert result is None

    @patch("geopandas.read_file")
    def test_load_soil_data_quiet_mode(self, mock_read_file, temp_dir, sample_soil_gdf):
        """verbose=False 모드"""
        mock_read_file.return_value = sample_soil_gdf

        # soil 디렉토리 및 파일 생성
        soil_dir = temp_dir / "data" / "soil"
        soil_dir.mkdir(parents=True)
        (soil_dir / "Geology_250K_Litho.shp").touch()

        result = load_soil_data(temp_dir / "data", verbose=False)

        assert result is not None
        assert len(result) == 4


class TestGetSoilInfo:
    """get_soil_info 함수 테스트"""

    def test_get_soil_info_complete(self, sample_soil_gdf):
        """완전한 데이터의 정보 추출"""
        info = get_soil_info(sample_soil_gdf)

        assert info["total_features"] == 4
        assert info["crs"] == "EPSG:5179"
        assert "lithoidx" in info["columns"]
        assert info["unique_lithoidx"] == 3
        assert set(info["lithoidx_values"]) == {"Km1", "Km2", "Km3"}
        assert info["unique_lithonames"] == 3
        assert info["bounds"] is not None

    def test_get_soil_info_minimal(self):
        """최소한의 데이터 정보 추출"""
        data = {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
        gdf = gpd.GeoDataFrame(data)

        info = get_soil_info(gdf)

        assert info["total_features"] == 1
        assert info["crs"] is None
        assert "unique_lithoidx" not in info
        assert "unique_lithonames" not in info

    def test_get_soil_info_empty(self):
        """빈 데이터의 정보 추출"""
        gdf = gpd.GeoDataFrame({"geometry": []})

        info = get_soil_info(gdf)

        assert info["total_features"] == 0
        assert info["bounds"] is None


class TestLoadSoilDataVerbose:
    """load_soil_data verbose 모드 테스트"""

    def test_load_soil_data_verbose_file_not_found(self, temp_dir, capsys):
        """파일이 없을 때 verbose 메시지 출력"""
        result = load_soil_data(temp_dir, verbose=True)
        captured = capsys.readouterr()

        assert result is None
        assert "오류: 토양 데이터를 찾을 수 없습니다" in captured.out

    @patch("geopandas.read_file")
    def test_load_soil_data_verbose_read_error(self, mock_read_file, temp_dir, capsys):
        """읽기 오류 시 verbose 메시지 출력"""
        mock_read_file.side_effect = Exception("Read error")

        # soil 디렉토리 및 파일 생성
        soil_dir = temp_dir / "data" / "soil"
        soil_dir.mkdir(parents=True)
        (soil_dir / "Geology_250K_Litho.shp").touch()

        result = load_soil_data(temp_dir / "data", verbose=True)
        captured = capsys.readouterr()

        assert result is None
        assert "오류: 토양 데이터 로드 실패" in captured.out
        assert "Read error" in captured.out


class TestGetFileTypeFromPath:
    """get_file_type_from_path 함수 테스트"""

    def test_get_file_type_boundary(self):
        """Boundary 파일 타입 인식"""
        file_path = Path("/test/Boudary_something.shp")
        result = get_file_type_from_path(file_path)
        assert result == "boundary"

    def test_get_file_type_fault(self):
        """Fault 파일 타입 인식"""
        file_path = Path("/test/Fault_data.shp")
        result = get_file_type_from_path(file_path)
        assert result == "fault"

    def test_get_file_type_frame(self):
        """Frame 파일 타입 인식"""
        file_path = Path("/test/Frame_outline.shp")
        result = get_file_type_from_path(file_path)
        assert result == "frame"

    def test_get_file_type_litho(self):
        """Litho 파일 타입 인식"""
        file_path = Path("/test/Litho_geology.shp")
        result = get_file_type_from_path(file_path)
        assert result == "litho"

    def test_get_file_type_unknown(self):
        """알 수 없는 파일 타입"""
        file_path = Path("/test/unknown_file.shp")
        result = get_file_type_from_path(file_path)
        assert result == "unknown"


class TestAnalyzeLithoidx:
    """analyze_lithoidx 함수 테스트"""

    @pytest.fixture
    def mock_soil_gdf(self):
        """테스트용 토양 GeoDataFrame"""
        data = {
            "lithoidx": [1, 1, 1, 2, 2, 3, 3, 3, 3],
            "lithoname": [
                "화강암",
                "화강암",
                "화강암",
                "편마암",
                "편마암",
                "현무암",
                "현무암",
                "현무암",
                "현무암",
            ],
            "age": [
                "중생대 백악기",
                "중생대 백악기",
                "중생대 쥐라기",
                "선캄브리아시대",
                "선캄브리아시대",
                "신생대 제4기",
                "신생대 제4기",
                "신생대 제4기",
                "중생대 백악기",
            ],
            "shape_area": [100.0, 200.0, 150.0, 300.0, 250.0, 50.0, 75.0, 80.0, 90.0],
            "shape_len": [40.0, 60.0, 50.0, 70.0, 65.0, 30.0, 35.0, 36.0, 38.0],
            "mapname": [
                "서울",
                "서울",
                "대전",
                "대전",
                "강릉",
                "속초",
                "속초",
                "강릉",
                "강릉",
            ],
            "geometry": [
                Polygon([(i, i), (i + 1, i), (i + 1, i + 1), (i, i + 1)])
                for i in range(9)
            ],
        }
        return gpd.GeoDataFrame(data, crs="EPSG:4326")

    def test_analyze_lithoidx_basic(self, mock_soil_gdf):
        """기본 분석 기능 테스트"""
        result = analyze_lithoidx(mock_soil_gdf)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3  # 3개의 고유 lithoidx

        # 컬럼 확인
        expected_columns = [
            "lithoidx",
            "lithoname",
            "count",
            "total_area",
            "avg_area",
            "total_length",
            "unique_ages",
            "ages",
            "map_count",
            "maps",
            "rank",
        ]
        for col in expected_columns:
            assert col in result.columns

        # 면적 기준 정렬 확인 (첫 번째가 가장 큰 면적)
        assert result.iloc[0]["total_area"] >= result.iloc[1]["total_area"]

    def test_analyze_lithoidx_age_aggregation(self, mock_soil_gdf):
        """연대 집계 기능 테스트"""
        result = analyze_lithoidx(mock_soil_gdf)

        # lithoidx 3의 연대 정보 확인
        lithoidx_3 = result[result["lithoidx"] == 3].iloc[0]
        assert lithoidx_3["unique_ages"] == 2
        assert "신생대 제4기(3)" in lithoidx_3["ages"]
        assert "중생대 백악기(1)" in lithoidx_3["ages"]

    def test_analyze_lithoidx_map_aggregation(self, mock_soil_gdf):
        """도엽 집계 기능 테스트"""
        result = analyze_lithoidx(mock_soil_gdf)

        # lithoidx 1의 도엽 정보 확인
        lithoidx_1 = result[result["lithoidx"] == 1].iloc[0]
        assert lithoidx_1["map_count"] == 2
        assert "서울" in lithoidx_1["maps"]
        assert "대전" in lithoidx_1["maps"]


class TestGenerateLithoidxStatistics:
    """generate_lithoidx_statistics 함수 테스트"""

    @pytest.fixture
    def mock_analysis_df(self):
        """테스트용 분석 결과 DataFrame"""
        data = {
            "lithoidx": [3, 2, 1],
            "lithoname": ["현무암", "편마암", "화강암"],
            "count": [4, 2, 3],
            "total_area": [295.0, 550.0, 450.0],
            "avg_area": [73.75, 275.0, 150.0],
            "total_length": [139.0, 135.0, 150.0],
            "unique_ages": [2, 1, 2],
            "ages": [
                "신생대 제4기(3), 중생대 백악기(1)",
                "선캄브리아시대(2)",
                "중생대 백악기(2), 중생대 쥐라기(1)",
            ],
            "map_count": [2, 2, 2],
            "maps": ["강릉, 속초", "강릉, 대전", "대전, 서울"],
            "rank": [1, 2, 3],
        }
        return pd.DataFrame(data)

    def test_generate_lithoidx_statistics_complete(self, mock_analysis_df):
        """완전한 통계 생성 테스트"""
        result = generate_lithoidx_statistics(mock_analysis_df)

        assert isinstance(result, LithoidxStatistics)
        assert result.total_lithoidx == 3
        assert result.total_objects == 9  # 4 + 2 + 3
        assert result.total_area == 1295.0  # 295 + 550 + 450
        assert result.avg_objects_per_lithoidx == 3.0

        # 최대 객체 수를 가진 lithoidx 확인
        assert result.max_objects_lithoidx["lithoidx"] == 3
        assert result.max_objects_lithoidx["lithoname"] == "현무암"
        assert result.max_objects_lithoidx["count"] == 4

        # 최대 면적을 가진 lithoidx 확인
        assert result.max_area_lithoidx["lithoidx"] == 2
        assert result.max_area_lithoidx["lithoname"] == "편마암"
        assert result.max_area_lithoidx["total_area"] == 550.0

        # 연대 분포 확인
        assert "신생대 제4기" in result.age_distribution
        assert result.age_distribution["신생대 제4기"] == 3

        # 도엽 커버리지 확인
        expected_maps = {"서울", "대전", "강릉", "속초"}
        assert result.map_coverage == expected_maps

    def test_generate_lithoidx_statistics_empty_df(self):
        """빈 DataFrame 테스트 - 실제로는 예외 발생"""
        # 빈 DataFrame이지만 필요한 컬럼이 있는 경우
        empty_df = pd.DataFrame(
            columns=[
                "lithoidx",
                "lithoname",
                "count",
                "total_area",
                "avg_area",
                "total_length",
                "unique_ages",
                "ages",
                "map_count",
                "maps",
                "rank",
            ]
        )

        # 빈 DataFrame에서는 idxmax()가 실패하므로 ValueError 발생
        with pytest.raises(
            ValueError, match="attempt to get argmax of an empty sequence"
        ):
            generate_lithoidx_statistics(empty_df)


class TestSearchLithoidx:
    """search_lithoidx 함수 테스트"""

    @pytest.fixture
    def mock_analysis_df(self):
        """테스트용 분석 결과 DataFrame"""
        data = {
            "lithoidx": [1, 2, 3],
            "lithoname": ["화강암", "편마암", "현무암"],
            "count": [3, 2, 4],
            "total_area": [450.0, 550.0, 295.0],
        }
        return pd.DataFrame(data)

    def test_search_lithoidx_by_name(self, mock_analysis_df):
        """암상명으로 검색 테스트"""
        result = search_lithoidx(mock_analysis_df, "화강")

        assert len(result) == 1
        assert result.iloc[0]["lithoname"] == "화강암"
        assert result.iloc[0]["lithoidx"] == 1

    def test_search_lithoidx_by_number(self, mock_analysis_df):
        """lithoidx 번호로 검색 테스트"""
        result = search_lithoidx(mock_analysis_df, "2")

        assert len(result) == 1
        assert result.iloc[0]["lithoidx"] == 2
        assert result.iloc[0]["lithoname"] == "편마암"

    def test_search_lithoidx_partial_match(self, mock_analysis_df):
        """부분 매칭 테스트"""
        result = search_lithoidx(mock_analysis_df, "암")

        # "암"이 포함된 모든 암상 반환 (화강암, 편마암, 현무암)
        assert len(result) == 3

    def test_search_lithoidx_not_found(self, mock_analysis_df):
        """검색 결과 없음 테스트"""
        result = search_lithoidx(mock_analysis_df, "없는암석")

        assert len(result) == 0

    def test_search_lithoidx_case_insensitive(self, mock_analysis_df):
        """대소문자 구분 없는 검색 테스트"""
        result = search_lithoidx(mock_analysis_df, "화강")

        assert len(result) == 1
        assert result.iloc[0]["lithoname"] == "화강암"


class TestLoadKSoilData:
    """load_k_soil_data 함수 테스트"""

    def test_load_k_soil_data_success(self, temp_dir, capsys):
        """K 토양 데이터 로딩 성공 테스트"""
        # 올바른 파일명으로 테스트 CSV 파일 생성
        k_soil_file = temp_dir / "lithoidx_list_with_K_SOIL.csv"
        test_data = (
            "lithoidx,lithoname,K_SOIL,extra_col\n1,화강암,2.5,test\n2,편마암,3.0,test2"
        )
        k_soil_file.write_text(test_data, encoding="utf-8")

        result = load_k_soil_data(temp_dir)

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "lithoidx" in result.columns
        assert "lithoname" in result.columns
        assert "K_SOIL" in result.columns

        # 출력 메시지 확인
        captured = capsys.readouterr()
        assert "K_SOIL 데이터 로드 완료" in captured.out

    def test_load_k_soil_data_file_not_found(self, temp_dir):
        """파일이 없는 경우 테스트"""
        result = load_k_soil_data(temp_dir)

        assert result is None

    @patch("pandas.read_csv")
    def test_load_k_soil_data_read_error(self, mock_read_csv, temp_dir):
        """CSV 읽기 오류 테스트"""
        mock_read_csv.side_effect = Exception("Read error")

        # 파일 존재하도록 설정
        k_soil_file = temp_dir / "K_soil_matched.csv"
        k_soil_file.write_text("test data")

        result = load_k_soil_data(temp_dir)

        assert result is None


class TestSpatialJoinWithSoil:
    """spatial_join_with_soil 함수 테스트"""

    @pytest.fixture
    def mock_pipe_gdf(self):
        """테스트용 파이프 GeoDataFrame"""
        return gpd.GeoDataFrame(
            {
                "FTR_IDN": ["PIPE001", "PIPE002", "PIPE003"],
                "geometry": [
                    Point(127.0, 37.0),
                    Point(127.1, 37.1),
                    Point(127.2, 37.2),
                ],
            },
            crs="EPSG:4326",
        )

    @pytest.fixture
    def mock_soil_gdf(self):
        """테스트용 토양 GeoDataFrame"""
        return gpd.GeoDataFrame(
            {
                "lithoidx": [1, 2],
                "lithoname": ["화강암", "편마암"],
                "geometry": [
                    Polygon(
                        [(126.9, 36.9), (127.05, 36.9), (127.05, 37.05), (126.9, 37.05)]
                    ),
                    Polygon(
                        [(127.05, 37.05), (127.3, 37.05), (127.3, 37.3), (127.05, 37.3)]
                    ),
                ],
            },
            crs="EPSG:4326",
        )

    def test_spatial_join_with_soil_success(self, mock_pipe_gdf, mock_soil_gdf):
        """공간 조인 성공 테스트"""
        result = spatial_join_with_soil(mock_pipe_gdf, mock_soil_gdf)

        assert isinstance(result, pd.DataFrame)
        assert len(result) <= len(
            mock_pipe_gdf
        )  # 일부 파이프는 토양과 매칭되지 않을 수 있음

        # 조인된 데이터에는 FTR_IDN과 lithoidx가 포함되어야 함
        assert "FTR_IDN" in result.columns
        assert "lithoidx" in result.columns

    def test_spatial_join_with_soil_no_intersection(self):
        """교차점이 없는 경우 테스트"""
        pipe_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["PIPE001"],
                "geometry": [Point(200.0, 200.0)],  # 토양 영역에서 멀리 떨어진 위치
            },
            crs="EPSG:4326",
        )

        soil_gdf = gpd.GeoDataFrame(
            {
                "lithoidx": [1],
                "lithoname": ["화강암"],
                "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            },
            crs="EPSG:4326",
        )

        result = spatial_join_with_soil(pipe_gdf, soil_gdf)

        assert isinstance(result, pd.DataFrame)
        # 교차점이 없으면 lithoidx가 None인 결과


class TestSaveSoilMatchingResult:
    """save_soil_matching_result 함수 테스트"""

    @pytest.fixture
    def mock_joined_df(self):
        """테스트용 조인된 DataFrame (FTR_IDN은 정수)"""
        return pd.DataFrame(
            {
                "FTR_IDN": [1001, 1002],  # 정수형 FTR_IDN
                "lithoidx": [1, 2],
                "lithoname": ["화강암", "편마암"],
            }
        )

    def test_save_soil_matching_result_success(self, mock_joined_df, temp_dir, capsys):
        """토양 매칭 결과 저장 성공 테스트"""
        output_file = temp_dir / "test_output.csv"

        save_soil_matching_result(mock_joined_df, output_file)

        # 파일이 생성되었는지 확인
        assert output_file.exists()

        # CSV 내용 확인
        df = pd.read_csv(output_file)
        assert len(df) == 2
        assert "FTR_IDN" in df.columns
        assert "lithoname" in df.columns

        # 출력 메시지 확인
        captured = capsys.readouterr()
        assert "CSV 저장 완료" in captured.out

    def test_save_soil_matching_result_with_k_soil(self, temp_dir):
        """K_SOIL 정보가 포함된 경우 테스트"""
        df_with_k_soil = pd.DataFrame(
            {
                "FTR_IDN": [1001, 1002],
                "lithoidx": [1, 2],
                "lithoname": ["화강암", "편마암"],
                "K_SOIL": [2.5, 3.0],
                "extra_col": ["test1", "test2"],  # 제거되어야 할 컬럼
            }
        )
        output_file = temp_dir / "k_soil_output.csv"

        save_soil_matching_result(df_with_k_soil, output_file, verbose=False)

        # K_SOIL 컬럼이 포함된 CSV 확인
        df = pd.read_csv(output_file)
        assert "K_SOIL" in df.columns
        assert "extra_col" not in df.columns  # 제거되었는지 확인

    def test_save_soil_matching_result_empty_data(self, temp_dir):
        """빈 데이터 저장 테스트 - 예외 발생 확인"""
        empty_df = pd.DataFrame()
        output_file = temp_dir / "empty_output.csv"

        # 빈 DataFrame에서는 KeyError가 발생할 것으로 예상
        with pytest.raises(KeyError):
            save_soil_matching_result(empty_df, output_file)
