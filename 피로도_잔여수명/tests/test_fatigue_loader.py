"""
fatigue_loader.py 테스트
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.fatigue_loader import (
    get_available_csv_files,
    get_fatigue_by_ftr_idn,
    get_fatigue_data_dir,
    get_fatigue_info,
    load_fatigue_data,
    validate_fatigue_data,
)


@pytest.fixture
def mock_fatigue_df():
    """테스트용 피로 손상 DataFrame"""
    data = {
        "FTR_IDN": [1001, 1002, 1003, None, 1005],
        "0520_D_final": [0.001, 0.005, 0.015, 0.1, 0.5],
        "0903_D_final": [0.002, 0.008, 0.02, 0.15, 0.8],
        "other_column": ["A", "B", "C", "D", "E"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_base_dir(tmp_path):
    """테스트용 기본 디렉토리"""
    return tmp_path


class TestGetFatigueDataDir:
    """get_fatigue_data_dir 함수 테스트"""

    def test_get_fatigue_data_dir_from_data(self, mock_base_dir):
        """data 디렉토리에서 pipe_fatigue 경로 반환 테스트"""
        data_dir = mock_base_dir / "data"
        data_dir.mkdir()

        result = get_fatigue_data_dir(data_dir)
        expected = data_dir / "pipe_fatigue"

        assert result == expected

    def test_get_fatigue_data_dir_from_raw(self, mock_base_dir):
        """raw 디렉토리에서 상위/pipe_fatigue 경로 반환 테스트"""
        raw_dir = mock_base_dir / "data" / "raw"
        raw_dir.mkdir(parents=True)

        result = get_fatigue_data_dir(raw_dir)
        expected = raw_dir.parent / "pipe_fatigue"

        assert result == expected


class TestGetAvailableCsvFiles:
    """get_available_csv_files 함수 테스트"""

    def test_get_available_csv_files_exists(self, mock_base_dir):
        """CSV 파일이 있는 디렉토리 테스트"""
        # 디렉토리 및 파일 생성
        fatigue_dir = mock_base_dir / "pipe_fatigue"
        fatigue_dir.mkdir()

        file1 = fatigue_dir / "fatigue_pipe_lm.csv"
        file2 = fatigue_dir / "fatigue_sply_ls.csv"
        file3 = fatigue_dir / "not_fatigue.txt"  # CSV가 아닌 파일

        file1.touch()
        file2.touch()
        file3.touch()

        result = get_available_csv_files(mock_base_dir)

        assert len(result) == 2
        assert "fatigue_pipe_lm" in result
        assert "fatigue_sply_ls" in result
        assert result["fatigue_pipe_lm"] == file1
        assert result["fatigue_sply_ls"] == file2

    def test_get_available_csv_files_empty(self, mock_base_dir):
        """CSV 파일이 없는 디렉토리 테스트"""
        # 빈 디렉토리 생성
        fatigue_dir = mock_base_dir / "pipe_fatigue"
        fatigue_dir.mkdir()

        result = get_available_csv_files(mock_base_dir)

        assert result == {}

    def test_get_available_csv_files_no_dir(self, mock_base_dir):
        """pipe_fatigue 디렉토리가 없는 경우 테스트"""
        result = get_available_csv_files(mock_base_dir)

        assert result == {}


class TestValidateFatigueData:
    """validate_fatigue_data 함수 테스트"""

    def test_validate_fatigue_data_success(self, mock_fatigue_df):
        """정상적인 데이터 검증 테스트"""
        required_columns = ["FTR_IDN", "0520_D_final"]

        result = validate_fatigue_data(mock_fatigue_df, required_columns)

        # NaN이 있는 행이 제거되었는지 확인
        assert len(result) == 4  # 원래 5개에서 NaN 1개 제거
        assert result["FTR_IDN"].isna().sum() == 0

    def test_validate_fatigue_data_missing_column(self, mock_fatigue_df):
        """필수 컬럼이 없는 경우 테스트"""
        required_columns = ["FTR_IDN", "missing_column"]

        with pytest.raises(ValueError, match="필수 컬럼이 누락되었습니다"):
            validate_fatigue_data(mock_fatigue_df, required_columns)

    def test_validate_fatigue_data_no_ftr_idn(self):
        """FTR_IDN 컬럼이 없는 DataFrame 테스트"""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        required_columns = ["other_col"]

        result = validate_fatigue_data(df, required_columns)

        # FTR_IDN이 없으면 NaN 제거 로직이 실행되지 않음
        assert len(result) == 3

    @patch("builtins.print")
    def test_validate_fatigue_data_with_nan_warning(self, mock_print, mock_fatigue_df):
        """NaN 제거 시 경고 메시지 테스트"""
        required_columns = ["FTR_IDN"]

        validate_fatigue_data(mock_fatigue_df, required_columns)

        mock_print.assert_called_with("경고: FTR_IDN이 NaN인 행 1개 제거")


class TestLoadFatigueData:
    """load_fatigue_data 함수 테스트"""

    def test_load_fatigue_data_success(self, tmp_path):
        """정상적인 CSV 로딩 테스트"""
        # CSV 파일 생성
        csv_path = tmp_path / "test_fatigue.csv"
        test_data = {
            "FTR_IDN": [1001, 1002, 1003],
            "0520_D_final": [0.001, 0.005, 0.015],
        }
        pd.DataFrame(test_data).to_csv(csv_path, index=False)

        with patch("builtins.print") as mock_print:
            result = load_fatigue_data(csv_path, verbose=True)

        assert result is not None
        assert len(result) == 3
        assert list(result.columns) == ["FTR_IDN", "0520_D_final"]
        assert result["FTR_IDN"].dtype == "object"  # 문자열로 변환됨

        # 출력 메시지 확인
        assert any(
            "피로 손상 데이터 로드 완료" in str(call)
            for call in mock_print.call_args_list
        )

    def test_load_fatigue_data_file_not_found(self, tmp_path):
        """파일이 없는 경우 테스트"""
        csv_path = tmp_path / "nonexistent.csv"

        with patch("builtins.print") as mock_print:
            result = load_fatigue_data(csv_path, verbose=True)

        assert result is None
        mock_print.assert_called_with(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")

    def test_load_fatigue_data_with_default_columns(self, tmp_path):
        """기본 필수 컬럼으로 테스트"""
        csv_path = tmp_path / "test_fatigue.csv"
        test_data = {"FTR_IDN": [1001], "0520_D_final": [0.001]}
        pd.DataFrame(test_data).to_csv(csv_path, index=False)

        result = load_fatigue_data(csv_path, required_columns=None, verbose=False)

        assert result is not None
        assert "FTR_IDN" in result.columns

    def test_load_fatigue_data_exception_handling(self, tmp_path):
        """CSV 읽기 예외 처리 테스트"""
        # 잘못된 형식의 파일 생성
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text("invalid,csv,content\nwith,wrong,format\n")

        with (
            patch("pandas.read_csv", side_effect=Exception("Read error")),
            patch("builtins.print") as mock_print,
        ):
            result = load_fatigue_data(csv_path, verbose=True)

        assert result is None
        assert any(
            "CSV 데이터 로드 실패" in str(call) for call in mock_print.call_args_list
        )


class TestGetFatigueByFtrIdn:
    """get_fatigue_by_ftr_idn 함수 테스트"""

    def test_get_fatigue_by_ftr_idn_success(self, mock_fatigue_df):
        """정상적인 FTR_IDN별 매핑 테스트"""
        # NaN 제거
        clean_df = mock_fatigue_df.dropna(subset=["FTR_IDN"])

        result = get_fatigue_by_ftr_idn(clean_df, "0520")

        assert len(result) == 4
        assert result["1001.0"] == 0.001  # float을 str로 변환하면 1001.0이 됨
        assert result["1002.0"] == 0.005
        assert result["1003.0"] == 0.015
        assert result["1005.0"] == 0.5

    @patch("builtins.print")
    def test_get_fatigue_by_ftr_idn_column_not_found(self, mock_print, mock_fatigue_df):
        """D_final 컬럼이 없는 경우 테스트"""
        clean_df = mock_fatigue_df.dropna(subset=["FTR_IDN"])

        result = get_fatigue_by_ftr_idn(clean_df, "9999")

        # 다른 D_final 컬럼을 찾아서 사용
        assert len(result) == 4
        mock_print.assert_any_call("경고: 9999_D_final 컬럼을 찾을 수 없습니다.")
        mock_print.assert_any_call("대체 컬럼 사용: 0520_D_final")

    def test_get_fatigue_by_ftr_idn_no_d_final_columns(self):
        """D_final 컬럼이 전혀 없는 경우 테스트"""
        df = pd.DataFrame({"FTR_IDN": [1001, 1002], "other_col": [1, 2]})

        with patch("builtins.print"):
            result = get_fatigue_by_ftr_idn(df, "0520")

        assert result == {}


class TestGetFatigueInfo:
    """get_fatigue_info 함수 테스트"""

    def test_get_fatigue_info_complete(self, mock_fatigue_df):
        """완전한 정보 반환 테스트"""
        result = get_fatigue_info(mock_fatigue_df)

        # 기본 정보
        assert result["total_records"] == 5
        assert "FTR_IDN" in result["columns"]
        assert "0520_D_final" in result["columns"]

        # FTR_IDN 정보 (NaN 제외하고 계산)
        assert result["unique_ftr_idn"] == 4

        # D_final 컬럼 정보
        assert "d_final_columns" in result
        assert "0520_D_final" in result["d_final_columns"]
        assert "0903_D_final" in result["d_final_columns"]

        # 통계 정보
        assert "d_final_stats" in result
        assert "0520_D_final" in result["d_final_stats"]

        stats_0520 = result["d_final_stats"]["0520_D_final"]
        assert "min" in stats_0520
        assert "max" in stats_0520
        assert "mean" in stats_0520
        assert "std" in stats_0520

        # 값 검증
        assert stats_0520["min"] == 0.001
        assert stats_0520["max"] == 0.5

    def test_get_fatigue_info_no_ftr_idn(self):
        """FTR_IDN이 없는 DataFrame 테스트"""
        df = pd.DataFrame({"other_col": [1, 2, 3], "0520_D_final": [0.1, 0.2, 0.3]})

        result = get_fatigue_info(df)

        assert result["total_records"] == 3
        assert "unique_ftr_idn" not in result
        assert "d_final_columns" in result

    def test_get_fatigue_info_no_d_final(self):
        """D_final 컬럼이 없는 DataFrame 테스트"""
        df = pd.DataFrame({"FTR_IDN": [1001, 1002], "other_col": [1, 2]})

        result = get_fatigue_info(df)

        assert result["total_records"] == 2
        assert result["unique_ftr_idn"] == 2
        assert "d_final_columns" not in result
        assert "d_final_stats" not in result

    def test_get_fatigue_info_empty_dataframe(self):
        """빈 DataFrame 테스트"""
        df = pd.DataFrame()

        result = get_fatigue_info(df)

        assert result["total_records"] == 0
        assert result["columns"] == []
        assert "unique_ftr_idn" not in result
