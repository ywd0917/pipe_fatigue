"""
main59_fix_smz_num.py 모듈 테스트
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

from main59_fix_smz_num import (
    load_zone_fatigue_data,
    detect_mismatch,
    fix_smz_num,
    validate_output,
    analyze_statistics,
    generate_report,
    save_results,
    print_mismatch_ftr_idn,
    print_statistics,
)


@pytest.fixture
def sample_zone_fatigue_data():
    """테스트용 zone_fatigue 데이터 생성 fixture"""
    data = {
        "FTR_IDN": [10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008],
        "zone": [520, 520, 243, 243, 461, 470, 520, 243],
        "SMZ_NUM": [240, 520, 240, 243, 461, 700, 580, 243],
        "DATA_SRC": [
            "PIPE_LM",
            "SPLY_LS",
            "PIPE_LM",
            "SPLY_LS",
            "PIPE_LM",
            "PIPE_LM",
            "SPLY_LS",
            "PIPE_LM",
        ],
        "D_final": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.4, 0.3],
    }
    return pd.DataFrame(data)


@pytest.fixture
def create_temp_csv(tmp_path):
    """임시 CSV 파일 생성 fixture"""

    def _create(df: pd.DataFrame, filename: str = "test_zone_fatigue.csv"):
        file_path = tmp_path / filename
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return file_path

    return _create


class TestLoadZoneFatigueData:
    """load_zone_fatigue_data 함수 테스트"""

    def test_load_valid_file(self, sample_zone_fatigue_data, create_temp_csv):
        """정상적인 파일 로드 테스트"""
        file_path = create_temp_csv(sample_zone_fatigue_data)

        df = load_zone_fatigue_data(file_path)

        assert df is not None
        assert len(df) == 8
        assert "FTR_IDN" in df.columns
        assert "zone" in df.columns
        assert "SMZ_NUM" in df.columns

    def test_load_nonexistent_file(self, tmp_path):
        """존재하지 않는 파일 로드 테스트"""
        file_path = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError):
            load_zone_fatigue_data(file_path)

    def test_load_file_missing_required_columns(self, tmp_path):
        """필수 컬럼이 없는 파일 로드 테스트"""
        # zone 컬럼이 없는 데이터
        data = {
            "FTR_IDN": [10001, 10002],
            "SMZ_NUM": [240, 520],
            "DATA_SRC": ["PIPE_LM", "SPLY_LS"],
        }
        df = pd.DataFrame(data)
        file_path = tmp_path / "missing_columns.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")

        with pytest.raises(ValueError, match="필수 컬럼.*누락"):
            load_zone_fatigue_data(file_path)

    def test_load_empty_file(self, tmp_path):
        """빈 파일 로드 테스트"""
        file_path = tmp_path / "empty.csv"
        file_path.write_text("", encoding="utf-8-sig")

        with pytest.raises(Exception):  # pd.errors.EmptyDataError 또는 다른 오류
            load_zone_fatigue_data(file_path)


class TestDetectMismatch:
    """detect_mismatch 함수 테스트"""

    def test_detect_mismatch_basic(self, sample_zone_fatigue_data):
        """기본 불일치 검출 테스트"""
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)

        # 불일치: FTR_IDN 10001 (zone=520, SMZ_NUM=240)
        #         FTR_IDN 10003 (zone=243, SMZ_NUM=240)
        #         FTR_IDN 10006 (zone=470, SMZ_NUM=700)
        #         FTR_IDN 10007 (zone=520, SMZ_NUM=580)
        # 일치: FTR_IDN 10002, 10004, 10005, 10008

        assert len(matched_df) == 4
        assert len(mismatched_df) == 4

        # 불일치 행 검증
        assert 10001 in mismatched_df["FTR_IDN"].values
        assert 10003 in mismatched_df["FTR_IDN"].values
        assert 10006 in mismatched_df["FTR_IDN"].values
        assert 10007 in mismatched_df["FTR_IDN"].values

        # 일치 행 검증
        assert 10002 in matched_df["FTR_IDN"].values
        assert 10004 in matched_df["FTR_IDN"].values
        assert 10005 in matched_df["FTR_IDN"].values
        assert 10008 in matched_df["FTR_IDN"].values

    def test_detect_mismatch_all_match(self):
        """모두 일치하는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, 243, 461],
            "SMZ_NUM": [520, 243, 461],
        }
        df = pd.DataFrame(data)

        matched_df, mismatched_df = detect_mismatch(df)

        assert len(matched_df) == 3
        assert len(mismatched_df) == 0

    def test_detect_mismatch_all_mismatch(self):
        """모두 불일치하는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, 243, 461],
            "SMZ_NUM": [240, 580, 700],
        }
        df = pd.DataFrame(data)

        matched_df, mismatched_df = detect_mismatch(df)

        assert len(matched_df) == 0
        assert len(mismatched_df) == 3

    def test_detect_mismatch_with_nan(self):
        """NaN 값이 있는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, np.nan, 461],
            "SMZ_NUM": [520, 243, np.nan],
        }
        df = pd.DataFrame(data)

        matched_df, mismatched_df = detect_mismatch(df)

        # NaN은 -1로 변환되어 비교되므로 불일치로 간주
        assert len(matched_df) == 1  # FTR_IDN 10001만 일치
        assert len(mismatched_df) == 2  # 10002, 10003은 불일치


