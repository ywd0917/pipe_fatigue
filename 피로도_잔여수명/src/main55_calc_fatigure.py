"""
Rain Flow Counting 계산 스크립트 (최신 1년 데이터)
- main53_rainflow.py를 참고해서 최신 1년치 데이터에서 high와 low의 rain flow counting을 구함
- 전체 데이터를 로드한 후 최근 1년 데이터를 추출하여 분석
"""

import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 새로운 모듈 import
from rainflow_processing import (
    analyze_date_range_rainflow,
    process_all_pipe_data_with_rainflow,
)
from pipe_prop import read_pipe_properties
from traffic_loader import print_unmapped_roads_summary

# 공통 설정 import
from common.config import (
    PRESSURE_DATA_FILES,
    PIPE_PROP_PATH,
)


def get_rainflow_summary(analysis_result: Dict[str, Any]) -> Dict[str, float]:
    """
    Rain Flow Counting 분석 결과에서 주요 값들을 추출

    Args:
        analysis_result: analyze_date_range_rainflow 함수의 결과

    Returns:
        Dict[str, float]: 주요 Rain Flow Counting 값들
    """
    if not analysis_result["success"]:
        return {
            "high_total_cycles": 0.0,
            "low_total_cycles": 0.0,
            "high_full_cycles": 0.0,
            "low_full_cycles": 0.0,
            "high_half_cycles": 0.0,
            "low_half_cycles": 0.0,
            "high_mean_range": 0.0,
            "low_mean_range": 0.0,
            "high_max_range": 0.0,
            "low_max_range": 0.0,
        }

    results = analysis_result["results"]

    return {
        "high_total_cycles": (
            results["high_pass"]["analysis"].get("total_cycles", 0.0)
            if results["high_pass"]["has_cycles"]
            else 0.0
        ),
        "low_total_cycles": (
            results["low_pass"]["analysis"].get("total_cycles", 0.0)
            if results["low_pass"]["has_cycles"]
            else 0.0
        ),
        "high_full_cycles": (
            results["high_pass"]["analysis"].get("full_cycles", 0.0)
            if results["high_pass"]["has_cycles"]
            else 0.0
        ),
        "low_full_cycles": (
            results["low_pass"]["analysis"].get("full_cycles", 0.0)
            if results["low_pass"]["has_cycles"]
            else 0.0
        ),
        "high_half_cycles": (
            results["high_pass"]["analysis"].get("half_cycles", 0.0)
            if results["high_pass"]["has_cycles"]
            else 0.0
        ),
        "low_half_cycles": (
            results["low_pass"]["analysis"].get("half_cycles", 0.0)
            if results["low_pass"]["has_cycles"]
            else 0.0
        ),
        "high_mean_range": (
            results["high_pass"]["analysis"].get("mean_range", 0.0)
            if results["high_pass"]["has_cycles"]
            else 0.0
        ),
        "low_mean_range": (
            results["low_pass"]["analysis"].get("mean_range", 0.0)
            if results["low_pass"]["has_cycles"]
            else 0.0
        ),
        "high_max_range": (
            results["high_pass"]["analysis"].get("max_range", 0.0)
            if results["high_pass"]["has_cycles"]
            else 0.0
        ),
        "low_max_range": (
            results["low_pass"]["analysis"].get("max_range", 0.0)
            if results["low_pass"]["has_cycles"]
            else 0.0
        ),
    }


