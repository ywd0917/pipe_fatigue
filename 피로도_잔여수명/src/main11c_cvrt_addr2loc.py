"""
공사관리대장 CSV 파일에서 주소를 좌표로 변환하고 작업일시를 추가
data/repair3/공사관리대장(0520).csv 파일을 읽어서 처리
결과는 results/repair3/관리대장_위치추가.csv로 저장
"""

import argparse
import logging
import warnings
from pathlib import Path

import pandas as pd

from src.common.config import DATA_DIR, RESULTS_DIR
from src.common.geocoding_constants import DEFAULT_API_DELAY

# main11에서 지오코딩 함수 import
from src.main11_convert_addr2loc import (
    load_geocoding_service,
    geocode_addresses,
    preprocess_address,
)

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 로거 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_work_datetime_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    작업일시 컬럼 생성 (접수번호와 공사일자 조합)

    Args:
        df: 입력 DataFrame

    Returns:
        작업일시 컬럼이 추가된 DataFrame
    """
    logger.info("작업일시 컬럼 생성 시작")

    work_datetimes = []
    last_valid_year = None  # 마지막 유효한 년도 저장
    invalid_count = 0

    for idx, row in df.iterrows():
        receipt_no = row.get("접수번호", "")
        work_date = row.get("공사일자", "")  # MM-DD 형식

        # 접수번호에서 년도 추출
        if receipt_no and str(receipt_no) != "-" and len(str(receipt_no)) >= 8:
            year = str(receipt_no)[:4]
            if year.isdigit() and 2000 <= int(year) <= 2030:
                last_valid_year = year  # 유효한 년도 저장
            else:
                year = last_valid_year if last_valid_year else "2024"
                invalid_count += 1
                if invalid_count <= 5:  # 처음 5개만 로그
                    logger.info(
                        f"행 {idx}: 비정상 접수번호 '{receipt_no}', 이전 년도 {year} 사용"
                    )
        else:
            # 접수번호가 없거나 '-'인 경우
            year = last_valid_year if last_valid_year else "2024"
            invalid_count += 1
            if invalid_count <= 5:  # 처음 5개만 로그
                logger.info(f"행 {idx}: 접수번호 없음/비정상, 이전 년도 {year} 사용")

        # MM-DD 형식을 YYYY-MM-DD로 변환
        if work_date and "-" in str(work_date):
            try:
                month, day = str(work_date).split("-")
                work_datetime = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except Exception as e:
                logger.warning(f"행 {idx}: 공사일자 파싱 실패 '{work_date}': {e}")
                work_datetime = None
        else:
            work_datetime = None

        work_datetimes.append(work_datetime)

    df["작업일시"] = work_datetimes

    # 통계 출력
    valid_count = sum(1 for dt in work_datetimes if dt is not None)
    logger.info(f"  - 작업일시 생성 완료: {valid_count}/{len(df)}개")
    if invalid_count > 0:
        logger.info(f"  - 비정상 접수번호: {invalid_count}개 (이전 년도 사용)")

    return df


def load_and_process_data(file_path: Path) -> pd.DataFrame:
    """
    CSV 파일 로드 및 전처리

    Args:
        file_path: CSV 파일 경로

    Returns:
        전처리된 DataFrame
    """
    logger.info(f"파일 로드 중: {file_path.name}")

    # CSV 파일 읽기
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file_path, encoding="cp949")
        except Exception as e:
            logger.error(f"파일을 읽을 수 없습니다: {e}")
            raise

    initial_count = len(df)

    # '지시번호'가 '계' 또는 '소계'인 행 제외
    if "지시번호" in df.columns:
        df = df[~df["지시번호"].astype(str).str.strip().isin(["계", "소계"])]
        filtered_count = initial_count - len(df)
        if filtered_count > 0:
            logger.info(f"  - '계'/'소계' 행 {filtered_count}개 제외")

    logger.info(f"  - 로드 완료: {len(df)}행")

    return df


def add_geocoding(
    df: pd.DataFrame,
    use_cache: bool = True,
    api_delay: float = DEFAULT_API_DELAY,
    no_api: bool = False,
) -> tuple[pd.DataFrame, list]:
    """
    주소를 좌표로 변환하여 컬럼 추가

    Args:
        df: 입력 DataFrame
        use_cache: 캐시 사용 여부
        api_delay: API 호출 간격
        no_api: API 호출 비활성화 여부

    Returns:
        (지오코딩이 추가된 DataFrame, 실패한 주소 리스트)
    """
    logger.info("지오코딩 시작")

    # 주소 컬럼 확인
    if "위치" not in df.columns:
        logger.error("위치 컬럼이 없습니다")
        raise ValueError("위치 컬럼이 필요합니다")

    # 주소 추출 및 전처리
    addresses = (
        df["위치"]
        .apply(lambda x: preprocess_address(str(x)) if pd.notna(x) else "")
        .tolist()
    )
    logger.info(f"  - 처리할 주소: {len(addresses)}개")

    # 지오코딩 수행
    latitudes, longitudes, failed_addresses = geocode_addresses(
        addresses, use_cache=use_cache, api_delay=api_delay, no_api=no_api
    )

    # 컬럼 추가
    df["위도"] = latitudes
    df["경도"] = longitudes

    # 성공률 계산
    success_count = sum(1 for lat in latitudes if lat is not None)
    success_rate = (success_count / len(addresses) * 100) if addresses else 0
    logger.info(
        f"  - 지오코딩 완료: {success_count}/{len(addresses)}개 성공 ({success_rate:.1f}%)"
    )

    return df, failed_addresses


def save_results(df: pd.DataFrame, output_path: Path, failed_addresses: list) -> None:
    """
    결과 저장 및 실패 주소 기록

    Args:
        df: 저장할 DataFrame
        output_path: 출력 파일 경로
        failed_addresses: 실패한 주소 리스트
    """
    # 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # CSV 저장
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"결과 저장 완료: {output_path}")
    logger.info(f"  - 총 {len(df)}행 x {len(df.columns)}열")

    # 위치 정보가 있는 행 수 출력
    valid_locations = df[(df["위도"].notna()) & (df["경도"].notna())]
    logger.info(f"  - 유효한 좌표: {len(valid_locations)}행")

    # 작업일시가 있는 행 수 출력
    valid_datetime = df[df["작업일시"].notna()]
    logger.info(f"  - 유효한 작업일시: {len(valid_datetime)}행")

    # 실패한 주소 저장
    if failed_addresses:
        failed_file = output_path.parent / f"{output_path.stem}_실패주소.txt"
        with failed_file.open("w", encoding="utf-8") as f:
            f.write(f"# 좌표 변환 실패 주소 목록 ({len(failed_addresses)}개)\n")
            f.write(f"# 생성 시간: {pd.Timestamp.now()}\n")
            f.write(f"# 출력 파일: {output_path.name}\n\n")
            for addr in failed_addresses:
                f.write(f"{addr}\n")
        logger.info(f"  - 실패 주소 저장: {failed_file.name}")


def main(
    use_api: bool = True,
    geocoding_service: str = "naver",
    use_cache: bool = True,
    test_mode: bool = False,
):
    """메인 실행 함수"""
    print("=" * 80)
    print("공사관리대장 데이터 지오코딩 및 작업일시 추가")
    print("=" * 80)

    # 파일 경로 설정
    input_dir = DATA_DIR / "repair3"
    if test_mode:
        input_file = input_dir / "test_10.csv"
        print("*** 테스트 모드: test_10.csv 파일 사용 ***")
    else:
        input_file = input_dir / "공사관리대장(0520).csv"
    output_dir = RESULTS_DIR
    output_file = output_dir / "관리대장_위치추가.csv"

    # 입력 파일 존재 확인
    if not input_file.exists():
        print(f"\n❌ 오류: 입력 파일이 없습니다.")
        print(f"  필요한 파일: {input_file}")
        print(f"\n파일을 '{input_dir}' 디렉토리에 추가한 후 다시 실행하세요.")
        logger.error(f"입력 파일 없음: {input_file}")
        return

    # 지오코딩 서비스 로드
    try:
        load_geocoding_service(geocoding_service)
        logger.info(f"{geocoding_service.capitalize()} 지오코딩 서비스 로드 완료")
    except Exception as e:
        logger.error(f"지오코딩 서비스 로드 실패: {e}")
        return

    try:
        # 1. 데이터 로드 및 전처리
        print("\n1. 데이터 파일 로드")
        df = load_and_process_data(input_file)

        # 2. 작업일시 컬럼 추가
        print("\n2. 작업일시 컬럼 생성")
        df = create_work_datetime_column(df)

        # 3. 지오코딩 적용
        print("\n3. 주소를 좌표로 변환 (지오코딩)")
        if not use_api:
            print("   ※ 캐시만 사용합니다 (API 호출 비활성화)")
        else:
            print("   ※ 처리 시간이 걸릴 수 있습니다...")

        df, failed_addresses = add_geocoding(
            df, use_cache=use_cache, no_api=not use_api
        )

        # 4. 결과 저장
        print("\n4. 결과 저장")
        save_results(df, output_file, failed_addresses)

        # 5. 최종 요약
        print("\n" + "=" * 80)
        print("처리 완료 요약")
        print("=" * 80)
        print(f"입력 파일: {input_file.name}")
        print(f"출력 파일: {output_file.name}")
        print(f"처리된 행: {len(df)}행")

        # 지오코딩 통계
        valid_locations = df[(df["위도"].notna()) & (df["경도"].notna())]
        print(f"\n지오코딩 결과:")
        print(f"  - 성공: {len(valid_locations)}개")
        print(f"  - 실패: {len(failed_addresses)}개")
        print(f"  - 성공률: {len(valid_locations)/len(df)*100:.1f}%")

        # 작업일시 통계
        valid_datetime = df[df["작업일시"].notna()]
        print(f"\n작업일시 생성:")
        print(f"  - 성공: {len(valid_datetime)}개")
        print(f"  - 실패: {len(df) - len(valid_datetime)}개")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="공사관리대장 데이터 지오코딩")
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="API 호출 없이 캐시만 사용 (기존 캐시된 데이터만 사용)",
    )
    parser.add_argument(
        "--geocoding-service",
        type=str,
        choices=["kakao", "naver"],
        default="naver",
        help="사용할 geocoding 서비스 (기본값: naver)",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="캐시 사용 안함 (항상 API 호출)"
    )
    parser.add_argument(
        "--test", action="store_true", help="테스트 모드 (test_10.csv 파일 사용)"
    )

    args = parser.parse_args()
    main(
        use_api=not args.no_api,
        geocoding_service=args.geocoding_service,
        use_cache=not args.no_cache,
        test_mode=args.test,
    )
