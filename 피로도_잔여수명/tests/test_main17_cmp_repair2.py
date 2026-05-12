"""
main17_cmp_repair2.py 테스트 코드
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main17_cmp_repair2 import (
    CNT_JNT_COLORS,
    PIPE_ALPHA,
    PIPE_LM_WIDTH,
    RECOVERY_COLORS,
    RECOVERY_POINT_ALPHA,
    RECOVERY_POINT_SIZE,
    SPLY_LS_WIDTH,
    get_cnt_jnt_color,
    load_pipe_joint_shapefiles,
    load_repair_csv_files,
    visualize_pipes_and_repair,
)


class TestConstants:
    """상수 정의 테스트"""

    def test_cnt_jnt_colors(self):
        """CNT_JNT 색상 정의 확인"""
        assert len(CNT_JNT_COLORS) == 7
        assert CNT_JNT_COLORS[0] == "#0066CC"  # 파란색
        assert CNT_JNT_COLORS[1] == "#00AA00"  # 초록색
        assert CNT_JNT_COLORS[2] == "#FFD700"  # 노란색
        assert CNT_JNT_COLORS[3] == "#FF8C00"  # 주황색
        assert CNT_JNT_COLORS[4] == "#FF0000"  # 빨간색
        assert CNT_JNT_COLORS[5] == "#800080"  # 보라색
        assert CNT_JNT_COLORS[6] == "#000000"  # 검은색

    def test_repair_colors(self):
        """복구 작업 색상 정의 확인"""
        assert len(RECOVERY_COLORS) == 4
        assert "지상누수" in RECOVERY_COLORS
        assert "지하누수" in RECOVERY_COLORS
        assert "긴급공사" in RECOVERY_COLORS
        assert "관리대장" in RECOVERY_COLORS

    def test_visualization_constants(self):
        """시각화 상수 확인"""
        assert PIPE_LM_WIDTH == 1.5
        assert SPLY_LS_WIDTH == 0.5
        assert PIPE_ALPHA == 0.7
        assert RECOVERY_POINT_SIZE == 30
        assert RECOVERY_POINT_ALPHA == 0.6


class TestGetCntJntColor:
    """CNT_JNT 색상 반환 함수 테스트"""

    def test_valid_cnt_values(self):
        """유효한 CNT_JNT 값에 대한 색상 반환"""
        assert get_cnt_jnt_color(0) == "#0066CC"
        assert get_cnt_jnt_color(1) == "#00AA00"
        assert get_cnt_jnt_color(2) == "#FFD700"
        assert get_cnt_jnt_color(3) == "#FF8C00"
        assert get_cnt_jnt_color(4) == "#FF0000"
        assert get_cnt_jnt_color(5) == "#800080"

    def test_high_cnt_values(self):
        """6 이상 CNT_JNT 값에 대한 색상 반환"""
        assert get_cnt_jnt_color(6) == "#000000"
        assert get_cnt_jnt_color(7) == "#000000"
        assert get_cnt_jnt_color(10) == "#000000"
        assert get_cnt_jnt_color(100) == "#000000"

    def test_negative_cnt_values(self):
        """음수 CNT_JNT 값에 대한 기본 색상 반환"""
        assert get_cnt_jnt_color(-1) == "#000000"  # 기본값은 검은색


class TestLoadPipeJointShapefiles:
    """파이프 Joint shapefile 로드 테스트"""

    def test_load_both_shapefiles(self, tmp_path):
        """PIPE_LM과 SPLY_LS 모두 로드"""
        # 테스트용 디렉토리 구조 생성
        shp_dir = tmp_path / "main15_extract_joint_data" / "shapefiles"
        shp_dir.mkdir(parents=True)

        # 테스트용 GeoDataFrame 생성
        pipe_lm_data = {"geometry": [LineString([(0, 0), (1, 1)])], "CNT_JNT": [2]}
        pipe_lm_gdf = gpd.GeoDataFrame(pipe_lm_data, crs="EPSG:5179")

        sply_ls_data = {"geometry": [LineString([(1, 1), (2, 2)])], "CNT_JNT": [3]}
        sply_ls_gdf = gpd.GeoDataFrame(sply_ls_data, crs="EPSG:5179")

        # Shapefile 저장
        pipe_lm_gdf.to_file(shp_dir / "PIPE_LM_JOINT.shp")
        sply_ls_gdf.to_file(shp_dir / "SPLY_LS_JOINT.shp")

        # 로드 테스트
        result = load_pipe_joint_shapefiles(tmp_path, verbose=False)

        assert result is not None
        assert len(result) == 2
        assert "PIPE_TYPE" in result.columns
        assert set(result["PIPE_TYPE"]) == {"PIPE_LM", "SPLY_LS"}

    def test_load_missing_files(self, tmp_path):
        """파일이 없을 때 처리"""
        result = load_pipe_joint_shapefiles(tmp_path, verbose=False)
        assert result is None

    def test_load_only_pipe_lm(self, tmp_path):
        """PIPE_LM만 있을 때"""
        shp_dir = tmp_path / "main15_extract_joint_data" / "shapefiles"
        shp_dir.mkdir(parents=True)

        pipe_lm_data = {"geometry": [LineString([(0, 0), (1, 1)])], "CNT_JNT": [1]}
        pipe_lm_gdf = gpd.GeoDataFrame(pipe_lm_data, crs="EPSG:5179")
        pipe_lm_gdf.to_file(shp_dir / "PIPE_LM_JOINT.shp")

        result = load_pipe_joint_shapefiles(tmp_path, verbose=False)

        assert result is not None
        assert len(result) == 1
        assert result["PIPE_TYPE"].iloc[0] == "PIPE_LM"


class TestLoadRepairCSVFiles:
    """복구 작업 CSV 파일 로드 테스트"""

    def test_load_all_repair_types(self, tmp_path):
        """모든 복구 타입 로드"""
        # 통합 CSV 파일 생성
        unified_csv = tmp_path / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
        unified_csv.parent.mkdir(parents=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7, 37.8, 37.9, 38.0, 38.1, 38.2],
                "경도": [126.9, 127.0, 126.8, 127.1, 126.9, 127.0, 126.8, 127.1],
                "파일타입": [
                    "지상누수",
                    "지상누수",
                    "지하누수",
                    "지하누수",
                    "긴급공사",
                    "긴급공사",
                    "관리대장",
                    "관리대장",
                ],
                "기타컬럼": [
                    "데이터1",
                    "데이터2",
                    "데이터3",
                    "데이터4",
                    "데이터5",
                    "데이터6",
                    "데이터7",
                    "데이터8",
                ],
            }
        )
        df.to_csv(unified_csv, index=False, encoding="utf-8-sig")

        # 전체 로드
        with patch("src.main17_cmp_repair2.UNIFIED_REPAIR_CSV", unified_csv):
            result = load_repair_csv_files(tmp_path, repair_type=None, verbose=False)

        assert result is not None
        assert len(result) == 8  # 각 타입별 2개씩, 총 8개
        assert "복구타입" in result.columns
        assert set(result["복구타입"]) == {
            "지상누수",
            "지하누수",
            "긴급공사",
            "관리대장",
        }

    def test_load_specific_repair_type(self, tmp_path):
        """특정 복구 타입만 로드"""
        # 통합 CSV 파일 생성
        unified_csv = tmp_path / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
        unified_csv.parent.mkdir(parents=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7],
                "경도": [126.9, 127.0, 126.8],
                "파일타입": ["지상누수", "지하누수", "긴급공사"],
            }
        )
        df.to_csv(unified_csv, index=False, encoding="utf-8-sig")

        with patch("src.main17_cmp_repair2.UNIFIED_REPAIR_CSV", unified_csv):
            result = load_repair_csv_files(
                tmp_path, repair_type="지상누수", verbose=False
            )

        assert result is not None
        assert len(result) == 1
        assert result["복구타입"].iloc[0] == "지상누수"

    def test_filter_invalid_coordinates(self, tmp_path):
        """유효하지 않은 좌표 필터링"""
        # 통합 CSV 파일 생성
        unified_csv = tmp_path / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
        unified_csv.parent.mkdir(parents=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, None, -1, 37.6],  # None과 음수는 필터링됨
                "경도": [126.9, 127.0, 127.0, None],  # None은 필터링됨
                "파일타입": ["지상누수", "지하누수", "긴급공사", "관리대장"],
            }
        )
        df.to_csv(unified_csv, index=False, encoding="utf-8-sig")

        with patch("src.main17_cmp_repair2.UNIFIED_REPAIR_CSV", unified_csv):
            result = load_repair_csv_files(
                tmp_path, repair_type="지상누수", verbose=False
            )

        assert result is not None
        assert len(result) == 1  # 첫 번째 행만 유효

    def test_no_repair_files(self, tmp_path):
        """복구 파일이 없을 때"""
        # Mock을 사용해서 파일이 없는 상황 시뮬레이션
        non_existent_path = (
            tmp_path / "main13_crop_520" / "누수공사_통합_520_위치추가.csv"
        )
        with patch("src.main17_cmp_repair2.UNIFIED_REPAIR_CSV", non_existent_path):
            result = load_repair_csv_files(tmp_path, verbose=False)
            assert result is None


class TestVisualizePipesAndRepair:
    """시각화 함수 테스트"""

    @patch("src.main17_cmp_repair2.plt.savefig")
    @patch("src.main17_cmp_repair2.plt.close")
    @patch("src.main17_cmp_repair2.setup_plot_style")
    def test_visualize_with_pipes_only(
        self, mock_setup, mock_close, mock_savefig, tmp_path
    ):
        """파이프만 있는 경우 시각화"""
        # Mock 설정
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_setup.return_value = (mock_fig, mock_ax)

        # 테스트 데이터
        pipe_data = {
            "geometry": [LineString([(0, 0), (1, 1)]), LineString([(1, 1), (2, 2)])],
            "CNT_JNT": [0, 3],
            "PIPE_TYPE": ["PIPE_LM", "SPLY_LS"],
        }
        pipe_gdf = gpd.GeoDataFrame(pipe_data, crs="EPSG:5179")

        output_path = tmp_path / "test_output.png"

        # 시각화 실행
        visualize_pipes_and_repair(
            pipe_gdf, None, "Test Title", output_path, verbose=False  # 복구 데이터 없음
        )

        # 검증
        mock_setup.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()
        mock_ax.add_collection.assert_called()  # LineCollection이 추가되었는지 확인

    @patch("src.main17_cmp_repair2.plt.savefig")
    @patch("src.main17_cmp_repair2.plt.close")
    @patch("src.main17_cmp_repair2.setup_plot_style")
    def test_visualize_with_pipes_and_repair(
        self, mock_setup, mock_close, mock_savefig, tmp_path
    ):
        """파이프와 복구 데이터 모두 있는 경우"""
        # Mock 설정
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_setup.return_value = (mock_fig, mock_ax)

        # 파이프 데이터
        pipe_data = {
            "geometry": [LineString([(198000, 197000), (199000, 198000)])],
            "CNT_JNT": [2],
            "PIPE_TYPE": ["PIPE_LM"],
        }
        pipe_gdf = gpd.GeoDataFrame(pipe_data, crs="EPSG:5179")

        # 복구 데이터
        repair_df = pd.DataFrame(
            {"위도": [37.5], "경도": [126.9], "복구타입": ["지상누수"]}
        )

        output_path = tmp_path / "test_output.png"

        # 시각화 실행
        visualize_pipes_and_repair(
            pipe_gdf, repair_df, "Test Title", output_path, verbose=False
        )

        # 검증
        mock_setup.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()
        mock_ax.scatter.assert_called()  # 복구 점이 그려졌는지 확인

    @patch("src.main17_cmp_repair2.plt.savefig")
    @patch("src.main17_cmp_repair2.plt.close")
    @patch("src.main17_cmp_repair2.setup_plot_style")
    def test_visualize_different_pipe_types(
        self, mock_setup, mock_close, mock_savefig, tmp_path
    ):
        """다른 파이프 타입의 선 두께 확인"""
        # Mock 설정
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_setup.return_value = (mock_fig, mock_ax)

        # 파이프 데이터 (PIPE_LM과 SPLY_LS)
        pipe_data = {
            "geometry": [LineString([(0, 0), (1, 1)]), LineString([(1, 1), (2, 2)])],
            "CNT_JNT": [1, 1],
            "PIPE_TYPE": ["PIPE_LM", "SPLY_LS"],
        }
        pipe_gdf = gpd.GeoDataFrame(pipe_data, crs="EPSG:5179")

        output_path = tmp_path / "test_output.png"

        # 시각화 실행
        visualize_pipes_and_repair(
            pipe_gdf, None, "Test Title", output_path, verbose=False
        )

        # LineCollection 호출 확인
        assert mock_ax.add_collection.call_count == 2  # PIPE_LM과 SPLY_LS 각각


class TestIntegration:
    """통합 테스트"""

    @patch("src.main17_cmp_repair2.plt.savefig")
    @patch("src.main17_cmp_repair2.plt.close")
    @patch("src.main17_cmp_repair2.setup_plot_style")
    def test_full_workflow(self, mock_setup, mock_close, mock_savefig, tmp_path):
        """전체 워크플로우 테스트"""
        # Mock 설정
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_setup.return_value = (mock_fig, mock_ax)

        # 디렉토리 구조 생성
        shp_dir = tmp_path / "main15_extract_joint_data" / "shapefiles"
        shp_dir.mkdir(parents=True)

        # Shapefile 생성
        pipe_data = {
            "geometry": [
                LineString([(198000, 197000), (199000, 198000)]),
                LineString([(199000, 198000), (200000, 199000)]),
            ],
            "CNT_JNT": [0, 5],
        }
        pipe_gdf = gpd.GeoDataFrame(pipe_data, crs="EPSG:5179")
        pipe_gdf.to_file(shp_dir / "PIPE_LM_JOINT.shp")

        # 통합 CSV 파일 생성
        unified_csv_dir = tmp_path / "main13_crop_520"
        unified_csv_dir.mkdir(parents=True)
        unified_csv = unified_csv_dir / "누수공사_통합_520_위치추가.csv"

        repair_df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [126.9, 127.0],
                "파일타입": ["지상누수", "지상누수"],
            }
        )
        repair_df.to_csv(unified_csv, index=False, encoding="utf-8-sig")

        # 데이터 로드
        pipes = load_pipe_joint_shapefiles(tmp_path, verbose=False)

        # UNIFIED_REPAIR_CSV 패치
        with patch("src.main17_cmp_repair2.UNIFIED_REPAIR_CSV", unified_csv):
            repair = load_repair_csv_files(
                tmp_path, repair_type="지상누수", verbose=False
            )

        assert pipes is not None
        assert repair is not None

        # 시각화
        output_path = tmp_path / "test_output.png"
        visualize_pipes_and_repair(
            pipes, repair, "Integration Test", output_path, verbose=False
        )

        # 검증
        mock_savefig.assert_called_once_with(output_path, dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
