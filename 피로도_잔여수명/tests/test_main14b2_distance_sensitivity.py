#!/usr/bin/env python3
"""
test_main14b2_distance_sensitivity.py

main14b2_distance_sensitivity.py 스크립트에 대한 테스트 코드

Author: assistant
Date: 2025-08-19
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# 프로젝트 루트 디렉토리를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import builtins
import contextlib

from src.main14b2_distance_sensitivity import (
    BASE_K_FACTORS,
    DAMAGE_FACTOR,
    OPTIONAL_K_FACTORS,
    analyze_csv_strategies,
    analyze_distance_sensitivity,
    create_correlation_table,
    create_matching_stats_table,
    create_sensitivity_report,
    run_main14b_with_distance,
)


class TestConstants:
    """상수 정의 테스트"""

    def test_base_k_factors_order(self):
        """BASE_K_FACTORS가 CSV 컬럼 순서대로 정의되었는지 테스트"""
        expected = [
            "STD_DIP",  # 관경이 첫 번째
            "K_age",
            "K_soil",
            "K_traffic",
            "hoop_stress",
            "K_stress",
            "K_total",
        ]
        assert expected == BASE_K_FACTORS

    def test_optional_k_factors(self):
        """OPTIONAL_K_FACTORS가 올바르게 정의되었는지 테스트"""
        assert OPTIONAL_K_FACTORS == ["K_repair"]

    def test_damage_factor(self):
        """DAMAGE_FACTOR가 올바르게 정의되었는지 테스트"""
        assert DAMAGE_FACTOR == "D_final"


# setup_korean_font 테스트는 test_common_korean_font_utils.py에서 처리


# parse_analysis_results 함수는 제거되었으므로 테스트도 제거


# parse_matching_stats 함수는 제거되었으므로 관련 테스트 클래스도 제거


class TestRunMain14bWithDistance:
    """main14b 실행 함수 테스트"""

    @patch("src.main14b2_distance_sensitivity.subprocess.run")
    @patch("src.main14b2_distance_sensitivity.shutil.copy")
    @patch("src.main14b2_distance_sensitivity.analyze_csv_strategies")
    def test_run_main14b_success(
        self, mock_analyze_csv, mock_copy, mock_subprocess, tmp_path
    ):
        """main14b 실행 성공 테스트"""
        # Mock 설정
        mock_subprocess.return_value = Mock(
            stdout="전체 클러스터: 755\n매칭률: 84.4%", stderr="", returncode=0
        )
        mock_analyze_csv.return_value = {
            "K_age": {
                "max": {"r": 0.035, "p": 0.3, "r_squared": 0.001},
                "nearest": {"r": 0.034, "p": 0.31, "r_squared": 0.001},
                "avg": {"r": 0.036, "p": 0.29, "r_squared": 0.001},
            }
        }

        # metadata.json 파일 생성 - Path("results") 사용 (실제 경로)
        metadata_file = Path("results") / "main14b" / "metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text(
            json.dumps(
                {
                    "total_clusters": 755,
                    "matched_clusters": 637,
                    "matching_rate": 84.4,
                    "avg_pipes_per_cluster": 2.5,
                }
            )
        )

        # CSV 파일 생성 - Path("results") 사용 (실제 경로)
        csv_file = Path("results") / "main14b" / "0520_repair_k_factors_matched.csv"
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        csv_file.touch()

        # TXT 파일 생성 - Path("results") 사용 (실제 경로)
        txt_file = Path("results") / "main14b" / "0520_repair_correlations_analysis.txt"
        txt_file.touch()

        try:
            result = run_main14b_with_distance(10, tmp_path)

            assert result["distance"] == 10
            assert result["execution_time"] > 0
            assert "matching_stats" in result
            assert "correlations" in result
        finally:
            # 정리
            import shutil

            if csv_file.exists():
                csv_file.unlink()
            if txt_file.exists():
                txt_file.unlink()
            if csv_file.parent.exists() and csv_file.parent != Path.cwd():
                with contextlib.suppress(builtins.BaseException):
                    shutil.rmtree(csv_file.parent)

    @patch("src.main14b2_distance_sensitivity.subprocess.run")
    def test_run_main14b_failure(self, mock_subprocess, tmp_path):
        """main14b 실행 실패 테스트"""
        from subprocess import CalledProcessError

        mock_subprocess.side_effect = CalledProcessError(1, "cmd", stderr="실행 실패")

        result = run_main14b_with_distance(10, tmp_path)

        assert result["distance"] == 10
        assert result["execution_time"] == -1
        assert "error" in result


class TestCreateCorrelationTable:
    """상관계수 테이블 생성 테스트"""

    def test_create_correlation_table(self, tmp_path):
        """상관계수 테이블 생성 및 저장 테스트"""
        # 테스트 데이터
        df_results = pd.DataFrame(
            [
                {
                    "distance": 10,
                    "correlations": {
                        "STD_DIP": -0.036,
                        "K_age": 0.035,
                        "K_soil": 0.037,
                    },
                },
                {
                    "distance": 20,
                    "correlations": {
                        "STD_DIP": -0.025,
                        "K_age": -0.003,
                        "K_soil": 0.036,
                    },
                },
            ]
        )

        create_correlation_table(df_results, tmp_path)

        # 파일이 생성되었는지 확인
        csv_file = tmp_path / "correlation_by_distance.csv"
        assert csv_file.exists()

        # 내용 확인
        df_saved = pd.read_csv(csv_file, index_col=0)
        assert 10 in df_saved.index
        assert 20 in df_saved.index


class TestCreateMatchingStatsTable:
    """매칭 통계 테이블 생성 테스트"""

    def test_create_matching_stats_table(self, tmp_path):
        """매칭 통계 테이블 생성 및 저장 테스트"""
        # 테스트 데이터
        df_results = pd.DataFrame(
            [
                {
                    "distance": 10,
                    "execution_time": 18.5,
                    "matching_stats": {
                        "total_clusters": 755,
                        "matched_clusters": 637,
                        "matching_rate": 84.4,
                    },
                }
            ]
        )

        create_matching_stats_table(df_results, tmp_path)

        # 파일이 생성되었는지 확인
        csv_file = tmp_path / "matching_statistics.csv"
        assert csv_file.exists()

        # 내용 확인
        df_saved = pd.read_csv(csv_file)
        assert len(df_saved) == 1
        assert df_saved.iloc[0]["distance"] == 10
        assert df_saved.iloc[0]["matching_rate"] == 84.4


class TestCreateSensitivityReport:
    """민감도 분석 보고서 생성 테스트"""

    def test_create_sensitivity_report(self, tmp_path):
        """보고서 생성 테스트"""
        # 테스트 데이터
        df_results = pd.DataFrame(
            [
                {
                    "distance": 10,
                    "execution_time": 18.5,
                    "matching_stats": {
                        "matching_rate": 84.4,
                        "matched_clusters": 637,
                        "total_clusters": 755,
                    },
                    "correlations": {
                        "STD_DIP": -0.036,
                        "K_age": 0.035,
                        "K_soil": 0.037,
                        "K_traffic": -0.038,
                        "hoop_stress": -0.023,
                        "K_stress": -0.042,
                        "K_total": -0.036,
                        "D_final": -0.035,
                    },
                    "p_values": {
                        "STD_DIP": 0.3,
                        "K_age": 0.3,
                        "K_soil": 0.3,
                        "K_traffic": 0.09,
                        "hoop_stress": 0.5,
                        "K_stress": 0.2,
                        "K_total": 0.3,
                        "D_final": 0.3,
                    },
                    "significant_factors": [
                        {"factor": "K_traffic", "r": -0.038, "p": 0.09}
                    ],
                },
                {
                    "distance": 30,
                    "execution_time": 18.6,
                    "matching_stats": {
                        "matching_rate": 99.6,
                        "matched_clusters": 891,
                        "total_clusters": 895,
                    },
                    "correlations": {
                        "STD_DIP": -0.010,
                        "K_age": -0.002,
                        "K_soil": 0.031,
                        "K_traffic": -0.061,
                        "hoop_stress": -0.018,
                        "K_stress": -0.038,
                        "K_total": -0.029,
                        "D_final": -0.031,
                    },
                    "p_values": {
                        "STD_DIP": 0.2,
                        "K_age": 0.9,
                        "K_soil": 0.4,
                        "K_traffic": 0.07,
                        "hoop_stress": 0.6,
                        "K_stress": 0.3,
                        "K_total": 0.4,
                        "D_final": 0.4,
                    },
                    "significant_factors": [
                        {"factor": "K_traffic", "r": -0.061, "p": 0.07}
                    ],
                },
            ]
        )

        create_sensitivity_report(df_results, tmp_path)

        # 파일이 생성되었는지 확인
        report_file = tmp_path / "sensitivity_report.md"
        assert report_file.exists()

        # 내용 확인
        content = report_file.read_text(encoding="utf-8")
        assert "# 거리 민감도 분석 보고서" in content
        assert "최적 거리" in content
        assert "매칭 성능" in content
        assert "상관관계 분석" in content


class TestAnalyzeDistanceSensitivity:
    """거리 민감도 분석 통합 테스트"""

    @patch("src.main14b2_distance_sensitivity.run_main14b_with_distance")
    @patch("src.main14b2_distance_sensitivity.create_visualizations")
    @patch("src.main14b2_distance_sensitivity.create_sensitivity_report")
    def test_analyze_distance_sensitivity(
        self, mock_report, mock_viz, mock_run, tmp_path
    ):
        """전체 분석 흐름 테스트"""
        # Mock 설정
        mock_run.return_value = {
            "distance": 10,
            "execution_time": 18.5,
            "matching_stats": {"matching_rate": 84.4},
            "correlations": {"K_age": 0.035},
            "p_values": {"K_age": 0.3},
            "significant_factors": [],
        }

        # 임시로 RESULTS_BASE 변경
        with patch("src.main14b2_distance_sensitivity.RESULTS_BASE", tmp_path):
            df_results = analyze_distance_sensitivity([10])

        assert len(df_results) == 1
        assert df_results.iloc[0]["distance"] == 10
        assert mock_run.called
        assert mock_viz.called
        assert mock_report.called


# 통합 테스트
class TestAnalyzeCsvStrategies:
    """CSV 전략 분석 테스트"""

    def test_analyze_csv_strategies_success(self, tmp_path):
        """정상적인 CSV 파일 분석 테스트"""
        # 테스트 CSV 파일 생성
        csv_file = tmp_path / "repair_k_factors_matched.csv"
        csv_data = """cluster_id,repair_count,max_K_age,nearest_K_age,avg_K_age,max_K_soil,nearest_K_soil,avg_K_soil
