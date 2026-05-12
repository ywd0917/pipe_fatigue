"""
파일 시스템 유틸리티 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.common.file_utils import (
    ensure_directory_exists,
    find_files_by_pattern,
    get_data_directory,
    get_file_by_keywords,
    get_shapefile_set,
    resolve_path,
    validate_file_exists,
)


class TestEnsureDirectoryExists:
    """ensure_directory_exists 함수 테스트"""

    def test_create_new_directory(self):
        """새 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "new_dir"
            assert not test_dir.exists()

            result = ensure_directory_exists(test_dir)

            assert test_dir.exists()
            assert test_dir.is_dir()
            assert result == test_dir

    def test_existing_directory(self):
        """기존 디렉토리 처리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)

            result = ensure_directory_exists(test_dir)

            assert result == test_dir
            assert test_dir.exists()

    def test_nested_directories(self):
        """중첩 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "level1" / "level2" / "level3"

            result = ensure_directory_exists(test_dir)

            assert test_dir.exists()
            assert result == test_dir


class TestFindFilesByPattern:
    """find_files_by_pattern 함수 테스트"""

    def test_find_files_by_extension(self):
        """확장자로 파일 찾기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # 테스트 파일 생성
            (base_dir / "file1.shp").touch()
            (base_dir / "file2.shp").touch()
            (base_dir / "file3.txt").touch()

            # .shp 파일만 찾기
            files = find_files_by_pattern(base_dir, "*.shp", recursive=False)

            assert len(files) == 2
            assert all(f.suffix == ".shp" for f in files)
            assert files[0].name == "file1.shp"
            assert files[1].name == "file2.shp"

    def test_recursive_search(self):
        """재귀적 검색"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            sub_dir = base_dir / "subdir"
            sub_dir.mkdir()

            # 파일 생성
            (base_dir / "file1.csv").touch()
            (sub_dir / "file2.csv").touch()

            # 재귀 검색
            files = find_files_by_pattern(base_dir, "*.csv", recursive=True)

            assert len(files) == 2
            assert any("subdir" in str(f) for f in files)

    def test_nonexistent_directory(self):
        """존재하지 않는 디렉토리"""
        base_dir = Path("/nonexistent/directory")

        files = find_files_by_pattern(base_dir, "*.txt")

        assert files == []

    @patch("src.common.file_utils.logger")
    def test_logging(self, mock_logger):
        """로깅 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "test.txt").touch()

            _ = find_files_by_pattern(base_dir, "*.txt")

            mock_logger.debug.assert_called_once()
            # 로그 형식이 "Found %d files matching pattern '%s' in %s" 이므로 파라미터 확인
            assert (
                mock_logger.debug.call_args[0][0]
                == "Found %d files matching pattern '%s' in %s"
            )
            assert mock_logger.debug.call_args[0][1] == 1  # 파일 개수
            assert (
                mock_logger.debug.call_args[0][2] == "**/*.txt"
            )  # recursive=True일 때 자동으로 **/ 추가됨


class TestGetFileByKeywords:
    """get_file_by_keywords 함수 테스트"""

    def test_find_file_with_keywords(self):
        """키워드로 파일 찾기"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # 테스트 파일 생성
            (base_dir / "road_network_2024.shp").touch()
            (base_dir / "soil_layer.shp").touch()

            # road와 network 키워드로 찾기
            file = get_file_by_keywords(base_dir, ["road", "network"])

            assert file is not None
            assert file.name == "road_network_2024.shp"

    def test_case_insensitive_search(self):
        """대소문자 구분 없는 검색"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "Road_Network.shp").touch()

            # 소문자 키워드로 검색
            file = get_file_by_keywords(
                base_dir, ["road", "network"], case_sensitive=False
            )

            assert file is not None
            assert file.name == "Road_Network.shp"

    def test_case_sensitive_search(self):
        """대소문자 구분 검색"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "Road_Network.shp").touch()

            # 대소문자가 맞지 않는 경우
            file = get_file_by_keywords(
                base_dir, ["road", "network"], case_sensitive=True
            )

            assert file is None

    def test_no_matching_file(self):
        """매칭되는 파일이 없는 경우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "something_else.shp").touch()

            file = get_file_by_keywords(base_dir, ["road", "network"])

            assert file is None


class TestValidateFileExists:
    """validate_file_exists 함수 테스트"""

    def test_existing_file(self):
        """존재하는 파일"""
        with tempfile.NamedTemporaryFile() as tmp:
            result = validate_file_exists(tmp.name, raise_error=False)
            assert result is True

    def test_nonexistent_file_no_raise(self):
        """존재하지 않는 파일 - 예외 발생 안함"""
        result = validate_file_exists("/nonexistent/file.txt", raise_error=False)
        assert result is False

    def test_nonexistent_file_raise(self):
        """존재하지 않는 파일 - 예외 발생"""
        with pytest.raises(FileNotFoundError) as excinfo:
            validate_file_exists("/nonexistent/file.txt", raise_error=True)

        assert "File not found" in str(excinfo.value)

    def test_directory_not_file(self):
        """디렉토리를 파일로 검사"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_file_exists(tmpdir, raise_error=False)
            assert result is False


