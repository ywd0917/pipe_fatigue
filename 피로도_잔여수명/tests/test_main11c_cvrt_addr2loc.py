"""
main11c_cvrt_addr2loc.py 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.main11c_cvrt_addr2loc import (
    create_work_datetime_column,
    load_and_process_data,
    add_geocoding,
    save_results,
)


class TestCreateWorkDatetimeColumn:
    """작업일시 컬럼 생성 테스트"""

    def test_normal_receipt_numbers(self):
        """정상적인 접수번호 처리"""
        df = pd.DataFrame(
            {
                "접수번호": ["20220102-0001", "20230305-0002", "20240615-0003"],
                "공사일자": ["01-02", "03-05", "06-15"],
            }
        )

        result = create_work_datetime_column(df)

        assert "작업일시" in result.columns
        assert result["작업일시"].iloc[0] == "2022-01-02"
        assert result["작업일시"].iloc[1] == "2023-03-05"
        assert result["작업일시"].iloc[2] == "2024-06-15"

    def test_missing_receipt_numbers(self):
        """접수번호가 없는 경우 처리"""
        df = pd.DataFrame(
            {
                "접수번호": ["20220102-0001", "-", "20220304-0003"],
                "공사일자": ["01-02", "02-15", "03-04"],
            }
        )

        result = create_work_datetime_column(df)

        # 두 번째 행은 이전 유효 년도(2022) 사용
        assert result["작업일시"].iloc[1] == "2022-02-15"
        assert result["작업일시"].iloc[2] == "2022-03-04"

    def test_invalid_receipt_numbers(self):
        """비정상 접수번호 처리"""
        df = pd.DataFrame(
            {
                "접수번호": ["20220102-0001", "INVALID", "20230405-0003"],
                "공사일자": ["01-02", "03-15", "04-05"],
            }
        )

        result = create_work_datetime_column(df)

        # 비정상 접수번호는 이전 유효 년도 사용
        assert result["작업일시"].iloc[0] == "2022-01-02"
        assert result["작업일시"].iloc[1] == "2022-03-15"  # 이전 년도 사용
        assert result["작업일시"].iloc[2] == "2023-04-05"

    def test_no_valid_year_fallback(self):
        """유효한 년도가 없을 때 기본값 사용"""
        df = pd.DataFrame(
            {"접수번호": ["-", "-", "-"], "공사일자": ["01-01", "02-02", "03-03"]}
        )

        result = create_work_datetime_column(df)

        # 모두 기본 년도(2024) 사용
        assert result["작업일시"].iloc[0] == "2024-01-01"
        assert result["작업일시"].iloc[1] == "2024-02-02"
        assert result["작업일시"].iloc[2] == "2024-03-03"

    def test_invalid_work_date(self):
        """잘못된 공사일자 처리"""
        df = pd.DataFrame(
            {
                "접수번호": ["20220102-0001", "20220203-0002"],
                "공사일자": ["01-02", "INVALID"],
            }
        )

        result = create_work_datetime_column(df)

        assert result["작업일시"].iloc[0] == "2022-01-02"
        assert pd.isna(result["작업일시"].iloc[1])  # 파싱 실패시 None


class TestLoadAndProcessData:
    """데이터 로드 및 전처리 테스트"""

    def test_load_csv_with_excluded_rows(self):
        """계/소계 행 제외 테스트"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write("지시번호,접수번호,공사일자,위치\n")
            f.write("1,20220102-0001,01-02,주소1\n")
            f.write("계,,,\n")
            f.write("2,20220103-0002,01-03,주소2\n")
            f.write("소계,,,\n")
            f.write("3,20220104-0003,01-04,주소3\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            df = load_and_process_data(temp_path)

            assert len(df) == 3  # 계/소계 제외
            assert "1" in df["지시번호"].values
            assert "2" in df["지시번호"].values
            assert "3" in df["지시번호"].values
            assert "계" not in df["지시번호"].values
            assert "소계" not in df["지시번호"].values
        finally:
            temp_path.unlink()

    def test_load_empty_file(self):
        """빈 파일 처리"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write("지시번호,접수번호,공사일자,위치\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            df = load_and_process_data(temp_path)
            assert len(df) == 0
        finally:
            temp_path.unlink()


class TestAddGeocoding:
    """지오코딩 기능 테스트"""

    @patch("src.main11c_cvrt_addr2loc.geocode_addresses")
    def test_geocoding_with_valid_addresses(self, mock_geocode):
        """유효한 주소 지오코딩"""
        # Mock 설정
        mock_geocode.return_value = (
            [35.8, 35.9, None],  # 위도
            [128.6, 128.7, None],  # 경도
            ["주소3"],  # 실패 주소
        )

        df = pd.DataFrame({"위치": ["동구 신평동 123", "동구 효목동 456", "주소3"]})

        result_df, failed = add_geocoding(df, use_cache=True, no_api=False)

        assert "위도" in result_df.columns
        assert "경도" in result_df.columns
        assert result_df["위도"].iloc[0] == 35.8
        assert result_df["경도"].iloc[0] == 128.6
        assert result_df["위도"].iloc[1] == 35.9
        assert result_df["경도"].iloc[1] == 128.7
        assert pd.isna(result_df["위도"].iloc[2])
        assert len(failed) == 1
        assert failed[0] == "주소3"

    def test_geocoding_without_location_column(self):
        """위치 컬럼이 없는 경우"""
        df = pd.DataFrame({"접수번호": ["20220102-0001"], "공사일자": ["01-02"]})

        with pytest.raises(ValueError, match="위치 컬럼이 필요합니다"):
            add_geocoding(df)

    @patch("src.main11c_cvrt_addr2loc.geocode_addresses")
    def test_geocoding_offline_mode(self, mock_geocode):
        """오프라인 모드 테스트"""
        mock_geocode.return_value = ([35.8], [128.6], [])

        df = pd.DataFrame({"위치": ["동구 신평동 123"]})

        result_df, failed = add_geocoding(df, use_cache=True, no_api=True)

        # no_api=True로 호출되었는지 확인
        mock_geocode.assert_called_once()
        call_args = mock_geocode.call_args[1]
        assert call_args["no_api"] == True


class TestSaveResults:
    """결과 저장 테스트"""

    def test_save_with_all_data(self):
        """모든 데이터 저장"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_file = temp_path / "test_output.csv"

            df = pd.DataFrame(
                {
                    "지시번호": ["1", "2", "3"],
                    "접수번호": ["20220102-0001", "20220103-0002", "-"],
                    "공사일자": ["01-02", "01-03", "01-04"],
                    "위치": ["주소1", "주소2", "주소3"],
                    "작업일시": ["2022-01-02", "2022-01-03", "2022-01-04"],
                    "위도": [35.8, 35.9, None],
                    "경도": [128.6, 128.7, None],
                }
            )

            failed_addresses = ["주소3"]

            save_results(df, output_file, failed_addresses)

            # 파일이 생성되었는지 확인
            assert output_file.exists()

            # 저장된 데이터 확인
            saved_df = pd.read_csv(output_file, encoding="utf-8-sig")
            assert len(saved_df) == 3
            assert "작업일시" in saved_df.columns
            assert "위도" in saved_df.columns
            assert "경도" in saved_df.columns

            # 실패 주소 파일 확인
            failed_file = output_file.parent / f"{output_file.stem}_실패주소.txt"
            assert failed_file.exists()

            with open(failed_file, "r", encoding="utf-8") as f:
                content = f.read()
                assert "주소3" in content
                assert "1개" in content

    def test_save_without_failed_addresses(self):
        """실패 주소가 없는 경우"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_file = temp_path / "test_output.csv"

            df = pd.DataFrame(
                {
                    "지시번호": ["1"],
                    "작업일시": ["2022-01-02"],
                    "위도": [35.8],
                    "경도": [128.6],
                }
            )

            save_results(df, output_file, [])

            assert output_file.exists()

            # 실패 주소 파일이 생성되지 않았는지 확인
            failed_file = output_file.parent / f"{output_file.stem}_실패주소.txt"
            assert not failed_file.exists()


class TestIntegration:
    """통합 테스트"""

    @patch("src.main11c_cvrt_addr2loc.load_geocoding_service")
    @patch("src.main11c_cvrt_addr2loc.geocode_addresses")
    def test_full_workflow(self, mock_geocode, mock_load_service):
        """전체 워크플로우 테스트"""
        # Mock 설정
        mock_geocode.return_value = (
            [35.8, 35.9],  # 위도
            [128.6, 128.7],  # 경도
            [],  # 실패 주소 없음
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 입력 파일 생성
            input_file = temp_path / "test_input.csv"
            with open(input_file, "w", encoding="utf-8-sig") as f:
                f.write("지시번호,접수번호,공사일자,위치\n")
                f.write("1,20220102-0001,01-02,동구 신평동 123\n")
                f.write("계,,,\n")  # 제외될 행
                f.write("2,20220103-0002,01-03,동구 효목동 456\n")

            # 처리
            df = load_and_process_data(input_file)
            df = create_work_datetime_column(df)
            df, failed = add_geocoding(df, use_cache=False, no_api=False)

            output_file = temp_path / "output.csv"
            save_results(df, output_file, failed)

            # 결과 확인
            assert output_file.exists()
            result_df = pd.read_csv(output_file, encoding="utf-8-sig")

            assert len(result_df) == 2  # 계 행 제외
            assert result_df["작업일시"].iloc[0] == "2022-01-02"
            assert result_df["작업일시"].iloc[1] == "2022-01-03"
            assert result_df["위도"].iloc[0] == 35.8
            assert result_df["경도"].iloc[1] == 128.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
