"""
main59_fix_smz_num.py - SMZ_NUM 정정 스크립트

zone_fatigue_merged.csv에서 zone과 SMZ_NUM이 불일치하는 데이터를 정정합니다.

배경:
- main13c에서 공간 조인으로 zone을 판별
- 원본 shapefile의 SMZ_NUM과 다를 수 있음
- zone이 실제 물리적 위치를 반영하므로 SMZ_NUM을 zone으로 정정

입력:
    - results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv

출력:
    - results/main59_fix_smz_num/fatigue_merged_zone_fixed.csv
    - results/main59_fix_smz_num/fix_report.txt
    - results/main59_fix_smz_num/mismatch_ftr_idn_list.csv
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from common.config import RESULTS_DIR


def load_zone_fatigue_data(file_path: Path) -> pd.DataFrame:
    """
    zone_fatigue_merged.csv를 로드하고 필수 컬럼을 검증합니다.

    Args:
        file_path: CSV 파일 경로

    Returns:
        로드된 DataFrame

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: 필수 컬럼이 없을 때
    """
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    print(f"\n{'='*60}")
    print(f"입력 파일: {file_path}")
    print(f"{'='*60}")

    # FTR_IDN을 int로 읽기 (CSV에 float로 저장되어 있을 수 있음)
    df = pd.read_csv(file_path, encoding="utf-8-sig", dtype={"FTR_IDN": int})

    # 필수 컬럼 확인
    required_columns = ["FTR_IDN", "zone", "SMZ_NUM"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"필수 컬럼 누락: {', '.join(missing)}")

    print(f"  - 전체 행 수: {len(df):,}개")
    print(f"  - 전체 컬럼 수: {len(df.columns)}개")
    print(f"  - zone 컬럼: 존재 ✓")
    print(f"  - SMZ_NUM 컬럼: 존재 ✓")

    return df


def detect_mismatch(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    zone과 SMZ_NUM이 일치하는 행과 불일치하는 행을 분리합니다.

    Args:
        df: 원본 DataFrame

    Returns:
        (match_df, mismatch_df) 튜플
    """
    # zone과 SMZ_NUM을 정수형으로 변환하여 비교
    # NaN 처리: fillna(-1)로 NaN을 -1로 치환
    zone_int = df["zone"].fillna(-1).astype(int)
    smz_int = df["SMZ_NUM"].fillna(-1).astype(int)

    mismatch_mask = zone_int != smz_int

    match_df = df[~mismatch_mask].copy()
    mismatch_df = df[mismatch_mask].copy()

    return match_df, mismatch_df


def print_mismatch_ftr_idn(mismatch_df: pd.DataFrame) -> None:
    """
    불일치하는 행의 FTR_IDN 목록을 콘솔에 출력합니다.

    Args:
        mismatch_df: 불일치 행 DataFrame
    """
    print(f"\n{'='*60}")
    print(f"불일치 FTR_IDN 목록 (총 {len(mismatch_df):,}개)")
    print(f"{'='*60}\n")

    for i, (idx, row) in enumerate(mismatch_df.iterrows(), 1):
        # FTR_IDN은 이미 int 타입으로 로드됨
        ftr_idn = row["FTR_IDN"]
        zone = int(row["zone"])
        smz_num = int(row["SMZ_NUM"])
        print(
            f"  {i:3d}. FTR_IDN: {ftr_idn:8d} | zone: {zone:3d} | SMZ_NUM: {smz_num:3d} → {zone:3d}"
        )


def analyze_statistics(mismatch_df: pd.DataFrame) -> dict:
    """
    불일치 패턴을 분석하여 통계를 생성합니다.

    Args:
        mismatch_df: 불일치 행 DataFrame

    Returns:
        통계 정보 딕셔너리
    """
    stats = {}

    # zone별 분포
    zone_dist = mismatch_df["zone"].value_counts().sort_index()
    stats["zone_distribution"] = zone_dist.to_dict()

    # 원본 SMZ_NUM별 분포
    smz_dist = mismatch_df["SMZ_NUM"].value_counts().sort_index()
    stats["smz_distribution"] = smz_dist.to_dict()

    # 교차표 (zone × SMZ_NUM)
    crosstab = pd.crosstab(mismatch_df["zone"], mismatch_df["SMZ_NUM"])
    stats["crosstab"] = crosstab

    return stats


