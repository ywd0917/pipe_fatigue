"""
피로 손상 계산 스크립트
- pass_filter.py를 참고해서 high, low 데이터를 받아옴
- 각각의 값에 rain flow counting 적용
- rain flow counting 그래프를 이미지로 저장
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, cast

# 기존 모듈 import
from common.korean_font_utils import setup_korean_font
from utils import interpolate_nan_values
from pass_filter import pass_filter
from rain_flow_counting import (
    rain_flow_counting,
    create_rainflow_histogram,
    analyze_rainflow_cycles,
    create_cumulative_rainflow_plot,
)
from common.config import (
    PRESSURE_DATA_FILES,
    RESULTS_DIR,
)


def load_and_process_data(file_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    데이터 파일을 로드하고 전처리하여 원본, 저대역, 고대역 데이터 반환

    Args:
        file_path: 데이터 파일 경로

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: (원본, 저대역, 고대역) 데이터
    """
    print(f"\n{'='*60}")
    print(f"데이터 로드 및 전처리: {file_path}")
    print(f"{'='*60}")

    # 데이터 로드
    df = pd.read_csv(file_path)
    df["msrmt_dt"] = pd.to_datetime(df["msrmt_dt"])
    df = df.sort_values("msrmt_dt").reset_index(drop=True)

    print(f"원본 데이터 크기: {df.shape}")
    print(f"데이터 기간: {df['msrmt_dt'].min()} ~ {df['msrmt_dt'].max()}")
    print(f"NaN 개수: {df['wtrprsr'].isna().sum()}")

    # NaN 값 보간
    pressure_data = interpolate_nan_values(
        np.array(df["wtrprsr"].values), pd.DatetimeIndex(df["msrmt_dt"])
    )

    # 샘플링 주파수
    sampling_rate = 1 / 300  # 5분 간격
    print(f"샘플링 주파수: {sampling_rate:.6f} Hz")

    # Pass Filter 적용
    low_pass, high_pass = pass_filter(pressure_data, sampling_rate, file_path)

    print("필터 적용 완료:")
    print(f"  - 원본 데이터 길이: {len(pressure_data)}")
    print(f"  - 저대역 데이터 길이: {len(low_pass)}")
    print(f"  - 고대역 데이터 길이: {len(high_pass)}")

    return pressure_data, low_pass, high_pass


