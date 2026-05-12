"""
main54_pipe_data.py 모듈 테스트
"""

import pytest
import pandas as pd
import numpy as np
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from main54_pipe_data import process_pipe_data, save_sample_data
from pipe_data import (
    check_file_info,
    analyze_csv_structure,
    read_csv_common,
    read_csv_pipe_lm,
    read_csv_sply_ls,
)
from pipe_const import MOP_CODE_MAPPING, PipeTypeValue, MOPCodeValue
from pipe_func import validate_pipe_type, validate_mop_code

# 테스트 상수 정의
DEFAULT_CHUNK_SIZE = 1000
TEST_OUTPUT_DIR = "test_results"
SAMPLE_PIPE_TYPES = ["ST", "DTC", "STS", "PVC", "GRP", "SP"]
SAMPLE_MOP_CODES = [
    1,
    2,
    3,
    4,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
]


@pytest.fixture
def sample_csv_content():
    """테스트용 CSV 콘텐츠 생성 fixture"""

    def _create_content(headers, rows):
        content = ",".join(headers) + "\n"
        for row in rows:
            content += ",".join(str(v) for v in row) + "\n"
        return content

    return _create_content


@pytest.fixture
def create_temp_csv_file(tmp_path):
    """임시 CSV 파일 생성 fixture"""

    def _create_file(filename, content):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


@pytest.fixture
def pipe_data_headers():
    """관망 데이터 헤더 fixture"""
    return [
        "wkt_geom",
        "FTR_CDE",
        "FTR_IDN",
        "HJD_CDE",
        "SHT_NUM",
        "MNG_CDE",
        "IST_YMD",
        "SAA_CDE",
        "MOP_CDE",
        "STD_DIP",
        "BYC_LEN",
        "JHT_CDE",
        "LOW_DEP",
        "HGH_DEP",
        "CNT_NUM",
        "SYS_CHK",
        "PIP_LBL",
        "IQT_CDE",
        "GIS_IDN",
        "FTC_CDE",
        "CLS_YMD",
        "GU_CDE",
        "SMZ_NUM",
        "MDZ_NUM",
        "LGZ_NUM",
        "AVG_DEP",
        "FNS_YMD",
        "WTP_CDE",
        "RMK_TXT",
    ]


class TestCheckFileInfo:
    """파일 정보 확인 함수 테스트"""

    def test_check_file_info_existing_file(
        self, create_temp_csv_file, sample_csv_content
    ):
        """존재하는 파일의 정보 확인 테스트"""
        # 임시 파일 생성
        content = sample_csv_content(["col1", "col2"], [[1, 2], [3, 4]])
        test_file = create_temp_csv_file("test.csv", content)

        result = check_file_info(str(test_file))

        assert result["path"] == str(test_file), "파일 경로가 일치하지 않습니다"
        assert result["size_bytes"] > 0, "파일 크기가 0바이트입니다"
        assert result["size_mb"] > 0, "파일 크기(MB)가 0입니다"
        assert isinstance(result["size_bytes"], int), "size_bytes가 정수가 아닙니다"
        assert isinstance(result["size_mb"], float), "size_mb가 실수가 아닙니다"

    def test_check_file_info_nonexistent_file(self):
        """존재하지 않는 파일 테스트"""
        with pytest.raises(FileNotFoundError):
            check_file_info("nonexistent_file.csv")


class TestAnalyzeCsvStructure:
    """CSV 구조 분석 함수 테스트"""

    @pytest.mark.parametrize(
        "has_date_fields,expected_date_count",
        [
            (True, 2),  # IST_YMD, FNS_YMD
            (False, 0),  # 날짜 필드 없음
        ],
    )
    def test_analyze_csv_structure_various_formats(
        self,
        create_temp_csv_file,
        sample_csv_content,
        has_date_fields,
        expected_date_count,
    ):
        """다양한 형식의 CSV 구조 분석 테스트"""
        if has_date_fields:
            headers = ["IST_YMD", "FNS_YMD", "name", "value"]
            rows = [
                ["20240101", "20240102", "test", 123],
                ["20240103", "20240104", "test2", 456],
            ]
        else:
            headers = ["name", "value"]
            rows = [["test", 123], ["test2", 456]]

        content = sample_csv_content(headers, rows)
        test_file = create_temp_csv_file("test.csv", content)

        result = analyze_csv_structure(str(test_file), nrows=2)

        assert result is not None, "분석 결과가 None입니다"
        assert "columns" in result, "columns 키가 없습니다"
        assert "dtypes" in result, "dtypes 키가 없습니다"
        assert "date_fields" in result, "date_fields 키가 없습니다"
        assert "sample_data" in result, "sample_data 키가 없습니다"

        # 날짜 필드 개수 확인
        assert (
            len(result["date_fields"]) == expected_date_count
        ), f"날짜 필드 개수가 {expected_date_count}개가 아닙니다"

        # 컬럼 확인
        assert result["columns"] == headers, "컬럼 목록이 일치하지 않습니다"

    def test_analyze_csv_structure_invalid_file(self):
        """잘못된 파일 구조 분석 테스트"""
        result = analyze_csv_structure("nonexistent_file.csv")
        assert result is None, "존재하지 않는 파일에 대해 None이 반환되지 않았습니다"