0,2,1.5,1.2,1.3,1.0,1.0,1.0
1,3,2.0,1.8,1.9,1.1,1.0,1.05
2,1,1.0,1.0,1.0,1.0,1.0,1.0
"""
        csv_file.write_text(csv_data)

        # 분석 실행
        analysis_factors = ["K_age", "K_soil"]
        results = analyze_csv_strategies(csv_file, analysis_factors)

        # 결과 검증
        assert "correlations" in results
        assert "p_values" in results
        assert "best_strategies" in results

        # 각 전략별로 상관관계 결과가 있어야 함
        for factor in ["K_age", "K_soil"]:
            for strategy in ["max", "nearest", "avg"]:
                key = f"{strategy}_{factor}"
                assert key in results["correlations"]
                assert key in results["p_values"]

            # 최적 전략이 선택되어야 함
            assert factor in results["best_strategies"]
            assert "strategy" in results["best_strategies"][factor]
            assert "r" in results["best_strategies"][factor]
            assert "p" in results["best_strategies"][factor]

    def test_analyze_csv_strategies_missing_file(self, tmp_path):
        """CSV 파일이 없을 때 처리 테스트"""
        # 존재하지 않는 파일
        csv_file = tmp_path / "non_existent.csv"

        # 분석 실행
        analysis_factors = ["K_age", "K_soil"]
        results = analyze_csv_strategies(csv_file, analysis_factors)

        # 빈 결과 반환
        assert results == {}

    def test_analyze_csv_strategies_empty_file(self, tmp_path):
        """빈 CSV 파일 처리 테스트"""
        # 빈 CSV 파일 생성
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        # 분석 실행 - pandas.errors.EmptyDataError 예상
        import pandas as pd

        with pytest.raises(pd.errors.EmptyDataError):
            analysis_factors = ["K_age", "K_soil"]
            results = analyze_csv_strategies(csv_file, analysis_factors)

    def test_analyze_csv_strategies_invalid_columns(self, tmp_path):
        """잘못된 컬럼 구조 처리 테스트"""
        # 잘못된 컬럼 구조
        csv_file = tmp_path / "invalid.csv"
        csv_data = """col1,col2,col3
