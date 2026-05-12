"""
'옥내' 텍스트 포함 데이터 분석 스크립트
누수 복구 작업 데이터에서 '옥내' 관련 작업을 식별하고 통계 분석
각 파일별로 다른 컬럼 구조를 처리하여 '옥내' 텍스트 검색
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd


# 파일별 검색 대상 컬럼 정의
SEARCH_COLUMNS = {
    "지상누수_위치추가.csv": ["공사개요", "주소", "공사명"],
    "지하누수_위치추가.csv": ["공사개요", "주소", "공사명"],
    "긴급공사_위치추가.csv": ["공사명", "주소", "공사개요"],
    "관리대장_위치추가.csv": ["위치", "공사개요"],
}

# 처리할 파일 목록
TARGET_FILES = list(SEARCH_COLUMNS.keys())


def normalize_text(text: str) -> str:
    """
    텍스트를 NFC 형태로 정규화

    Args:
        text: 정규화할 텍스트

    Returns:
        NFC로 정규화된 텍스트
    """
    if pd.isna(text):
        return text
    return unicodedata.normalize("NFC", str(text))


def search_with_normalization(series: pd.Series, keyword: str) -> pd.Series:
    """
    유니코드 정규화를 고려한 텍스트 검색
    NFC와 NFD 두 형태 모두 검색하여 결과를 OR 연산으로 결합

    Args:
        series: 검색할 pandas Series
        keyword: 검색 키워드

    Returns:
        매칭 결과 boolean Series
    """
    # 키워드를 NFC와 NFD 두 형태로 준비
    keyword_nfc = unicodedata.normalize("NFC", keyword)
    keyword_nfd = unicodedata.normalize("NFD", keyword)

    # 두 형태 모두 검색하여 OR 연산
    mask_nfc = series.astype(str).str.contains(keyword_nfc, na=False, case=False)
    mask_nfd = series.astype(str).str.contains(keyword_nfd, na=False, case=False)

    return mask_nfc | mask_nfd


def load_and_search_file(
    file_path: Path, search_columns: List[str], keyword: str = "옥내"
) -> Tuple[pd.DataFrame, Dict]:
    """
    CSV 파일을 로드하고 지정된 컬럼에서 키워드를 검색
    유니코드 정규화를 고려하여 NFC/NFD 모두 검색

    Args:
        file_path: CSV 파일 경로
        search_columns: 검색할 컬럼 리스트
        keyword: 검색할 키워드 (기본: "옥내")

    Returns:
        tuple: (전체 DataFrame, 검색 결과 딕셔너리)
    """
    # CSV 파일 읽기
    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    except Exception as e:
        print(f"⚠️  {file_path.name} 읽기 실패: {e}")
        return None, None

    # 모든 문자열 컬럼을 NFC로 정규화 (선택사항: 데이터 일관성을 위해)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(normalize_text)

    # 검색 결과 초기화
    search_results = {
        "total_rows": len(df),
        "matched_rows": 0,
        "column_matches": {},
        "matched_indices": set(),
    }

    # 각 컬럼별로 검색
    for column in search_columns:
        if column not in df.columns:
            print(f"  ⚠️  컬럼 '{column}'이(가) {file_path.name}에 없음")
            continue

        # 유니코드 정규화를 고려한 검색
        mask = search_with_normalization(df[column], keyword)
        matched_count = mask.sum()

        if matched_count > 0:
            search_results["column_matches"][column] = {
                "count": int(matched_count),
                "indices": df[mask].index.tolist(),
            }
            search_results["matched_indices"].update(df[mask].index.tolist())

    # 전체 매칭된 유니크 행 수
    search_results["matched_rows"] = len(search_results["matched_indices"])
    search_results["matched_indices"] = list(search_results["matched_indices"])

    return df, search_results


def analyze_temporal_pattern(df: pd.DataFrame, matched_indices: List[int]) -> Dict:
    """
    매칭된 데이터의 시간적 패턴 분석

    Args:
        df: 전체 DataFrame
        matched_indices: 매칭된 행 인덱스 리스트

    Returns:
        시간별 분포 딕셔너리
    """
    if not matched_indices or "작업일시" not in df.columns:
        return {}

    matched_df = df.iloc[matched_indices].copy()

    # 작업일시 파싱
    try:
        matched_df["작업일시_parsed"] = pd.to_datetime(
            matched_df["작업일시"], errors="coerce"
        )
        valid_dates = matched_df["작업일시_parsed"].dropna()

        if len(valid_dates) == 0:
            return {}

        # 연도별, 월별 집계
        yearly = valid_dates.dt.year.value_counts().sort_index()
        monthly = valid_dates.dt.to_period("M").value_counts().sort_index()

        return {
            "yearly": yearly.to_dict() if len(yearly) > 0 else {},
            "monthly": (
                {str(k): v for k, v in monthly.to_dict().items()}
                if len(monthly) > 0
                else {}
            ),
            "date_range": {
                "start": str(valid_dates.min().date()),
                "end": str(valid_dates.max().date()),
            },
        }
    except Exception as e:
        print(f"  ⚠️  시간 분석 실패: {e}")
        return {}


def print_summary(all_results: Dict):
    """
    분석 결과 요약 출력

    Args:
        all_results: 전체 분석 결과 딕셔너리
    """
    print("\n" + "=" * 80)
    print("'옥내' 텍스트 포함 현황 분석 결과")
    print("=" * 80)

    # 전체 통계
    total_all = sum(r["total_rows"] for r in all_results.values() if r)
    matched_all = sum(r["matched_rows"] for r in all_results.values() if r)

    print(f"\n📊 전체 통계")
    print(f"  - 전체 데이터: {total_all:,}행")
    print(f"  - '옥내' 포함: {matched_all:,}행 ({matched_all/total_all*100:.1f}%)")

    # 파일별 통계
    print(f"\n📁 파일별 통계")
    for file_name, result in all_results.items():
        if result:
            total = result["total_rows"]
            matched = result["matched_rows"]
            percentage = (matched / total * 100) if total > 0 else 0
            print(f"  - {file_name}: {matched:,}/{total:,}행 ({percentage:.1f}%)")
        else:
            print(f"  - {file_name}: 데이터 없음")

    # 컬럼별 분포
    print(f"\n📋 컬럼별 분포")
    column_totals = {}
    for result in all_results.values():
        if result:
            for column, data in result.get("column_matches", {}).items():
                column_totals[column] = column_totals.get(column, 0) + data["count"]

    for column, count in sorted(
        column_totals.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  - {column}: {count:,}건")

    # 시간적 분포 (연도별)
    print(f"\n📅 연도별 분포")
    yearly_totals = {}
    for result in all_results.values():
        if result and "temporal_pattern" in result:
            for year, count in result["temporal_pattern"].get("yearly", {}).items():
                yearly_totals[year] = yearly_totals.get(year, 0) + count

    if yearly_totals:
        for year in sorted(yearly_totals.keys()):
            print(f"  - {year}년: {yearly_totals[year]:,}건")
    else:
        print("  - 시간 정보 없음")


def save_results(all_results: Dict, output_dir: Path):
    """
    분석 결과를 파일로 저장

    Args:
        all_results: 전체 분석 결과
        output_dir: 출력 디렉토리
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. JSON 형식으로 전체 통계 저장
    stats_file = output_dir / "옥내작업_통계.json"

    # JSON 직렬화 가능한 형태로 변환
    json_results = {}
    for file_name, result in all_results.items():
        if result:
            json_results[file_name] = {
                "total_rows": result["total_rows"],
                "matched_rows": result["matched_rows"],
                "percentage": (
                    round(result["matched_rows"] / result["total_rows"] * 100, 2)
                    if result["total_rows"] > 0
                    else 0
                ),
                "column_matches": {
                    col: data["count"]
                    for col, data in result.get("column_matches", {}).items()
                },
                "temporal_pattern": result.get("temporal_pattern", {}),
            }

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(json_results, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 통계 파일 저장: {stats_file}")

    # 2. 요약 텍스트 파일 저장
    summary_file = output_dir / "옥내작업_요약.txt"

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("'옥내' 텍스트 포함 데이터 분석 요약\n")
        f.write("=" * 50 + "\n")
        f.write(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"검색 키워드: '옥내'\n\n")

        # 전체 통계
        total_all = sum(r["total_rows"] for r in all_results.values() if r)
        matched_all = sum(r["matched_rows"] for r in all_results.values() if r)
        f.write(f"전체 통계:\n")
        f.write(f"- 전체 데이터: {total_all:,}행\n")
        f.write(
            f"- '옥내' 포함: {matched_all:,}행 ({matched_all/total_all*100:.1f}%)\n\n"
        )

        # 파일별 통계
        f.write("파일별 통계:\n")
        for file_name, result in all_results.items():
            if result:
                total = result["total_rows"]
                matched = result["matched_rows"]
                percentage = (matched / total * 100) if total > 0 else 0
                f.write(f"- {file_name}: {matched:,}/{total:,}행 ({percentage:.1f}%)\n")

        f.write("\n컬럼별 분포:\n")
        column_totals = {}
        for result in all_results.values():
            if result:
                for column, data in result.get("column_matches", {}).items():
                    column_totals[column] = column_totals.get(column, 0) + data["count"]

        for column, count in sorted(
            column_totals.items(), key=lambda x: x[1], reverse=True
        ):
            f.write(f"- {column}: {count:,}건\n")

    print(f"✓ 요약 파일 저장: {summary_file}")


def export_matched_rows(all_results: Dict, all_dataframes: Dict, output_dir: Path):
    """
    '옥내' 포함 행들을 별도 CSV로 추출

    Args:
        all_results: 전체 분석 결과
        all_dataframes: 전체 DataFrame 딕셔너리
        output_dir: 출력 디렉토리
    """
    matched_dfs = []

    for file_name, result in all_results.items():
        if result and result["matched_rows"] > 0:
            df = all_dataframes[file_name]
            matched_indices = result["matched_indices"]

            # 매칭된 행 추출
            matched_df = df.iloc[matched_indices].copy()
            matched_df["원본파일"] = file_name
            matched_dfs.append(matched_df)

    if matched_dfs:
        # 모든 매칭된 행 통합
        combined_df = pd.concat(matched_dfs, ignore_index=True, sort=False)

        # CSV로 저장
        export_file = output_dir / "옥내작업_추출.csv"
        combined_df.to_csv(export_file, index=False, encoding="utf-8-sig")

        print(f"✓ 추출 파일 저장: {export_file}")
        print(f"  - 총 {len(combined_df):,}행 추출")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="'옥내' 텍스트 포함 데이터 분석")
    parser.add_argument(
        "--output-dir",
        default="results/main11f_check_indoor",
        help="출력 디렉토리 (기본: results/main11f_check_indoor)",
    )
    parser.add_argument("--verbose", action="store_true", help="상세 정보 출력")
    parser.add_argument(
        "--export-matches", action="store_true", help="'옥내' 포함 행을 별도 CSV로 추출"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("'옥내' 텍스트 포함 데이터 분석 시작")
    print("=" * 80)

    results_dir = Path("results")
    if not results_dir.exists():
        print(f"❌ {results_dir} 디렉토리를 찾을 수 없습니다.")
        sys.exit(1)

    all_results = {}
    all_dataframes = {}

    # 각 파일 처리
    for file_name in TARGET_FILES:
        file_path = results_dir / file_name
        search_cols = SEARCH_COLUMNS[file_name]

        print(f"\n📄 {file_name} 처리 중...")

        if not file_path.exists():
            print(f"  ⚠️  파일을 찾을 수 없음")
            all_results[file_name] = None
            continue

        # 파일 로드 및 검색
        df, search_result = load_and_search_file(file_path, search_cols)

        if df is None or search_result is None:
            all_results[file_name] = None
            continue

        # 시간적 패턴 분석
        if search_result["matched_rows"] > 0:
            temporal = analyze_temporal_pattern(df, search_result["matched_indices"])
            search_result["temporal_pattern"] = temporal

        all_results[file_name] = search_result
        all_dataframes[file_name] = df

        if args.verbose:
            print(f"  ✓ 전체: {search_result['total_rows']:,}행")
            print(f"  ✓ '옥내' 포함: {search_result['matched_rows']:,}행")
            for col, data in search_result["column_matches"].items():
                print(f"    - {col}: {data['count']:,}건")

    # 결과 요약 출력
    print_summary(all_results)

    # 결과 저장
    output_path = Path(args.output_dir)
    save_results(all_results, output_path)

    # 매칭된 행 추출 (옵션)
    if args.export_matches:
        export_matched_rows(all_results, all_dataframes, output_path)

    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