class TestReadCsvInChunks:
    """청크 단위 CSV 읽기 함수 테스트"""

    def test_read_csv_in_chunks_success(self, tmp_path):
        """정상적인 청크 단위 읽기 테스트"""
        # 임시 CSV 파일 생성 (여러 행)
        test_file = tmp_path / "test.csv"
        test_content = "IST_YMD,FNS_YMD,name,value\n"
        for i in range(10):
            test_content += f"2024010{i%10},2024010{(i+1)%10},test{i},{i*10}\n"
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_common(
                str(test_file), chunksize=3, date_columns=["IST_YMD", "FNS_YMD"]
            )
        )

        assert len(chunks) > 0

        # 첫 번째 청크 확인
        first_chunk = chunks[0]
        assert isinstance(first_chunk, pd.DataFrame)
        assert len(first_chunk) <= 3
        assert "IST_YMD" in first_chunk.columns
        assert "FNS_YMD" in first_chunk.columns

        # BEG_YMD 필드가 추가되었는지 확인
        assert "BEG_YMD" in first_chunk.columns
        assert pd.api.types.is_datetime64_any_dtype(first_chunk["BEG_YMD"])

    def test_read_csv_in_chunks_with_pip_lbl(self, tmp_path):
        """PIP_LBL이 있는 경우 PIP_TYPE 필드 추가 테스트"""
        # PIP_LBL이 포함된 CSV 파일 생성
        test_file = tmp_path / "test.csv"
        test_content = "IST_YMD,FNS_YMD,PIP_LBL,value\n"
        test_content += "20240101,20240102,700-ST-86,100\n"
        test_content += "20240103,20240104,400-DTC-94,200\n"
        test_content += "20240105,20240106,250-DTC-02,300\n"
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_pipe_lm(
                str(test_file), chunksize=5, date_columns=["IST_YMD", "FNS_YMD"]
            )
        )

        assert len(chunks) > 0

        # 첫 번째 청크 확인
        first_chunk = chunks[0]

        # BEG_YMD와 PIP_TYPE 필드가 모두 추가되었는지 확인
        assert "BEG_YMD" in first_chunk.columns
        assert "PIP_TYPE" in first_chunk.columns

        # PIP_TYPE 값이 올바르게 추출되었는지 확인
        expected_types = ["ST", "DTC", "DTC"]
        actual_types = first_chunk["PIP_TYPE"].tolist()
        assert actual_types == expected_types

        # 원본 컬럼 수 + 3개 추가 필드 (BEG_YMD, PIP_TYPE, PIP_TYPE_VALID)
        assert (
            len(first_chunk.columns) == 7
        )  # 4개 원본 + BEG_YMD + PIP_TYPE + PIP_TYPE_VALID

    def test_read_csv_in_chunks_invalid_file(self):
        """잘못된 파일 청크 읽기 테스트"""
        chunks = list(read_csv_common("nonexistent_file.csv"))
        assert len(chunks) == 0