1,2,3
4,5,6
"""
        csv_file.write_text(csv_data)

        # 분석 실행
        analysis_factors = ["K_age", "K_soil"]
        results = analyze_csv_strategies(csv_file, analysis_factors)

        # 빈 best_strategies 반환 (매칭되는 컬럼이 없음)
        assert results["best_strategies"] == {}
        assert results["correlations"] == {}
        assert results["p_values"] == {}


class TestCsvFileValidation:
    """CSV 파일 유효성 검사 테스트"""

    @patch("src.main14b2_distance_sensitivity.subprocess.run")
    def test_csv_file_not_found_error(self, mock_subprocess, tmp_path):
        """CSV 파일이 없을 때 오류 메시지 테스트"""
        # Mock 설정 - main14b는 성공하지만 CSV 파일 생성 안됨
        mock_subprocess.return_value = Mock(stdout="실행 완료", stderr="", returncode=0)

        # 임시 디렉토리 생성
        test_dir = tmp_path / "test_distance_10m"
        test_dir.mkdir(parents=True, exist_ok=True)

        # CSV 파일은 생성하지 않음 (없는 상태 유지)

        # 함수 실행
        result = run_main14b_with_distance(10, test_dir)

        # CSV 파일이 없어서 오류 반환
        assert "error" in result
        assert result["error"] == "CSV file not found"
        assert result["execution_time"] == -1


class TestIntegration:
    """통합 테스트"""

    @patch("src.main14b2_distance_sensitivity.create_visualizations")
    def test_full_workflow(self, mock_viz, tmp_path):
        """전체 워크플로우 테스트 (실제 실행 없이)"""
        with patch(
            "src.main14b2_distance_sensitivity.subprocess.run"
        ) as mock_subprocess:
            with patch("src.main14b2_distance_sensitivity.RESULTS_BASE", tmp_path):
                # Mock 설정
                mock_subprocess.return_value = Mock(
                    stdout="전체 클러스터: 755\n매칭률: 84.4%", stderr="", returncode=0
                )

                # metadata.json 파일 생성 - Path("results") 사용
                metadata_dir = Path("results") / "main14b"
                metadata_dir.mkdir(parents=True, exist_ok=True)
                metadata_file = metadata_dir / "metadata.json"
                metadata_file.write_text(
                    json.dumps(
                        {
                            "total_clusters": 755,
                            "matched_clusters": 637,
                            "matching_rate": 84.4,
                            "avg_pipes_per_cluster": 2.5,
                        }
                    )
                )

                # CSV 파일 생성 - Path("results") 사용
                csv_file = (
                    Path("results") / "main14b" / "0520_repair_k_factors_matched.csv"
                )
                csv_file.parent.mkdir(parents=True, exist_ok=True)
                csv_file.write_text("distance,dummy,data\n10,1,2", encoding="utf-8")

                txt_file = (
                    Path("results")
                    / "main14b"
                    / "0520_repair_correlations_analysis.txt"
                )
                txt_file.write_text(
                    """
