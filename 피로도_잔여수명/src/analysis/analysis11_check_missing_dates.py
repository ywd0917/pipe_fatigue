"""
날짜 컬럼 누락 분석 스크립트
data/repair2/ 폴더의 CSV 파일들에서 날짜 정보가 없는 레코드를 찾음
우선순위1: 접수일시 > 작업시작일시 > 작업종료일
우선순위2: 민원접수번호 > 공사일련번호 (날짜 형식인 경우)
"""

import pandas as pd
from pathlib import Path
import sys
from datetime import datetime


def check_date_format(value):
    """
    값이 날짜 형식인지 확인
    형식: YYYYMMDDHHMMSS 또는 YYYY-MM-DD HH:MM:SS 등

    Args:
        value: 확인할 값

    Returns:
        bool: 날짜 형식이면 True
    """
    if pd.isna(value):
        return False

    value_str = str(value).strip()

    # 빈 문자열이거나 'nan'인 경우
    if value_str == "" or value_str == "nan":
        return False

    # 숫자로만 이루어진 경우 (YYYYMMDD 또는 YYYYMMDDHHMMSS 형식)
    if value_str.replace(".0", "").isdigit():
        clean_val = value_str.replace(".0", "")
        # 8자리 (날짜) 또는 12-14자리 (날짜시간)
        if len(clean_val) in [8, 12, 14]:
            try:
                year = int(clean_val[:4])
                if 2000 <= year <= 2030:
                    return True
            except:
                pass

    # 하이픈이나 슬래시가 포함된 경우 (YYYY-MM-DD 형식)
    if "-" in value_str or "/" in value_str:
        try:
            # pandas로 날짜 파싱 시도
            parsed = pd.to_datetime(value_str, errors="coerce")
            if not pd.isna(parsed):
                if 2000 <= parsed.year <= 2030:
                    return True
        except:
            pass

    return False


def check_missing_dates(df, filename):
    """
    모든 날짜 컬럼이 누락된 레코드 확인

    Args:
        df: 분석할 DataFrame
        filename: 파일명 (디버깅용)

    Returns:
        (3개 날짜 누락 DataFrame, 5개 전체 누락 DataFrame, 날짜 컬럼 정보 dict)
    """
    # 우선순위1: 기본 날짜 컬럼 (3개)
    date_columns_primary = ["접수일시", "작업시작일시", "작업종료일"]

    # 우선순위2: 추가 날짜 컬럼 (민원접수번호, 공사일련번호)
    date_columns_secondary = ["민원접수번호", "공사일련번호"]

    # 실제로 존재하는 컬럼 찾기
    existing_primary = [col for col in date_columns_primary if col in df.columns]
    existing_secondary = [col for col in date_columns_secondary if col in df.columns]

    # 민원접수번호와 공사일련번호가 날짜 형식인지 확인
    date_format_info = {}
    for col in existing_secondary:
        if col in df.columns:
            # 샘플 10개로 날짜 형식 여부 확인
            sample = df[col].dropna().head(10)
            date_count = sum(check_date_format(val) for val in sample)
            is_date_format = (
                date_count > len(sample) * 0.5
            )  # 50% 이상이 날짜 형식이면 날짜 컬럼으로 간주
            date_format_info[col] = is_date_format

    # 날짜 형식인 secondary 컬럼만 포함
    existing_secondary_dates = [
        col for col in existing_secondary if date_format_info.get(col, False)
    ]

    # 3개 날짜 컬럼 누락 확인
    mask_primary = pd.Series([True] * len(df))
    for col in existing_primary:
        col_missing = (
            df[col].isna()
            | (df[col].astype(str).str.strip() == "")
            | (df[col].astype(str).str.strip() == "nan")
        )
        mask_primary = mask_primary & col_missing

    missing_primary = df[mask_primary]

    # 5개 전체 (3개 + 2개 추가) 누락 확인
    mask_all = mask_primary.copy()
    for col in existing_secondary_dates:
        col_missing = (
            df[col].isna()
            | (df[col].astype(str).str.strip() == "")
            | (df[col].astype(str).str.strip() == "nan")
        )
        mask_all = mask_all & col_missing

    missing_all = df[mask_all]

    column_info = {
        "primary_columns": existing_primary,
        "secondary_columns": existing_secondary,
        "secondary_date_columns": existing_secondary_dates,
        "date_format_info": date_format_info,
    }

    return missing_primary, missing_all, column_info