def compare_date_range_rainflow_results(
    all_results: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    여러 파일의 날짜 범위 Rain Flow Counting 결과 비교

    Args:
        all_results: 모든 파일의 분석 결과

    Returns:
        pd.DataFrame: 비교 결과 데이터프레임
    """
    print(f"\n{'='*80}")
    print("날짜 범위 Rain Flow Counting 결과 비교 분석")
    print(f"{'='*80}")

    # 성공적으로 분석된 결과만 필터링
    successful_results = [r for r in all_results if r["success"]]

    if not successful_results:
        print("비교할 수 있는 성공적인 분석 결과가 없습니다.")
        return pd.DataFrame()

    # 비교 테이블 생성
    comparison_data = []

    for result in successful_results:
        file_name = result["file_name"]

        # data_period 키가 있는지 확인 (analyze_date_range_rainflow의 반환값 구조 확인)
        if "start_date" in result and "end_date" in result:
            period_start = result["start_date"].strftime("%Y-%m-%d")
            period_end = result["end_date"].strftime("%Y-%m-%d")
            data_points = result.get("data_count", 0)
        else:
            # 기본값 설정
            period_start = "N/A"
            period_end = "N/A"
            data_points = 0

        # 각 데이터 타입별 결과 추가 (low_pass, high_pass만)
        for data_type in ["low_pass", "high_pass"]:
            result_data = result["results"][data_type]

            if result_data["has_cycles"]:
                analysis = result_data["analysis"]
                comparison_data.append(
                    {
                        "File": file_name,
                        "Data_Type": data_type.replace("_", " ").title(),
                        "Data_Points": data_points,
                        "Period_Start": period_start,
                        "Period_End": period_end,
                        "Total_Cycles": analysis["total_cycles"],
                        "Full_Cycles": analysis["full_cycles"],
                        "Half_Cycles": analysis["half_cycles"],
                        "Mean_Range": analysis["mean_range"],
                        "Max_Range": analysis["max_range"],
                        "Std_Range": analysis["std_range"],
                    }
                )
            else:
                comparison_data.append(
                    {
                        "File": file_name,
                        "Data_Type": data_type.replace("_", " ").title(),
                        "Data_Points": data_points,
                        "Period_Start": period_start,
                        "Period_End": period_end,
                        "Total_Cycles": 0.0,
                        "Full_Cycles": 0,
                        "Half_Cycles": 0,
                        "Mean_Range": 0.0,
                        "Max_Range": 0.0,
                        "Std_Range": 0.0,
                    }
                )

    if comparison_data:
        # DataFrame으로 변환
        df_comparison = pd.DataFrame(comparison_data)

        print("\n날짜 범위 Rain Flow Counting 비교 테이블:")
        print("=" * 140)
        print(df_comparison.to_string(index=False, float_format="%.3f"))

        # 요약 통계
        print(f"\n{'='*60}")
        print("요약 통계 (날짜 범위)")
        print(f"{'='*60}")

        for data_type in ["Low Pass", "High Pass"]:
            subset = df_comparison[df_comparison["Data_Type"] == data_type]
            if not subset.empty and subset["Total_Cycles"].sum() > 0:
                print(f"\n{data_type} 데이터:")
                print(f"  - 평균 총 사이클 수: {subset['Total_Cycles'].mean():.1f}")
                print(f"  - 평균 전체 사이클 수: {subset['Full_Cycles'].mean():.1f}")
                print(f"  - 평균 반 사이클 수: {subset['Half_Cycles'].mean():.1f}")
                print(f"  - 평균 범위: {subset['Mean_Range'].mean():.3f}")
                print(f"  - 평균 최대 범위: {subset['Max_Range'].mean():.3f}")

        return df_comparison

    return pd.DataFrame()


def main(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    process_pipes: bool = True,
    process_rainflow: bool = True,
) -> None:
    """
    메인 실행 함수

    Args:
        start_date: 분석 시작 날짜 (None이면 2023-01-01 사용)
        end_date: 분석 종료 날짜 (None이면 2023-12-31 사용)
        process_pipes: 파이프 데이터 처리 여부 (Rain Flow Counting, 재료계수(K_material), 피로도 포함)
        process_rainflow: 기본 Rain Flow Counting 분석 여부 (압력 데이터만)
    """
    print(
        "통합 데이터 분석 프로그램 (나이 기반 Rain Flow Counting, 재료계수(K_material) 및 피로도 포함)"
    )
    print("=" * 80)

    try:
        # 파이프 속성 데이터 로드
        pipe_properties = None
        if process_pipes:
            pipe_properties = read_pipe_properties(str(PIPE_PROP_PATH))
            if pipe_properties.empty:
                print("파이프 속성 데이터를 로드할 수 없어 프로그램을 종료합니다.")
                return

        # 1. 파이프 데이터 처리 및 나이 기반 Rain Flow Counting 계산 (재료계수(K_material) 및 피로도 포함)
        if process_pipes:
            print(
                "\n[1단계] 파이프 데이터 처리, Rain Flow Counting, 재료계수(K_material) 및 피로도 계산"
            )
            if pipe_properties is not None:
                process_all_pipe_data_with_rainflow(pipe_properties)
    
    except FileNotFoundError as e:
        missing_file = Path(str(e))
        print(f"\n오류: 필수 입력 파일을 찾을 수 없습니다")
        print(f"누락된 파일: {missing_file}")
        sys.exit(1)

    # 2. 기본 Rain Flow Counting 분석 (압력 데이터만)
    if process_rainflow:
        print("\n[2단계] 기본 Rain Flow Counting 분석")

        # 기본값 설정
        if start_date is None:
            start_date = datetime(2023, 1, 1)
        if end_date is None:
            end_date = datetime(2023, 12, 31, 23, 59, 59)

        print(
            f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        )

        # 데이터 파일 경로 (0470, 0520 파일 선택)
        # 파일명에서 지역 코드를 확인하여 선택
        data_files = []
        for file_path in PRESSURE_DATA_FILES:
            file_name = file_path.name
            if "0470" in file_name or "0520" in file_name:
                data_files.append(file_path)

        all_results = []

        # 각 파일 분석
        for file_path in data_files:
            if Path(file_path).exists():
                result = analyze_date_range_rainflow(
                    str(file_path), start_date, end_date
                )
                all_results.append(result)

                # 주요 Rain Flow Counting 값 출력
                if result["success"]:
                    summary = get_rainflow_summary(result)
                    print(f"\n{'-'*50}")
                    print(f"주요 Rain Flow Counting 값 - {result['file_name']}")
                    print(f"{'-'*50}")
                    print(f"고주파 총 사이클: {summary['high_total_cycles']:.1f}")
                    print(f"저주파 총 사이클: {summary['low_total_cycles']:.1f}")
                    print(f"고주파 전체 사이클: {summary['high_full_cycles']:.0f}개")
                    print(f"저주파 전체 사이클: {summary['low_full_cycles']:.0f}개")
                    print(f"고주파 반 사이클: {summary['high_half_cycles']:.0f}개")
                    print(f"저주파 반 사이클: {summary['low_half_cycles']:.0f}개")
                    print(f"고주파 평균 범위: {summary['high_mean_range']:.3f}")
                    print(f"저주파 평균 범위: {summary['low_mean_range']:.3f}")
            else:
                print(f"파일을 찾을 수 없습니다: {file_path}")
                all_results.append(
                    {
                        "file_path": file_path,
                        "file_name": Path(file_path).name,
                        "error": "File not found",
                        "success": False,
                    }
                )

        # 결과 비교
        if all_results:
            # 최종 요약
            successful_count = sum(1 for r in all_results if r["success"])
            total_count = len(all_results)

            print(f"\n{'='*80}")
            print("기본 Rain Flow Counting 분석 완료")
            print(f"{'='*80}")
            print(f"총 파일 수: {total_count}")
            print(f"성공적으로 분석된 파일 수: {successful_count}")
            print(f"실패한 파일 수: {total_count - successful_count}")

            if successful_count > 0:
                print("\n분석 결과:")
                print(
                    f"  - {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} 기간 데이터 Rain Flow Counting 계산 완료"
                )
                print("  - High Pass와 Low Pass 필터 적용하여 주파수별 분석")
                print("  - Rain Flow Counting을 통한 사이클 기반 분석")

    # 3단계와 4단계는 이제 1단계에 통합되었음

    print(f"\n{'='*80}")
    print("전체 프로그램 실행 완료")
    print(f"{'='*80}")

    # 생성된 파일 목록 출력
    results_dir = Path("results")
    if results_dir.exists():
        print("\n생성된 결과 파일:")
        result_files = list(results_dir.glob("*.csv"))
        for i, file_path in enumerate(sorted(result_files), 1):
            file_size = file_path.stat().st_size / 1024  # KB
            print(f"  {i:2d}. {file_path.name} ({file_size:.1f} KB)")

    # 매핑되지 않은 도로 정보 출력
    if process_pipes:
        print_unmapped_roads_summary()


if __name__ == "__main__":
    main()