class TestGetShapefileSet:
    """get_shapefile_set 함수 테스트"""

    def test_complete_shapefile_set(self):
        """완전한 shapefile 세트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test"

            # 필수 파일 생성
            for ext in [".shp", ".shx", ".dbf"]:
                (base_path.with_suffix(ext)).touch()

            # 선택적 파일 생성
            (base_path.with_suffix(".prj")).touch()

            file_set = get_shapefile_set(base_path.with_suffix(".shp"))

            assert ".shp" in file_set
            assert ".shx" in file_set
            assert ".dbf" in file_set
            assert ".prj" in file_set
            assert len(file_set) == 4

    @patch("src.common.file_utils.logger")
    def test_missing_required_files(self, mock_logger):
        """필수 파일이 없는 경우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = Path(tmpdir) / "test.shp"
            shp_path.touch()

            file_set = get_shapefile_set(shp_path)

            assert ".shp" in file_set
            assert ".shx" not in file_set
            assert ".dbf" not in file_set

            # 경고 로그 확인
            mock_logger.warning.assert_called_once()
            assert (
                "Missing required shapefile components"
                in mock_logger.warning.call_args[0][0]
            )


class TestGetDataDirectory:
    """get_data_directory 함수 테스트"""

    def test_existing_directory(self):
        """존재하는 디렉토리"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            sub_path = base_dir / "data" / "raw"
            sub_path.mkdir(parents=True)

            result = get_data_directory(base_dir, ["data", "raw"])

            assert result == sub_path
            assert result.exists()

    def test_create_missing_directory(self):
        """없는 디렉토리 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            result = get_data_directory(
                base_dir, ["data", "processed"], create_if_missing=True
            )

            assert result is not None
            assert result.exists()
            assert result == base_dir / "data" / "processed"

    def test_missing_directory_no_create(self):
        """없는 디렉토리 - 생성 안함"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            result = get_data_directory(
                base_dir, ["data", "processed"], create_if_missing=False
            )

            assert result is None


class TestResolvePath:
    """resolve_path 함수 테스트"""

    def test_absolute_path(self):
        """절대 경로"""
        abs_path = Path("/absolute/path")
        result = resolve_path(abs_path)
        assert result == abs_path

    def test_relative_path_with_base(self):
        """상대 경로 - 기준 디렉토리 지정"""
        base_dir = Path("/base/dir")
        rel_path = Path("subdir/file.txt")

        result = resolve_path(rel_path, base_dir)

        assert result == Path("/base/dir/subdir/file.txt")

    def test_relative_path_no_base(self):
        """상대 경로 - 기준 디렉토리 없음"""
        rel_path = Path("subdir/file.txt")

        with patch("pathlib.Path.cwd", return_value=Path("/current/dir")):
            result = resolve_path(rel_path)

        assert result == Path("/current/dir/subdir/file.txt")

    def test_path_resolution(self):
        """경로 정규화"""
        base_dir = Path("/base/dir")
        complex_path = Path("./subdir/../another/./file.txt")

        result = resolve_path(complex_path, base_dir)

        assert result == Path("/base/dir/another/file.txt")