class TestSaveSampleData:
    """샘플 데이터 저장 함수 테스트"""

    def test_save_sample_data_success(self, tmp_path):
        """정상적인 샘플 데이터 저장 테스트"""
        # 샘플 데이터 생성
        df1 = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        df2 = pd.DataFrame({"col1": [5, 6], "col2": [7, 8]})

        result = {"sample_chunks": [df1, df2]}

        output_dir = str(tmp_path)
        save_sample_data(result, output_dir)

        # 저장된 파일 확인
        output_file = tmp_path / "pipe_data_sample.csv"
        assert output_file.exists()

        # 저장된 데이터 확인
        saved_df = pd.read_csv(output_file)
        assert len(saved_df) == 4  # df1 + df2
        assert list(saved_df.columns) == ["col1", "col2"]

    def test_save_sample_data_no_chunks(self, tmp_path):
        """청크가 없는 경우 테스트"""
        result = {"sample_chunks": []}
        output_dir = str(tmp_path)

        # 예외가 발생하지 않아야 함
        save_sample_data(result, output_dir)

        # 파일이 생성되지 않아야 함
        output_file = tmp_path / "pipe_data_sample.csv"
        assert not output_file.exists()

    def test_save_sample_data_none_result(self, tmp_path):
        """None 결과 테스트"""
        output_dir = str(tmp_path)

        # 예외가 발생하지 않아야 함
        save_sample_data(None, output_dir)

        # 파일이 생성되지 않아야 함
        output_file = tmp_path / "pipe_data_sample.csv"
        assert not output_file.exists()


class TestProcessPipeData:
    """관망 데이터 처리 함수 테스트"""

    def test_process_pipe_data_success(self, tmp_path):
        """정상적인 데이터 처리 테스트"""
        # 임시 CSV 파일 생성 (관망 데이터 형태)
        test_file = tmp_path / "pipe_data.csv"
        test_content = "wkt_geom,FTR_CDE,FTR_IDN,IST_YMD,FNS_YMD,STD_DIP,BYC_LEN\n"
        test_content += "LINESTRING(0 0, 1 1),SA001,12345,20240101,20240102,400,100.5\n"
        test_content += "LINESTRING(1 1, 2 2),SA002,12346,20240103,20240104,300,200.3\n"
        test_file.write_text(test_content, encoding="utf-8")

        output_dir = str(tmp_path / "results")
        result = process_pipe_data(str(test_file), read_csv_common, output_dir)

        assert result is not None
        assert "file_info" in result
        assert "structure_info" in result
        assert "date_fields" in result
        assert "all_chunks" in result
        assert "total_rows" in result

        # 날짜 필드 확인
        assert "IST_YMD" in result["date_fields"]
        assert "FNS_YMD" in result["date_fields"]

        # 파일 정보 확인
        assert result["file_info"]["path"] == str(test_file)
        assert result["file_info"]["size_bytes"] > 0

    def test_process_pipe_data_invalid_file(self, tmp_path):
        """잘못된 파일 처리 테스트"""
        output_dir = str(tmp_path / "results")

        with pytest.raises(FileNotFoundError):
            process_pipe_data("nonexistent_file.csv", read_csv_common, output_dir)