def print_statistics(
    stats: dict, total_rows: int, match_count: int, mismatch_count: int
) -> None:
    """
    통계를 콘솔에 출력합니다.

    Args:
        stats: 통계 정보 딕셔너리
        total_rows: 전체 행 수
        match_count: 일치 행 수
        mismatch_count: 불일치 행 수
    """
    print(f"\n{'='*60}")
    print("불일치 검출 결과")
    print(f"{'='*60}\n")

    match_pct = (match_count / total_rows) * 100
    mismatch_pct = (mismatch_count / total_rows) * 100

    print(f"✅ 일치: {match_count:,}개 ({match_pct:.2f}%)")
    print(f"⚠️  불일치: {mismatch_count:,}개 ({mismatch_pct:.2f}%)")

    # zone별 분포
    print(f"\n{'='*60}")
    print("zone별 불일치 분포")
    print(f"{'='*60}\n")

    for zone, count in sorted(stats["zone_distribution"].items()):
        zone_pct = (count / mismatch_count) * 100
        print(f"  zone {int(zone):3d}: {count:3d}건 ({zone_pct:.2f}%)")

    # 원본 SMZ_NUM별 분포
    print(f"\n{'='*60}")
    print("원본 SMZ_NUM 분포")
    print(f"{'='*60}\n")

    for smz, count in sorted(stats["smz_distribution"].items()):
        smz_pct = (count / mismatch_count) * 100
        print(f"  {int(smz):3d}: {count:3d}건 ({smz_pct:.2f}%)")


def fix_smz_num(df: pd.DataFrame, mismatch_mask: pd.Series) -> pd.DataFrame:
    """
    불일치 행의 SMZ_NUM을 zone 값으로 정정합니다.

    Args:
        df: 원본 DataFrame
        mismatch_mask: 불일치 행 마스크

    Returns:
        SMZ_NUM이 정정된 DataFrame
    """
    df_fixed = df.copy()

    # 원본 백업 (리포트용)
    df_fixed["SMZ_NUM_원본"] = df_fixed["SMZ_NUM"].copy()

    # 불일치 행의 SMZ_NUM을 zone 값으로 덮어쓰기
    df_fixed.loc[mismatch_mask, "SMZ_NUM"] = df_fixed.loc[mismatch_mask, "zone"]

    return df_fixed


def validate_output(df: pd.DataFrame) -> bool:
    """
    출력 DataFrame에서 zone == SMZ_NUM인지 검증합니다.

    Args:
        df: 검증할 DataFrame

    Returns:
        모든 행이 일치하면 True, 아니면 False
    """
    zone_int = df["zone"].fillna(-1).astype(int)
    smz_int = df["SMZ_NUM"].fillna(-1).astype(int)

    mismatch_count = (zone_int != smz_int).sum()

    return mismatch_count == 0


