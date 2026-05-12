# Copy the original file with indentation fixes
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from src.main11d_cmp_dup import (
    load_files,
    convert_to_epsg5179,
    find_duplicates,
    find_cross_file_duplicates,
    calculate_distances_within_groups,
    save_results,
    print_results,
    main,
)


class TestLoadFiles:
    """파일 로드 함수 테스트"""

    @patch("pandas.read_csv")
    @patch("src.main11d_cmp_dup.Path")
    def test_load_files_with_valid_files(self, mock_path_class, mock_read_csv):
        """유효한 CSV 파일 로드 테스트"""
        # Create mock file paths with required attributes
        mock_file1 = MagicMock()
        mock_file1.exists.return_value = True
        mock_file1.name = "지상누수_위치추가.csv"

        mock_file2 = MagicMock()
        mock_file2.exists.return_value = True
        mock_file2.name = "지하누수_위치추가.csv"

        mock_file3 = MagicMock()
        mock_file3.exists.return_value = False  # 긴급공사 파일은 없음

        mock_file4 = MagicMock()
        mock_file4.exists.return_value = False  # 관리대장 파일도 없음

        # Mock results directory
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True

        # Setup __truediv__ to return appropriate file mocks
        def truediv_side_effect(self, other):
            if "지상누수" in other:
                return mock_file1
            elif "지하누수" in other:
                return mock_file2
            elif "긴급공사" in other:
                return mock_file3
            elif "관리대장" in other:
                return mock_file4
            return MagicMock()

        mock_results_dir.__truediv__ = truediv_side_effect

        # Mock Path class to return results_dir when called with "results"
        mock_path_class.return_value = mock_results_dir

        # Mock CSV 데이터
        mock_df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [37.5665, 37.5666],
                "경도": [126.9780, 126.9781],
                "주소": ["서울시 중구", "서울시 종로구"],
            }
        )
        mock_read_csv.return_value = mock_df

        # Mock sorted to return paths in order
        with patch("builtins.sorted", return_value=[mock_file1, mock_file2]):
            result = load_files()

        assert len(result) == 2
        assert "지상누수_위치추가.csv" in result
        assert "지하누수_위치추가.csv" in result

    @patch("src.main11d_cmp_dup.Path.exists")
    @patch("src.main11d_cmp_dup.Path.glob")
    @patch("pandas.read_csv")
    def test_load_files_missing_columns(self, mock_read_csv, mock_glob, mock_exists):
        """필수 컬럼이 없는 파일 처리 테스트"""
        mock_exists.return_value = True
        mock_glob.return_value = [Path("results/test.csv")]

        # 필수 컬럼이 없는 DataFrame
        mock_df = pd.DataFrame({"date": ["2024-01-01"], "location": ["서울"]})
        mock_read_csv.return_value = mock_df

        with pytest.raises(ValueError) as exc_info:
            load_files()
        assert "필수 컬럼 누락" in str(exc_info.value)

    @patch("src.main11d_cmp_dup.Path.exists")
    def test_load_files_no_results_directory(self, mock_exists):
        """results 디렉토리가 없는 경우 테스트"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError):
            load_files()

    @patch("src.main11d_cmp_dup.Path")
    def test_load_files_no_matching_files(self, mock_path_class):
        """매칭되는 파일이 없는 경우 테스트"""
        # Mock results directory
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True

        # All files don't exist
        mock_file = MagicMock()
        mock_file.exists.return_value = False

        mock_results_dir.__truediv__ = lambda self, other: mock_file
        mock_path_class.return_value = mock_results_dir

        with pytest.raises(FileNotFoundError) as exc_info:
            load_files()
        assert "처리할 파일이 없습니다" in str(exc_info.value)

    @patch("pandas.read_csv")
    @patch("src.main11d_cmp_dup.Path")
    def test_load_files_with_encoding_issues(self, mock_path_class, mock_read_csv):
        """인코딩 문제 처리 테스트"""
        # Mock file path
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.name = "긴급공사_위치추가.csv"

        # Mock results directory
        mock_results_dir = MagicMock()
        mock_results_dir.exists.return_value = True

        def truediv_side_effect(self, other):
            if "긴급공사" in other:
                return mock_file
            # Other files don't exist
            mock_nonexist = MagicMock()
            mock_nonexist.exists.return_value = False
            return mock_nonexist

        mock_results_dir.__truediv__ = truediv_side_effect
        mock_path_class.return_value = mock_results_dir

        # Mock CSV data - first encoding fails, second succeeds
        mock_df = pd.DataFrame(
            {"작업일시": ["2024-01-01"], "위도": [37.5665], "경도": [126.9780]}
        )

        def read_csv_side_effect(path, encoding):
            if encoding == "utf-8-sig":
                raise UnicodeDecodeError("utf-8-sig", b"", 0, 1, "")
            return mock_df

        mock_read_csv.side_effect = read_csv_side_effect

        with patch("builtins.sorted", return_value=[mock_file]):
            result = load_files()

        assert len(result) == 1
        assert "긴급공사_위치추가.csv" in result


class TestConvertToEpsg5179:
    """좌표 변환 함수 테스트"""

    def test_convert_valid_coordinates(self):
        """유효한 좌표 변환 테스트"""
        df = pd.DataFrame({"위도": [37.5665], "경도": [126.9780]})

        result = convert_to_epsg5179(df)

        assert "x_5179" in result.columns
        assert "y_5179" in result.columns
        assert result["x_5179"].iloc[0] > 0
        assert result["y_5179"].iloc[0] > 0

    def test_convert_multiple_coordinates(self):
        """여러 좌표 변환 테스트"""
        df = pd.DataFrame(
            {
                "위도": [37.5665, 35.1796, 33.4996],
                "경도": [126.9780, 129.0756, 126.5312],
            }
        )

        result = convert_to_epsg5179(df)

        assert len(result) == 3
        assert result["x_5179"].notna().all()
        assert result["y_5179"].notna().all()

    def test_convert_with_dataframe(self):
        """DataFrame 인터페이스로 변환 테스트"""
        df = pd.DataFrame(
            {
                "위도": [35.8714, 37.5665],
                "경도": [128.6014, 126.9780],
                "기타": ["데이터1", "데이터2"],
            }
        )

        result = convert_to_epsg5179(df)
        assert "x_5179" in result.columns
        assert "y_5179" in result.columns
        assert "기타" in result.columns  # 다른 컬럼도 유지되어야 함


class TestFindDuplicatesWithinFile:
    """파일 내 중복 찾기 함수 테스트"""

    def test_find_exact_duplicates(self):
        """정확히 같은 좌표의 중복 찾기"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "위도": [37.5665, 37.5665, 37.5665],
                "경도": [126.9780, 126.9780, 126.9780],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)

        # 같은 날짜의 중복만 찾아야 함 (첫 두 행)
        assert len(duplicates) == 2
        assert duplicates["작업일자"].iloc[0] == duplicates["작업일자"].iloc[1]

    def test_find_duplicates_with_tolerance(self):
        """허용 오차 내의 중복 찾기"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01"],
                "위도": [37.5665, 37.5666],  # 약간 다른 좌표
                "경도": [126.9780, 126.9781],
            }
        )

        # 큰 허용 오차로 중복 찾기
        duplicates = find_duplicates(df, "test_file", tolerance=30.0)
        assert len(duplicates) == 2

    def test_no_duplicates(self):
        """중복이 없는 경우 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [37.5665, 35.1796, 33.4996],
                "경도": [126.9780, 129.0756, 126.5312],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 0

    def test_with_nan_values(self):
        """NaN 값이 포함된 경우 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01", np.nan],
                "위도": [37.5665, np.nan, 37.5665],
                "경도": [126.9780, 126.9780, np.nan],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        # NaN이 있는 행은 제외됨
        assert len(duplicates) == 0

    def test_distance_calculation(self):
        """그룹 내 거리 계산 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01"],
                "위도": [37.5665, 37.5666],
                "경도": [126.9780, 126.9781],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=30.0)

        if len(duplicates) > 0:
            assert "그룹내거리_m" in duplicates.columns