관경 (STD_DIP):
  상관계수: -0.0361
  p-value: 0.3044

파이프 연령 계수 (K_age):
  상관계수: 0.0351
  p-value: 0.3361
                """,
                    encoding="utf-8",
                )

                # 분석 실행 (거리 10m만)
                df_results = analyze_distance_sensitivity([10])

                # 결과 확인
                assert len(df_results) == 1

                # 생성된 파일 확인
                integrated_dir = tmp_path / "integrated_analysis"
                assert integrated_dir.exists()
                assert (integrated_dir / "correlation_by_distance.csv").exists()
                assert (integrated_dir / "matching_statistics.csv").exists()
                assert (integrated_dir / "sensitivity_report.md").exists()


class TestCreateVisualizations:
    """시각화 생성 테스트"""

    def test_create_visualizations_with_valid_data(self, tmp_path):
        """유효한 데이터로 시각화 생성 테스트"""
        from src.main14b2_distance_sensitivity import create_visualizations

        # 테스트 데이터 생성
        df_results = pd.DataFrame(
            [
                {
                    "distance": 10,
                    "execution_time": 18.5,
                    "matching_stats": {
                        "matching_rate": 84.4,
                        "matched_clusters": 637,
                        "total_clusters": 755,
                    },
                    "correlations": {
                        "STD_DIP": -0.036,
                        "K_age": 0.035,
                        "K_soil": 0.037,
                        "K_traffic": -0.038,
                        "hoop_stress": -0.023,
                        "K_stress": -0.042,
                        "K_total": -0.036,
                        "D_final": -0.035,
                    },
                    "p_values": {
                        "STD_DIP": 0.3,
                        "K_age": 0.3,
                        "K_soil": 0.3,
                        "K_traffic": 0.09,
                        "hoop_stress": 0.5,
                        "K_stress": 0.2,
                        "K_total": 0.3,
                        "D_final": 0.3,
                    },
                },
                {
                    "distance": 30,
                    "execution_time": 18.6,
                    "matching_stats": {
                        "matching_rate": 99.6,
                        "matched_clusters": 891,
                        "total_clusters": 895,
                    },
                    "correlations": {
                        "STD_DIP": -0.010,
                        "K_age": -0.002,
                        "K_soil": 0.031,
                        "K_traffic": -0.061,
                        "hoop_stress": -0.018,
                        "K_stress": -0.038,
                        "K_total": -0.029,
                        "D_final": -0.031,
                    },
                    "p_values": {
                        "STD_DIP": 0.2,
                        "K_age": 0.9,
                        "K_soil": 0.4,
                        "K_traffic": 0.07,
                        "hoop_stress": 0.6,
                        "K_stress": 0.3,
                        "K_total": 0.4,
                        "D_final": 0.4,
                    },
                },
            ]
        )

        # 시각화 생성
        create_visualizations(df_results, tmp_path)

        # 생성된 파일 확인 (실제 파일명으로 수정)
        assert (tmp_path / "distance_sensitivity_analysis.png").exists()
        assert (tmp_path / "individual_factor_analysis.png").exists()

    def test_create_visualizations_with_empty_data(self, tmp_path):
        """빈 데이터로 시각화 처리 테스트"""
        from src.main14b2_distance_sensitivity import create_visualizations

        # 빈 데이터프레임
        df_results = pd.DataFrame()

        # 시각화 생성 - KeyError 예상 (distance 컬럼이 없음)
        with pytest.raises(KeyError):
            create_visualizations(df_results, tmp_path)

    @patch("matplotlib.pyplot.savefig")
    def test_create_visualizations_plot_settings(self, mock_savefig, tmp_path):
        """플롯 설정 테스트"""
        from src.main14b2_distance_sensitivity import create_visualizations

        # 최소 데이터
        df_results = pd.DataFrame(
            [
                {
                    "distance": 10,
                    "matching_stats": {"matching_rate": 84.4},
                    "correlations": {"K_age": 0.035},
                    "p_values": {"K_age": 0.3},
                }
            ]
        )

        # 시각화 생성
        create_visualizations(df_results, tmp_path)

        # savefig 호출 확인
        assert mock_savefig.called
        # dpi=300, bbox_inches='tight' 등의 설정이 사용되는지 확인
        call_kwargs = mock_savefig.call_args_list[0][1]
        assert call_kwargs.get("dpi") == 300
        assert call_kwargs.get("bbox_inches") == "tight"


class TestMain:
    """main 함수 테스트"""

    @patch("src.main14b2_distance_sensitivity.analyze_distance_sensitivity")
    def test_main_execution(self, mock_analyze):
        """main 함수 실행 테스트"""
        from src.main14b2_distance_sensitivity import main

        # Mock 설정 - 빈 DataFrame 반환
        mock_analyze.return_value = pd.DataFrame()

        # main 실행
        main()

        # analyze_distance_sensitivity가 호출되었는지 확인
        mock_analyze.assert_called_once()
        called_distances = mock_analyze.call_args[0][0]
        # main 함수의 기본 거리: [10, 20, 30, 50, 100]
        assert called_distances == [10, 20, 30, 50, 100]

    @patch("src.main14b2_distance_sensitivity.analyze_distance_sensitivity")
    @patch("builtins.print")
    def test_main_output(self, mock_print, mock_analyze):
        """main 함수 출력 테스트"""
        from src.main14b2_distance_sensitivity import main

        # Mock 설정
        mock_analyze.return_value = pd.DataFrame()

        # main 실행
        main()

        # 출력 메시지 확인
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("거리 민감도 분석 시작" in str(call) for call in print_calls)
        assert any("분석 거리:" in str(call) for call in print_calls)


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_analyze_csv_strategies_with_nan_values(self, tmp_path):
        """NaN 값이 포함된 CSV 분석 테스트"""
        from src.main14b2_distance_sensitivity import analyze_csv_strategies

        # NaN 값이 포함된 CSV 파일 생성
        csv_file = tmp_path / "test_with_nan.csv"
        csv_data = """cluster_id,repair_count,max_K_age,nearest_K_age,avg_K_age
