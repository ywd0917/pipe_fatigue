"""
Soil (지질) 데이터 리스트 출력 스크립트
Geology_250K_Litho의 lithoidx별 정보를 텍스트로 출력
"""

import argparse
import warnings
from pathlib import Path

import pandas as pd

from src import soil_loader
from src.common.config import RAW_DATA_DIR, RESULTS_DIR

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def print_lithoidx_info(df: pd.DataFrame, top_n: int | None = None) -> None:
    """lithoidx 정보를 텍스트로 출력"""
    print("\n" + "=" * 100)
    print("Lithoidx별 암상 정보 분석")
    print("=" * 100)
    print(f"전체 lithoidx 수: {len(df)}개")
    print(f"전체 객체 수: {df['count'].sum():,}개")
    print(f"전체 면적: {df['total_area'].sum():,.2f}")
    print()

    # 상위 N개만 출력
    display_df = df.head(top_n) if top_n else df

    for _, row in display_df.iterrows():
        print(f"\n[순위 {row['rank']}] Lithoidx: {row['lithoidx']}")
        print(f"  암상명: {row['lithoname']}")
        print(f"  객체 수: {row['count']:,}개")
        print(f"  총 면적: {row['total_area']:,.2f}")
        print(f"  평균 면적: {row['avg_area']:,.2f}")
        print(f"  총 둘레: {row['total_length']:,.2f}")
        print(f"  지질시대 분포 ({row['unique_ages']}개): {row['ages']}")
        print(f"  포함된 도엽 ({row['map_count']}개): {row['maps']}")
        print("-" * 100)

    if top_n and len(df) > top_n:
        print(f"\n... 외 {len(df) - top_n}개 lithoidx")


def print_summary_statistics(stats: soil_loader.LithoidxStatistics) -> None:
    """전체 통계 요약 출력"""
    print("\n" + "=" * 100)
    print("전체 통계 요약")
    print("=" * 100)
    print(f"총 lithoidx 수: {stats.total_lithoidx:,}개")
    print(f"총 객체 수: {stats.total_objects:,}개")
    print(f"총 면적: {stats.total_area:,.2f}")
    print(f"lithoidx당 평균 객체 수: {stats.avg_objects_per_lithoidx:.1f}개")
    print()

    print("가장 많은 객체를 가진 lithoidx:")
    max_obj = stats.max_objects_lithoidx
    print(
        f"  Lithoidx {max_obj['lithoidx']}: {max_obj['lithoname']} ({max_obj['count']:,}개)"
    )
    print()

    print("가장 넓은 면적을 가진 lithoidx:")
    max_area = stats.max_area_lithoidx
    print(
        f"  Lithoidx {max_area['lithoidx']}: {max_area['lithoname']} (면적: {max_area['total_area']:,.2f})"
    )
    print()

    print(f"지질시대 분포 ({len(stats.age_distribution)}개 시대):")
    for age, count in sorted(
        stats.age_distribution.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {age}: {count:,}개 객체")
    print()

    print(f"도엽 커버리지: {len(stats.map_coverage)}개 도엽")
    print(f"  {', '.join(sorted(stats.map_coverage))}")


def save_to_csv(df: pd.DataFrame, output_path: Path) -> None:
    """분석 결과를 CSV 파일로 저장"""
    columns = [
        "rank",
        "lithoidx",
        "lithoname",
        "count",
        "total_area",
        "avg_area",
        "total_length",
        "unique_ages",
        "ages",
        "map_count",
        "maps",
    ]

    df[columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nCSV 파일 저장 완료: {output_path}")


def handle_search_mode(df: pd.DataFrame, search_term: str) -> None:
    """검색 모드 처리"""
    result = soil_loader.search_lithoidx(df, search_term)
    if result.empty:
        print(f"\n'{search_term}'에 해당하는 결과를 찾을 수 없습니다.")
    else:
        print(f"\n'{search_term}' 검색 결과: {len(result)}개")
        print_lithoidx_info(result)


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="Soil (지질) lithoidx별 정보 리스트 출력"
    )
    parser.add_argument("--top", type=int, help="상위 N개만 출력")
    parser.add_argument("--search", type=str, help="특정 lithoidx 또는 암상명 검색")
    parser.add_argument("--csv", action="store_true", help="결과를 CSV 파일로 저장")
    parser.add_argument("--output", type=str, help="출력 파일 경로")
    parser.add_argument("--summary", action="store_true", help="전체 통계 요약만 출력")

    args = parser.parse_args()

    print("Lithoidx 정보 분석 시작...")
    print(f"데이터 디렉토리: {RAW_DATA_DIR}")

    # 데이터 로드 및 분석
    gdf = soil_loader.load_soil_data(RAW_DATA_DIR)
    if gdf is None:
        print("오류: Litho 데이터를 로드할 수 없습니다.")
        return

    df = soil_loader.analyze_lithoidx(gdf)
    stats = soil_loader.generate_lithoidx_statistics(df)

    # 결과 출력
    if args.summary:
        print_summary_statistics(stats)
    elif args.search:
        handle_search_mode(df, args.search)
    else:
        print_lithoidx_info(df, args.top)
        print_summary_statistics(stats)

    # CSV 저장
    if args.csv:
        output_path = (
            Path(args.output) if args.output else RESULTS_DIR / "lithoidx_list.csv"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_to_csv(df, output_path)


if __name__ == "__main__":
    main()