def generate_report(
    stats: dict, total_rows: int, match_count: int, mismatch_count: int
) -> str:
    """
    텍스트 리포트를 생성합니다.

    Args:
        stats: 통계 정보 딕셔너리
        total_rows: 전체 행 수
        match_count: 일치 행 수
        mismatch_count: 불일치 행 수

    Returns:
        리포트 텍스트
    """
    lines = []
    lines.append("=== main59: SMZ_NUM 정정 리포트 ===")
    lines.append(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 전체 통계
    lines.append("📊 처리 통계")
    lines.append("━" * 60)
    match_pct = (match_count / total_rows) * 100
    mismatch_pct = (mismatch_count / total_rows) * 100
    lines.append(f"전체 행 수: {total_rows:,}개")
    lines.append(f"일치 행 수: {match_count:,}개 ({match_pct:.2f}%)")
    lines.append(f"불일치 행 수: {mismatch_count:,}개 ({mismatch_pct:.2f}%)")
    lines.append(f"정정 완료: {mismatch_count:,}개\n")

    # zone별 분포
    lines.append("🔍 zone별 정정 분포")
    lines.append("━" * 60)
    for zone, count in sorted(stats["zone_distribution"].items()):
        zone_pct = (count / mismatch_count) * 100
        lines.append(f"zone {int(zone):3d}: {count:3d}건 ({zone_pct:.2f}%)")
    lines.append("")

    # 원본 SMZ_NUM별 분포
    lines.append("📋 정정 전 SMZ_NUM 분포")
    lines.append("━" * 60)
    for smz, count in sorted(stats["smz_distribution"].items()):
        smz_pct = (count / mismatch_count) * 100
        lines.append(
            f"{int(smz):3d} → zone별로 정정: {count:3d}건 ({smz_pct:.2f}%)"
        )
    lines.append("")

    # 교차표
    lines.append("📊 교차표 (zone × SMZ_NUM_원본)")
    lines.append("━" * 60)

    crosstab = stats["crosstab"]
    # 헤더
    smz_cols = sorted([int(c) for c in crosstab.columns])
    header = "zone\\SMZ" + "".join([f"{c:5d}" for c in smz_cols])
    lines.append(header)

    # 각 zone별 행
    for zone in sorted([int(r) for r in crosstab.index]):
        row_values = []
        for smz in smz_cols:
            if smz in crosstab.columns and zone in crosstab.index:
                val = crosstab.loc[zone, smz]
                row_values.append(f"{int(val):5d}")
            else:
                row_values.append("    0")
        row_str = f"  {zone:3d}" + "".join(row_values)
        lines.append(row_str)
    lines.append("")

    # 완료 메시지
    lines.append("✅ 정정 완료")
    lines.append("━" * 60)
    lines.append("출력 파일: results/main59_fix_smz_num/zone_fatigue_merged_fixed.csv")
    lines.append("검증 결과: 모든 행에서 zone == SMZ_NUM 보장됨")

    return "\n".join(lines)


def save_results(
    df_fixed: pd.DataFrame, mismatch_df: pd.DataFrame, report: str, output_dir: Path
) -> None:
    """
    모든 출력 파일을 저장합니다.

    Args:
        df_fixed: 정정된 DataFrame
        mismatch_df: 불일치 행 DataFrame (원본 값 포함)
        report: 리포트 텍스트
        output_dir: 출력 디렉토리
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 정정된 CSV 저장 (SMZ_NUM_원본 컬럼 제외)
    output_csv = output_dir / "fatigue_merged_zone_fixed.csv"
    df_output = df_fixed.drop(columns=["SMZ_NUM_원본"], errors="ignore")
    df_output.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n✅ 정정된 CSV 저장: {output_csv}")

    # 2. 리포트 파일 저장
    report_path = output_dir / "fix_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 리포트 저장: {report_path}")

    # 3. 불일치 FTR_IDN 목록 저장
    if len(mismatch_df) > 0:
        mismatch_list = mismatch_df[
            ["FTR_IDN", "zone", "SMZ_NUM", "DATA_SRC"]
        ].copy()
        mismatch_list["SMZ_NUM_원본"] = mismatch_list["SMZ_NUM"]
        mismatch_list["SMZ_NUM_정정후"] = mismatch_list["zone"]
        mismatch_list = mismatch_list[
            ["FTR_IDN", "zone", "SMZ_NUM_원본", "SMZ_NUM_정정후", "DATA_SRC"]
        ]

        mismatch_csv = output_dir / "mismatch_ftr_idn_list.csv"
        mismatch_list.to_csv(mismatch_csv, index=False, encoding="utf-8-sig")
        print(f"✅ 불일치 목록 저장: {mismatch_csv}")


def main() -> None:
    """메인 실행 함수"""
    print("\n" + "=" * 60)
    print("main59_fix_smz_num.py - SMZ_NUM 정정 스크립트")
    print("=" * 60)

    # 입력 파일 경로
    input_path = RESULTS_DIR / "main13c_zone_fatigue_merge" / "zone_fatigue_merged.csv"

    # 출력 디렉토리
    output_dir = RESULTS_DIR / "main59_fix_smz_num"

    try:
        # 1. 데이터 로드
        df = load_zone_fatigue_data(input_path)

        # 2. 불일치 검출
        match_df, mismatch_df = detect_mismatch(df)
        match_count = len(match_df)
        mismatch_count = len(mismatch_df)
        total_rows = len(df)

        # 3. 불일치 FTR_IDN 목록 출력
        if mismatch_count > 0:
            print_mismatch_ftr_idn(mismatch_df)

            # 4. 통계 분석
            stats = analyze_statistics(mismatch_df)

            # 5. 통계 출력
            print_statistics(stats, total_rows, match_count, mismatch_count)

            # 6. SMZ_NUM 정정
            print(f"\n{'='*60}")
            print("SMZ_NUM 정정 중...")
            print(f"{'='*60}")

            mismatch_mask = df["zone"].fillna(-1).astype(int) != df["SMZ_NUM"].fillna(
                -1
            ).astype(int)
            df_fixed = fix_smz_num(df, mismatch_mask)

            # 7. 검증
            if validate_output(df_fixed):
                print("\n✅ 검증 완료: 모든 행에서 zone == SMZ_NUM")
            else:
                print("\n⚠️  경고: 일부 행에서 여전히 불일치가 존재합니다.")

            # 8. 리포트 생성
            report = generate_report(stats, total_rows, match_count, mismatch_count)

            # 9. 결과 저장
            print(f"\n{'='*60}")
            print("결과 저장 중...")
            print(f"{'='*60}")
            save_results(df_fixed, mismatch_df, report, output_dir)

            print(f"\n{'='*60}")
            print(f"✅ 처리 완료: {mismatch_count:,}개 행 정정")
            print(f"{'='*60}\n")

        else:
            print(f"\n{'='*60}")
            print("✅ 모든 행이 이미 일치합니다. 정정 불필요.")
            print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
