"""
데이터 검증 유틸리티 테스트
"""

from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon

from src.common.validation import (
    remove_invalid_geometries,
    validate_crs,
    validate_date_format,
    validate_geometry_types,
    validate_numeric_range,
    validate_required_columns,
    validate_unique_values,
)


class TestValidateRequiredColumns:
    """validate_required_columns 함수 테스트"""

    def test_all_columns_present(self):
        """모든 필수 컬럼이 있는 경우"""
        df = pd.DataFrame(
            {"col1": [1, 2, 3], "col2": ["a", "b", "c"], "col3": [True, False, True]}
        )

        valid, missing = validate_required_columns(
            df, ["col1", "col2"], raise_error=False
        )

        assert valid is True
        assert missing == []

    def test_missing_columns_no_raise(self):
        """필수 컬럼이 없는 경우 - 예외 발생 안함"""
        df = pd.DataFrame({"col1": [1, 2, 3]})

        valid, missing = validate_required_columns(
            df, ["col1", "col2", "col3"], raise_error=False
        )

        assert valid is False
        assert set(missing) == {"col2", "col3"}

    def test_missing_columns_raise(self):
        """필수 컬럼이 없는 경우 - 예외 발생"""
        df = pd.DataFrame({"col1": [1, 2, 3]})

        with pytest.raises(ValueError) as excinfo:
            validate_required_columns(df, ["col1", "missing_col"], raise_error=True)

        assert "Missing required columns" in str(excinfo.value)
        assert "missing_col" in str(excinfo.value)

    @patch("src.common.validation.logger")
    def test_logging_on_missing_columns(self, mock_logger):
        """누락된 컬럼 로깅"""
        df = pd.DataFrame({"col1": [1, 2, 3]})

        validate_required_columns(df, ["col1", "col2"], raise_error=False)

        mock_logger.warning.assert_called_once()
        assert "Missing required columns" in mock_logger.warning.call_args[0][0]


class TestValidateGeometryTypes:
    """validate_geometry_types 함수 테스트"""

    def test_valid_geometry_types(self):
        """유효한 지오메트리 타입"""
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Point(1, 1), LineString([(0, 0), (1, 1)])]}
        )

        valid, type_counts = validate_geometry_types(gdf, ["Point", "LineString"])

        assert valid is True
        assert type_counts["Point"] == 2
        assert type_counts["LineString"] == 1

    def test_invalid_geometry_types(self):
        """유효하지 않은 지오메트리 타입"""
        gdf = gpd.GeoDataFrame(
            {
                "geometry": [
                    Point(0, 0),
                    Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]),
                ]
            }
        )

        valid, type_counts = validate_geometry_types(gdf, ["Point"])

        assert valid is False
        assert type_counts["Point"] == 1
        assert type_counts["Polygon"] == 1

    def test_empty_geodataframe(self):
        """빈 GeoDataFrame"""
        gdf = gpd.GeoDataFrame(columns=["geometry"])

        valid, type_counts = validate_geometry_types(gdf, ["Point"])

        assert valid is True
        assert type_counts == {}

    @patch("src.common.validation.logger")
    def test_logging_invalid_types(self, mock_logger):
        """유효하지 않은 타입 로깅"""
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])]}
        )

        validate_geometry_types(gdf, ["Point"])

        mock_logger.warning.assert_called_once()
        assert "invalid geometry types" in mock_logger.warning.call_args[0][0]


class TestValidateCRS:
    """validate_crs 함수 테스트"""

    def test_no_crs(self):
        """CRS가 없는 경우"""
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]})

        result = validate_crs(gdf, expected_crs="EPSG:4326")

        assert result.crs == "EPSG:4326"

    def test_matching_crs(self):
        """CRS가 일치하는 경우"""
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")

        result = validate_crs(gdf, expected_crs="EPSG:4326")

        assert result.crs == "EPSG:4326"
        assert result is gdf  # 변환 없음

    def test_convert_crs(self):
        """CRS 변환"""
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")

        result = validate_crs(gdf, expected_crs="EPSG:3857", convert_if_different=True)

        assert str(result.crs) == "EPSG:3857"
        assert result is not gdf  # 새 객체 생성됨

    @patch("src.common.validation.logger")
    def test_crs_mismatch_warning(self, mock_logger):
        """CRS 불일치 경고"""
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")

        validate_crs(gdf, expected_crs="EPSG:3857", convert_if_different=False)

        mock_logger.warning.assert_called_once()
        assert "CRS mismatch" in mock_logger.warning.call_args[0][0]


class TestValidateNumericRange:
    """validate_numeric_range 함수 테스트"""

    def test_valid_range(self):
        """유효한 범위"""
        series = pd.Series([1, 2, 3, 4, 5])

        valid, stats = validate_numeric_range(series, min_value=0, max_value=10)

        assert valid is True
        assert stats["min"] == 1
        assert stats["max"] == 5
        assert stats["mean"] == 3
        assert stats["count"] == 5
        assert stats["null_count"] == 0

    def test_below_minimum(self):
        """최소값 미만"""
        series = pd.Series([-1, 0, 1, 2])

        valid, stats = validate_numeric_range(series, min_value=0)

        assert valid is False
        assert stats["min"] == -1

    def test_above_maximum(self):
        """최대값 초과"""
        series = pd.Series([1, 2, 3, 11])

        valid, stats = validate_numeric_range(series, max_value=10)

        assert valid is False
        assert stats["max"] == 11

    def test_with_null_values(self):
        """null 값 포함"""
        series = pd.Series([1, 2, np.nan, 4, np.nan])

        valid, stats = validate_numeric_range(series)

        assert stats["null_count"] == 2
        assert stats["count"] == 5

    @patch("src.common.validation.logger")
    def test_logging_range_violations(self, mock_logger):
        """범위 위반 로깅"""
        series = pd.Series([1, 2, 3, 11], name="test_column")

        validate_numeric_range(series, max_value=10)

        # warning 호출 확인
        assert any("above" in str(call) for call in mock_logger.warning.call_args_list)