class TestFindCrossFileDuplicates:
    """파일 간 중복 찾기 함수 테스트"""

    def test_find_cross_file_duplicates(self):
        """파일 간 중복 찾기 테스트"""
        file_data = {
            "file1.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [37.5665], "경도": [126.9780]}
            ),
            "file2.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [37.5665], "경도": [126.9780]}
            ),
        }

        cross_duplicates = find_cross_file_duplicates(file_data, tolerance=1.0)

        assert len(cross_duplicates) == 2  # 두 파일에서 각 1개씩
        assert cross_duplicates["source_file"].nunique() == 2

    def test_no_cross_file_duplicates(self):
        """파일 간 중복이 없는 경우 테스트"""
        file_data = {
            "file1.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [37.5665], "경도": [126.9780]}
            ),
            "file2.csv": pd.DataFrame(
                {
                    "작업일시": ["2024-01-02"],  # 다른 날짜
                    "위도": [37.5665],
                    "경도": [126.9780],
                }
            ),
        }

        cross_duplicates = find_cross_file_duplicates(file_data, tolerance=1.0)
        assert len(cross_duplicates) == 0

    def test_multiple_file_duplicates(self):
        """3개 이상 파일 간 중복 테스트"""
        file_data = {
            f"file{i}.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [37.5665], "경도": [126.9780]}
            )
            for i in range(1, 4)
        }

        cross_duplicates = find_cross_file_duplicates(file_data, tolerance=1.0)

        assert len(cross_duplicates) == 3
        assert cross_duplicates["source_file"].nunique() == 3