class TestFixSmzNum:
    """fix_smz_num 함수 테스트"""

    def test_fix_smz_num_basic(self, sample_zone_fatigue_data):
        """기본 SMZ_NUM 수정 테스트"""
        _, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        mismatch_mask = sample_zone_fatigue_data["FTR_IDN"].isin(
            mismatched_df["FTR_IDN"]
        )

        df_fixed = fix_smz_num(sample_zone_fatigue_data, mismatch_mask)

        # SMZ_NUM_원본 컬럼이 생성되었는지 확인
        assert "SMZ_NUM_원본" in df_fixed.columns

        # 불일치했던 행들의 SMZ_NUM이 zone과 일치하는지 확인
        for idx, row in df_fixed[mismatch_mask].iterrows():
            assert row["SMZ_NUM"] == row["zone"]

        # 원본 값이 백업되었는지 확인
        original_mismatched = sample_zone_fatigue_data[mismatch_mask]
        for idx, row in df_fixed[mismatch_mask].iterrows():
            original_value = original_mismatched.loc[idx, "SMZ_NUM"]
            assert row["SMZ_NUM_원본"] == original_value

    def test_fix_smz_num_preserves_matched_rows(self, sample_zone_fatigue_data):
        """일치하는 행은 변경되지 않아야 함"""
        matched_df, _ = detect_mismatch(sample_zone_fatigue_data)
        mismatch_mask = ~sample_zone_fatigue_data["FTR_IDN"].isin(
            matched_df["FTR_IDN"]
        )

        df_fixed = fix_smz_num(sample_zone_fatigue_data, mismatch_mask)

        # 일치하는 행들은 원본과 동일해야 함
        for ftr_idn in matched_df["FTR_IDN"]:
            original_row = sample_zone_fatigue_data[
                sample_zone_fatigue_data["FTR_IDN"] == ftr_idn
            ].iloc[0]
            fixed_row = df_fixed[df_fixed["FTR_IDN"] == ftr_idn].iloc[0]
            assert fixed_row["SMZ_NUM"] == original_row["SMZ_NUM"]
            assert fixed_row["zone"] == original_row["zone"]


class TestValidateOutput:
    """validate_output 함수 테스트"""

    def test_validate_output_all_match(self):
        """모두 일치하는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, 243, 461],
            "SMZ_NUM": [520, 243, 461],
        }
        df = pd.DataFrame(data)

        result = validate_output(df)

        assert result == True

    def test_validate_output_with_mismatch(self):
        """불일치가 있는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, 243, 461],
            "SMZ_NUM": [240, 243, 461],  # 10001 불일치
        }
        df = pd.DataFrame(data)

        result = validate_output(df)

        assert result == False

    def test_validate_output_with_nan(self):
        """NaN 값이 있는 경우"""
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, np.nan, 461],
            "SMZ_NUM": [520, 243, 461],
        }
        df = pd.DataFrame(data)

        result = validate_output(df)

        # NaN이 있으면 불일치로 간주
        assert result == False


class TestAnalyzeStatistics:
    """analyze_statistics 함수 테스트"""

    def test_analyze_statistics_basic(self, sample_zone_fatigue_data):
        """기본 통계 분석 테스트"""
        _, mismatched_df = detect_mismatch(sample_zone_fatigue_data)

        stats = analyze_statistics(mismatched_df)

        assert "zone_distribution" in stats
        assert "smz_distribution" in stats
        assert "crosstab" in stats

        # zone 분포 확인
        zone_dist = stats["zone_distribution"]
        assert 520 in zone_dist  # zone 520이 가장 많음
        assert 243 in zone_dist
        assert 470 in zone_dist

        # SMZ_NUM 분포 확인
        smz_dist = stats["smz_distribution"]
        assert 240 in smz_dist
        assert 580 in smz_dist
        assert 700 in smz_dist

    def test_analyze_statistics_empty_dataframe(self):
        """빈 DataFrame에 대한 통계 분석"""
        data = {
            "FTR_IDN": [],
            "zone": [],
            "SMZ_NUM": [],
        }
        df = pd.DataFrame(data)

        stats = analyze_statistics(df)

        assert "zone_distribution" in stats
        assert "smz_distribution" in stats
        assert "crosstab" in stats
        assert len(stats["zone_distribution"]) == 0
        assert len(stats["smz_distribution"]) == 0