def perform_rainflow_analysis(
    data: np.ndarray, data_type: str, file_name: str, output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Rain Flow Counting 분석 수행

    Args:
        data: 분석할 데이터
        data_type: 데이터 타입 ("original", "low_pass", "high_pass")
        file_name: 파일명
        output_dir: 출력 디렉토리

    Returns:
        Dict[str, Any]: 분석 결과
    """
    if output_dir is None:
        output_dir = RESULTS_DIR / "main53_rainflow"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'-'*40}")
    print(f"Rain Flow Counting 분석: {data_type}")
    print(f"{'-'*40}")

    # Rain Flow Counting 수행
    cycles = rain_flow_counting(data)

    if not cycles:
        print(f"  경고: {data_type} 데이터에서 사이클을 찾을 수 없습니다.")
        return {"cycles": [], "analysis": {}, "histogram_path": ""}

    # 사이클 분석
    analysis = analyze_rainflow_cycles(cycles)

    print("  Rain Flow Counting 결과:")
    print(f"    - 총 사이클 수: {analysis['total_cycles']:.1f}")
    print(f"    - 전체 사이클: {analysis['full_cycles']}개")
    print(f"    - 반 사이클: {analysis['half_cycles']}개")
    print(f"    - 평균 범위: {analysis['mean_range']:.3f}")
    print(f"    - 최대 범위: {analysis['max_range']:.3f}")
    print(f"    - 피로 손상 등가: {analysis['damage_equivalent']:.2e}")

    # 히스토그램 생성
    Path(output_dir).mkdir(exist_ok=True)
    base_name = Path(file_name).stem
    histogram_path = f"{output_dir}/rainflow_{data_type}_{base_name}.png"

    title = f"{data_type.replace('_', ' ').title()} - {base_name}"
    create_rainflow_histogram(cycles, title, histogram_path)

    # 누적 Rain Flow Count 그래프 생성
    cumulative_path = f"{output_dir}/cumulative_{data_type}_{base_name}.png"
    cumulative_title = (
        f"{data_type.replace('_', ' ').title()} 누적 사이클 - {base_name}"
    )
    create_cumulative_rainflow_plot(data, cycles, cumulative_title, cumulative_path)

    return {
        "cycles": cycles,
        "analysis": analysis,
        "histogram_path": histogram_path,
        "cumulative_path": cumulative_path,
    }


def analyze_file_fatigue(
    file_path: str, output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    파일별 피로 손상 분석

    Args:
        file_path: 분석할 파일 경로
        output_dir: 결과 저장 디렉토리

    Returns:
        Dict[str, Any]: 분석 결과
    """
    if output_dir is None:
        output_dir = RESULTS_DIR / "main53_rainflow"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_name = Path(file_path).name
    print(f"\n{'='*80}")
    print(f"피로 손상 분석 시작: {file_name}")
    print(f"{'='*80}")

    try:
        # 데이터 로드 및 전처리
        original_data, low_pass_data, high_pass_data = load_and_process_data(file_path)

        # 각 데이터에 대해 Rain Flow Counting 수행
        results = {}

        # 1. 원본 데이터 분석 (그래프 생성 안함)
        print(f"\n{'-'*40}")
        print("Rain Flow Counting 분석: original (그래프 생성 안함)")
        print(f"{'-'*40}")

        cycles_original = rain_flow_counting(original_data)
        if cycles_original:
            analysis_original = analyze_rainflow_cycles(cycles_original)
            print("  Rain Flow Counting 결과:")
            print(f"    - 총 사이클 수: {analysis_original['total_cycles']:.1f}")
            print(f"    - 전체 사이클: {analysis_original['full_cycles']}개")
            print(f"    - 반 사이클: {analysis_original['half_cycles']}개")
            print(f"    - 평균 범위: {analysis_original['mean_range']:.3f}")
            print(f"    - 최대 범위: {analysis_original['max_range']:.3f}")
            print(f"    - 피로 손상 등가: {analysis_original['damage_equivalent']:.2e}")

            results["original"] = {
                "cycles": cycles_original,
                "analysis": analysis_original,
                "histogram_path": "",  # 그래프 생성 안함
            }
        else:
            print("  경고: original 데이터에서 사이클을 찾을 수 없습니다.")
            results["original"] = {"cycles": [], "analysis": {}, "histogram_path": ""}

        # 2. 저대역 데이터 분석
        results["low_pass"] = perform_rainflow_analysis(
            low_pass_data, "low_pass", file_name, output_dir
        )

        # 3. 고대역 데이터 분석
        results["high_pass"] = perform_rainflow_analysis(
            high_pass_data, "high_pass", file_name, output_dir
        )

        # 결과 요약
        print(f"\n{'='*60}")
        print(f"피로 손상 분석 결과 요약: {file_name}")
        print(f"{'='*60}")

        for data_type, result in results.items():
            if result["cycles"]:
                analysis = cast(Dict[str, Any], result["analysis"])
                print(f"\n{data_type.replace('_', ' ').title()} 데이터:")
                print(f"  - 총 사이클 수: {analysis['total_cycles']:.1f}")
                print(f"  - 평균 범위: {analysis['mean_range']:.3f}")
                print(f"  - 최대 범위: {analysis['max_range']:.3f}")
                print(f"  - 피로 손상 등가: {analysis['damage_equivalent']:.2e}")
                print(f"  - 히스토그램: {result['histogram_path']}")
            else:
                print(f"\n{data_type.replace('_', ' ').title()} 데이터: 사이클 없음")

        return {
            "file_path": file_path,
            "file_name": file_name,
            "results": results,
            "success": True,
        }

    except Exception as e:
        print(f"파일 {file_path} 분석 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return {
            "file_path": file_path,
            "file_name": file_name,
            "error": str(e),
            "success": False,
        }


def compare_fatigue_results(
    all_results: List[Dict[str, Any]], output_dir: Optional[Path] = None
) -> None:
    """
    여러 파일의 피로 손상 결과 비교

    Args:
        all_results: 모든 파일의 분석 결과
        output_dir: 출력 디렉토리
    """
    if output_dir is None:
        output_dir = RESULTS_DIR / "main53_rainflow"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print("피로 손상 결과 비교 분석")
    print(f"{'='*80}")

    # 성공적으로 분석된 결과만 필터링
    successful_results = [r for r in all_results if r["success"]]

    if not successful_results:
        print("비교할 수 있는 성공적인 분석 결과가 없습니다.")
        return

    # 비교 테이블 생성
    comparison_data = []

    for result in successful_results:
        file_name = result["file_name"]

        for data_type in ["original", "low_pass", "high_pass"]:
            if result["results"][data_type]["cycles"]:
                analysis = result["results"][data_type]["analysis"]
                comparison_data.append(
                    {
                        "File": file_name,
                        "Data_Type": data_type.replace("_", " ").title(),
                        "Total_Cycles": analysis["total_cycles"],
                        "Mean_Range": analysis["mean_range"],
                        "Max_Range": analysis["max_range"],
                        "Std_Range": analysis["std_range"],
                        "Damage_Equivalent": analysis["damage_equivalent"],
                    }
                )

    if comparison_data:
        # DataFrame으로 변환하여 출력
        df_comparison = pd.DataFrame(comparison_data)

        print("\n피로 손상 비교 테이블:")
        print("=" * 120)
        print(df_comparison.to_string(index=False, float_format="%.3f"))

        # CSV로 저장
        comparison_path = f"{output_dir}/fatigue_comparison.csv"
        df_comparison.to_csv(comparison_path, index=False)
        print(f"\n비교 결과가 {comparison_path}에 저장되었습니다.")

        # 요약 통계
        print(f"\n{'='*60}")
        print("요약 통계")
        print(f"{'='*60}")

        for data_type in ["Original", "Low Pass", "High Pass"]:
            subset = df_comparison[df_comparison["Data_Type"] == data_type]
            if not subset.empty:
                print(f"\n{data_type} 데이터:")
                print(f"  - 평균 사이클 수: {subset['Total_Cycles'].mean():.1f}")
                print(f"  - 평균 범위: {subset['Mean_Range'].mean():.3f}")
                print(f"  - 평균 피로 손상: {subset['Damage_Equivalent'].mean():.2e}")


def main() -> None:
    """메인 실행 함수"""
    setup_korean_font()  # 한글 폰트 설정
    print("피로 손상 계산 프로그램")
    print("Rain Flow Counting을 이용한 피로 해석")
    print("=" * 80)

    # 데이터 파일 경로
    data_files = PRESSURE_DATA_FILES

    # 결과 저장 디렉토리 생성
    output_dir = RESULTS_DIR / "main53_rainflow"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    all_results = []

    # 각 파일 분석
    for file_path in data_files:
        if Path(file_path).exists():
            result = analyze_file_fatigue(str(file_path), output_dir)
            all_results.append(result)
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
    compare_fatigue_results(all_results, output_dir)

    # 최종 요약
    successful_count = sum(1 for r in all_results if r["success"])
    total_count = len(all_results)

    print(f"\n{'='*80}")
    print("피로 손상 분석 완료")
    print(f"{'='*80}")
    print(f"총 파일 수: {total_count}")
    print(f"성공적으로 분석된 파일 수: {successful_count}")
    print(f"실패한 파일 수: {total_count - successful_count}")

    if successful_count > 0:
        print("\n생성된 결과 파일들:")
        print(f"  - Rain Flow Counting 히스토그램들이 {output_dir}/ 디렉토리에 저장됨")
        print(f"  - 비교 분석 결과: {output_dir}/fatigue_comparison.csv")
        print("\n각 히스토그램은 다음 정보를 포함합니다:")
        print("  1. 사이클 범위 분포")
        print("  2. 가중 사이클 범위 분포 (사이클 수 고려)")
        print("  3. 사이클 평균값 분포")
        print("  4. 범위 vs 평균값 산점도")


if __name__ == "__main__":
    main()