class TestDefines:
    """타입 정의 테스트"""

    def test_mop_code_mapping(self):
        """MOP 코드 매핑 테스트"""
        # 기본 매핑 확인
        assert MOP_CODE_MAPPING[1] == "STS"
        assert MOP_CODE_MAPPING[9] == "DTC"
        assert MOP_CODE_MAPPING[22] == "SPOL"

        # 모든 매핑이 올바른 타입인지 확인
        for code, pipe_type in MOP_CODE_MAPPING.items():
            assert isinstance(code, int)
            assert isinstance(pipe_type, str)

    @pytest.mark.parametrize(
        "pipe_type,expected",
        [
            # 유효한 파이프 타입
            ("STS", True),
            ("DTC", True),
            ("SPOL", True),
            ("ST", True),
            ("PVC", True),
            # 유효하지 않은 파이프 타입
            ("INVALID", False),
            ("", False),
            ("123", False),
            ("steel", False),  # 소문자
        ],
    )
    def test_validate_pipe_type(self, pipe_type, expected):
        """파이프 타입 유효성 검증 테스트"""
        result = validate_pipe_type(pipe_type)
        assert (
            result == expected
        ), f"validate_pipe_type('{pipe_type}')가 {expected}를 반환해야 하지만 {result}를 반환했습니다"

    @pytest.mark.parametrize(
        "mop_code,expected",
        [
            # 유효한 MOP 코드
            (1, True),  # STS
            (9, True),  # DTC
            (22, True),  # SPOL
            (14, True),  # DTEP
            (16, True),  # HIVP
            # 유효하지 않은 MOP 코드
            (0, False),
            (5, False),  # 5는 매핑에 없음
            (21, False),  # 21도 매핑에 없음
            (100, False),
            (-1, False),
            (999, False),
        ],
    )
    def test_validate_mop_code(self, mop_code, expected):
        """MOP 코드 유효성 검증 테스트"""
        result = validate_mop_code(mop_code)
        assert (
            result == expected
        ), f"validate_mop_code({mop_code})가 {expected}를 반환해야 하지만 {result}를 반환했습니다"

    def test_sply_ls_with_mop_mapping(self, tmp_path):
        """SPLY_LS에서 MOP_CDE 매핑 테스트"""
        # MOP_CDE가 포함된 CSV 파일 생성
        test_file = tmp_path / "test_sply.csv"
        test_content = "IST_YMD,FNS_YMD,MOP_CDE,value\n"
        test_content += "20240101,20240102,1,100\n"  # 1 -> STS
        test_content += "20240103,20240104,9,200\n"  # 9 -> DTC
        test_content += "20240105,20240106,22,300\n"  # 22 -> SPOL
        test_content += "20240107,20240108,999,400\n"  # 999 -> 매핑 없음 (NaN)
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_sply_ls(
                str(test_file), chunksize=10, date_columns=["IST_YMD", "FNS_YMD"]
            )
        )

        assert len(chunks) > 0

        # 첫 번째 청크 확인
        first_chunk = chunks[0]

        # PIP_TYPE 필드가 추가되었는지 확인
        assert "PIP_TYPE" in first_chunk.columns

        # PIP_TYPE 값이 올바르게 매핑되었는지 확인
        expected_types = ["STS", "DTC", "SPOL", None]  # 999는 매핑되지 않아 NaN
        actual_types = first_chunk["PIP_TYPE"].tolist()

        # NaN 처리를 위해 pandas의 isna 사용
        for i, (expected, actual) in enumerate(zip(expected_types, actual_types)):
            if expected is None:
                assert pd.isna(actual), f"Index {i}: expected NaN, got {actual}"
            else:
                assert (
                    actual == expected
                ), f"Index {i}: expected {expected}, got {actual}"