0,2,1.5,NaN,1.3
1,3,2.0,1.8,NaN
2,1,NaN,1.0,1.0
"""
        csv_file.write_text(csv_data)

        # 분석 실행
        results = analyze_csv_strategies(csv_file, ["K_age"])

        # NaN이 있어도 처리되어야 함
        assert "correlations" in results
        assert "p_values" in results

    # parse_matching_stats 함수는 제거되었으므로 관련 테스트도 제거

    @patch("src.main14b2_distance_sensitivity.subprocess.run")
    def test_run_main14b_with_timeout(self, mock_subprocess, tmp_path):
        """타임아웃 시나리오 테스트"""
        from subprocess import TimeoutExpired

        # TimeoutExpired는 현재 코드에서 처리되지 않으므로 예외가 발생함
        mock_subprocess.side_effect = TimeoutExpired("cmd", 300)

        from src.main14b2_distance_sensitivity import run_main14b_with_distance

        # TimeoutExpired가 처리되지 않으므로 예외가 전파됨
        with pytest.raises(TimeoutExpired):
            run_main14b_with_distance(10, tmp_path)


class TestPerformance:
    """성능 관련 테스트"""

    def test_large_dataset_handling(self, tmp_path):
        """대용량 데이터셋 처리 테스트"""
        from src.main14b2_distance_sensitivity import analyze_csv_strategies

        # 큰 CSV 파일 생성 (1000행)
        csv_file = tmp_path / "large_dataset.csv"
        header = "cluster_id,repair_count,max_K_age,nearest_K_age,avg_K_age"
        rows = []
        for i in range(1000):
            rows.append(
                f"{i},{i % 10},{1.0 + i * 0.001},{1.0 + i * 0.001},{1.0 + i * 0.001}"
            )

        csv_content = header + "\n" + "\n".join(rows)
        csv_file.write_text(csv_content)

        # 분석 실행 및 시간 측정
        import time

        start_time = time.time()
        results = analyze_csv_strategies(csv_file, ["K_age"])
        elapsed_time = time.time() - start_time

        # 결과 확인
        assert "correlations" in results
        assert "best_strategies" in results
        # 1000행 처리가 5초 이내에 완료되어야 함
        assert elapsed_time < 5.0, f"Processing took too long: {elapsed_time:.2f}s"

    @patch("src.main14b2_distance_sensitivity.subprocess.run")
    def test_concurrent_execution_handling(self, mock_subprocess, tmp_path):
        """동시 실행 처리 테스트"""
        from src.main14b2_distance_sensitivity import run_main14b_with_distance
        import threading

        # Mock 설정
        mock_subprocess.return_value = Mock(
            stdout="전체 클러스터: 755\n매칭률: 84.4%", stderr="", returncode=0
        )

        results = []

        def run_analysis(distance):
            result = run_main14b_with_distance(distance, tmp_path / f"dist_{distance}")
            results.append(result)

        # 여러 스레드에서 동시 실행
        threads = []
        for distance in [10, 20, 30]:
            thread = threading.Thread(target=run_analysis, args=(distance,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 모든 실행이 완료되었는지 확인
        assert len(results) == 3
        # execution_time은 -1 (CSV 파일 없음) 또는 >= 0
        assert all("execution_time" in r for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
