"""
repair_loader.py 테스트
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.repair_loader import (
    filter_by_smlz,
    get_repair_data_dir,
    get_repair_file_types,
    get_repair_stats,
    load_all_repair_data,
    load_repair_data,
    validate_repair_data,
)


@pytest.fixture
def mock_repair_df():
    """테스트용 복구 작업 DataFrame"""
    data = {
        "구군": ["중구", "서구", "중구", "남구", "서구"],
        "주소": ["주소1", "주소2", "주소3", "주소4", "주소5"],
        "소구역번호": ["001", "002", "003", "", "005"],
        "복구공사구분": ["긴급", "일반", "긴급", "일반", "긴급"],
        "공사명": ["공사1", "공사2", "공사3", "공사4", "공사5"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_base_dir(tmp_path):
    """테스트용 기본 디렉토리"""
    return tmp_path


class TestGetRepairDataDir:
    """get_repair_data_dir 함수 테스트"""

    def test_get_repair_data_dir_from_data_with_sample(self, mock_base_dir):
        """data 디렉토리에서 sample 사용 테스트"""
        data_dir = mock_base_dir / "data"
        repair_dir = data_dir / "repair"
        sample_dir = repair_dir / "sample"
        sample_dir.mkdir(parents=True)

        result = get_repair_data_dir(data_dir, use_sample=True)

        assert result == sample_dir

    def test_get_repair_data_dir_from_data_no_sample(self, mock_base_dir):
        """data 디렉토리에서 sample 없이 테스트"""
        data_dir = mock_base_dir / "data"
        repair_dir = data_dir / "repair"
        repair_dir.mkdir(parents=True)

        result = get_repair_data_dir(data_dir, use_sample=True)

        assert result == repair_dir

    def test_get_repair_data_dir_from_raw(self, mock_base_dir):
        """raw 디렉토리에서 테스트"""
        raw_dir = mock_base_dir / "data" / "raw"
        raw_dir.mkdir(parents=True)

        result = get_repair_data_dir(raw_dir, use_sample=False)

        expected = raw_dir.parent / "repair"
        assert result == expected

    def test_get_repair_data_dir_use_sample_false(self, mock_base_dir):
        """use_sample=False 테스트"""
        data_dir = mock_base_dir / "data"
        repair_dir = data_dir / "repair"
        sample_dir = repair_dir / "sample"
        sample_dir.mkdir(parents=True)

        result = get_repair_data_dir(data_dir, use_sample=False)

        assert result == repair_dir


class TestGetRepairFileTypes:
    """get_repair_file_types 함수 테스트"""

    def test_get_repair_file_types(self):
        """복구 작업 파일 타입 반환 테스트"""
        result = get_repair_file_types()

        assert isinstance(result, dict)
        assert "긴급복구" in result
        assert result["긴급복구"] == "긴급복구"

    def test_get_repair_file_types_no_other_types(self):
        """다른 타입들이 주석처리되어 있는지 확인"""
        result = get_repair_file_types()

        # 현재는 긴급복구만 활성화
        assert len(result) == 1
        assert list(result.keys()) == ["긴급복구"]


class TestValidateRepairData:
    """validate_repair_data 함수 테스트"""

    def test_validate_repair_data_success(self, mock_repair_df):
        """정상적인 데이터 검증 테스트"""
        required_columns = ["구군", "주소"]

        with patch("builtins.print") as mock_print:
            result = validate_repair_data(mock_repair_df, required_columns)

        # 빈 소구역번호가 있는 행이 제거되었는지 확인
        assert len(result) == 4  # 원래 5개에서 빈 값 1개 제거
        assert "" not in result["소구역번호"].values

        # 경고 메시지 출력 확인
        mock_print.assert_called_with("경고: 소구역번호가 없는 행 1개 제거")

    def test_validate_repair_data_missing_column(self, mock_repair_df):
        """필수 컬럼이 없는 경우 테스트"""
        required_columns = ["구군", "missing_column"]

        with pytest.raises(ValueError, match="필수 컬럼이 누락되었습니다"):
            validate_repair_data(mock_repair_df, required_columns)

    def test_validate_repair_data_no_smlz_column(self):
        """소구역번호 컬럼이 없는 DataFrame 테스트"""
        df = pd.DataFrame({"구군": ["중구", "서구"], "주소": ["주소1", "주소2"]})
        required_columns = ["구군", "주소"]

        result = validate_repair_data(df, required_columns)

        # 소구역번호 컬럼이 없으면 필터링이 실행되지 않음
        assert len(result) == 2

    def test_validate_repair_data_with_variations(self):
        """소구역번호 컬럼명 변형 테스트"""
        df = pd.DataFrame(
            {
                "구군": ["중구", "서구"],
                "주소": ["주소1", "주소2"],
                " 소구역번호 ": ["001", "002"],  # 공백 포함
            }
        )
        required_columns = ["구군", "주소"]

        result = validate_repair_data(df, required_columns)

        assert len(result) == 2


class TestLoadRepairData:
    """load_repair_data 함수 테스트"""

    def test_load_repair_data_success(self, tmp_path, mock_repair_df):
        """정상적인 CSV 로딩 테스트"""
        # CSV 파일 생성
        csv_path = tmp_path / "test_repair.csv"
        mock_repair_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        with patch("builtins.print") as mock_print:
            result = load_repair_data(csv_path, verbose=True)

        assert result is not None
        assert len(result) == 4  # 빈 소구역번호 행 제거됨
        assert list(result.columns) == list(mock_repair_df.columns)

        # 출력 메시지 확인
        assert any(
            "데이터 로드 완료" in str(call) for call in mock_print.call_args_list
        )
        assert any(
            "구군별 작업 건수" in str(call) for call in mock_print.call_args_list
        )

    def test_load_repair_data_file_not_found(self, tmp_path):
        """파일이 없는 경우 테스트"""
        csv_path = tmp_path / "nonexistent.csv"

        with patch("builtins.print") as mock_print:
            result = load_repair_data(csv_path, verbose=True)

        assert result is None
        mock_print.assert_called_with(f"오류: CSV 파일을 찾을 수 없습니다: {csv_path}")

    def test_load_repair_data_with_default_columns(self, tmp_path):
        """기본 필수 컬럼으로 테스트"""
        test_data = {"구군": ["중구"], "주소": ["주소1"]}
        csv_path = tmp_path / "test_repair.csv"
        pd.DataFrame(test_data).to_csv(csv_path, index=False, encoding="utf-8-sig")

        result = load_repair_data(csv_path, required_columns=None, verbose=False)

        assert result is not None
        assert "구군" in result.columns
        assert "주소" in result.columns

    def test_load_repair_data_exception_handling(self, tmp_path):
        """CSV 읽기 예외 처리 테스트"""
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text("invalid content")

        with (
            patch("pandas.read_csv", side_effect=Exception("Read error")),
            patch("builtins.print") as mock_print,
        ):
            result = load_repair_data(csv_path, verbose=True)

        assert result is None
        assert any(
            "CSV 데이터 로드 실패" in str(call) for call in mock_print.call_args_list
        )


class TestFilterBySmlz:
    """filter_by_smlz 함수 테스트"""

    def test_filter_by_smlz_success(self, mock_repair_df):
        """정상적인 소구역 필터링 테스트"""
        # 빈 값 제거
        clean_df = mock_repair_df[mock_repair_df["소구역번호"] != ""]

        smlz_numbers = ["001", "003", "999"]  # 999는 없는 번호
        result = filter_by_smlz(clean_df, smlz_numbers)

        assert len(result) == 2  # 001, 003만 매칭
        assert "001" in result["소구역번호"].values
        assert "003" in result["소구역번호"].values

    def test_filter_by_smlz_no_column(self):
        """소구역번호 컬럼이 없는 경우 테스트"""
        df = pd.DataFrame({"구군": ["중구", "서구"], "주소": ["주소1", "주소2"]})

        with patch("builtins.print") as mock_print:
            result = filter_by_smlz(df, ["001", "002"])

        # 원본 DataFrame 반환
        assert len(result) == 2
        mock_print.assert_called_with("경고: 소구역번호 컬럼을 찾을 수 없습니다.")

    def test_filter_by_smlz_empty_list(self, mock_repair_df):
        """빈 필터 리스트 테스트"""
        result = filter_by_smlz(mock_repair_df, [])

        assert len(result) == 0

    def test_filter_by_smlz_type_conversion(self, mock_repair_df):
        """타입 변환 테스트 (숫자를 문자열로)"""
        smlz_numbers = [1, 2, 3]  # 숫자 리스트
        result = filter_by_smlz(mock_repair_df, smlz_numbers)

        # 숫자가 문자열로 변환되어 매칭되지 않음 (001 != 1)
        assert len(result) == 0


class TestGetRepairStats:
    """get_repair_stats 함수 테스트"""

    def test_get_repair_stats_complete(self, mock_repair_df):
        """완전한 통계 정보 반환 테스트"""
        result = get_repair_stats(mock_repair_df)

        # 기본 정보
        assert result["total_records"] == 5
        assert "구군" in result["columns"]
        assert "소구역번호" in result["columns"]

        # 구군별 통계
        assert "by_district" in result
        assert result["by_district"]["중구"] == 2
        assert result["by_district"]["서구"] == 2
        assert result["by_district"]["남구"] == 1

        # 소구역별 통계
        assert "by_smlz" in result
        assert "unique_smlz_count" in result
        assert result["unique_smlz_count"] == 5  # 빈 값 포함

        # 복구공사구분별 통계
        assert "by_work_type" in result
        assert result["by_work_type"]["긴급"] == 3
        assert result["by_work_type"]["일반"] == 2

    def test_get_repair_stats_missing_columns(self):
        """일부 컬럼이 없는 경우 테스트"""
        df = pd.DataFrame({"구군": ["중구", "서구"], "주소": ["주소1", "주소2"]})

        result = get_repair_stats(df)

        assert result["total_records"] == 2
        assert "by_district" in result
        assert "by_smlz" not in result
        assert "by_work_type" not in result

    def test_get_repair_stats_empty_dataframe(self):
        """빈 DataFrame 테스트"""
        df = pd.DataFrame()

        result = get_repair_stats(df)

        assert result["total_records"] == 0
        assert result["columns"] == []


class TestLoadAllRepairData:
    """load_all_repair_data 함수 테스트"""

    def test_load_all_repair_data_success(self, tmp_path):
        """모든 복구 데이터 로딩 성공 테스트"""
        # repair 디렉토리 생성
        repair_dir = tmp_path / "repair"
        repair_dir.mkdir()

        # 긴급복구 파일 생성
        emergency_data = {
            "구군": ["중구", "서구"],
            "주소": ["주소1", "주소2"],
            "소구역번호": ["001", "002"],
        }
        emergency_file = repair_dir / "긴급복구.csv"
        pd.DataFrame(emergency_data).to_csv(
            emergency_file, index=False, encoding="utf-8-sig"
        )

        with patch("builtins.print"):
            result = load_all_repair_data(tmp_path, verbose=True, use_sample=False)

        assert len(result) == 1
        assert "긴급복구" in result
        assert len(result["긴급복구"]) == 2

    def test_load_all_repair_data_with_sample(self, tmp_path):
        """샘플 디렉토리 우선 사용 테스트"""
        # repair/sample 디렉토리 생성
        sample_dir = tmp_path / "repair" / "sample"
        sample_dir.mkdir(parents=True)

        # 샘플 긴급복구 파일 생성
        sample_data = {"구군": ["중구"], "주소": ["샘플주소"], "소구역번호": ["999"]}
        sample_file = sample_dir / "긴급복구.csv"
        pd.DataFrame(sample_data).to_csv(sample_file, index=False, encoding="utf-8-sig")

        with patch("builtins.print"):
            result = load_all_repair_data(tmp_path, verbose=True, use_sample=True)

        assert len(result) == 1
        assert "긴급복구" in result
        assert result["긴급복구"]["주소"].iloc[0] == "샘플주소"

    def test_load_all_repair_data_no_files(self, tmp_path):
        """파일이 없는 경우 테스트"""
        repair_dir = tmp_path / "repair"
        repair_dir.mkdir()

        result = load_all_repair_data(tmp_path, verbose=False, use_sample=False)

        assert result == {}

    def test_load_all_repair_data_empty_file(self, tmp_path):
        """빈 파일인 경우 테스트"""
        repair_dir = tmp_path / "repair"
        repair_dir.mkdir()

        # 빈 DataFrame으로 파일 생성
        empty_file = repair_dir / "긴급복구.csv"
        pd.DataFrame().to_csv(empty_file, index=False, encoding="utf-8-sig")

        with patch("builtins.print"):
            result = load_all_repair_data(tmp_path, verbose=True, use_sample=False)

        # 빈 DataFrame은 결과에 포함되지 않음
        assert result == {}