class TestGenerateReport:
    """generate_report 함수 테스트"""

    def test_generate_report_basic(self, sample_zone_fatigue_data):
        """기본 리포트 생성 테스트"""
        total_rows = len(sample_zone_fatigue_data)
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        stats = analyze_statistics(mismatched_df)

        report = generate_report(stats, total_rows, len(matched_df), len(mismatched_df))

        assert "main59: SMZ_NUM 정정 리포트" in report
        assert "처리 통계" in report
        assert "zone별 정정 분포" in report
        assert "정정 전 SMZ_NUM 분포" in report
        assert "교차표" in report
        assert str(total_rows) in report
        assert str(len(mismatched_df)) in report

    def test_generate_report_includes_percentages(self, sample_zone_fatigue_data):
        """리포트에 비율이 포함되는지 테스트"""
        total_rows = len(sample_zone_fatigue_data)
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        stats = analyze_statistics(mismatched_df)

        report = generate_report(stats, total_rows, len(matched_df), len(mismatched_df))

        # 비율 표시가 포함되는지 확인
        assert "%" in report


class TestSaveResults:
    """save_results 함수 테스트"""

    def test_save_results_creates_output_files(
        self, sample_zone_fatigue_data, tmp_path
    ):
        """결과 파일들이 생성되는지 테스트"""
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        mismatch_mask = sample_zone_fatigue_data["FTR_IDN"].isin(
            mismatched_df["FTR_IDN"]
        )
        df_fixed = fix_smz_num(sample_zone_fatigue_data, mismatch_mask)
        stats = analyze_statistics(mismatched_df)
        report = generate_report(stats, len(sample_zone_fatigue_data), len(matched_df), len(mismatched_df))

        output_dir = tmp_path / "results"

        save_results(df_fixed, mismatched_df, report, output_dir)

        # 출력 파일들이 생성되었는지 확인
        assert (output_dir / "fatigue_merged_zone_fixed.csv").exists()
        assert (output_dir / "fix_report.txt").exists()
        assert (output_dir / "mismatch_ftr_idn_list.csv").exists()

    def test_save_results_fixed_csv_content(
        self, sample_zone_fatigue_data, tmp_path
    ):
        """정정된 CSV 파일의 내용 검증"""
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        mismatch_mask = sample_zone_fatigue_data["FTR_IDN"].isin(
            mismatched_df["FTR_IDN"]
        )
        df_fixed = fix_smz_num(sample_zone_fatigue_data, mismatch_mask)
        stats = analyze_statistics(mismatched_df)
        report = generate_report(stats, len(sample_zone_fatigue_data), len(matched_df), len(mismatched_df))

        output_dir = tmp_path / "results"

        save_results(df_fixed, mismatched_df, report, output_dir)

        # 저장된 CSV 파일 읽기
        saved_df = pd.read_csv(
            output_dir / "fatigue_merged_zone_fixed.csv", encoding="utf-8-sig"
        )

        # SMZ_NUM_원본 컬럼이 제거되었는지 확인
        assert "SMZ_NUM_원본" not in saved_df.columns

        # 행 수가 동일한지 확인
        assert len(saved_df) == len(df_fixed)

        # zone == SMZ_NUM 검증
        assert (saved_df["zone"] == saved_df["SMZ_NUM"]).all()

    def test_save_results_mismatch_list_content(
        self, sample_zone_fatigue_data, tmp_path
    ):
        """불일치 목록 CSV 파일의 내용 검증"""
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        mismatch_mask = sample_zone_fatigue_data["FTR_IDN"].isin(
            mismatched_df["FTR_IDN"]
        )
        df_fixed = fix_smz_num(sample_zone_fatigue_data, mismatch_mask)
        stats = analyze_statistics(mismatched_df)
        report = generate_report(stats, len(sample_zone_fatigue_data), len(matched_df), len(mismatched_df))

        output_dir = tmp_path / "results"

        save_results(df_fixed, mismatched_df, report, output_dir)

        # 불일치 목록 CSV 파일 읽기
        mismatch_list = pd.read_csv(
            output_dir / "mismatch_ftr_idn_list.csv", encoding="utf-8-sig"
        )

        # 필수 컬럼이 있는지 확인
        assert "FTR_IDN" in mismatch_list.columns
        assert "zone" in mismatch_list.columns
        assert "SMZ_NUM_원본" in mismatch_list.columns
        assert "SMZ_NUM_정정후" in mismatch_list.columns

        # 행 수가 불일치 개수와 동일한지 확인
        assert len(mismatch_list) == len(mismatched_df)


