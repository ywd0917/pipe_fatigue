"""
파일 시스템 관련 공통 유틸리티

이 모듈은 파일 경로 처리, 파일 검색, 파일 읽기/쓰기 등의 공통 기능을 제공합니다.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_directory_exists(path: Path) -> Path:
    """
    디렉토리가 존재하는지 확인하고 없으면 생성

    Args:
        path: 확인할 디렉토리 경로

    Returns:
        생성되거나 확인된 디렉토리 경로
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_files_by_pattern(
    base_dir: Path, pattern: str, recursive: bool = True
) -> list[Path]:
    """
    패턴에 맞는 파일들을 찾아 반환

    Args:
        base_dir: 검색할 기본 디렉토리
        pattern: 파일 패턴 (예: "*.shp", "**/*.csv")
        recursive: 하위 디렉토리 포함 여부

    Returns:
        찾은 파일 경로 목록
    """
    base_dir = Path(base_dir)
    if not base_dir.exists():
        logger.warning("Directory not found: %s", base_dir)
        return []

    if recursive and "**" not in pattern:
        pattern = f"**/{pattern}"

    files = list(base_dir.glob(pattern))
    logger.debug(
        "Found %d files matching pattern '%s' in %s", len(files), pattern, base_dir
    )
    return sorted(files)


def get_file_by_keywords(
    base_dir: Path,
    keywords: list[str],
    extension: str = ".shp",
    case_sensitive: bool = False,
) -> Path | None:
    """
    키워드를 포함하는 파일 찾기

    Args:
        base_dir: 검색할 기본 디렉토리
        keywords: 파일명에 포함되어야 할 키워드 목록
        extension: 파일 확장자
        case_sensitive: 대소문자 구분 여부

    Returns:
        찾은 파일 경로 (없으면 None)
    """
    files = find_files_by_pattern(base_dir, f"*{extension}")

    for file in files:
        filename = file.name if case_sensitive else file.name.lower()
        keywords_to_check = (
            keywords if case_sensitive else [k.lower() for k in keywords]
        )

        if all(keyword in filename for keyword in keywords_to_check):
            logger.debug("Found file matching keywords %s: %s", keywords, file)
            return file

    logger.warning("No file found with keywords %s in %s", keywords, base_dir)
    return None


def validate_file_exists(file_path: str | Path, raise_error: bool = True) -> bool:
    """
    파일 존재 여부 확인

    Args:
        file_path: 확인할 파일 경로
        raise_error: 파일이 없을 때 예외 발생 여부

    Returns:
        파일 존재 여부

    Raises:
        FileNotFoundError: raise_error=True이고 파일이 없을 때
    """
    file_path = Path(file_path)
    exists = file_path.exists() and file_path.is_file()

    if not exists:
        msg = f"File not found: {file_path}"
        if raise_error:
            raise FileNotFoundError(msg)
        logger.warning(msg)

    return exists


def get_shapefile_set(shapefile_path: Path) -> dict[str, Path]:
    """
    Shapefile 관련 파일들(.shp, .shx, .dbf, .prj) 경로 반환

    Args:
        shapefile_path: .shp 파일 경로

    Returns:
        확장자별 파일 경로 딕셔너리
    """
    base_path = shapefile_path.with_suffix("")
    extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix"]

    file_set = {}
    for ext in extensions:
        file_path = base_path.with_suffix(ext)
        if file_path.exists():
            file_set[ext] = file_path

    # 필수 파일 확인
    required = [".shp", ".shx", ".dbf"]
    missing = [ext for ext in required if ext not in file_set]
    if missing:
        logger.warning(
            "Missing required shapefile components for %s: %s", shapefile_path, missing
        )

    return file_set


def get_data_directory(
    base_dir: Path, subdirs: list[str], create_if_missing: bool = False
) -> Path | None:
    """
    데이터 디렉토리 경로 가져오기

    Args:
        base_dir: 기본 디렉토리
        subdirs: 하위 디렉토리 목록
        create_if_missing: 없을 때 생성 여부

    Returns:
        데이터 디렉토리 경로 (없으면 None)
    """
    path = Path(base_dir)
    for subdir in subdirs:
        path = path / subdir

    if not path.exists():
        if create_if_missing:
            return ensure_directory_exists(path)
        logger.warning("Directory not found: %s", path)
        return None

    return path


def resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """
    상대 경로를 절대 경로로 변환

    Args:
        path: 변환할 경로
        base_dir: 기준 디렉토리 (None이면 현재 작업 디렉토리)

    Returns:
        절대 경로
    """
    path = Path(path)

    if path.is_absolute():
        return path

    base_dir = Path.cwd() if base_dir is None else Path(base_dir)

    return (base_dir / path).resolve()