def analyze_date_quality(df, date_cols, check_date_fmt=False):
    """
    날짜 컬럼의 품질 분석

    Args:
        df: DataFrame
        date_cols: 날짜 컬럼 리스트
        check_date_fmt: 날짜 형식 확인 여부

    Returns:
        dict: 각 컬럼별 통계
    """
    stats = {}

    for col in date_cols:
        if col in df.columns:
            total = len(df)
            missing = df[col].isna().sum()
            empty_str = (df[col].astype(str).str.strip() == "").sum()
            filled = total - missing - empty_str

            stat_dict = {
                "total": total,
                "filled": filled,
                "missing": missing,
                "empty_str": empty_str,
                "fill_rate": (filled / total * 100) if total > 0 else 0,
            }

            # 날짜 형식 확인 (민원접수번호, 공사일련번호용)
            if check_date_fmt and filled > 0:
                sample = df[col].dropna().head(100)
                date_count = sum(check_date_format(val) for val in sample)
                stat_dict["is_date_format"] = date_count > len(sample) * 0.5
                stat_dict["date_format_ratio"] = (
                    (date_count / len(sample) * 100) if len(sample) > 0 else 0
                )

            stats[col] = stat_dict

    return stats


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("날짜 컬럼 누락 분석 (확장판)")
    print("=" * 70)
    print("분석 대상: data/repair2/ 디렉토리")
    print("우선순위1: 접수일시 > 작업시작일시 > 작업종료일")
    print("우선순위2: 민원접수번호 > 공사일련번호 (날짜 형식인 경우)")
    print("-" * 70)

    # 대상 파일
    repair_dir = Path("data/repair2")
    files = ["지상누수.csv", "지하누수.csv", "기타공사.csv"]

    if not repair_dir.exists():
        print(f"❌ 디렉토리를 찾을 수 없습니다: {repair_dir}")
        sys.exit(1)

    total_records = 0
    total_missing_primary = 0
    total_missing_all = 0
    all_results = []

    for filename in files:
        filepath = repair_dir / filename

        if not filepath.exists():
            print(f"⚠️  {filename} 파일이 없습니다.")
            continue

        print(f"\n📁 {filename} 분석 중...")

        try:
            # CSV 파일 로드
            df = pd.read_csv(filepath, encoding="utf-8-sig", low_memory=False)
            total_records += len(df)

            # 날짜 누락 확인
            missing_primary, missing_all, column_info = check_missing_dates(
                df, filename
            )

            # 날짜 품질 통계
            primary_stats = analyze_date_quality(df, column_info["primary_columns"])
            secondary_stats = analyze_date_quality(
                df, column_info["secondary_columns"], check_date_fmt=True
            )

            # 결과 저장
            result = {
                "file": filename,
                "total_records": len(df),
                "missing_primary": len(missing_primary),
                "missing_all": len(missing_all),
                "percentage_primary": (
                    (len(missing_primary) / len(df)) * 100 if len(df) > 0 else 0
                ),
                "percentage_all": (
                    (len(missing_all) / len(df)) * 100 if len(df) > 0 else 0
                ),
                "column_info": column_info,
                "primary_stats": primary_stats,
                "secondary_stats": secondary_stats,
                "sample_missing_primary": missing_primary.index.tolist()[:10],
                "sample_missing_all": missing_all.index.tolist()[:10],
            }
            all_results.append(result)
            total_missing_primary += len(missing_primary)
            total_missing_all += len(missing_all)

            # 콘솔 출력
            print(f"  총 레코드: {len(df):,}개")
            print(f"\n  [기본 날짜 컬럼] {', '.join(column_info['primary_columns'])}")

            # 기본 날짜 컬럼별 통계
            for col, stats in primary_stats.items():
                print(
                    f"    - {col}: {stats['filled']:,}개 입력 ({stats['fill_rate']:.1f}%)"
                )

            print(f"\n  [추가 확인 컬럼]")
            for col in column_info["secondary_columns"]:
                if col in secondary_stats:
                    stats = secondary_stats[col]
                    is_date = column_info["date_format_info"].get(col, False)
                    date_str = "날짜형식 O" if is_date else "날짜형식 X"
                    print(
                        f"    - {col}: {stats['filled']:,}개 입력 ({stats['fill_rate']:.1f}%) [{date_str}]"
                    )
                    if "date_format_ratio" in stats:
                        print(
                            f"      → 날짜형식 비율: {stats['date_format_ratio']:.1f}%"
                        )

            print(f"\n  📊 누락 통계:")
            print(
                f"    - 3개 기본 날짜 모두 누락: {len(missing_primary):,}개 ({result['percentage_primary']:.1f}%)"
            )

            if column_info["secondary_date_columns"]:
                print(
                    f"    - 5개 전체 (3+2) 모두 누락: {len(missing_all):,}개 ({result['percentage_all']:.1f}%)"
                )

            if len(missing_primary) > 0:
                sample_rows = missing_primary.index.tolist()[:5]
                print(
                    f"\n  📌 3개 기본 날짜 누락 행 (Excel 행번호): {[r+2 for r in sample_rows]}"
                )

                # 누락된 레코드의 일부 정보 표시
                if "주소" in missing_primary.columns:
                    print("  📍 누락 레코드 주소 샘플:")
                    for idx in sample_rows[:3]:
                        if idx in df.index:
                            addr = df.loc[idx, "주소"]
                            print(f"      행 {idx+2}: {addr}")

        except Exception as e:
            print(f"  ❌ 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            continue

    # 전체 요약
    print("\n" + "=" * 70)
    print("📊 전체 요약")
    print("=" * 70)
    print(f"총 분석 파일: {len(all_results)}개")
    print(f"총 레코드 수: {total_records:,}개")
    print(
        f"3개 기본 날짜 누락: {total_missing_primary:,}개 ({(total_missing_primary/total_records*100):.2f}%)"
        if total_records > 0
        else ""
    )
    print(
        f"5개 전체 날짜 누락: {total_missing_all:,}개 ({(total_missing_all/total_records*100):.2f}%)"
        if total_records > 0
        else ""
    )

    # 상세 보고서 저장
    if all_results:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        report_file = results_dir / "날짜누락_분석결과.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("날짜 컬럼 누락 분석 결과 (확장판)\n")
            f.write("=" * 70 + "\n")
            f.write(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"분석 대상: data/repair2/ 디렉토리\n")
            f.write(f"우선순위1: 접수일시 > 작업시작일시 > 작업종료일\n")
            f.write(f"우선순위2: 민원접수번호 > 공사일련번호 (날짜 형식인 경우)\n")
            f.write("=" * 70 + "\n\n")

            for result in all_results:
                f.write(f"\n파일: {result['file']}\n")
                f.write("-" * 50 + "\n")
                f.write(f"총 레코드: {result['total_records']:,}개\n\n")

                f.write("[기본 날짜 컬럼]\n")
                f.write(
                    f"컬럼: {', '.join(result['column_info']['primary_columns'])}\n"
                )
                for col, stats in result["primary_stats"].items():
                    f.write(
                        f"  - {col}: {stats['filled']:,}/{stats['total']:,} ({stats['fill_rate']:.1f}%)\n"
                    )
                    f.write(
                        f"    (누락: {stats['missing']:,}, 빈값: {stats['empty_str']:,})\n"
                    )

                f.write("\n[추가 날짜 컬럼]\n")
                f.write(
                    f"컬럼: {', '.join(result['column_info']['secondary_columns'])}\n"
                )
                for col, stats in result["secondary_stats"].items():
                    is_date = result["column_info"]["date_format_info"].get(col, False)
                    date_str = "날짜형식" if is_date else "비날짜형식"
                    f.write(
                        f"  - {col} [{date_str}]: {stats['filled']:,}/{stats['total']:,} ({stats['fill_rate']:.1f}%)\n"
                    )
                    if "date_format_ratio" in stats:
                        f.write(
                            f"    날짜형식 비율: {stats['date_format_ratio']:.1f}%\n"
                        )

                f.write(f"\n누락 통계:\n")
                f.write(
                    f"  - 3개 기본 날짜 모두 누락: {result['missing_primary']:,}개 ({result['percentage_primary']:.1f}%)\n"
                )
                f.write(
                    f"  - 5개 전체 날짜 모두 누락: {result['missing_all']:,}개 ({result['percentage_all']:.1f}%)\n"
                )

                if result["sample_missing_primary"]:
                    f.write(f"\n3개 기본 날짜 누락 행 번호 (Excel 기준, 최대 10개): \n")
                    excel_rows = [r + 2 for r in result["sample_missing_primary"]]
                    f.write(f"  {excel_rows}\n")

                if (
                    result["sample_missing_all"]
                    and result["sample_missing_all"] != result["sample_missing_primary"]
                ):
                    f.write(f"\n5개 전체 날짜 누락 행 번호 (Excel 기준, 최대 10개): \n")
                    excel_rows = [r + 2 for r in result["sample_missing_all"]]
                    f.write(f"  {excel_rows}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write("전체 요약\n")
            f.write("=" * 70 + "\n")
            f.write(f"총 분석 파일: {len(all_results)}개\n")
            f.write(f"총 레코드 수: {total_records:,}개\n")
            f.write(
                f"3개 기본 날짜 누락: {total_missing_primary:,}개 ({(total_missing_primary/total_records*100):.2f}%)\n"
                if total_records > 0
                else ""
            )
            f.write(
                f"5개 전체 날짜 누락: {total_missing_all:,}개 ({(total_missing_all/total_records*100):.2f}%)\n"
                if total_records > 0
                else ""
            )

            # 파일별 누락률 순위
            f.write("\n파일별 누락률 순위 (3개 기본 날짜 기준):\n")
            sorted_results = sorted(
                all_results, key=lambda x: x["percentage_primary"], reverse=True
            )
            for i, result in enumerate(sorted_results, 1):
                f.write(
                    f"  {i}. {result['file']}: {result['percentage_primary']:.1f}% ({result['missing_primary']:,}/{result['total_records']:,})\n"
                )

        print(f"\n📄 상세 보고서 저장: {report_file}")

        # CSV 형식으로도 저장 (Excel에서 보기 편하게)
        csv_file = results_dir / "날짜누락_분석결과.csv"
        summary_data = []
        for result in all_results:
            summary_data.append(
                {
                    "파일명": result["file"],
                    "총레코드": result["total_records"],
                    "3개기본날짜누락": result["missing_primary"],
                    "3개누락비율(%)": round(result["percentage_primary"], 2),
                    "5개전체날짜누락": result["missing_all"],
                    "5개누락비율(%)": round(result["percentage_all"], 2),
                    "민원접수번호_날짜형식": (
                        "○"
                        if result["column_info"]["date_format_info"].get(
                            "민원접수번호", False
                        )
                        else "×"
                    ),
                    "공사일련번호_날짜형식": (
                        "○"
                        if result["column_info"]["date_format_info"].get(
                            "공사일련번호", False
                        )
                        else "×"
                    ),
                }
            )

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        print(f"📊 요약 CSV 저장: {csv_file}")


if __name__ == "__main__":
    main()
