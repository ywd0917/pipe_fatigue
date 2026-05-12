#!/usr/bin/env python3
"""
test_visualization.py

main14_common/visualization.py 모듈에 대한 테스트 코드

Author: assistant
Date: 2025-01-27
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from typing import Any

import pandas as pd
import pytest
import numpy as np

# 프로젝트 루트 디렉토리를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.main14_common.visualization import plot_individual_repairs_with_clusters


class TestPlotIndividualRepairsWithClusters:
    """plot_individual_repairs_with_clusters 함수 테스트"""

    @pytest.fixture
    def mock_ax(self):
        """matplotlib axes 모의 객체"""
        ax = Mock()
        ax.scatter = Mock()
        ax.text = Mock()
        return ax

    @pytest.fixture
    def mock_convert_wgs84(self):
        """WGS84 변환 함수 모의 객체"""

        def converter(df):
            # 간단한 GeoDataFrame 모의 객체 생성
            mock_gdf = Mock()
            mock_gdf.__len__ = Mock(return_value=len(df))

            # geometry.x와 geometry.y 속성 설정
            geometry = Mock()
            geometry.x = pd.Series(
                df["경도"].values if "경도" in df.columns else [126.0] * len(df)
            )
            geometry.y = pd.Series(
                df["위도"].values if "위도" in df.columns else [37.0] * len(df)
            )
            mock_gdf.geometry = geometry

            return mock_gdf

        return converter

    @pytest.fixture
    def mock_cluster_function(self):
        """클러스터링 함수 모의 객체"""

        def cluster_func(gdf, cluster_distance=10.0):
            # 클러스터 DataFrame 생성
            clusters = pd.DataFrame(
                {
                    "x": [126.0, 126.01, 126.02],
                    "y": [37.0, 37.01, 37.02],
                    "repair_count": [1, 3, 5],
                }
            )
            return clusters

        return cluster_func

    @pytest.fixture
    def sample_repair_data(self):
        """샘플 재작업 데이터"""
        return {
            "지상누수": pd.DataFrame(
                {
                    "경도": [126.0, 126.001, 126.002],
                    "위도": [37.0, 37.001, 37.002],
                    "작업타입": ["지상누수"] * 3,
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "경도": [126.01, 126.011],
                    "위도": [37.01, 37.011],
                    "작업타입": ["지하누수"] * 2,
                }
            ),
        }

    @pytest.fixture
    def sample_all_repair_data(self):
        """모든 4가지 재작업 타입 데이터"""
        return {
            "지상누수": pd.DataFrame(
                {
                    "경도": [126.0, 126.001, 126.002],
                    "위도": [37.0, 37.001, 37.002],
                    "작업타입": ["지상누수"] * 3,
                }
            ),
            "지하누수": pd.DataFrame(
                {
                    "경도": [126.01, 126.011],
                    "위도": [37.01, 37.011],
                    "작업타입": ["지하누수"] * 2,
                }
            ),
            "긴급공사": pd.DataFrame(
                {
                    "경도": [126.02, 126.021],
                    "위도": [37.02, 37.021],
                    "작업타입": ["긴급공사"] * 2,
                }
            ),
            "관리대장": pd.DataFrame(
                {
                    "경도": [126.03],
                    "위도": [37.03],
                    "작업타입": ["관리대장"],
                }
            ),
        }

    def test_empty_repair_data(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function
    ):
        """빈 재작업 데이터 처리 테스트"""
        # Given: 빈 재작업 데이터
        repair_data = {}

        # When: 함수 호출
        legend_elements, cluster_count = plot_individual_repairs_with_clusters(
            mock_ax, repair_data, mock_convert_wgs84, mock_cluster_function
        )

        # Then: 빈 결과 반환
        assert legend_elements == []
        assert cluster_count == 0
        mock_ax.scatter.assert_not_called()
        mock_ax.text.assert_not_called()

    def test_single_repair_type(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function
    ):
        """단일 재작업 타입 처리 테스트"""
        # Given: 지상누수 데이터만 있는 경우
        repair_data = {
            "지상누수": pd.DataFrame(
                {
                    "경도": [126.0, 126.001],
                    "위도": [37.0, 37.001],
                    "작업타입": ["지상누수"] * 2,
                }
            )
        }

        # When: 함수 호출
        with patch(
            "src.common.config.REPAIR_COLORS", {"지상누수": ("blue", "지상누수")}
        ):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax, repair_data, mock_convert_wgs84, mock_cluster_function
            )

        # Then: scatter가 한 번 호출됨
        assert mock_ax.scatter.call_count == 1
        assert len(legend_elements) >= 1  # 최소 1개의 범례 요소
        assert cluster_count == 3  # 모의 클러스터 함수가 3개 반환

    def test_multiple_repair_types(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function, sample_repair_data
    ):
        """다중 재작업 타입 처리 테스트"""
        # Given: 여러 재작업 타입 데이터
        repair_colors = {
            "지상누수": ("#FF1493", "지상누수"),
            "지하누수": ("#0000FF", "지하누수"),
            "긴급공사": ("#FF8C00", "긴급공사"),
            "관리대장": ("#008000", "관리대장"),
        }

        # When: 함수 호출
        with patch("src.common.config.REPAIR_COLORS", repair_colors):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax, sample_repair_data, mock_convert_wgs84, mock_cluster_function
            )

        # Then: 각 타입별로 scatter 호출
        assert mock_ax.scatter.call_count == 2
        assert len(legend_elements) >= 2  # 각 타입별 범례 + 클러스터 정보

    def test_cluster_number_display(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function, sample_repair_data
    ):
        """클러스터 번호 표시 테스트"""
        # Given: 재작업 데이터와 클러스터링 결과
        repair_colors = {"지상누수": ("blue", "지상누수")}

        # When: 함수 호출
        with patch("src.common.config.REPAIR_COLORS", repair_colors):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax,
                {"지상누수": sample_repair_data["지상누수"]},
                mock_convert_wgs84,
                mock_cluster_function,
            )

        # Then: 2개 이상 클러스터에 대해 text 호출
        # mock_cluster_function이 repair_count [1, 3, 5] 반환
        # repair_count >= 2인 것은 2개 (3, 5)
        assert mock_ax.text.call_count == 2

        # 첫 번째 text 호출 검증 (repair_count=3)
        first_call = mock_ax.text.call_args_list[0]
        assert first_call[0][2] == "3"  # 표시되는 숫자
        assert "yellow" in str(first_call[1]["bbox"])  # 3개는 노란색 배경

        # 두 번째 text 호출 검증 (repair_count=5)
        second_call = mock_ax.text.call_args_list[1]
        assert second_call[0][2] == "5"  # 표시되는 숫자
        assert "orange" in str(second_call[1]["bbox"])  # 5개는 주황색 배경

    def test_cluster_color_by_count(self, mock_ax, mock_convert_wgs84):
        """클러스터 개수별 색상 테스트"""

        # Given: 다양한 개수의 클러스터
        def custom_cluster_func(gdf, cluster_distance=10.0):
            return pd.DataFrame(
                {
                    "x": [126.0, 126.01, 126.02, 126.03],
                    "y": [37.0, 37.01, 37.02, 37.03],
                    "repair_count": [2, 4, 6, 10],  # 각각 다른 색상 구간
                }
            )

        repair_data = {
            "지상누수": pd.DataFrame(
                {
                    "경도": [126.0] * 10,
                    "위도": [37.0] * 10,
                    "작업타입": ["지상누수"] * 10,
                }
            )
        }

        # When: 함수 호출
        with patch(
            "src.common.config.REPAIR_COLORS", {"지상누수": ("blue", "지상누수")}
        ):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax, repair_data, mock_convert_wgs84, custom_cluster_func
            )

        # Then: 각 개수별로 적절한 색상 설정
        text_calls = mock_ax.text.call_args_list
        assert len(text_calls) == 4  # repair_count >= 2인 클러스터 4개

        # 색상 검증
        colors = [call[1]["bbox"]["facecolor"] for call in text_calls]
        assert colors[0] == "yellow"  # 2개
        assert colors[1] == "orange"  # 4개
        assert colors[2] == "red"  # 6개
        assert colors[3] == "red"  # 10개

    def test_none_repair_type(self, mock_ax, mock_convert_wgs84, mock_cluster_function):
        """None 값이 포함된 재작업 데이터 처리 테스트"""
        # Given: None이 포함된 데이터
        repair_data = {
            "지상누수": pd.DataFrame({"경도": [126.0], "위도": [37.0]}),
            "지하누수": None,
            "기타": pd.DataFrame(),  # 빈 DataFrame
        }

        # When: 함수 호출
        with patch(
            "src.common.config.REPAIR_COLORS",
            {
                "지상누수": ("blue", "지상누수"),
                "지하누수": ("red", "지하누수"),
                "기타": ("green", "기타"),
            },
        ):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax, repair_data, mock_convert_wgs84, mock_cluster_function
            )

        # Then: None과 빈 DataFrame은 무시됨
        assert mock_ax.scatter.call_count == 1  # 지상누수만 처리됨

    def test_cluster_legend_info(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function, sample_repair_data
    ):
        """클러스터 정보가 범례에 추가되는지 테스트"""
        # Given: 재작업 데이터
        repair_colors = {"지상누수": ("blue", "지상누수")}

        # When: 함수 호출
        with patch("src.common.config.REPAIR_COLORS", repair_colors):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax,
                {"지상누수": sample_repair_data["지상누수"]},
                mock_convert_wgs84,
                mock_cluster_function,
            )

        # Then: 범례에 클러스터 정보 포함
        # 마지막 범례 요소는 클러스터 정보여야 함
        assert len(legend_elements) >= 2
        last_legend = legend_elements[-1]
        assert hasattr(last_legend, "get_label")
        # Mock 객체이므로 label 확인은 생략

    def test_all_four_repair_types(
        self, mock_ax, mock_convert_wgs84, mock_cluster_function, sample_all_repair_data
    ):
        """4가지 모든 재작업 타입 처리 테스트"""
        # Given: 4가지 재작업 타입 데이터
        repair_colors = {
            "지상누수": ("#FF1493", "지상누수"),
            "지하누수": ("#0000FF", "지하누수"),
            "긴급공사": ("#FF8C00", "긴급공사"),
            "관리대장": ("#008000", "관리대장"),
        }

        # When: 함수 호출
        with patch("src.common.config.REPAIR_COLORS", repair_colors):
            legend_elements, cluster_count = plot_individual_repairs_with_clusters(
                mock_ax,
                sample_all_repair_data,
                mock_convert_wgs84,
                mock_cluster_function,
            )

        # Then: 모든 타입이 처리됨
        assert mock_ax.scatter.call_count == 4  # 4개 타입 모두 scatter 호출
        assert len(legend_elements) >= 4  # 최소 4개의 범례 요소 + 클러스터 정보

    @patch("builtins.print")
    def test_console_output(
        self,
        mock_print,
        mock_ax,
        mock_convert_wgs84,
        mock_cluster_function,
        sample_repair_data,
    ):
        """콘솔 출력 테스트"""
        # Given: 재작업 데이터
        repair_colors = {"지상누수": ("blue", "지상누수")}

        # When: 함수 호출
        with patch("src.common.config.REPAIR_COLORS", repair_colors):
            plot_individual_repairs_with_clusters(
                mock_ax,
                {"지상누수": sample_repair_data["지상누수"]},
                mock_convert_wgs84,
                mock_cluster_function,
            )

        # Then: 적절한 정보 출력
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("전체 재작업" in str(call) for call in print_calls)
        assert any("클러스터링 결과" in str(call) for call in print_calls)
        assert any("2개 이상 클러스터" in str(call) for call in print_calls)