class TestPrintFunctions:
    """출력 함수 테스트"""

    def test_print_mismatch_ftr_idn(self, sample_zone_fatigue_data, capsys):
        """불일치 FTR_IDN 출력 함수 테스트"""
        _, mismatched_df = detect_mismatch(sample_zone_fatigue_data)

        print_mismatch_ftr_idn(mismatched_df)

        captured = capsys.readouterr()
        assert "불일치 FTR_IDN 목록" in captured.out
        assert "10001" in captured.out  # 불일치 FTR_IDN 중 하나
        assert "→" in captured.out  # 화살표 표시

    def test_print_statistics(self, sample_zone_fatigue_data, capsys):
        """통계 출력 함수 테스트"""
        matched_df, mismatched_df = detect_mismatch(sample_zone_fatigue_data)
        stats = analyze_statistics(mismatched_df)

        print_statistics(stats, len(sample_zone_fatigue_data), len(matched_df), len(mismatched_df))

        captured = capsys.readouterr()
        assert "zone별 불일치 분포" in captured.out
        assert "원본 SMZ_NUM 분포" in captured.out


class TestIntegration:
    """통합 테스트"""

    def test_full_pipeline(self, sample_zone_fatigue_data, tmp_path):
        """전체 파이프라인 통합 테스트"""
        # 1. 임시 파일 생성
        input_file = tmp_path / "zone_fatigue_merged.csv"
        sample_zone_fatigue_data.to_csv(
            input_file, index=False, encoding="utf-8-sig"
        )

        # 2. 데이터 로드
        df = load_zone_fatigue_data(input_file)
        assert df is not None
        assert len(df) == 8

        # 3. 불일치 검출
        matched_df, mismatched_df = detect_mismatch(df)
        assert len(matched_df) == 4
        assert len(mismatched_df) == 4

        # 4. SMZ_NUM 수정
        mismatch_mask = df["FTR_IDN"].isin(mismatched_df["FTR_IDN"])
        df_fixed = fix_smz_num(df, mismatch_mask)
        assert "SMZ_NUM_원본" in df_fixed.columns

        # 5. 검증
        is_valid = validate_output(df_fixed)
        assert is_valid == True

        # 6. 통계 분석
        stats = analyze_statistics(mismatched_df)
        assert "zone_distribution" in stats
        assert "smz_distribution" in stats
        assert "crosstab" in stats

        # 7. 리포트 생성
        report = generate_report(stats, len(df), len(matched_df), len(mismatched_df))
        assert len(report) > 0
        assert "main59: SMZ_NUM 정정 리포트" in report

        # 8. 결과 저장
        output_dir = tmp_path / "results"
        save_results(df_fixed, mismatched_df, report, output_dir)

        # 9. 출력 파일 검증
        assert (output_dir / "fatigue_merged_zone_fixed.csv").exists()
        assert (output_dir / "fix_report.txt").exists()
        assert (output_dir / "mismatch_ftr_idn_list.csv").exists()

        # 10. 최종 결과 검증
        final_df = pd.read_csv(
            output_dir / "fatigue_merged_zone_fixed.csv", encoding="utf-8-sig"
        )
        assert (final_df["zone"] == final_df["SMZ_NUM"]).all()
        assert "SMZ_NUM_원본" not in final_df.columns

    def test_pipeline_with_no_mismatches(self, tmp_path):
        """불일치가 없는 경우의 파이프라인 테스트"""
        # 모두 일치하는 데이터
        data = {
            "FTR_IDN": [10001, 10002, 10003],
            "zone": [520, 243, 461],
            "SMZ_NUM": [520, 243, 461],
            "DATA_SRC": ["PIPE_LM", "SPLY_LS", "PIPE_LM"],
        }
        df = pd.DataFrame(data)

        # 임시 파일 생성
        input_file = tmp_path / "zone_fatigue_matched.csv"
        df.to_csv(input_file, index=False, encoding="utf-8-sig")

        # 파이프라인 실행
        df_loaded = load_zone_fatigue_data(input_file)
        matched_df, mismatched_df = detect_mismatch(df_loaded)

        assert len(matched_df) == 3
        assert len(mismatched_df) == 0

        # 검증 (이미 모두 일치)
        is_valid = validate_output(df_loaded)
        assert is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
