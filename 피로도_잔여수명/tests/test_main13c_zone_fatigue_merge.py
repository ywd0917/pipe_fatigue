#!/usr/bin/env python3
"""
test_main13c_zone_fatigue_merge.py

main13c_zone_fatigue_merge.py의 테스트 코드
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Polygon

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main13c_zone_fatigue_merge import (
    determine_zone,
    filter_zone_columns,
    load_fatigue_csv,
    load_pipe_shapefile,
    load_zone_boundaries,
    merge_fatigue_and_shapefile,
)


class TestLoadFatigueCSV:
    """피로 손상 CSV 로드 테스트"""

    @patch("src.main13c_zone_fatigue_merge.pd.read_csv")
    def test_load_fatigue_csv_success(self, mock_read_csv):
        """정상적인 CSV 로드"""
        mock_df = pd.DataFrame(
            {
                "FTR_IDN": ["P001", "P002"],
                "0470_D_final": [0.1, 0.2],
                "0480_D_final": [0.3, 0.4],
            }
        )
        mock_read_csv.return_value = mock_df

        result = load_fatigue_csv(Path("test.csv"), "PIPE_LM")

        assert len(result) == 2
        assert "FTR_IDN" in result.columns
        mock_read_csv.assert_called_once_with(Path("test.csv"), encoding="utf-8-sig")

    @patch("src.main13c_zone_fatigue_merge.pd.read_csv")
    def test_load_fatigue_csv_failure(self, mock_read_csv):
        """CSV 로드 실패"""
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        with pytest.raises(FileNotFoundError):
            load_fatigue_csv(Path("nonexistent.csv"), "PIPE_LM")


class TestLoadPipeShapefile:
    """파이프 Shapefile 로드 테스트"""

    @patch("src.main13c_zone_fatigue_merge.gpd.read_file")
    def test_load_pipe_shapefile_success(self, mock_read_file):
        """정상적인 Shapefile 로드"""
        mock_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["P001", "P002"],
                "geometry": [
                    LineString([(0, 0), (1, 1)]),
                    LineString([(1, 1), (2, 2)]),
                ],
            },
            crs="EPSG:5179",
        )
        mock_read_file.return_value = mock_gdf

        result = load_pipe_shapefile(Path("test.shp"), "PIPE_LM")

        assert len(result) == 2
        assert "FTR_IDN" in result.columns
        assert result.crs == "EPSG:5179"

    @patch("src.main13c_zone_fatigue_merge.gpd.read_file")
    def test_load_pipe_shapefile_with_crs_conversion(self, mock_read_file):
        """다른 CRS에서 변환"""
        mock_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["P001"],
                "geometry": [LineString([(126.9, 37.5), (127.0, 37.6)])],
            },
            crs="EPSG:4326",
        )

        # to_crs 메서드 모킹
        mock_gdf_converted = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["P001"],
                "geometry": [LineString([(960000, 1940000), (961000, 1941000)])],
            },
            crs="EPSG:5179",
        )
        mock_gdf.to_crs = MagicMock(return_value=mock_gdf_converted)

        mock_read_file.return_value = mock_gdf

        result = load_pipe_shapefile(Path("test.shp"), "PIPE_LM")

        assert result.crs == "EPSG:5179"
        mock_gdf.to_crs.assert_called_once_with("EPSG:5179")


class TestLoadZoneBoundaries:
    """구역 경계 로드 테스트"""

    @patch("src.main13c_zone_fatigue_merge.Path.exists")
    @patch("src.main13c_zone_fatigue_merge.gpd.read_file")
    def test_load_zone_boundaries_all(self, mock_read_file, mock_exists):
        """모든 구역 경계 로드"""
        mock_exists.return_value = True

        # SMLZ 데이터
        smlz_gdf = gpd.GeoDataFrame(
            {
                "SMZ_NUM": ["0243", "0461", "0470", "0480", "0490"],
                "geometry": [
                    Polygon([(-2, -1), (-1, -1), (-1, 0), (-2, 0)]),
                    Polygon([(-1, -1), (0, -1), (0, 0), (-1, 0)]),
                    Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                    Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                    Polygon([(2, 0), (3, 0), (3, 1), (2, 1)]),
                ],
            },
            crs="EPSG:5179",
        )

        # MDLZ 데이터
        mdlz_gdf = gpd.GeoDataFrame(
            {"geometry": [Polygon([(0, 0), (3, 0), (3, 2), (0, 2)])]}, crs="EPSG:5179"
        )

        mock_read_file.side_effect = [smlz_gdf, mdlz_gdf]

        result = load_zone_boundaries(Path("test_dir"))

        assert "0243" in result
        assert "0461" in result
        assert "0470" in result
        assert "0480" in result
        assert "0490" in result
        assert "0520" in result
        assert len(result) == 6

    @patch("src.main13c_zone_fatigue_merge.Path.exists")
    def test_load_zone_boundaries_no_files(self, mock_exists):
        """경계 파일이 없는 경우"""
        mock_exists.return_value = False

        result = load_zone_boundaries(Path("test_dir"))

        assert result == {}


class TestDetermineZone:
    """구역 판별 테스트"""

    def test_determine_zone_subregion(self):
        """소구역 판별 - 0470"""
        # 파이프 geometry
        pipe_line = LineString([(0.5, 0.5), (0.6, 0.6)])

        # 구역 경계
        boundaries = {
            "0243": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-2, -1), (-1, -1), (-1, 0), (-2, 0)])]}
            ),
            "0461": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-1, -1), (0, -1), (0, 0), (-1, 0)])]}
            ),
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            ),
            "0520": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (3, 0), (3, 2), (0, 2)])]}
            ),
        }

        zone = determine_zone(pipe_line, boundaries)
        assert zone == "0470"

    def test_determine_zone_0243(self):
        """소구역 판별 - 0243"""
        # 파이프 geometry
        pipe_line = LineString([(-1.5, -0.5), (-1.4, -0.4)])

        # 구역 경계
        boundaries = {
            "0243": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-2, -1), (-1, -1), (-1, 0), (-2, 0)])]}
            ),
            "0461": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-1, -1), (0, -1), (0, 0), (-1, 0)])]}
            ),
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            ),
        }

        zone = determine_zone(pipe_line, boundaries)
        assert zone == "0243"

    def test_determine_zone_0461(self):
        """소구역 판별 - 0461"""
        # 파이프 geometry
        pipe_line = LineString([(-0.5, -0.5), (-0.4, -0.4)])

        # 구역 경계
        boundaries = {
            "0243": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-2, -1), (-1, -1), (-1, 0), (-2, 0)])]}
            ),
            "0461": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-1, -1), (0, -1), (0, 0), (-1, 0)])]}
            ),
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            ),
        }

        zone = determine_zone(pipe_line, boundaries)
        assert zone == "0461"

    def test_determine_zone_main_region(self):
        """중구역 판별"""
        # 파이프 geometry (소구역 밖, 중구역 안)
        pipe_line = LineString([(2.5, 1.5), (2.6, 1.6)])

        boundaries = {
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            ),
            "0520": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (3, 0), (3, 2), (0, 2)])]}
            ),
        }

        zone = determine_zone(pipe_line, boundaries)
        assert zone == "0520"

    def test_determine_zone_unknown(self):
        """어느 구역에도 속하지 않는 경우"""
        pipe_line = LineString([(10, 10), (11, 11)])

        boundaries = {
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            )
        }

        zone = determine_zone(pipe_line, boundaries)
        assert zone == "UNKNOWN"


class TestMergeFatigueAndShapefile:
    """피로 손상 데이터와 Shapefile 병합 테스트"""

    def test_merge_and_zone_determination(self):
        """병합 및 구역 판별"""
        # 피로 손상 데이터
        fatigue_df = pd.DataFrame(
            {
                "FTR_IDN": ["P001", "P002"],
                "0243_D_final": [0.05, 0.15],
                "0461_D_final": [0.06, 0.16],
                "0470_D_final": [0.1, 0.2],
                "0480_D_final": [0.3, 0.4],
                "0490_D_final": [0.5, 0.6],
            }
        )

        # 파이프 GeoDataFrame
        pipe_gdf = gpd.GeoDataFrame(
            {
                "FTR_IDN": ["P001", "P002", "P003"],
                "geometry": [
                    LineString([(0.5, 0.5), (0.6, 0.6)]),
                    LineString([(1.5, 0.5), (1.6, 0.6)]),
                    LineString([(2.5, 0.5), (2.6, 0.6)]),
                ],
            }
        )

        # 구역 경계
        boundaries = {
            "0243": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-2, -1), (-1, -1), (-1, 0), (-2, 0)])]}
            ),
            "0461": gpd.GeoDataFrame(
                {"geometry": [Polygon([(-1, -1), (0, -1), (0, 0), (-1, 0)])]}
            ),
            "0470": gpd.GeoDataFrame(
                {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]}
            ),
            "0480": gpd.GeoDataFrame(
                {"geometry": [Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])]}
            ),
            "0490": gpd.GeoDataFrame(
                {"geometry": [Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])]}
            ),
        }

        result = merge_fatigue_and_shapefile(
            fatigue_df, pipe_gdf, boundaries, "PIPE_LM"
        )

        assert len(result) == 2  # P001, P002만 매칭
        assert "zone" in result.columns
        assert "DATA_SRC" in result.columns
        assert result["DATA_SRC"].iloc[0] == "PIPE_LM"
        assert result["zone"].iloc[0] == "0470"  # P001은 0470 구역
        assert result["zone"].iloc[1] == "0480"  # P002는 0480 구역


class TestFilterZoneColumns:
    """구역별 컬럼 필터링 테스트"""

    def test_filter_zone_columns(self):
        """구역별 컬럼 필터링 및 prefix 제거"""
        df = pd.DataFrame(
            {
                "DATA_SRC": ["PIPE_LM", "PIPE_LM", "PIPE_LM", "PIPE_LM", "SPLY_LS"],
                "zone": ["0243", "0461", "0470", "0480", "0520"],
                "FTR_IDN": ["P001", "P002", "P003", "P004", "S001"],
                "0243_D_final": [0.1, 0.2, 0.3, 0.4, 0.5],
                "0243_remaining_life": [10, 20, 30, 40, 50],
                "0461_D_final": [0.15, 0.25, 0.35, 0.45, 0.55],
                "0461_remaining_life": [15, 25, 35, 45, 55],
                "0470_D_final": [0.2, 0.3, 0.4, 0.5, 0.6],
                "0470_remaining_life": [20, 30, 40, 50, 60],
                "0480_D_final": [0.3, 0.4, 0.5, 0.6, 0.7],
                "0480_remaining_life": [30, 40, 50, 60, 70],
                "0490_D_final": [0.4, 0.5, 0.6, 0.7, 0.8],
                "0490_remaining_life": [40, 50, 60, 70, 80],
                "0520_D_final": [0.5, 0.6, 0.7, 0.8, 0.9],
                "0520_remaining_life": [50, 60, 70, 80, 90],
            }
        )

        result = filter_zone_columns(df)

        # 기본 검증
        assert len(result) == 5
        assert result.columns[0] == "DATA_SRC"
        assert result.columns[1] == "zone"

        # 0243 행 확인
        row_0243 = result[result["zone"] == "0243"].iloc[0]
        assert "D_final" in result.columns  # prefix 제거됨
        assert "remaining_life" in result.columns
        assert row_0243["D_final"] == 0.1
        assert row_0243["remaining_life"] == 10

        # 0461 행 확인
        row_0461 = result[result["zone"] == "0461"].iloc[0]
        assert row_0461["D_final"] == 0.25
        assert row_0461["remaining_life"] == 25

        # 0470 행 확인
        row_0470 = result[result["zone"] == "0470"].iloc[0]
        assert row_0470["D_final"] == 0.4
        assert row_0470["remaining_life"] == 40

        # 0480 행 확인
        row_0480 = result[result["zone"] == "0480"].iloc[0]
        assert row_0480["D_final"] == 0.6
        assert row_0480["remaining_life"] == 60

        # 0520 행 확인
        row_0520 = result[result["zone"] == "0520"].iloc[0]
        assert row_0520["D_final"] == 0.9
        assert row_0520["remaining_life"] == 90

    def test_filter_zone_columns_with_unknown(self):
        """UNKNOWN 구역 처리"""
        df = pd.DataFrame(
            {
                "DATA_SRC": ["PIPE_LM"],
                "zone": ["UNKNOWN"],
                "FTR_IDN": ["P999"],
                "0243_D_final": [0.05],
                "0461_D_final": [0.06],
                "0470_D_final": [0.1],
                "0480_D_final": [0.2],
                "0490_D_final": [0.25],
            }
        )

        result = filter_zone_columns(df)

        assert len(result) == 1
        assert "D_final" not in result.columns  # zone 관련 컬럼 제외
        assert "FTR_IDN" in result.columns  # 기본 컬럼만 유지


class TestColumnOrder:
    """컬럼 순서 테스트"""

    def test_column_order_preserved(self):
        """DATA_SRC와 zone이 맨 앞, 나머지는 원본 순서 유지"""
        df = pd.DataFrame(
            {
                "FTR_IDN": ["P001"],
                "HJD_CDE": ["123"],
                "zone": ["0470"],
                "DATA_SRC": ["PIPE_LM"],
                "0470_D_final": [0.1],
            }
        )

        result = filter_zone_columns(df)

        columns = list(result.columns)
        assert columns[0] == "DATA_SRC"
        assert columns[1] == "zone"
        assert "FTR_IDN" in columns
        assert "HJD_CDE" in columns

    def test_met_idn_column_position(self):
        """MET_IDN 컬럼이 올바른 위치에 있는지 확인 (CLS_YMD 다음, GU_CDE 앞)"""
        df = pd.DataFrame(
            {
                "DATA_SRC": ["SPLY_LS", "PIPE_LM"],
                "zone": ["0470", "0470"],
                "FTR_IDN": ["S001", "P001"],
                "CLS_YMD": ["2023-01-01", None],
                "MET_IDN": ["12345", None],  # SPLY_LS에만 존재
                "GU_CDE": ["GU001", "GU002"],
                "K_total": [1.5, 1.6],
                "0470_D_final": [0.1, 0.2],
            }
        )

        result = filter_zone_columns(df)
        columns = list(result.columns)
        
        # MET_IDN이 존재하는지 확인
        assert "MET_IDN" in columns
        
        # MET_IDN의 위치 확인
        met_idn_idx = columns.index("MET_IDN")
        cls_ymd_idx = columns.index("CLS_YMD")
        gu_cde_idx = columns.index("GU_CDE")
        
        # MET_IDN이 CLS_YMD 다음, GU_CDE 앞에 있는지 확인
        assert cls_ymd_idx < met_idn_idx < gu_cde_idx, (
            f"MET_IDN position error: CLS_YMD({cls_ymd_idx}) < MET_IDN({met_idn_idx}) < GU_CDE({gu_cde_idx})"
        )
        
        # SPLY_LS 데이터에는 MET_IDN 값이 있고, PIPE_LM에는 NaN이어야 함
        sply_row = result[result["DATA_SRC"] == "SPLY_LS"].iloc[0]
        pipe_row = result[result["DATA_SRC"] == "PIPE_LM"].iloc[0]
        
        assert sply_row["MET_IDN"] == "12345"
        assert pd.isna(pipe_row["MET_IDN"]) or pipe_row["MET_IDN"] is None

    def test_zone_column_order_preserved(self):
        """zone 컬럼들이 원본 CSV 순서를 유지하는지 확인"""
        df = pd.DataFrame(
            {
                "DATA_SRC": ["SPLY_LS"],
                "zone": ["0470"],
                "FTR_IDN": ["S001"],
                "K_total": [1.5],
                # 원본 CSV의 zone 컬럼 순서대로 정의
                "0470_low_total_cycles": [1000],
                "0470_high_total_cycles": [2000],
                "0470_low_fatigue_damage": [0.1],
                "0470_high_fatigue_damage": [0.2],
                "0470_D_base": [0.01],
                "0470_D_final_org": [0.02],
                "0470_D_final": [0.03],
                "0470_remaining_life_years": [25],
            }
        )

        result = filter_zone_columns(df)
        columns = list(result.columns)
        
        # zone 컬럼들의 순서 확인 (prefix 제거된 상태)
        expected_zone_order = [
            "low_total_cycles",
            "high_total_cycles", 
            "low_fatigue_damage",
            "high_fatigue_damage",
            "D_base",
            "D_final_org",
            "D_final",
            "remaining_life_years"
        ]
        
        # K_total 다음부터 zone 컬럼들이 나타나야 함
        k_total_idx = columns.index("K_total")
        zone_columns_in_result = columns[k_total_idx + 1:]
        
        # zone 컬럼들이 예상 순서와 일치하는지 확인
        assert zone_columns_in_result == expected_zone_order, (
            f"Zone column order mismatch: expected {expected_zone_order}, got {zone_columns_in_result}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