class TestPipTypeValidation:
    """PIP_TYPE 검증 기능 테스트"""

    def test_pipe_lm_with_valid_pip_types(self, tmp_path):
        """유효한 PIP_TYPE 값들에 대한 검증 테스트"""
        # 유효한 PIP_LBL이 포함된 CSV 파일 생성
        test_file = tmp_path / "test_pipe_lm.csv"
        test_content = "IST_YMD,FNS_YMD,PIP_LBL,value\n"
        test_content += "20240101,20240102,700-ST-86,100\n"  # ST (유효)
        test_content += "20240103,20240104,400-DTC-94,200\n"  # DTC (유효)
        test_content += "20240105,20240106,250-STS-02,300\n"  # STS (유효)
        test_content += "20240107,20240108,300-PVC-01,400\n"  # PVC (유효)
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_pipe_lm(
                str(test_file),
                chunksize=10,
                date_columns=["IST_YMD", "FNS_YMD"],
                verbose=False,
            )
        )

        assert len(chunks) > 0
        chunk = chunks[0]

        # PIP_TYPE과 PIP_TYPE_VALID 필드가 추가되었는지 확인
        assert "PIP_TYPE" in chunk.columns
        assert "PIP_TYPE_VALID" in chunk.columns

        # 모든 값이 유효해야 함
        assert chunk["PIP_TYPE_VALID"].all(), "모든 PIP_TYPE 값이 유효해야 함"

        # 추출된 PIP_TYPE 값 확인
        expected_types = ["ST", "DTC", "STS", "PVC"]
        actual_types = chunk["PIP_TYPE"].tolist()
        assert actual_types == expected_types

    def test_pipe_lm_with_invalid_pip_types(self, tmp_path):
        """유효하지 않은 PIP_TYPE 값들에 대한 검증 테스트"""
        # 유효하지 않은 PIP_LBL이 포함된 CSV 파일 생성
        test_file = tmp_path / "test_pipe_lm.csv"
        test_content = "IST_YMD,FNS_YMD,PIP_LBL,value\n"
        test_content += "20240101,20240102,700-ST-86,100\n"  # ST (유효)
        test_content += "20240103,20240104,400-INVALID-94,200\n"  # INVALID (무효)
        test_content += "20240105,20240106,250-STEEL-02,300\n"  # STEEL (무효)
        test_content += "20240107,20240108,300-DTC-01,400\n"  # DTC (유효)
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_pipe_lm(
                str(test_file),
                chunksize=10,
                date_columns=["IST_YMD", "FNS_YMD"],
                verbose=False,
            )
        )

        assert len(chunks) > 0
        chunk = chunks[0]

        # PIP_TYPE과 PIP_TYPE_VALID 필드가 추가되었는지 확인
        assert "PIP_TYPE" in chunk.columns
        assert "PIP_TYPE_VALID" in chunk.columns

        # 유효성 검증 결과 확인
        expected_validity = [
            True,
            False,
            False,
            True,
        ]  # ST(유효), INVALID(무효), STEEL(무효), DTC(유효)
        actual_validity = chunk["PIP_TYPE_VALID"].tolist()
        assert actual_validity == expected_validity

        # 유효하지 않은 값들이 NaN으로 변경되었는지 확인
        expected_cleaned_types = ["ST", None, None, "DTC"]
        actual_cleaned_types = chunk["PIP_TYPE"].tolist()

        for i, (expected, actual) in enumerate(
            zip(expected_cleaned_types, actual_cleaned_types)
        ):
            if expected is None:
                assert pd.isna(actual), f"Index {i}: expected NaN, got {actual}"
            else:
                assert (
                    actual == expected
                ), f"Index {i}: expected {expected}, got {actual}"

    def test_pipe_lm_with_missing_pip_lbl(self, tmp_path):
        """PIP_LBL이 없는 경우 테스트"""
        # PIP_LBL이 없는 CSV 파일 생성
        test_file = tmp_path / "test_pipe_lm.csv"
        test_content = "IST_YMD,FNS_YMD,other_col,value\n"
        test_content += "20240101,20240102,data1,100\n"
        test_content += "20240103,20240104,data2,200\n"
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_pipe_lm(
                str(test_file),
                chunksize=10,
                date_columns=["IST_YMD", "FNS_YMD"],
                verbose=False,
            )
        )

        assert len(chunks) > 0
        chunk = chunks[0]

        # PIP_TYPE 필드가 추가되지 않아야 함
        assert "PIP_TYPE" not in chunk.columns
        assert "PIP_TYPE_VALID" not in chunk.columns

    def test_pipe_lm_with_malformed_pip_lbl(self, tmp_path):
        """잘못된 형식의 PIP_LBL에 대한 테스트"""
        # 잘못된 형식의 PIP_LBL이 포함된 CSV 파일 생성
        test_file = tmp_path / "test_pipe_lm.csv"
        test_content = "IST_YMD,FNS_YMD,PIP_LBL,value\n"
        test_content += "20240101,20240102,700-ST-86,100\n"  # 정상 형식
        test_content += (
            "20240103,20240104,INVALID_FORMAT,200\n"  # 잘못된 형식 (하이픈 없음)
        )
        test_content += "20240105,20240106,300-,300\n"  # 잘못된 형식 (타입 없음)
        test_content += "20240107,20240108,,400\n"  # 빈 값
        test_file.write_text(test_content, encoding="utf-8")

        chunks = list(
            read_csv_pipe_lm(
                str(test_file),
                chunksize=10,
                date_columns=["IST_YMD", "FNS_YMD"],
                verbose=False,
            )
        )

        assert len(chunks) > 0
        chunk = chunks[0]

        # PIP_TYPE과 PIP_TYPE_VALID 필드가 추가되었는지 확인
        assert "PIP_TYPE" in chunk.columns
        assert "PIP_TYPE_VALID" in chunk.columns

        # 실제 검증 결과 확인
        expected_validity = [
            True,
            True,
            False,
            True,
        ]  # ST(유효), None(유효), ""(무효), None(유효)
        actual_validity = chunk["PIP_TYPE_VALID"].tolist()
        assert actual_validity == expected_validity

        # 추출된 값 확인 (잘못된 형식은 None이 추출됨)
        actual_types = chunk["PIP_TYPE"].tolist()

        # 첫 번째는 'ST', 나머지는 None이어야 함
        assert actual_types[0] == "ST"
        assert pd.isna(actual_types[1])  # 'INVALID_FORMAT'에서 split 결과 None
        assert pd.isna(
            actual_types[2]
        )  # '300-'에서 split 결과 ""이고 유효하지 않아 None으로 변경됨
        assert pd.isna(actual_types[3])  # 빈 값에서 split 결과 None


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def create_pipe_data_file(
        self, create_temp_csv_file, sample_csv_content, pipe_data_headers
    ):
        """실제 관망 데이터와 유사한 테스트 파일 생성 fixture"""

        def _create(num_rows=50):
            rows = []
            for i in range(num_rows):
                row_data = [
                    f"LINESTRING({i} {i}, {i+1} {i+1})",  # wkt_geom
                    "SA001",  # FTR_CDE
                    f"{10000 + i}",  # FTR_IDN
                    "2723061000",  # HJD_CDE
                    f"{35803000 + i}",  # SHT_NUM
                    "54000",  # MNG_CDE
                    f"2024010{i%10}",  # IST_YMD
                    "SA003",  # SAA_CDE
                    "12",  # MOP_CDE
                    f"{400 + i*10}",  # STD_DIP
                    f"{100.5 + i}",  # BYC_LEN
                    "",  # JHT_CDE
                    "0",  # LOW_DEP
                    "0",  # HGH_DEP
                    f"{20119006912 + i}",  # CNT_NUM
                    "1",  # SYS_CHK
                    f"400-ST-{i:02d}",  # PIP_LBL
                    "IQT903",  # IQT_CDE
                    f"{10000 + i}",  # GIS_IDN
                    "SA003",  # FTC_CDE
                    "",  # CLS_YMD
                    "B",  # GU_CDE
                    f"{230 + i}",  # SMZ_NUM
                    f"{519 + i}",  # MDZ_NUM
                    "S0",  # LGZ_NUM
                    "1.2",  # AVG_DEP
                    f"2024010{(i+1)%10}",  # FNS_YMD
                    "SS00201",  # WTP_CDE
                    "",  # RMK_TXT
                ]
                rows.append(row_data)

            content = sample_csv_content(pipe_data_headers, rows)
            return create_temp_csv_file("pipe_data.csv", content)

        return _create

    def test_full_pipeline(self, create_pipe_data_file, tmp_path, pipe_data_headers):
        """전체 파이프라인 테스트"""
        # 실제 관망 데이터와 유사한 구조의 테스트 파일 생성
        test_file = create_pipe_data_file(num_rows=50)

        # 전체 파이프라인 실행
        output_dir = str(tmp_path / "results")
        result = process_pipe_data(str(test_file), read_csv_pipe_lm, output_dir)

        # 결과 검증
        assert result is not None, "처리 결과가 None입니다"
        assert (
            len(result["date_fields"]) >= 2
        ), "날짜 필드가 2개 미만입니다"  # IST_YMD, FNS_YMD 최소
        assert len(result["all_chunks"]) > 0, "청크가 비어있습니다"
        assert result["total_rows"] > 0, "처리된 행이 없습니다"
        assert (
            result["structure_info"]["columns"] == pipe_data_headers
        ), "컬럼 목록이 일치하지 않습니다"

        # 전체 데이터 저장 테스트 (호환성을 위해 키 변경)
        result_for_save = result.copy()
        result_for_save["sample_chunks"] = result["all_chunks"]
        save_sample_data(result_for_save, output_dir)

        # 저장된 파일 확인
        sample_file = Path(output_dir) / "pipe_data_sample.csv"
        assert sample_file.exists(), "샘플 파일이 생성되지 않았습니다"

        # 저장된 데이터 검증
        saved_df = pd.read_csv(sample_file)
        assert len(saved_df) > 0, "저장된 데이터가 비어있습니다"
        assert (
            len(saved_df) == result["total_rows"]
        ), f"저장된 행 수({len(saved_df)})가 전체 행 수({result['total_rows']})와 다릅니다"
        # 원본 컬럼 수 + BEG_YMD + PIP_TYPE + PIP_TYPE_VALID = 29 + 3 = 32
        expected_cols = len(pipe_data_headers) + 3
        assert (
            len(saved_df.columns) == expected_cols
        ), f"컬럼 수({len(saved_df.columns)})가 예상값({expected_cols})과 다릅니다"


if __name__ == "__main__":
    pytest.main([__file__])