class TestCalculateDistancesWithinGroups:
    """그룹 내 거리 계산 함수 테스트"""

    def test_calculate_distances(self):
        """거리 계산 테스트"""
        df = pd.DataFrame(
            {
                "작업일자": ["2024-01-01", "2024-01-01"],
                "x_5179": [100.0, 105.0],
                "y_5179": [200.0, 203.0],
                "x_rounded": [100.0, 100.0],
                "y_rounded": [200.0, 200.0],
            }
        )

        result = calculate_distances_within_groups(df)

        assert "그룹내거리_m" in result.columns
        assert result["그룹내거리_m"].iloc[0] == 0.0  # 첫 번째는 0
        assert result["그룹내거리_m"].iloc[1] > 0  # 두 번째는 양수

    def test_multiple_groups(self):
        """여러 그룹에 대한 거리 계산"""
        df = pd.DataFrame(
            {
                "작업일자": ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"],
                "x_5179": [100.0, 105.0, 200.0, 205.0],
                "y_5179": [200.0, 203.0, 300.0, 303.0],
                "x_rounded": [100.0, 100.0, 200.0, 200.0],
                "y_rounded": [200.0, 200.0, 300.0, 300.0],
            }
        )

        result = calculate_distances_within_groups(df)

        assert len(result) == 4
        assert result.iloc[0]["그룹내거리_m"] == 0.0
        assert result.iloc[2]["그룹내거리_m"] == 0.0
        assert result.iloc[1]["그룹내거리_m"] > 0
        assert result.iloc[3]["그룹내거리_m"] > 0
        # 거리 계산 확인
        assert result.iloc[1]["그룹내거리_m"] == pytest.approx(
            np.sqrt((105 - 100) ** 2 + (203 - 200) ** 2), rel=0.01
        )
        assert result.iloc[3]["그룹내거리_m"] == pytest.approx(
            np.sqrt(5**2 + 3**2), rel=0.01
        )