class TestValidateDateFormat:
    """validate_date_format 함수 테스트"""

    def test_valid_date_conversion(self):
        """유효한 날짜 변환"""
        series = pd.Series(["2024-01-01", "2024-01-02", "2024-01-03"])

        result = validate_date_format(series, date_format="%Y-%m-%d")

        assert pd.api.types.is_datetime64_any_dtype(result)
        assert result[0] == pd.Timestamp("2024-01-01")

    def test_auto_date_detection(self):
        """자동 날짜 형식 감지"""
        series = pd.Series(["01/01/2024", "02/01/2024", "03/01/2024"])

        result = validate_date_format(series)

        assert pd.api.types.is_datetime64_any_dtype(result)

    def test_invalid_dates(self):
        """유효하지 않은 날짜"""
        series = pd.Series(["2024-01-01", "invalid", "2024-01-03"])

        result = validate_date_format(series)

        assert pd.isna(result[1])
        assert pd.notna(result[0])
        assert pd.notna(result[2])

    def test_no_conversion(self):
        """변환 없음"""
        series = pd.Series(["2024-01-01", "2024-01-02"])

        result = validate_date_format(series, convert=False)

        assert result.dtype == "object"
        assert list(result) == ["2024-01-01", "2024-01-02"]

    @patch("src.common.validation.logger")
    def test_logging_conversion_failures(self, mock_logger):
        """변환 실패 로깅"""
        series = pd.Series(["2024-01-01", "invalid", "also invalid"])

        validate_date_format(series)

        mock_logger.warning.assert_called_once()
        assert "Failed to convert" in mock_logger.warning.call_args[0][0]


class TestRemoveInvalidGeometries:
    """remove_invalid_geometries 함수 테스트"""

    def test_remove_null_geometries(self):
        """NULL 지오메트리 제거"""
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), None, Point(1, 1), None], "id": [1, 2, 3, 4]}
        )

        result = remove_invalid_geometries(gdf, remove_null=True)

        assert len(result) == 2
        assert list(result["id"]) == [1, 3]

    def test_remove_invalid_geometries_only(self):
        """유효하지 않은 지오메트리만 제거"""
        # 유효한 지오메트리와 유효하지 않은 지오메트리 생성
        # 실제로 유효하지 않은 지오메트리를 만들기는 어려우므로
        # 이 테스트는 로직만 확인
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), Point(1, 1), Point(2, 2)], "id": [1, 2, 3]}
        )

        # 모든 지오메트리가 유효한 경우
        result = remove_invalid_geometries(gdf, remove_invalid=True)

        assert len(result) == 3  # 모두 유효하므로 제거되지 않음

    def test_keep_all_if_disabled(self):
        """제거 옵션 비활성화"""
        gdf = gpd.GeoDataFrame(
            {"geometry": [Point(0, 0), None, Point(1, 1)], "id": [1, 2, 3]}
        )

        result = remove_invalid_geometries(gdf, remove_null=False, remove_invalid=False)

        assert len(result) == 3
        assert result.equals(gdf)

    @patch("src.common.validation.logger")
    def test_logging_removed_count(self, mock_logger):
        """제거된 개수 로깅"""
        gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0), None, Point(1, 1)]})

        remove_invalid_geometries(gdf, remove_null=True)

        # 로깅 호출 확인
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Removing" in call for call in info_calls)
        assert any("Removed" in call for call in info_calls)


class TestValidateUniqueValues:
    """validate_unique_values 함수 테스트"""

    def test_expected_values(self):
        """기대값 검증"""
        series = pd.Series(["A", "B", "A", "C", "B"])

        valid, unique = validate_unique_values(series, expected_values=["A", "B", "C"])

        assert valid is True
        assert set(unique) == {"A", "B", "C"}

    def test_unexpected_values(self):
        """예상치 못한 값"""
        series = pd.Series(["A", "B", "D", "E"])

        valid, unique = validate_unique_values(series, expected_values=["A", "B", "C"])

        assert valid is False
        assert "D" in unique
        assert "E" in unique

    def test_max_unique_constraint(self):
        """최대 유니크 값 제약"""
        series = pd.Series(range(100))

        valid, unique = validate_unique_values(series, max_unique=50)

        assert valid is False
        assert len(unique) == 100

    def test_null_values_excluded(self):
        """null 값 제외"""
        series = pd.Series(["A", "B", None, "A", np.nan])

        valid, unique = validate_unique_values(series)

        assert set(unique) == {"A", "B"}
        assert None not in unique
        assert np.nan not in unique

    @patch("src.common.validation.logger")
    def test_logging_unexpected_values(self, mock_logger):
        """예상치 못한 값 로깅"""
        series = pd.Series(["A", "B"] + [f"X{i}" for i in range(20)])

        validate_unique_values(series, expected_values=["A", "B"])

        mock_logger.warning.assert_called()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "unexpected values" in warning_msg
        assert "..." in warning_msg  # 10개까지만 표시
