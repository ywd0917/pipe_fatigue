"""
재작업 데이터 통합 스크립트
results/*_위치추가.csv 파일들을 하나의 통합 파일로 병합
필수 컬럼: 작업일시, 위도, 경도
파일타입 컬럼을 추가하여 원본 파일 구분
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd

# Import SEARCH_COLUMNS and Unicode normalization from main11f for indoor filtering
from main11f_check_indoor import SEARCH_COLUMNS, search_with_normalization


# 처리할 파일명 목록 지정
# ※ 여기서 병합할 CSV 파일명을 직접 지정하세요
TARGET_FILES = [
    "지상누수_위치추가.csv",
    "지하누수_위치추가.csv",
    # "기타공사_위치추가.csv",
    "긴급공사_위치추가.csv",
    "관리대장_위치추가.csv",
]

# ID 컬럼 매핑 (각 파일별 고유 식별자 컬럼)
ID_COLUMN_MAPPING = {
    "지상누수_위치추가.csv": "긴급복구공사일련번호",
    "지하누수_위치추가.csv": "긴급복구공사일련번호",
    "긴급공사_위치추가.csv": "접수번호",
    "관리대장_위치추가.csv": "접수번호",
}


def filter_indoor_work(
    df: pd.DataFrame, file_name: str, search_columns: List[str], verbose: bool = False
) -> Tuple[pd.DataFrame, Dict]:
    """
    '옥내' 텍스트가 포함된 행을 필터링하여 제거

    Args:
        df: 원본 DataFrame
        file_name: 파일명 (컬럼 매핑용)
        search_columns: 검색할 컬럼 리스트
        verbose: 상세 출력 여부

    Returns:
        tuple: (필터링된 DataFrame, 필터링 통계)
    """
    original_count = len(df)
    keyword = "옥내"

    # 매칭된 행 인덱스를 수집
    matched_indices = set()
    column_matches = {}

    for column in search_columns:
        if column not in df.columns:
            if verbose:
                print(f"    ⚠️  컬럼 '{column}'이(가) {file_name}에 없음")
            continue

        # 유니코드 정규화를 고려한 검색 (NFC/NFD 모두 찾기)
        mask = search_with_normalization(df[column], keyword)
        matched_count = mask.sum()

        if matched_count > 0:
            column_matches[column] = matched_count
            matched_indices.update(df[mask].index.tolist())

    # 매칭된 행 제거
    filtered_df = df.drop(index=list(matched_indices))
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count

    filter_stats = {
        "original_count": original_count,
        "filtered_count": filtered_count,
        "removed_count": removed_count,
        "removed_percentage": (
            (removed_count / original_count * 100) if original_count > 0 else 0
        ),
        "column_matches": column_matches,
    }

    if verbose and removed_count > 0:
        print(
            f"    ✓ '옥내' 필터링: {removed_count:,}행 제거 ({filter_stats['removed_percentage']:.1f}%)"
        )
        for col, count in column_matches.items():
            print(f"      - {col}: {count}건")

    return filtered_df, filter_stats


def load_and_validate_files(filter_indoor: bool = True, verbose: bool = False):
    """
    results 디렉토리에서 파일 로드 및 필수 컬럼 검증

    Args:
        filter_indoor: '옥내' 텍스트 필터링 여부 (기본: True)
        verbose: 상세 출력 여부

    Returns:
        tuple: (유효한 DataFrame 리스트, 파일 통계, 필터링 통계)

    Raises:
        ValueError: 필수 컬럼이 없는 경우
    """
    results_dir = Path("results")
    if not results_dir.exists():
        raise FileNotFoundError(f"{results_dir} 디렉토리를 찾을 수 없습니다.")

    valid_dataframes = []
    missing_columns = {}
    file_stats = {}
    filter_stats = {} if filter_indoor else None

    print("\n파일 로드 및 검증 중...")
    print("-" * 50)

    if filter_indoor:
        print("📌 '옥내' 텍스트 필터링 활성화")

    for file_name in TARGET_FILES:
        file_path = results_dir / file_name

        if not file_path.exists():
            print(f"⚠️  파일을 찾을 수 없음: {file_name}")
            continue

        try:
            # CSV 파일 로드 (DtypeWarning 방지를 위해 low_memory=False 설정)
            df = pd.read_csv(file_path, encoding="utf-8-sig", low_memory=False)

            # 필수 컬럼 확인
            required_columns = ["작업일시", "위도", "경도"]
            missing = [col for col in required_columns if col not in df.columns]

            if missing:
                missing_columns[file_name] = missing
                print(f"❌ {file_name}: 필수 컬럼 누락 - {', '.join(missing)}")
            else:
                # 파일타입 컬럼 추가 (파일명에서 _위치추가.csv 제거)
                file_type = file_name.replace("_위치추가.csv", "")
                df["파일타입"] = file_type
                
                # ID 컬럼 추가
                if file_name in ID_COLUMN_MAPPING:
                    id_column = ID_COLUMN_MAPPING[file_name]
                    if id_column in df.columns:
                        df["ID"] = df[id_column].astype(str).fillna("")
                    else:
                        df["ID"] = ""
                        if verbose:
                            print(f"    ⚠️  ID 컬럼 '{id_column}'이(가) {file_name}에 없음")
                else:
                    df["ID"] = ""

                original_count = len(df)

                # 유효 위치 필터링 (위도와 경도가 모두 null이 아닌 행)
                valid_location_mask = df["위도"].notna() & df["경도"].notna()
                df_with_location = df[valid_location_mask].copy()
                location_count = len(df_with_location)
                location_removed = original_count - location_count

                # 옥내 필터링 적용 (유효 위치가 있는 데이터에만)
                if filter_indoor and file_name in SEARCH_COLUMNS:
                    df_filtered, f_stats = filter_indoor_work(
                        df_with_location,
                        file_name,
                        SEARCH_COLUMNS[file_name],
                        verbose=verbose,
                    )
                    filter_stats[file_name] = f_stats
                    filter_stats[file_name]["location_removed"] = location_removed
                    final_count = len(df_filtered)

                    # 3단계 출력
                    print(
                        f"✓ {file_name}: {original_count:,}행 → {location_count:,}행 (유효 위치) → {final_count:,}행 (필터링 후)"
                    )
                    if verbose or (
                        location_removed > 0 or f_stats["removed_count"] > 0
                    ):
                        if location_removed > 0:
                            print(f"  - 위치 없음: {location_removed:,}행 제거")
                        if f_stats["removed_count"] > 0:
                            print(f"  - 옥내 필터: {f_stats['removed_count']:,}행 제거")

                    df = df_filtered
                else:
                    # 필터링 비활성화 시에도 유효 위치만 사용
                    df = df_with_location
                    if location_removed > 0:
                        print(
                            f"✓ {file_name}: {original_count:,}행 → {location_count:,}행 (유효 위치)"
                        )
                        if verbose:
                            print(f"  - 위치 없음: {location_removed:,}행 제거")
                    else:
                        print(f"✓ {file_name}: {len(df):,}행 로드 완료")

                valid_dataframes.append(df)
                file_stats[file_name] = len(df)

        except Exception as e:
            print(f"❌ {file_name} 읽기 실패: {e}")
            continue

    # 필수 컬럼이 없는 파일이 있으면 오류 발생
    if missing_columns:
        error_msg = "\n" + "=" * 50
        error_msg += "\n❌ 필수 컬럼이 없는 파일 발견:\n"
        error_msg += "=" * 50 + "\n"
        for file_name, cols in missing_columns.items():
            error_msg += f"\n파일: {file_name}\n"
            error_msg += f"  누락된 컬럼: {', '.join(cols)}\n"
        error_msg += "\n" + "=" * 50
        error_msg += "\n\n모든 파일에 '작업일시', '위도', '경도' 컬럼이 필요합니다."

        print(error_msg)
        raise ValueError(f"필수 컬럼 누락: {len(missing_columns)}개 파일에서 오류")

    if not valid_dataframes:
        raise ValueError("병합할 유효한 파일이 없습니다.")

    print(f"\n총 {len(valid_dataframes)}개 파일 로드 성공")
    print(f"전체 행 수: {sum(file_stats.values()):,}행")

    # 필터링 요약 출력
    if filter_stats:
        total_location_removed = sum(
            s.get("location_removed", 0) for s in filter_stats.values()
        )
        total_indoor_removed = sum(
            s.get("removed_count", 0) for s in filter_stats.values()
        )

        print(f"\n📊 데이터 처리 요약:")
        if total_location_removed > 0:
            print(f"  - 위치 정보 없음으로 제거: {total_location_removed:,}행")
        if filter_indoor and total_indoor_removed > 0:
            print(f"  - '옥내' 필터링으로 제거: {total_indoor_removed:,}행")
            for file_name, stats in filter_stats.items():
                if stats["removed_count"] > 0:
                    print(f"    • {file_name}: {stats['removed_count']}행")

    return valid_dataframes, file_stats, filter_stats


def merge_dataframes(dataframes):
    """
    여러 DataFrame을 하나로 병합

    Args:
        dataframes: DataFrame 리스트

    Returns:
        병합된 DataFrame
    """
    print("\n데이터 병합 중...")

    # 모든 DataFrame 합치기
    merged_df = pd.concat(dataframes, ignore_index=True, sort=False)

    # 병합 후 통계
    print(f"✓ 병합 완료: 총 {len(merged_df):,}행")

    # 파일타입별 통계
    type_counts = merged_df["파일타입"].value_counts()
    print("\n파일타입별 분포:")
    for file_type, count in type_counts.items():
        percentage = (count / len(merged_df)) * 100
        print(f"  - {file_type}: {count:,}행 ({percentage:.1f}%)")

    return merged_df


def analyze_data_quality(df):
    """
    데이터 품질 분석

    Args:
        df: 병합된 DataFrame
    """
    print("\n데이터 품질 분석:")
    print("-" * 50)

    # 필수 컬럼의 결측값 확인
    essential_cols = ["작업일시", "위도", "경도"]
    for col in essential_cols:
        missing_count = df[col].isna().sum()
        missing_pct = (missing_count / len(df)) * 100
        if missing_count > 0:
            print(f"⚠️  {col}: {missing_count:,}개 결측 ({missing_pct:.1f}%)")
        else:
            print(f"✓ {col}: 결측값 없음")

    # 날짜 형식 검증
    try:
        df["작업일시_parsed"] = pd.to_datetime(df["작업일시"], errors="coerce")
        invalid_dates = df["작업일시_parsed"].isna().sum()
        if invalid_dates > 0:
            print(f"⚠️  유효하지 않은 날짜: {invalid_dates:,}개")
        else:
            print(f"✓ 모든 날짜 형식 유효")

        # 날짜 범위
        valid_dates = df["작업일시_parsed"].dropna()
        if len(valid_dates) > 0:
            print(
                f"  날짜 범위: {valid_dates.min().date()} ~ {valid_dates.max().date()}"
            )
    except Exception as e:
        print(f"⚠️  날짜 파싱 오류: {e}")

    # 좌표 유효성 검사 (대한민국 범위)
    lat_valid = df["위도"].between(33, 43, inclusive="both")
    lon_valid = df["경도"].between(124, 132, inclusive="both")
    valid_coords = lat_valid & lon_valid
    invalid_coords = (~valid_coords).sum()

    if invalid_coords > 0:
        print(f"⚠️  유효하지 않은 좌표: {invalid_coords:,}개")
    else:
        print(f"✓ 모든 좌표 유효 (한국 범위 내)")

    # 중복 행 확인
    duplicate_rows = df.duplicated().sum()
    if duplicate_rows > 0:
        print(f"⚠️  완전 중복 행: {duplicate_rows:,}개")
    else:
        print(f"✓ 완전 중복 행 없음")


def save_merged_data(df, output_dir, filter_stats=None):
    """
    병합된 데이터를 파일로 저장

    Args:
        df: 병합된 DataFrame
        output_dir: 출력 디렉토리
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 출력 파일명
    output_file = output_path / "누수공사_통합_위치추가.csv"

    # 지정된 컬럼만 선택하여 저장 (원본파일 제외)
    columns_to_keep = [
        "ID", "작업일시", "위도", "경도", "파일타입",
        "공사명", "공사개요", "구군", "주소",
        "중구역번호", "소구역번호", "도로구분", "누수관경",
        "누수량", "용수구분", "용도구분"
    ]
    # 존재하는 컬럼만 필터링
    columns_to_keep = [col for col in columns_to_keep if col in df.columns]
    df_to_save = df[columns_to_keep].copy()

    # CSV 저장 (지정된 컬럼만)
    df_to_save.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(f"\n✓ 통합 파일 저장 완료: {output_file}")
    print(f"  - 총 {len(df_to_save):,}행")
    print(f"  - 총 {len(df_to_save.columns)}개 컬럼")

    # 요약 정보 파일 저장
    summary_file = output_path / "통합_요약.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("누수공사 데이터 통합 요약\n")
        f.write("=" * 50 + "\n")
        f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"통합 파일: {output_file.name}\n")
        f.write(f"\n총 레코드 수: {len(df_to_save):,}행\n")
        f.write(
            f"총 컬럼 수: {len(df_to_save.columns)}개\n"
        )
        f.write(f"  - 컬럼 목록: {', '.join(columns_to_keep)}\n")

        f.write("\n파일타입별 분포:\n")
        type_counts = df["파일타입"].value_counts()
        for file_type, count in type_counts.items():
            percentage = (count / len(df)) * 100
            f.write(f"  - {file_type}: {count:,}행 ({percentage:.1f}%)\n")

        f.write("\n원본 파일 목록:\n")
        for file_name in TARGET_FILES:
            f.write(f"  - {file_name}\n")

        # 데이터 처리 통계 추가
        if filter_stats:
            total_location_removed = sum(
                s.get("location_removed", 0) for s in filter_stats.values()
            )
            total_indoor_removed = sum(
                s.get("removed_count", 0) for s in filter_stats.values()
            )

            f.write("\n데이터 처리 통계:\n")
            if total_location_removed > 0:
                f.write(f"  - 위치 정보 없음으로 제거: {total_location_removed:,}행\n")
            if total_indoor_removed > 0:
                f.write(f"\n'옥내' 텍스트 필터링 결과:\n")
                f.write(f"  - 총 제거된 행: {total_indoor_removed:,}행\n")
                for file_name, stats in filter_stats.items():
                    if stats["removed_count"] > 0:
                        f.write(
                            f"  - {file_name}: {stats['removed_count']}행 제거 ({stats['removed_percentage']:.1f}%)\n"
                        )

        # 날짜 범위
        try:
            df["작업일시_parsed"] = pd.to_datetime(df["작업일시"], errors="coerce")
            valid_dates = df["작업일시_parsed"].dropna()
            if len(valid_dates) > 0:
                f.write(
                    f"\n날짜 범위: {valid_dates.min().date()} ~ {valid_dates.max().date()}\n"
                )
        except:
            pass

    print(f"✓ 요약 파일 저장: {summary_file}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="재작업 데이터 통합 (여러 CSV 파일을 하나로 병합)"
    )
    parser.add_argument(
        "--output-dir",
        default="results/main11e_merge_all_repairs",
        help="출력 디렉토리 (기본: results/main11e_merge_all_repairs)",
    )
    parser.add_argument("--verbose", action="store_true", help="상세 정보 출력")
    parser.add_argument(
        "--no-filter-indoor",
        action="store_true",
        help="'옥내' 텍스트 필터링 비활성화 (기본: 필터링 활성화)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("재작업 데이터 통합 시작")
    print("=" * 80)

    try:
        # 필터링 설정 (--no-filter-indoor 옵션이 있으면 False)
        filter_indoor = not args.no_filter_indoor

        if filter_indoor:
            print("\n🔍 '옥내' 작업 필터링이 활성화되어 있습니다.")
            print("   (비활성화하려면 --no-filter-indoor 옵션을 사용하세요)\n")
        else:
            print("\n⚠️  '옥내' 작업 필터링이 비활성화되어 있습니다.\n")

        # 1. 파일 로드 및 검증
        dataframes, file_stats, filter_stats = load_and_validate_files(
            filter_indoor=filter_indoor, verbose=args.verbose
        )

        # 2. 데이터 병합
        merged_df = merge_dataframes(dataframes)

        # 3. 데이터 품질 분석
        analyze_data_quality(merged_df)

        # 4. 결과 저장
        save_merged_data(merged_df, args.output_dir, filter_stats)

        print("\n" + "=" * 80)
        print("데이터 통합 완료")
        print("=" * 80)

    except ValueError as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n파일 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류 발생: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