class TestSaveResults:
    """결과 저장 함수 테스트"""

    def test_save_results_with_duplicates(self, tmp_path):
        """중복이 있는 경우 결과 저장 테스트"""
        within_duplicates = {
            "file1.csv": pd.DataFrame(
                {
                    "작업일자": ["2024-01-01"],
                    "위도": [35.8714],
                    "경도": [128.6014],
                    "x_5179": [100.0],
                    "y_5179": [200.0],
                    "x_rounded": [100.0],
                    "y_rounded": [200.0],
                    "주소또는위치": ["주소1"],
                    "그룹내거리_m": [0.0],
                    "원본행번호": [2],
                }
            )
        }

        across_duplicates = pd.DataFrame(
            {
                "source_file": ["file1.csv", "file2.csv"],
                "작업일자": ["2024-01-01", "2024-01-01"],
                "위도": [35.8714, 35.8714],
                "경도": [128.6014, 128.6014],
                "x_5179": [100.0, 100.0],
                "y_5179": [200.0, 200.0],
                "x_rounded": [100.0, 100.0],
                "y_rounded": [200.0, 200.0],
                "주소또는위치": ["주소1", "주소2"],
                "그룹내거리_m": [0.0, 0.0],
                "원본행번호": [2, 2],
            }
        )

        output_path = tmp_path / "test_output"
        tolerance = 30  # Add tolerance parameter
        save_results(within_duplicates, across_duplicates, output_path, tolerance)

        # 파일 생성 확인
        assert (output_path / "중복분석_요약.txt").exists()
        assert (output_path / "중복분석_상세.csv").exists()

        # 텍스트 파일 내용 확인
        txt_content = (output_path / "중복분석_요약.txt").read_text(encoding="utf-8")
        assert "중복 분석 요약" in txt_content
        assert "파일별 통계" in txt_content
        assert "파일 간 중복" in txt_content

        # CSV 파일 내용 확인
        df_saved = pd.read_csv(output_path / "중복분석_상세.csv", encoding="utf-8-sig")
        assert len(df_saved) > 0  # Check that there is data saved

    def test_save_results_no_duplicates(self, tmp_path):
        """중복이 없는 경우 결과 저장 테스트"""
        within_duplicates = {}
        across_duplicates = pd.DataFrame()  # Empty DataFrame instead of list

        output_path = tmp_path / "test_output"
        tolerance = 30  # Add tolerance parameter
        save_results(within_duplicates, across_duplicates, output_path, tolerance)

        # 텍스트 파일만 생성됨
        assert (output_path / "중복분석_요약.txt").exists()
        assert not (output_path / "중복분석_상세.csv").exists()

        # 내용 확인
        txt_content = (output_path / "중복분석_요약.txt").read_text(encoding="utf-8")
        assert "파일 내 중복 없음" in txt_content or "파일 간 중복: 0개" in txt_content

    def test_save_results_summary(self, tmp_path):
        """요약 정보 저장 테스트"""
        within_duplicates = {
            "file1.csv": pd.DataFrame(
                {
                    "작업일자": ["2024-01-01"] * 10,
                    "x_rounded": [100.0] * 10,
                    "y_rounded": [200.0] * 10,
                }
            ),
            "file2.csv": pd.DataFrame(
                {
                    "작업일자": ["2024-01-02"] * 5,
                    "x_rounded": [150.0] * 5,
                    "y_rounded": [250.0] * 5,
                }
            ),
        }
        across_duplicates = pd.DataFrame(
            {
                "작업일자": ["2024-01-03"] * 3,
                "x_rounded": [200.0] * 3,
                "y_rounded": [300.0] * 3,
                "source_file": [
                    "file1.csv",
                    "file2.csv",
                    "file1.csv",
                ],  # Add source_file column
            }
        )  # DataFrame with proper columns

        output_path = tmp_path / "test_output"
        tolerance = 30  # Add tolerance parameter
        save_results(within_duplicates, across_duplicates, output_path, tolerance)

        txt_content = (output_path / "중복분석_요약.txt").read_text(encoding="utf-8")
        assert "file1.csv: 10개 중복" in txt_content
        assert "file2.csv: 5개 중복" in txt_content
        assert "파일 간 중복: 3개" in txt_content


class TestPrintResults:
    """결과 출력 함수 테스트"""

    def test_print_results_with_duplicates(self, capsys):
        """중복이 있는 경우 출력 테스트"""
        within_duplicates = {
            "file1.csv": pd.DataFrame(
                {
                    "작업일자": ["2024-01-01"] * 5,
                    "x_rounded": [100.0] * 5,
                    "y_rounded": [200.0] * 5,
                    "그룹내거리_m": [0.0, 1.0, 2.0, 3.0, 4.0],
                    "주소또는위치": ["주소1"] * 5,
                    "원본행번호": [2, 3, 4, 5, 6],
                }
            )
        }
        across_duplicates = pd.DataFrame(
            {
                "작업일자": ["2024-01-01"] * 3,
                "x_rounded": [100.0] * 3,
                "y_rounded": [200.0] * 3,
                "source_file": ["file1.csv", "file2.csv", "file1.csv"],
                "그룹내거리_m": [0.0, 1.0, 2.0],
                "주소또는위치": ["주소1", "주소2", "주소3"],
                "원본행번호": [2, 3, 4],
            }
        )

        print_results(within_duplicates, across_duplicates, tolerance=1.0)

        captured = capsys.readouterr()
        assert "중복 분석 결과" in captured.out
        assert "file1.csv" in captured.out

    def test_print_results_no_duplicates(self, capsys):
        """중복이 없는 경우 출력 테스트"""
        print_results({}, pd.DataFrame(), tolerance=1.0)

        captured = capsys.readouterr()
        assert "파일 내 중복 없음" in captured.out
        assert "파일 간 중복 없음" in captured.out


