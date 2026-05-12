"""
main11_convert_addr2loc.py 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock
import numpy as np

import pandas as pd
import pytest

from src.main11_convert_addr2loc import (
    geocode_addresses,
    get_repair2_files,
    load_geocoding_service,
    preprocess_address,
    process_csv_file,
    parse_numeric_date_column,
)


class TestParseNumericDateColumn:
    """숫자 형식 날짜 파싱 테스트"""

    def test_parse_numeric_format(self):
        """숫자 형식 날짜 정상 파싱"""
        df = pd.DataFrame(
            {"접수일시": [202206230912.0, 202207251313.0, 202208151430.0]}
        )
        dates = parse_numeric_date_column(df, "접수일시")

        assert isinstance(dates, pd.Series)
        assert dates.iloc[0] == pd.Timestamp("2022-06-23 09:12:00")
        assert dates.iloc[1] == pd.Timestamp("2022-07-25 13:13:00")
        assert dates.iloc[2] == pd.Timestamp("2022-08-15 14:30:00")

    def test_parse_with_nan(self):
        """NaN 값 처리"""
        df = pd.DataFrame({"작업시작일시": [202206230912.0, np.nan, 202208151430.0]})
        dates = parse_numeric_date_column(df, "작업시작일시")

        assert dates.iloc[0] == pd.Timestamp("2022-06-23 09:12:00")
        assert pd.isna(dates.iloc[1])
        assert dates.iloc[2] == pd.Timestamp("2022-08-15 14:30:00")

    def test_parse_invalid_year(self):
        """비정상 연도 필터링"""
        df = pd.DataFrame(
            {"작업종료일": [199912312359.0, 202206230912.0, 203101010000.0]}
        )
        dates = parse_numeric_date_column(df, "작업종료일")

        assert pd.isna(dates.iloc[0])  # 1999년
        assert dates.iloc[1] == pd.Timestamp("2022-06-23 09:12:00")  # 정상
        assert pd.isna(dates.iloc[2])  # 2031년

    def test_parse_missing_column(self):
        """존재하지 않는 컬럼 처리"""
        df = pd.DataFrame({"주소": ["대구 북구", "대구 수성구"]})
        dates = parse_numeric_date_column(df, "작업일시")

        assert isinstance(dates, pd.Series)
        assert dates.isna().all()
        assert len(dates) == len(df)

    def test_parse_mixed_formats(self):
        """다양한 형식 혼재"""
        df = pd.DataFrame(
            {"접수일시": [202206230912.0, "202207251313", 202208151430, None, ""]}
        )
        dates = parse_numeric_date_column(df, "접수일시")

        assert dates.iloc[0] == pd.Timestamp("2022-06-23 09:12:00")
        assert dates.iloc[1] == pd.Timestamp("2022-07-25 13:13:00")
        assert dates.iloc[2] == pd.Timestamp("2022-08-15 14:30:00")
        assert pd.isna(dates.iloc[3])
        assert pd.isna(dates.iloc[4])


class TestGeocodingService:
    """Geocoding 서비스 로드 테스트"""

    def test_load_naver_service(self):
        """Naver 서비스 로드"""
        load_geocoding_service("naver")

        # 전역 변수가 설정되었는지 확인
        import src.main11_convert_addr2loc

        assert src.main11_convert_addr2loc.GEOCODING_SERVICE == "naver"
        assert src.main11_convert_addr2loc.geocode_address is not None
        assert src.main11_convert_addr2loc.check_api_credentials is not None

    def test_load_kakao_service(self):
        """Kakao 서비스 로드"""
        load_geocoding_service("kakao")

        # 전역 변수가 설정되었는지 확인
        import src.main11_convert_addr2loc

        assert src.main11_convert_addr2loc.GEOCODING_SERVICE == "kakao"
        assert src.main11_convert_addr2loc.geocode_address is not None
        assert src.main11_convert_addr2loc.check_api_credentials is not None

    def test_load_invalid_service(self):
        """잘못된 서비스 로드"""
        with pytest.raises(ValueError, match="지원하지 않는 geocoding 서비스"):
            load_geocoding_service("invalid")


class TestPreprocessAddress:
    """주소 전처리 테스트"""

    def test_preprocess_none(self):
        """None 입력"""
        assert preprocess_address(None) is None

    def test_preprocess_empty_string(self):
        """빈 문자열"""
        assert preprocess_address("") == ""

    def test_preprocess_with_slash(self):
        """슬래시 포함 주소"""
        address = "대구광역시 달서구 성당로 123 / 성당동"
        result = preprocess_address(address)
        assert result == "대구광역시 달서구 성당로 123"

    def test_preprocess_with_parentheses(self):
        """괄호 포함 주소"""
        address = "대구광역시 달서구 성당로 123 (성당동)"
        result = preprocess_address(address)
        assert result == "대구광역시 달서구 성당로 123"

    def test_preprocess_with_special_keywords(self):
        """특수 키워드 포함"""
        address = "대구광역시 북구 읍내동 1236-4 폐전"
        result = preprocess_address(address)
        assert result == "대구광역시 북구 읍내동 1236-4"

    def test_preprocess_without_city(self):
        """시도명 없는 주소"""
        address = "달서구 성당로 123"
        result = preprocess_address(address)
        assert result == "대구 달서구 성당로 123"


class TestGeocodeAddresses:
    """주소 변환 테스트"""

    def test_geocode_without_credentials(self):
        """API 자격 증명 없음"""
        load_geocoding_service("naver")

        # 모듈 임포트 후 함수 mock
        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=False)

        try:
            addresses = ["대구광역시 달서구 성당로 123"]
            lats, lons, failed = geocode_addresses(addresses)

            # API 자격 증명이 없으면 모든 값이 None이어야 함
            assert lats == [None]
            assert lons == [None]
            assert failed == []
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check

    def test_geocode_success(self):
        """정상적인 주소 변환"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        src.main11_convert_addr2loc.geocode_address = Mock(return_value=(35.8, 128.5))

        try:
            addresses = ["대구광역시 달서구 성당로 123"]
            lats, lons, failed = geocode_addresses(addresses)

            assert lats == [35.8]
            assert lons == [128.5]
            assert failed == []
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_geocode_failure(self):
        """주소 변환 실패"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        src.main11_convert_addr2loc.geocode_address = Mock(return_value=None)

        try:
            addresses = ["존재하지 않는 주소"]
            lats, lons, failed = geocode_addresses(addresses)

            assert lats == [None]
            assert lons == [None]
            assert failed == ["존재하지 않는 주소"]
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_geocode_mixed_results(self):
        """일부 성공, 일부 실패"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        mock_geocode = Mock()
        mock_geocode.side_effect = [(35.8, 128.5), None, (35.9, 128.6)]
        src.main11_convert_addr2loc.geocode_address = mock_geocode

        try:
            addresses = ["주소1", "주소2", "주소3"]
            lats, lons, failed = geocode_addresses(addresses)

            assert lats == [35.8, None, 35.9]
            assert lons == [128.5, None, 128.6]
            assert failed == ["주소2"]
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_geocode_with_none_addresses(self):
        """None이 포함된 주소 리스트"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        mock_geocode = Mock()
        mock_geocode.side_effect = [(35.8, 128.5), (35.9, 128.6)]
        src.main11_convert_addr2loc.geocode_address = mock_geocode

        try:
            addresses = ["주소1", None, "", "nan", "주소2"]
            lats, lons, failed = geocode_addresses(addresses)

            assert len(lats) == 5
            assert len(lons) == 5
            assert lats[0] == 35.8
            assert lats[1] is None  # None
            assert lats[2] is None  # empty string
            assert lats[3] is None  # "nan"
            assert lats[4] == 35.9
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode


class TestProcessCSVFile:
    """CSV 파일 처리 테스트"""

    def test_process_csv_without_address_column(self):
        """주소 컬럼이 없는 CSV"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "test.csv"
            output_path = Path(tmp_dir) / "output.csv"

            # 주소 컬럼이 없는 데이터
            df = pd.DataFrame({"이름": ["A", "B"], "값": [1, 2]})
            df.to_csv(input_path, index=False, encoding="utf-8-sig")

            load_geocoding_service("naver")
            process_csv_file(input_path, output_path, verbose=False)

            # 출력 파일이 생성되지 않아야 함
            assert not output_path.exists()

    def test_process_csv_success(self):
        """정상적인 CSV 처리"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        src.main11_convert_addr2loc.geocode_address = Mock(return_value=(35.8, 128.5))

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = Path(tmp_dir) / "test.csv"
                output_path = Path(tmp_dir) / "output.csv"

                # 테스트 데이터
                df = pd.DataFrame(
                    {
                        "주소": [
                            "대구광역시 달서구 성당로 123",
                            "대구광역시 북구 대학로 80",
                        ],
                        "값": [1, 2],
                    }
                )
                df.to_csv(input_path, index=False, encoding="utf-8-sig")

                process_csv_file(input_path, output_path, verbose=False)

                # 결과 확인
                assert output_path.exists()
                result_df = pd.read_csv(output_path, encoding="utf-8-sig")

                assert "위도" in result_df.columns
                assert "경도" in result_df.columns
                assert len(result_df) == 2
                assert result_df["위도"][0] == 35.8
                assert result_df["경도"][0] == 128.5
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_process_csv_with_date_columns(self):
        """날짜 컬럼과 작업일시 생성 테스트"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        src.main11_convert_addr2loc.geocode_address = Mock(return_value=(35.8, 128.5))

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = Path(tmp_dir) / "test.csv"
                output_path = Path(tmp_dir) / "output.csv"

                # 날짜 컬럼이 있는 테스트 데이터
                df = pd.DataFrame(
                    {
                        "주소": [
                            "대구광역시 달서구 성당로 123",
                            "대구광역시 북구 대학로 80",
                        ],
                        "접수일시": [202206230912.0, np.nan],
                        "작업시작일시": [np.nan, 202207251313.0],
                        "작업종료일": [202206231130.0, 202207251530.0],
                    }
                )
                df.to_csv(input_path, index=False, encoding="utf-8-sig")

                process_csv_file(input_path, output_path, verbose=False)

                # 결과 확인
                assert output_path.exists()
                result_df = pd.read_csv(output_path, encoding="utf-8-sig")

                # 작업일시 컬럼이 추가되었는지 확인
                assert "작업일시" in result_df.columns

                # 우선순위에 따른 날짜 확인 (접수일시 > 작업시작일시 > 작업종료일)
                # 첫 번째 행: 접수일시가 있으므로 2022-06-23 09:12
                assert pd.to_datetime(result_df["작업일시"][0]) == pd.Timestamp(
                    "2022-06-23 09:12:00"
                )

                # 두 번째 행: 접수일시가 없고, 작업시작일시가 있으므로 2022-07-25 13:13
                assert pd.to_datetime(result_df["작업일시"][1]) == pd.Timestamp(
                    "2022-07-25 13:13:00"
                )
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_process_csv_date_priority(self):
        """날짜 우선순위 확인 테스트"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        src.main11_convert_addr2loc.geocode_address = Mock(return_value=(35.8, 128.5))

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = Path(tmp_dir) / "test.csv"
                output_path = Path(tmp_dir) / "output.csv"

                # 모든 날짜 컬럼이 있는 경우 - 접수일시가 우선
                df = pd.DataFrame(
                    {
                        "주소": ["대구 북구", "대구 수성구", "대구 달서구"],
                        "접수일시": [202206230900.0, np.nan, np.nan],
                        "작업시작일시": [202206231000.0, 202207251000.0, np.nan],
                        "작업종료일": [202206231100.0, 202207251100.0, 202208151100.0],
                    }
                )
                df.to_csv(input_path, index=False, encoding="utf-8-sig")

                process_csv_file(input_path, output_path, verbose=False)

                result_df = pd.read_csv(output_path, encoding="utf-8-sig")

                # 첫 번째 행: 접수일시 우선 (09:00)
                assert pd.to_datetime(result_df["작업일시"][0]) == pd.Timestamp(
                    "2022-06-23 09:00:00"
                )

                # 두 번째 행: 접수일시 없음, 작업시작일시 사용 (10:00)
                assert pd.to_datetime(result_df["작업일시"][1]) == pd.Timestamp(
                    "2022-07-25 10:00:00"
                )

                # 세 번째 행: 접수일시, 작업시작일시 없음, 작업종료일 사용 (11:00)
                assert pd.to_datetime(result_df["작업일시"][2]) == pd.Timestamp(
                    "2022-08-15 11:00:00"
                )
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode

    def test_process_csv_with_failed_addresses(self):
        """실패한 주소가 있는 경우"""
        load_geocoding_service("naver")

        import src.main11_convert_addr2loc

        original_check = src.main11_convert_addr2loc.check_api_credentials
        original_geocode = src.main11_convert_addr2loc.geocode_address

        src.main11_convert_addr2loc.check_api_credentials = Mock(return_value=True)
        mock_geocode = Mock()
        mock_geocode.side_effect = [(35.8, 128.5), None]
        src.main11_convert_addr2loc.geocode_address = mock_geocode

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                input_path = Path(tmp_dir) / "test.csv"
                output_path = Path(tmp_dir) / "output.csv"

                # 테스트 데이터
                df = pd.DataFrame({"주소": ["성공주소", "실패주소"], "값": [1, 2]})
                df.to_csv(input_path, index=False, encoding="utf-8-sig")

                process_csv_file(input_path, output_path, verbose=False)

                # 결과 파일 확인
                assert output_path.exists()

                # 실패 주소 파일 확인
                failed_file = output_path.parent / f"{output_path.stem}_실패주소.txt"
                assert failed_file.exists()

                with failed_file.open(encoding="utf-8") as f:
                    content = f.read()
                    assert "실패주소" in content
        finally:
            src.main11_convert_addr2loc.check_api_credentials = original_check
            src.main11_convert_addr2loc.geocode_address = original_geocode


class TestGetRepair2Files:
    """repair2 파일 찾기 테스트"""

    def test_get_files_no_directory(self):
        """디렉토리가 없는 경우"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir) / "data"
            files = get_repair2_files(data_dir)
            assert files == []

    def test_get_files_with_csv(self):
        """CSV 파일이 있는 경우"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            data_dir = Path(tmp_dir) / "data"
            repair2_dir = data_dir / "repair2"
            repair2_dir.mkdir(parents=True)

            # CSV 파일 생성
            (repair2_dir / "file1.csv").touch()
            (repair2_dir / "file2.csv").touch()
            (repair2_dir / "other.txt").touch()  # 다른 확장자

            files = get_repair2_files(data_dir)
            assert len(files) == 2
            assert all(f.suffix == ".csv" for f in files)
            assert all(f.parent.name == "repair2" for f in files)
