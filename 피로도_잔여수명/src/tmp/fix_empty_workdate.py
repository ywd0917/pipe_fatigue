#!/usr/bin/env python3
"""
작업일시가 비어있는 행들을 재파싱하는 스크립트
results/*_위치추가.csv 파일들을 처리하여 누락된 작업일시를 복구

`main11_convert_addr2loc.py`를 돌리기에는 너무 시간이 오래 걸려서 임시로 만든 스크립트.
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.main11_convert_addr2loc import parse_numeric_date_column


def fix_empty_workdate(location_file: Path, backup: bool = True) -> dict:
    """
    작업일시가 비어있는 행들을 재파싱하여 수정

    Args:
        location_file: 처리할 *_위치추가.csv 파일
        backup: 백업 파일 생성 여부

    Returns:
        처리 통계 딕셔너리
    """
    print(f"\n📋 처리 중: {location_file.name}")

    # 위치추가 파일 읽기
    try:
        df = pd.read_csv(location_file, encoding="utf-8-sig", low_memory=False)
    except Exception as e:
        print(f"  ❌ 파일 읽기 실패: {e}")
        return {"status": "failed", "reason": str(e)}

    # 초기 통계
    total_rows = len(df)
    empty_before = df["작업일시"].isna().sum() if "작업일시" in df.columns else total_rows

    print(f"  전체 행: {total_rows:,}")
    print(f"  작업일시 없음: {empty_before:,} ({empty_before/total_rows*100:.1f}%)")

    if empty_before == 0:
        print("  ✓ 모든 행에 작업일시가 있음")
        return {
            "status": "success",
            "total_rows": total_rows,
            "empty_before": 0,
            "empty_after": 0,
            "fixed": 0
        }

    # 작업일시 컬럼이 없으면 생성
    if "작업일시" not in df.columns:
        df["작업일시"] = pd.NaT

    # 작업일시가 비어있는 행의 인덱스
    empty_mask = df["작업일시"].isna()

    # 날짜 컬럼 우선순위대로 파싱
    date_columns = []

    # 1순위: 접수일시
    if "접수일시" in df.columns:
        print("  📅 접수일시 컬럼 파싱 중...")
        parsed_dates = parse_numeric_date_column(df, "접수일시")
        date_columns.append(parsed_dates)
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df)))

    # 2순위: 작업시작일시 또는 작업시작
    work_start_col = None
    if "작업시작일시" in df.columns:
        work_start_col = "작업시작일시"
    elif "작업시작" in df.columns:
        work_start_col = "작업시작"

    if work_start_col:
        print(f"  📅 {work_start_col} 컬럼 파싱 중...")
        parsed_dates = parse_numeric_date_column(df, work_start_col)
        date_columns.append(parsed_dates)
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df)))

    # 3순위: 작업종료일 또는 작업종료
    work_end_col = None
    if "작업종료일" in df.columns:
        work_end_col = "작업종료일"
    elif "작업종료" in df.columns:
        work_end_col = "작업종료"

    if work_end_col:
        print(f"  📅 {work_end_col} 컬럼 파싱 중...")
        parsed_dates = parse_numeric_date_column(df, work_end_col)
        date_columns.append(parsed_dates)
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df)))

    # 4순위: 공사일자
    if "공사일자" in df.columns:
        print("  📅 공사일자 컬럼 파싱 중...")
        parsed_dates = parse_numeric_date_column(df, "공사일자")
        date_columns.append(parsed_dates)
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df)))

    # 5순위: 민원접수번호 (날짜 정보가 포함된 경우)
    if "민원접수번호" in df.columns:
        print("  📅 민원접수번호 컬럼 파싱 중...")
        parsed_dates = parse_numeric_date_column(df, "민원접수번호")
        date_columns.append(parsed_dates)
    else:
        date_columns.append(pd.Series([pd.NaT] * len(df)))

    # 우선순위에 따라 첫 번째 유효한 날짜 선택 (모든 date_columns 사용)
    new_workdates = date_columns[0]
    for i in range(1, len(date_columns)):
        new_workdates = new_workdates.fillna(date_columns[i])

    # 빈 작업일시만 업데이트 (기존 값은 유지)
    df.loc[empty_mask, "작업일시"] = new_workdates[empty_mask]

    # 최종 통계
    empty_after = df["작업일시"].isna().sum()
    fixed_count = empty_before - empty_after

    print(f"  수정됨: {fixed_count:,}개")
    print(f"  남은 빈 값: {empty_after:,}개")

    # 백업 생성
    if backup and fixed_count > 0:
        backup_file = location_file.with_suffix(".csv.bak")
        shutil.copy2(location_file, backup_file)
        print(f"  💾 백업 생성: {backup_file.name}")

    # 파일 저장
    if fixed_count > 0:
        df.to_csv(location_file, index=False, encoding="utf-8-sig")
        print(f"  ✅ 파일 저장 완료")

    return {
        "status": "success",
        "total_rows": total_rows,
        "empty_before": empty_before,
        "empty_after": empty_after,
        "fixed": fixed_count
    }


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("작업일시 재파싱 스크립트")
    print("=" * 60)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # results 디렉토리에서 *_위치추가.csv 파일 찾기 (하위 디렉토리 제외)
    # NFD/NFC 문제 해결을 위해 iterdir() 사용하고 NFD 형태도 검색
    import unicodedata

    results_dir = project_root / "results"
    nfc_suffix = "_위치추가.csv"
    nfd_suffix = unicodedata.normalize('NFD', nfc_suffix)

    location_files = sorted([
        f for f in results_dir.iterdir()
        if f.is_file() and (f.name.endswith(nfc_suffix) or f.name.endswith(nfd_suffix))
    ])

    if not location_files:
        print("\n⚠️  위치추가 파일을 찾을 수 없습니다.")
        return

    print(f"\n찾은 파일: {len(location_files)}개")
    for f in location_files:
        print(f"  - {f.name}")

    # 전체 통계 초기화
    total_stats = {
        "processed": 0,
        "total_fixed": 0,
        "total_empty_before": 0,
        "total_empty_after": 0,
        "failed": []
    }

    # 각 파일 처리
    for location_file in location_files:
        result = fix_empty_workdate(location_file)

        if result["status"] == "success":
            total_stats["processed"] += 1
            total_stats["total_fixed"] += result["fixed"]
            total_stats["total_empty_before"] += result["empty_before"]
            total_stats["total_empty_after"] += result["empty_after"]
        else:
            total_stats["failed"].append(location_file.name)

    # 최종 요약
    print("\n" + "=" * 60)
    print("처리 완료 요약")
    print("=" * 60)
    print(f"처리된 파일: {total_stats['processed']}/{len(location_files)}개")
    print(f"총 수정된 행: {total_stats['total_fixed']:,}개")
    print(f"처리 전 빈 값: {total_stats['total_empty_before']:,}개")
    print(f"처리 후 빈 값: {total_stats['total_empty_after']:,}개")

    if total_stats["total_empty_before"] > 0:
        recovery_rate = (total_stats["total_fixed"] / total_stats["total_empty_before"]) * 100
        print(f"복구율: {recovery_rate:.1f}%")

    if total_stats["failed"]:
        print(f"\n⚠️  실패한 파일:")
        for name in total_stats["failed"]:
            print(f"  - {name}")

    print("\n✨ 작업 완료!")


if __name__ == "__main__":
    main()