class TestMain:
    """메인 함수 테스트"""

    @patch("sys.argv", ["test_script.py"])
    @patch("src.main11d_cmp_dup.save_results")
    @patch("src.main11d_cmp_dup.find_cross_file_duplicates")
    @patch("src.main11d_cmp_dup.find_duplicates")
    @patch("src.main11d_cmp_dup.load_files")
    def test_main_normal_flow(self, mock_load, mock_within, mock_cross, mock_save):
        """정상적인 실행 플로우 테스트"""
        mock_load.return_value = {
            "file1.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [35.8714], "경도": [128.6014]}
            )
        }
        mock_within.return_value = pd.DataFrame()
        mock_cross.return_value = pd.DataFrame()

        main()

        assert mock_load.called
        assert mock_within.called
        assert mock_cross.called
        assert mock_save.called

    @patch("src.main11d_cmp_dup.load_files")
    def test_main_with_error(self, mock_load):
        """에러 발생 시 처리 테스트"""
        mock_load.side_effect = ValueError("필수 컬럼 누락")

        with patch("sys.argv", ["test_script.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("src.main11d_cmp_dup.load_files")
    def test_main_no_files(self, mock_load):
        """파일이 없는 경우 테스트"""
        mock_load.return_value = {}

        with patch("sys.argv", ["test_script.py"]):
            main()  # Should complete without error

    @patch("sys.argv", ["test_script.py", "--tolerance", "5.0"])
    @patch("src.main11d_cmp_dup.find_duplicates")
    @patch("src.main11d_cmp_dup.load_files")
    def test_main_with_custom_tolerance(self, mock_load, mock_within):
        """커스텀 허용 오차 테스트"""
        mock_load.return_value = {
            "file1.csv": pd.DataFrame(
                {"작업일시": ["2024-01-01"], "위도": [35.8714], "경도": [128.6014]}
            )
        }
        mock_within.return_value = pd.DataFrame()

        with patch("src.main11d_cmp_dup.find_cross_file_duplicates") as mock_cross:
            mock_cross.return_value = pd.DataFrame()
            with patch("src.main11d_cmp_dup.save_results"):
                main()

        # tolerance=5.0으로 호출되었는지 확인
        mock_within.assert_called_with(
            mock_load.return_value["file1.csv"], "file1.csv", 5.0, False
        )

    @patch("sys.argv", ["test_script.py", "--output", "custom_output"])
    @patch("src.main11d_cmp_dup.Path")
    @patch("src.main11d_cmp_dup.load_files")
    @patch("src.main11d_cmp_dup.save_results")
    @patch("src.main11d_cmp_dup.find_duplicates")
    @patch("src.main11d_cmp_dup.find_cross_file_duplicates")
    def test_main_with_custom_output(
        self, mock_cross, mock_within, mock_save, mock_load, mock_path
    ):
        """커스텀 출력 디렉토리 테스트"""
        mock_load.return_value = {
            "file1.csv": pd.DataFrame({"작업일시": [], "위도": [], "경도": []})
        }
        mock_within.return_value = pd.DataFrame()
        mock_cross.return_value = pd.DataFrame()

        main()

        # custom_output으로 save_results가 호출되었는지 확인
        assert mock_save.called
        call_args = mock_save.call_args[0]
        assert "custom_output" in str(call_args[2])


class TestIntegration:
    """통합 테스트"""

    def test_full_workflow_with_duplicates(self, tmp_path):
        """전체 워크플로우 테스트 (중복 있음)"""
        # 실제 임시 디렉토리와 파일 생성
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # 중복이 있는 테스트 데이터
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "위도": [35.8714, 35.8714, 35.8720],  # 첫 2개는 중복
                "경도": [128.6014, 128.6014, 128.6020],
            }
        )
        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-03", "2024-01-04"],
                "위도": [35.8714, 35.8725],  # 첫번째는 df1과 중복
                "경도": [128.6014, 128.6025],
            }
        )

        # 실제 CSV 파일 생성
        (results_dir / "지상누수_위치추가.csv").write_text(df1.to_csv(index=False))
        (results_dir / "지하누수_위치추가.csv").write_text(df2.to_csv(index=False))

        # Path를 실제 results_dir로 패치
        with patch("src.main11d_cmp_dup.Path") as mock_path_class:
            mock_path_class.return_value = results_dir

            # 함수 실행
            datafiles = load_files()
            assert len(datafiles) == 2

            # 파일 내 중복 찾기
            all_within_duplicates = {}
            for filename, df in datafiles.items():
                within_dup = find_duplicates(df, filename, tolerance=1.0)
                if len(within_dup) > 0:
                    all_within_duplicates[filename] = within_dup

            # 지상누수 파일에서 중복이 발견되어야 함
            assert any("지상누수" in str(k) for k in all_within_duplicates.keys())

    def test_full_workflow_no_duplicates(self, tmp_path):
        """전체 워크플로우 테스트 (중복 없음)"""
        # 실제 임시 디렉토리와 파일 생성
        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # 중복이 없는 테스트 데이터
        df1 = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "위도": [35.8714, 35.8814, 35.8914],  # 모두 충분히 떨어져 있음
                "경도": [128.6014, 128.6114, 128.6214],
            }
        )
        df2 = pd.DataFrame(
            {
                "작업일시": ["2024-01-04", "2024-01-05"],
                "위도": [35.9014, 35.9114],  # df1과도 충분히 떨어져 있음
                "경도": [128.6314, 128.6414],
            }
        )

        # 실제 CSV 파일 생성
        (results_dir / "지상누수_위치추가.csv").write_text(df1.to_csv(index=False))
        (results_dir / "지하누수_위치추가.csv").write_text(df2.to_csv(index=False))

        # Path를 실제 results_dir로 패치
        with patch("src.main11d_cmp_dup.Path") as mock_path_class:
            mock_path_class.return_value = results_dir

            # 함수 실행
            datafiles = load_files()
            assert len(datafiles) == 2

            # 파일 내 중복 찾기
            all_within_duplicates = {}
            for filename, df in datafiles.items():
                within_dup = find_duplicates(df, filename, tolerance=1.0)
                if len(within_dup) > 0:
                    all_within_duplicates[filename] = within_dup

            # 중복이 없어야 함
            assert len(all_within_duplicates) == 0


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_dataframe_handling(self):
        """빈 DataFrame 처리 테스트"""
        # Empty DataFrame with required columns
        df = pd.DataFrame(columns=["작업일시", "위도", "경도"])
        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 0

    def test_single_row_dataframe(self):
        """단일 행 DataFrame 테스트"""
        df = pd.DataFrame(
            {"작업일시": ["2024-01-01"], "위도": [35.8714], "경도": [128.6014]}
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 0

    def test_all_nan_coordinates(self):
        """모든 좌표가 NaN인 경우 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-02"],
                "위도": [np.nan, np.nan],
                "경도": [np.nan, np.nan],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 0

    def test_invalid_date_format(self):
        """잘못된 날짜 형식 처리 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["invalid_date", "2024-01-01"],
                "위도": [35.8714, 35.8714],
                "경도": [128.6014, 128.6014],
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        # 유효한 날짜만 처리됨
        assert len(duplicates) <= 1

    def test_extreme_tolerance_values(self):
        """극단적인 허용 오차 값 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01"],
                "위도": [35.8714, 36.8714],  # 1도 차이 (약 111km)
                "경도": [128.6014, 128.6014],
            }
        )

        # 매우 작은 허용 오차
        duplicates = find_duplicates(df, "test_file", tolerance=0.001)
        assert len(duplicates) == 0

        # 매우 큰 허용 오차 (200km)
        duplicates = find_duplicates(df, "test_file", tolerance=200000.0)
        assert len(duplicates) == 2

    def test_duplicate_within_same_file(self):
        """같은 파일 내에 완전히 동일한 레코드 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01"] * 5,
                "위도": [35.8714] * 5,
                "경도": [128.6014] * 5,
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 5

    def test_boundary_coordinates(self):
        """경계 좌표값 테스트"""
        df = pd.DataFrame(
            {
                "작업일시": ["2024-01-01", "2024-01-01"],
                "위도": [33.0, 43.0],  # 한국 위도 경계
                "경도": [124.0, 132.0],  # 한국 경도 경계
            }
        )

        duplicates = find_duplicates(df, "test_file", tolerance=1.0)
        assert len(duplicates) == 0  # 너무 멀리 떨어져 있음
