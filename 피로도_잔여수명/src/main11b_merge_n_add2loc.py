"""
두 긴급공사 데이터에서 중복 데이터를 제거하고 병합 후 지오코딩 수행.
data/repair/ 폴더의 CSV 파일에서 두개의 파일을 읽어서 처리.
결과는 results/긴급공사_위치추가.csv로 저장.
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


def parse_date_column(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    날짜 컬럼을 datetime으로 파싱 (문자열/숫자 형식 모두 지원)

    Args:
        df: DataFrame
        column_name: 파싱할 컬럼명

    Returns:
        파싱된 datetime Series (파싱 실패 시 NaT)
    """
    if column_name not in df.columns:
        return pd.Series(pd.NaT, index=df.index)

    # 샘플로 형식 확인
    sample = (
        df[column_name].dropna().iloc[0] if not df[column_name].dropna().empty else None
    )

    if sample is None:
        return pd.Series(pd.NaT, index=df.index)

    # 문자열 형식 처리 ("YYYY-MM-DD HH:MM")
    if isinstance(sample, str) and "-" in str(sample):
        dates = pd.to_datetime(
            df[column_name], format="%Y-%m-%d %H:%M", errors="coerce"
        )
    # 숫자 형식 처리 (YYYYMMDDHHMM.0)
    else:
        date_str = df[column_name].astype(str).str.replace(".0", "", regex=False)
        dates = pd.to_datetime(date_str, format="%Y%m%d%H%M", errors="coerce")

    # 비정상 날짜 필터링 (2000년 이전, 2030년 이후)
    dates.loc[dates.dt.year < 2000] = pd.NaT
    dates.loc[dates.dt.year > 2030] = pd.NaT

    return dates


def load_repair_data(file_path: Path) -> pd.DataFrame:
    """
    CSV 파일 로드 및 기본 전처리

    Args:
        file_path: CSV 파일 경로

    Returns:
        전처리된 DataFrame
    """
    logger.info(f"파일 로드 중: {file_path.name}")

    # CSV 파일 읽기 (인코딩 처리)
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


