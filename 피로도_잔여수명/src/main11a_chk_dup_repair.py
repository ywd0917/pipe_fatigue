"""
두 긴급공사 데이터에서 중복 데이터가 있는지 검증하는 목적
data/repair/ 폴더의 CSV 파일에서 두개의 파일을 읽어서 중복 체크
"""

import pandas as pd
import os
from pathlib import Path
from collections import Counter
from datetime import datetime


def main():
    # 프로젝트 루트 경로 설정
    project_root = Path(__file__).parent.parent
    repair_dir = project_root / "data" / "repair"
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)

    # CSV 파일 경로
    file1_path = repair_dir / "긴급복구.csv"
    file2_path = repair_dir / "긴급복구공사관리(0520).csv"

    print("=" * 80)
    print("접수번호 중복 검사 시작")
    print("=" * 80)

    # 파일 읽기
    print(f"\n1. 파일 읽기:")
    print(f"   - {file1_path.name}")
    df1 = pd.read_csv(file1_path, encoding="utf-8-sig")
    print(f"     전체 행 수: {len(df1):,}")

    print(f"   - {file2_path.name}")
    df2 = pd.read_csv(file2_path, encoding="utf-8-sig")
    print(f"     전체 행 수: {len(df2):,}")

    # '지시번호' 컬럼이 '계' 또는 '소계'인 행 제외
    print("\n2. 데이터 필터링 ('지시번호'가 '계' 또는 '소계'인 행 제외):")

    # 첫 번째 파일
    df1_filtered = df1[~df1["지시번호"].astype(str).str.strip().isin(["계", "소계"])]
    print(f"   - {file1_path.name}: {len(df1):,} → {len(df1_filtered):,} 행")

    # 두 번째 파일
    df2_filtered = df2[~df2["지시번호"].astype(str).str.strip().isin(["계", "소계"])]
    print(f"   - {file2_path.name}: {len(df2):,} → {len(df2_filtered):,} 행")

    # 접수번호가 비어있지 않은 행만 선택
    print("\n3. 접수번호가 있는 행만 선택:")
    df1_with_receipt = df1_filtered[
        df1_filtered["접수번호"].notna() & (df1_filtered["접수번호"] != "")
    ]
    print(f"   - {file1_path.name}: {len(df1_with_receipt):,} 행")

    df2_with_receipt = df2_filtered[
        df2_filtered["접수번호"].notna() & (df2_filtered["접수번호"] != "")
    ]
    print(f"   - {file2_path.name}: {len(df2_with_receipt):,} 행")

    # 접수번호 추출
    receipt_nums1 = df1_with_receipt["접수번호"].astype(str).tolist()
    receipt_nums2 = df2_with_receipt["접수번호"].astype(str).tolist()

    # 각 파일 내 중복 검사
    print("\n" + "=" * 80)
    print("4. 각 파일 내 중복 검사:")
    print("=" * 80)

    # 파일1 내 중복
    counter1 = Counter(receipt_nums1)
    duplicates1 = {k: v for k, v in counter1.items() if v > 1}

    print(f"\n{file1_path.name}:")
    if duplicates1:
        print(f"   중복된 접수번호 개수: {len(duplicates1)}개")
        print("   중복 상세:")
        for receipt_num, count in sorted(
            duplicates1.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"      - {receipt_num}: {count}번 중복")
        if len(duplicates1) > 10:
            print(f"      ... 외 {len(duplicates1) - 10}개")
    else:
        print("   ✓ 중복 없음")

    # 파일2 내 중복
    counter2 = Counter(receipt_nums2)
    duplicates2 = {k: v for k, v in counter2.items() if v > 1}

    print(f"\n{file2_path.name}:")
    if duplicates2:
        print(f"   중복된 접수번호 개수: {len(duplicates2)}개")
        print("   중복 상세:")
        for receipt_num, count in sorted(
            duplicates2.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"      - {receipt_num}: {count}번 중복")
        if len(duplicates2) > 10:
            print(f"      ... 외 {len(duplicates2) - 10}개")
    else:
        print("   ✓ 중복 없음")

    # 두 파일 간 중복 검사
    print("\n" + "=" * 80)
    print("5. 두 파일 간 중복 검사:")
    print("=" * 80)

    set1 = set(receipt_nums1)
    set2 = set(receipt_nums2)
    intersection = set1 & set2

    if intersection:
        print(f"   양쪽 파일에 모두 존재하는 접수번호: {len(intersection)}개")
        print("   중복 상세 (최대 20개 표시):")
        for receipt_num in sorted(list(intersection))[:20]:
            # 각 파일에서 해당 접수번호의 정보 가져오기
            info1 = df1_with_receipt[
                df1_with_receipt["접수번호"].astype(str) == receipt_num
            ].iloc[0]
            info2 = df2_with_receipt[
                df2_with_receipt["접수번호"].astype(str) == receipt_num
            ].iloc[0]
            print(f"\n   접수번호: {receipt_num}")
            print(
                f"      파일1 - 주소: {info1.get('주소', 'N/A')}, 접수일시: {info1.get('접수일시', 'N/A')}"
            )
            print(
                f"      파일2 - 주소: {info2.get('주소', 'N/A')}, 접수일시: {info2.get('접수일시', 'N/A')}"
            )

        if len(intersection) > 20:
            print(f"\n   ... 외 {len(intersection) - 20}개")
    else:
        print("   ✓ 두 파일 간 중복 없음")

    # 결과 요약
    print("\n" + "=" * 80)
    print("6. 요약:")
    print("=" * 80)
    print(
        f"   - {file1_path.name}: 총 {len(receipt_nums1):,}개 접수번호, {len(duplicates1)}개 내부 중복"
    )
    print(
        f"   - {file2_path.name}: 총 {len(receipt_nums2):,}개 접수번호, {len(duplicates2)}개 내부 중복"
    )
    print(f"   - 두 파일 간 중복: {len(intersection)}개")

    # 결과를 CSV로 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"duplicate_check_{timestamp}.csv"

    # 상세 결과 데이터프레임 생성
    results_data = []

    # 파일1 내부 중복
    for receipt_num, count in duplicates1.items():
        results_data.append(
            {
                "중복유형": f"{file1_path.name} 내부 중복",
                "접수번호": receipt_num,
                "중복횟수": count,
                "파일명": file1_path.name,
            }
        )

    # 파일2 내부 중복
    for receipt_num, count in duplicates2.items():
        results_data.append(
            {
                "중복유형": f"{file2_path.name} 내부 중복",
                "접수번호": receipt_num,
                "중복횟수": count,
                "파일명": file2_path.name,
            }
        )

    # 파일 간 중복
    for receipt_num in intersection:
        results_data.append(
            {
                "중복유형": "파일 간 중복",
                "접수번호": receipt_num,
                "중복횟수": 2,
                "파일명": "양쪽 파일",
            }
        )

    if results_data:
        results_df = pd.DataFrame(results_data)
        results_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n7. 상세 결과 저장:")
        print(f"   → {output_path}")
    else:
        print("\n7. 중복이 발견되지 않아 별도 파일을 생성하지 않았습니다.")

    print("\n" + "=" * 80)
    print("접수번호 중복 검사 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
