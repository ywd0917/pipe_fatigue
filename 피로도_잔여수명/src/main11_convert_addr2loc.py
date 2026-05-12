"""
주소를 위치 좌표로 변환하는 스크립트
data/repair2/ 폴더의 CSV 파일에 위도/경도 컬럼을 추가하여
results/repair2/ 폴더에 저장
"""

import argparse
import logging
import time
import warnings
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from src.common.config import DATA_DIR, RESULTS_DIR
from src.common.geocoding_constants import (
    DEFAULT_API_DELAY,
    PROGRESS_LOG_INTERVAL,
    STATISTICS_LOG_INTERVAL,
)

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 로거 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Geocoding 서비스 선택

GEOCODING_SERVICE: str | None = None
geocode_address: Callable[[str, bool], tuple[float, float] | None] | None = None
check_api_credentials: Callable[[], bool] | None = None


def parse_numeric_date_column(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    숫자 형식의 날짜 컬럼을 datetime으로 파싱

    Args:
        df: DataFrame
        column_name: 파싱할 컬럼명

    Returns:
        파싱된 datetime Series (파싱 실패 시 NaT)
    """
    if column_name not in df.columns:
        return pd.Series(pd.NaT, index=df.index)

    # 숫자 형식 (예: 202206230912.0)을 문자열로 변환
    date_str = df[column_name].astype(str).str.replace(".0", "", regex=False)

    # 자릿수에 따라 다른 형식으로 파싱
    dates = pd.Series(pd.NaT, index=df.index)

    # 14자리: YYYYMMDDHHMMSS (초 포함)
    mask_14 = date_str.str.len() == 14
    if mask_14.any():
        dates.loc[mask_14] = pd.to_datetime(
            date_str[mask_14], format="%Y%m%d%H%M%S", errors="coerce"
        )

    # 12자리: YYYYMMDDHHMM (분까지) 또는 YYYYMMDDNNNN (민원접수번호)
    mask_12 = date_str.str.len() == 12
    if mask_12.any():
        # 민원접수번호 형식인 경우 앞 8자리만 사용
        if column_name == "민원접수번호":
            dates.loc[mask_12] = pd.to_datetime(
                date_str[mask_12].str[:8], format="%Y%m%d", errors="coerce"
            )
        else:
            dates.loc[mask_12] = pd.to_datetime(
                date_str[mask_12], format="%Y%m%d%H%M", errors="coerce"
            )

    # 13자리 또는 기타: 자동 파싱 시도
    mask_other = ~mask_14 & ~mask_12 & (date_str.str.len() > 0) & (date_str != "nan")
    if mask_other.any():
        dates.loc[mask_other] = pd.to_datetime(
            date_str[mask_other], errors="coerce"
        )

    # 비정상적인 날짜 필터링 (2000년 이전, 2030년 이후)
    dates.loc[dates.dt.year < 2000] = pd.NaT
    dates.loc[dates.dt.year > 2030] = pd.NaT

    return dates


def load_geocoding_service(service: str = "naver") -> None:
    """
    Geocoding 서비스 로드

    Args:
        service: 사용할 서비스 (kakao, naver)
    """
    global GEOCODING_SERVICE, geocode_address, check_api_credentials, GeocodingError

    GEOCODING_SERVICE = service

    if service == "kakao":
        from src.common.geocoding_kakao_sqlite_v2 import (
            check_api_credentials as _check_api_credentials,
        )
        from src.common.geocoding_kakao_sqlite_v2 import (
            geocode_address as _geocode_address,
        )

        geocode_address = _geocode_address
        check_api_credentials = _check_api_credentials
        logger.info("Kakao SQLite 캐시 사용")
    elif service == "naver":
        from src.common.geocoding_naver_sqlite import (
            check_api_credentials as _check_api_credentials,
        )
        from src.common.geocoding_naver_sqlite import (
            geocode_address as _geocode_address,
        )

        geocode_address = _geocode_address
        check_api_credentials = _check_api_credentials
        logger.info("Naver SQLite 캐시 사용")
    else:
        raise ValueError(f"지원하지 않는 geocoding 서비스: {service}")

    logger.info("Geocoding 서비스 로드: %s", service.upper())


def geocode_addresses(
    addresses: list[str | None],
    use_cache: bool = True,
    api_delay: float = DEFAULT_API_DELAY,
    no_api: bool = False,
) -> tuple[list[float | None], list[float | None], list[str]]:
    """
    주소 리스트를 좌표로 변환

    Args:
        addresses: 변환할 주소 리스트 (None 포함 가능)
        use_cache: 캐시 사용 여부
        api_delay: API 호출 간 지연 시간
        no_api: API 호출 없이 캐시만 사용 (오프라인 모드)

    Returns:
        (위도 리스트, 경도 리스트, 실패 주소 리스트) - 변환 실패 시 None
    """
    # 유효한 주소 개수 계산
    valid_count = sum(
        1
        for addr in addresses
        if addr is not None and str(addr).strip() and str(addr).lower() != "nan"
    )

    if no_api:
        logger.info(
            "오프라인 모드: 주소 %d개 중 유효한 주소 %d개를 캐시에서 검색 중...",
            len(addresses),
            valid_count,
        )
    else:
        logger.info(
            "주소 %d개 중 유효한 주소 %d개를 좌표로 변환 중...",
            len(addresses),
            valid_count,
        )

    # API 자격 증명 확인 (no_api 모드에서는 건너뜀)
    if not no_api and (check_api_credentials is None or not check_api_credentials()):
        logger.error("API 자격 증명이 없습니다. .env 파일을 확인해주세요.")
        logger.info(
            ".env.example 파일을 참고하여 .env 파일을 생성하고 API 키를 설정해주세요."
        )
        return [None] * len(addresses), [None] * len(addresses), []

    try:
        # 결과 리스트 초기화
        latitudes: list[float | None] = []
        longitudes: list[float | None] = []
        success_count = 0
        failed_addresses = []
        valid_processed = 0

        # 각 주소 처리
        for i, address in enumerate(addresses):
            # nan, None, 빈 문자열 체크
            if address is None or (
                isinstance(address, str)
                and (not address.strip() or address.lower() == "nan")
            ):
                latitudes.append(None)
                longitudes.append(None)
                continue

            # 유효한 주소인 경우 geocoding
            valid_processed += 1
            try:
                # 진행률 표시 (유효한 주소 기준)
                if valid_processed % PROGRESS_LOG_INTERVAL == 0 or valid_processed == 1:
                    progress = valid_processed / valid_count * 100
                    logger.info(
                        "진행 상황: [%d/%d] (%.1f%%)",
                        valid_processed,
                        valid_count,
                        progress,
                    )

                if geocode_address is None:
                    raise RuntimeError("Geocoding service not loaded")
                result = geocode_address(address, use_cache, no_api)
                if result:
                    lat, lon = result
                    latitudes.append(lat)
                    longitudes.append(lon)
                    success_count += 1
                else:
                    latitudes.append(None)
                    longitudes.append(None)
                    failed_addresses.append(address)

                # 중간 통계 출력
                if valid_processed % STATISTICS_LOG_INTERVAL == 0:
                    current_success_rate = (success_count / valid_processed) * 100
                    fail_count = valid_processed - success_count
                    logger.info(
                        "=== 중간 통계: %d개 성공, %d개 실패, 성공률 %.1f%% ===",
                        success_count,
                        fail_count,
                        current_success_rate,
                    )

            except Exception as e:
                logger.error("주소 변환 실패 [%s]: %s", address, e)
                latitudes.append(None)
                longitudes.append(None)
                failed_addresses.append(address)

            # API 호출 간 지연
            if i < len(addresses) - 1 and valid_processed > 0:
                time.sleep(api_delay)

        logger.info("Geocoding 완료: %d/%d개 성공", success_count, valid_count)
        if failed_addresses:
            logger.info("실패한 주소 %d개", len(failed_addresses))

        return latitudes, longitudes, failed_addresses

    except Exception as e:
        logger.error("Geocoding 오류: %s", e)
        return [None] * len(addresses), [None] * len(addresses), []


def preprocess_address(address: str) -> str:
    """
    주소 전처리

    Args:
        address: 원본 주소

    Returns:
        전처리된 주소
    """
    if not address or not isinstance(address, str):
        return address

    # 기본 정리
    addr = address.strip()

    # 슬래시가 있으면 슬래시 전까지만 사용
    if "/" in addr:
        addr = addr.split("/")[0].strip()

    # 괄호가 있으면 괄호 전까지만 사용
    if "(" in addr:
        addr = addr.split("(")[0].strip()

    # 특수 키워드 제거 (폐전, 폐지 등)
    remove_keywords = ["폐전", "폐지", "폐업", "철거"]
    for keyword in remove_keywords:
        if keyword in addr:
            addr = addr.replace(keyword, "").strip()

    # 시도명이 없으면 추가 (대구 지역 가정)
    if not any(
        city in addr
        for city in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
    ) and any(gu in addr for gu in ["남구", "북구", "동구", "서구", "중구", "수성구", "달서구", "달성군"]):
        addr = "대구 " + addr

    return addr


def process_csv_file(
    input_path: Path,
    output_path: Path,
    use_cache: bool = True,
    api_delay: float = DEFAULT_API_DELAY,
    no_api: bool = False,
    verbose: bool = True,
) -> None:
    """
    CSV 파일에 위도/경도 컬럼 추가

    Args:
        input_path: 입력 CSV 파일 경로
        output_path: 출력 CSV 파일 경로
        verbose: 상세 정보 출력 여부
    """
    if verbose:
        print(f"\n파일 처리 중: {input_path.name}")

    # CSV 파일 읽기 (low_memory=False로 dtype 경고 방지)
    try:
        df = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        # 다른 인코딩 시도
        try:
            df = pd.read_csv(input_path, encoding="cp949", low_memory=False)
        except Exception as e:
            print(f"  오류: 파일을 읽을 수 없습니다 - {e}")
            return

    if verbose:
        print(f"  - 원본 데이터: {len(df)}행 x {len(df.columns)}열")

    # 주소 컬럼 확인
    if "주소" not in df.columns:
        logger.error("주소 컬럼이 없습니다: %s", input_path.name)
        return

    # 주소를 좌표로 변환
    addresses = df["주소"].tolist()

    # 원본 주소를 그대로 사용 (전처리 없음)
    latitudes, longitudes, failed_addresses = geocode_addresses(
        addresses, use_cache=use_cache, api_delay=api_delay, no_api=no_api
    )

    # 새로운 컬럼 추가
    df["위도"] = latitudes
    df["경도"] = longitudes

    # 날짜 컬럼 통합 - 우선순위: 접수일시 > 작업시작일시 > 작업종료일
    # 각 행마다 우선순위를 적용
    date_columns = []
    if "접수일시" in df.columns:
        date_columns.append(parse_numeric_date_column(df, "접수일시"))
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df), index=df.index))

    if "작업시작일시" in df.columns:
        date_columns.append(parse_numeric_date_column(df, "작업시작일시"))
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df), index=df.index))

    if "작업종료일" in df.columns:
        date_columns.append(parse_numeric_date_column(df, "작업종료일"))
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df), index=df.index))

    # 4순위: 민원접수번호 (날짜 정보가 포함된 경우)
    if "민원접수번호" in df.columns:
        date_columns.append(parse_numeric_date_column(df, "민원접수번호"))
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df), index=df.index))

    # 우선순위에 따라 첫 번째 유효한 날짜 선택
    df["작업일시"] = date_columns[0].fillna(date_columns[1]).fillna(date_columns[2]).fillna(date_columns[3])

    # 변환 성공률 계산
    success_count = sum(1 for lat in latitudes if lat is not None)
    if verbose:
        print(f"  - 좌표 변환: {success_count}/{len(df)}개 성공")
        # 작업일시 생성 정보 추가
        if "작업일시" in df.columns:
            valid_dates = df["작업일시"].notna().sum()
            print(f"  - 작업일시 생성: {valid_dates}/{len(df)}개")

    # 결과 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if verbose:
        print(f"  - 저장 완료: {output_path}")
        print(f"  - 결과 데이터: {len(df)}행 x {len(df.columns)}열")

    # 실패한 주소를 별도 파일로 저장
    if failed_addresses:
        failed_file = output_path.parent / f"{output_path.stem}_실패주소.txt"
        with failed_file.open("w", encoding="utf-8") as f:
            f.write(f"# 좌표 변환 실패 주소 목록 ({len(failed_addresses)}개)\n")
            f.write(f"# 생성 시간: {pd.Timestamp.now()}\n")
            f.write(f"# 원본 파일: {input_path.name}\n\n")
            for addr in failed_addresses:
                f.write(f"{addr}\n")
        if verbose:
            print(f"  - 실패 주소 저장: {failed_file}")


def get_repair2_files(data_dir: Path) -> list[Path]:
    """
    repair2 디렉토리의 모든 CSV 파일 찾기

    Args:
        data_dir: 데이터 디렉토리

    Returns:
        CSV 파일 경로 리스트
    """
    repair2_dir = data_dir / "repair2"
    if not repair2_dir.exists():
        print(f"오류: {repair2_dir} 디렉토리를 찾을 수 없습니다.")
        return []

    csv_files = list(repair2_dir.glob("*.csv"))
    return sorted(csv_files)


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="복구 작업 CSV 파일에 위도/경도 컬럼을 추가하여 위치 정보 포함 파일 생성"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="처리할 CSV 파일명 (예: 기타공사.csv, 지상누수.csv). 지정하지 않으면 모든 파일 처리",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="data/repair2 폴더의 모든 CSV 파일 처리 (기본값)",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="입력 디렉토리 (기본값: data/repair2)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 (기본값: results)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Geocoding 캐시 사용 안함",
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="API 호출 없이 SQLite 캐시만 사용 (오프라인 모드)",
    )
    parser.add_argument(
        "--api-delay",
        type=float,
        default=DEFAULT_API_DELAY,
        help=f"API 호출 간 지연 시간 (초, 기본값: {DEFAULT_API_DELAY})",
    )
    parser.add_argument(
        "--geocoding-service",
        type=str,
        choices=["kakao", "naver"],
        default="naver",
        help="사용할 geocoding 서비스 (기본값: naver)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="최소 정보만 출력",
    )

    args = parser.parse_args()

    # 디렉토리 설정
    input_dir = Path(args.input_dir) if args.input_dir else DATA_DIR / "repair2"
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    verbose = not args.quiet
    use_cache = not args.no_cache
    no_api = args.no_api

    # Geocoding 서비스 로드
    load_geocoding_service(args.geocoding_service)

    print("복구 작업 CSV 파일 처리 시작...")
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    print(f"Geocoding 서비스: {args.geocoding_service.upper()}")
    print(f"캐시 사용: {'예' if use_cache else '아니오'}")
    if no_api:
        print(f"모드: 오프라인 (API 호출 없음, 캐시만 사용)")
    else:
        print(f"API 지연 시간: {args.api_delay}초")

    # API 자격 증명 확인 (no_api 모드에서는 건너뜀)
    if not no_api and (check_api_credentials is None or not check_api_credentials()):
        print(
            f"\n[오류] {args.geocoding_service.upper()} API 키가 설정되지 않았습니다."
        )
        print("다음 단계를 따라주세요:")
        print("1. .env.example 파일을 .env로 복사")
        if args.geocoding_service == "kakao":
            print("2. .env 파일에 KAKAO_API_KEY 설정")
            print("3. https://developers.kakao.com 에서 REST API 키 확인")
        else:
            print("2. .env 파일에 NAVER_API_KEY_ID와 NAVER_API_KEY 설정")
            print(
                "3. https://console.ncloud.com/naver-service/application 에서 API 키 확인"
            )
        return

    # CSV 파일 결정
    csv_files = []
    if args.files:
        # 특정 파일들이 지정된 경우
        for filename in args.files:
            file_path = input_dir / filename
            if file_path.exists():
                csv_files.append(file_path)
            else:
                print(f"경고: {filename} 파일을 찾을 수 없습니다.")
    else:
        # 모든 CSV 파일 처리 (--all이 기본값)
        csv_files = get_repair2_files(
            input_dir.parent if input_dir.name == "repair2" else input_dir
        )

    if not csv_files:
        print("처리할 CSV 파일이 없습니다.")
        return

    print(f"\n처리할 CSV 파일: {len(csv_files)}개")
    for f in csv_files:
        print(f"  - {f.name}")

    # 각 파일 처리
    for csv_file in csv_files:
        # 출력 파일명 생성
        output_filename = f"{csv_file.stem}_위치추가.csv"
        output_path = output_dir / output_filename

        # 파일 처리
        process_csv_file(
            csv_file, output_path, use_cache, args.api_delay, no_api, verbose
        )

    print("\n모든 파일 처리 완료!")
    print(f"결과 파일 위치: {output_dir}")

    # 캐시 통계 출력
    if use_cache:
        if GEOCODING_SERVICE == "kakao":
            from src.common.geocoding_kakao_sqlite_v2 import get_cache_stats
        elif GEOCODING_SERVICE == "naver":
            from src.common.geocoding_naver_sqlite import get_cache_stats

        stats = get_cache_stats()
        print("\n캐시 통계:")
        print(f"  - 총 캐시 항목: {stats['total']:,}개")
        print(f"  - 성공: {stats['success']:,}개 ({stats['success_rate']:.1f}%)")
        print(f"  - 주소 못찾음: {stats['not_found']:,}개")
        print(f"  - 오류: {stats['error']:,}개")


if __name__ == "__main__":
    main()