def remove_duplicates_and_merge(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    접수번호 기준 중복 제거 및 병합

    Args:
        df1: 첫 번째 DataFrame (긴급복구.csv)
        df2: 두 번째 DataFrame (긴급복구공사관리.csv)

    Returns:
        중복 제거 후 병합된 DataFrame
    """
    logger.info("중복 제거 및 병합 시작")
    logger.info(f"  - 입력: df1={len(df1)}행, df2={len(df2)}행")

    # 접수번호가 있는 행과 없는 행 분리
    df1_with_receipt = df1[df1["접수번호"].notna() & (df1["접수번호"] != "")]
    df1_no_receipt = df1[df1["접수번호"].isna() | (df1["접수번호"] == "")]

    df2_with_receipt = df2[df2["접수번호"].notna() & (df2["접수번호"] != "")]
    df2_no_receipt = df2[df2["접수번호"].isna() | (df2["접수번호"] == "")]

    logger.info(
        f"  - df1: 접수번호 있음={len(df1_with_receipt)}, 없음={len(df1_no_receipt)}"
    )
    logger.info(
        f"  - df2: 접수번호 있음={len(df2_with_receipt)}, 없음={len(df2_no_receipt)}"
    )

    # 중복 제거 (df1 우선)
    receipt_nums_df1 = set(df1_with_receipt["접수번호"].astype(str))
    df2_duplicates = df2_with_receipt[
        df2_with_receipt["접수번호"].astype(str).isin(receipt_nums_df1)
    ]
    df2_unique = df2_with_receipt[
        ~df2_with_receipt["접수번호"].astype(str).isin(receipt_nums_df1)
    ]

    duplicate_count = len(df2_duplicates)
    if duplicate_count > 0:
        logger.info(f"  - 중복 접수번호 {duplicate_count}개 발견 (df2에서 제거)")
        # 중복된 접수번호 샘플 출력
        sample_duplicates = list(df2_duplicates["접수번호"].head(5))
        logger.info(f"    예시: {sample_duplicates}")

    # 병합
    result = pd.concat(
        [
            df1_with_receipt,  # df1의 접수번호 있는 행
            df1_no_receipt,  # df1의 접수번호 없는 행
            df2_unique,  # df2의 중복 제거된 행
            df2_no_receipt,  # df2의 접수번호 없는 행
        ],
        ignore_index=True,
    )

    logger.info(f"  - 병합 완료: 총 {len(result)}행")
    logger.info(
        f"    (df1: {len(df1)}행 + df2: {len(df2_unique) + len(df2_no_receipt)}행)"
    )

    # 날짜 컬럼 통합 - 우선순위: 접수일시 > 작업시작 > 작업종료
    if "접수일시" in result.columns:
        result["작업일시"] = parse_date_column(result, "접수일시")
    elif "작업시작" in result.columns:
        result["작업일시"] = parse_date_column(result, "작업시작")
    elif "작업종료" in result.columns:
        result["작업일시"] = parse_date_column(result, "작업종료")
    else:
        result["작업일시"] = pd.NaT

    logger.info(f"  - 작업일시 컬럼 생성 완료")

    return result


def add_geocoding(
    df: pd.DataFrame,
    use_cache: bool = True,
    api_delay: float = DEFAULT_API_DELAY,
    use_api: bool = True,
) -> tuple[pd.DataFrame, list]:
    """
    주소를 좌표로 변환하여 컬럼 추가

    Args:
        df: 입력 DataFrame
        use_cache: 캐시 사용 여부
        api_delay: API 호출 간격
        use_api: API 호출 사용 여부 (False면 캐시만 사용)

    Returns:
        (지오코딩이 추가된 DataFrame, 실패한 주소 리스트)
    """
    logger.info("지오코딩 시작")

    # 주소 컬럼 확인
    if "주소" not in df.columns:
        logger.error("주소 컬럼이 없습니다")
        raise ValueError("주소 컬럼이 필요합니다")

    # 주소 추출
    addresses = df["주소"].tolist()
    logger.info(f"  - 처리할 주소: {len(addresses)}개")

    # 지오코딩 수행
    latitudes, longitudes, failed_addresses = geocode_addresses(
        addresses, use_cache=use_cache, api_delay=api_delay, no_api=not use_api
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


def main(use_api: bool = True, geocoding_service: str = "naver"):
    """메인 실행 함수"""
    print("=" * 80)
    print("긴급공사 데이터 병합 및 지오코딩")
    print("=" * 80)

    # 파일 경로 설정
    repair_dir = DATA_DIR / "repair"
    file1_path = repair_dir / "긴급복구.csv"
    file2_path = repair_dir / "긴급복구공사관리(0520).csv"
    output_path = RESULTS_DIR / "긴급공사_위치추가.csv"

    # 입력 파일 존재 확인
    missing_files = []
    if not file1_path.exists():
        missing_files.append(str(file1_path))
    if not file2_path.exists():
        missing_files.append(str(file2_path))

    if missing_files:
        print("\n❌ 오류: 필수 입력 파일이 없습니다.")
        print("-" * 40)
        for file_path in missing_files:
            print(f"  파일 없음: {file_path}")
        print("-" * 40)
        print("\n다음 파일들이 필요합니다:")
        print(f"  1. {file1_path}")
        print(f"  2. {file2_path}")
        print(f"\n파일들을 '{repair_dir}' 디렉토리에 추가한 후 다시 실행하세요.")
        logger.error(f"필수 입력 파일 없음: {missing_files}")
        return

    # 지오코딩 서비스 로드
    try:
        load_geocoding_service(geocoding_service)
        logger.info(f"{geocoding_service.capitalize()} 지오코딩 서비스 로드 완료")
    except Exception as e:
        logger.error(f"{geocoding_service.capitalize()} 서비스 로드 실패: {e}")
        # 다른 서비스로 폴백 시도
        fallback_service = "kakao" if geocoding_service == "naver" else "naver"
        logger.info(f"{fallback_service.capitalize()} 서비스로 전환 시도")
        try:
            load_geocoding_service(fallback_service)
            logger.info(f"{fallback_service.capitalize()} 지오코딩 서비스 로드 완료")
        except Exception as e2:
            logger.error(f"지오코딩 서비스 로드 실패: {e2}")
            return

    try:
        # 1. 두 파일 로드
        print("\n1. 데이터 파일 로드")
        df1 = load_repair_data(file1_path)
        df2 = load_repair_data(file2_path)

        # 2. 중복 제거 및 병합
        print("\n2. 중복 제거 및 병합")
        merged_df = remove_duplicates_and_merge(df1, df2)

        # 3. 지오코딩 적용
        print("\n3. 주소를 좌표로 변환 (지오코딩)")
        if not use_api:
            print("   ※ 캐시만 사용합니다 (API 호출 비활성화)")
        else:
            print("   ※ 처리 시간이 걸릴 수 있습니다...")
        geocoded_df, failed_addresses = add_geocoding(
            merged_df, use_cache=True, use_api=use_api
        )

        # 4. 결과 저장
        print("\n4. 결과 저장")
        save_results(geocoded_df, output_path, failed_addresses)

        # 5. 최종 요약
        print("\n" + "=" * 80)
        print("처리 완료 요약")
        print("=" * 80)
        print(f"입력 파일 1: {file1_path.name} ({len(df1)}행)")
        print(f"입력 파일 2: {file2_path.name} ({len(df2)}행)")
        print(f"중복 제거 후: {len(merged_df)}행")
        print(f"출력 파일: {output_path.name}")

        # 지오코딩 통계
        valid_locations = geocoded_df[
            (geocoded_df["위도"].notna()) & (geocoded_df["경도"].notna())
        ]
        print(f"\n지오코딩 결과:")
        print(f"  - 성공: {len(valid_locations)}개")
        print(f"  - 실패: {len(failed_addresses)}개")
        print(f"  - 성공률: {len(valid_locations)/len(merged_df)*100:.1f}%")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="긴급공사 데이터 병합 및 지오코딩")
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

    args = parser.parse_args()
    main(use_api=not args.no_api, geocoding_service=args.geocoding_service)
