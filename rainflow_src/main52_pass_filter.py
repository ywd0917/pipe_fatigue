"""
Pass Filter 적용 및 시각화 스크립트
- find_freq.py에서 찾은 V자 최저점을 기준으로 저대역/고대역 성분 분리
- 하나의 그래프에 4개 서브플롯으로 표시:
  (1) 원본 데이터
  (2) Low Pass 필터 결과 (저대역)
  (3) High Pass 필터 결과 (고대역)
  (4) Low Pass + High Pass 합성 결과
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Any, Optional

# 한글 폰트 설정 및 유틸리티 함수 import
from common.korean_font_utils import setup_korean_font
from utils import interpolate_nan_values
from pass_filter import (
    pass_filter,
    VALLEY_PERIOD,
    VALLEY_FREQ,
    LOW_PASS_MARGIN,
    HIGH_PASS_MARGIN,
)
from common.config import (
    PRESSURE_DATA_FILES,
    RESULTS_DIR,
)


def create_pass_filter_visualization(
    data: np.ndarray,
    low_pass: np.ndarray,
    high_pass: np.ndarray,
    combined: np.ndarray,
    file_name: str,
    output_dir: Optional[Path] = None,
) -> str:
    """
    하나의 그래프에 4개 라인을 겹쳐서 시각화
    (1) 원본 데이터
    (2) 저대역 성분 (Low Pass 필터)
    (3) 고대역 성분 (High Pass 필터)
    (4) 저대역 + 고대역 합성 결과
    """
    if output_dir is None:
        output_dir = RESULTS_DIR / "main52"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.ioff()

    # 동적으로 시각화 범위 설정
    total_len = len(data)
    start_idx = min(10000, int(total_len * 0.2))  # 전체의 20% 지점 또는 10000
    end_idx = min(start_idx + 1000, total_len)  # 1000개 데이터 또는 끝까지

    # 데이터가 충분하지 않은 경우 처리
    if start_idx >= total_len:
        start_idx = max(0, total_len - 1000)
        end_idx = total_len

    data_slice = data[start_idx:end_idx]
    low_pass_slice = low_pass[start_idx:end_idx]
    high_pass_slice = high_pass[start_idx:end_idx]
    combined_slice = combined[start_idx:end_idx]

    n_points = len(data_slice)
    time_minutes = (
        np.arange(start_idx, start_idx + n_points) * 5
    )  # 5분 간격을 분 단위로 표시

    # 하나의 그래프에 4개 라인 겹쳐서 표시
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))

    # 4개 라인 플롯
    ax.plot(
        time_minutes, data_slice, "k-", linewidth=2, alpha=0.8, label="(1) 원본 데이터"
    )
    ax.plot(
        time_minutes,
        low_pass_slice,
        "r-",
        linewidth=2,
        alpha=0.8,
        label="(2) 저대역 성분 (Low Pass)",
    )
    ax.plot(
        time_minutes,
        high_pass_slice,
        "b-",
        linewidth=2,
        alpha=0.8,
        label="(3) 고대역 성분 (High Pass)",
    )
    ax.plot(
        time_minutes,
        combined_slice,
        "g--",
        linewidth=2,
        alpha=0.8,
        label="(4) 합성 신호 (2+3)",
    )

    # 그래프 설정
    ax.set_title(
        f"V자 최저점 기준 Pass Filter 분석 결과 - {file_name}",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_xlabel("시간 (분)", fontsize=12)
    ax.set_ylabel("압력", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc="upper right")
    ax.set_xlim(time_minutes[0], time_minutes[-1])

    # 통계 정보 텍스트 박스
    stats_text = f"""통계 정보 (전체 데이터):
원본: 평균={np.mean(data):.3f}, 표준편차={np.std(data):.3f}
저대역: 평균={np.mean(low_pass):.3f}, 표준편차={np.std(low_pass):.3f}
고대역: 평균={np.mean(high_pass):.3f}, 표준편차={np.std(high_pass):.3f}
합성: 평균={np.mean(combined):.3f}, 표준편차={np.std(combined):.3f}
V자 최저점: {VALLEY_PERIOD:.1f}분 주기"""

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        fontsize=9,
    )

    # 레이아웃 조정
    plt.tight_layout()

    # 파일명에서 확장자 제거하고 저장
    base_name = Path(file_name).stem
    output_path = f"{output_dir}/valley_based_filter_{base_name}.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"V자 최저점 기준 Pass Filter 시각화가 {output_path}에 저장되었습니다.")

    return output_path


def analyze_file(file_path: str) -> Dict[str, Any]:
    """파일별 Pass Filter 분석 및 시각화"""
    print(f"\n{'='*60}")
    print(f"파일 분석 시작: {file_path}")
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

    # 합성 신호 계산 (저대역 + 고대역)
    combined = low_pass + high_pass

    # 시각화 생성
    file_name = Path(file_path).name
    output_path = create_pass_filter_visualization(
        pressure_data, low_pass, high_pass, combined, file_name
    )

    # 결과 요약
    print(f"\n{'='*40}")
    print("분석 결과 요약")
    print(f"{'='*40}")
    print("원본 신호:")
    print(f"  - 평균: {np.mean(pressure_data):.4f}")
    print(f"  - 표준편차: {np.std(pressure_data):.4f}")
    print(f"  - 범위: {np.min(pressure_data):.4f} ~ {np.max(pressure_data):.4f}")

    print(f"저대역 성분 (V자 최저점 {VALLEY_PERIOD:.1f}분 이하):")
    print(f"  - 평균: {np.mean(low_pass):.4f}")
    print(f"  - 표준편차: {np.std(low_pass):.4f}")
    print(f"  - 원본 대비 에너지: {(np.var(low_pass)/np.var(pressure_data)*100):.1f}%")

    print(f"고대역 성분 (V자 최저점 {VALLEY_PERIOD:.1f}분 이상):")
    print(f"  - 평균: {np.mean(high_pass):.4f}")
    print(f"  - 표준편차: {np.std(high_pass):.4f}")
    print(f"  - 원본 대비 에너지: {(np.var(high_pass)/np.var(pressure_data)*100):.1f}%")

    print("합성 신호:")
    print(f"  - 평균: {np.mean(combined):.4f}")
    print(f"  - 표준편차: {np.std(combined):.4f}")
    print(f"  - 원본과의 상관계수: {np.corrcoef(pressure_data, combined)[0,1]:.4f}")

    return {
        "file_path": file_path,
        "original": pressure_data,
        "low_pass": low_pass,
        "high_pass": high_pass,
        "combined": combined,
        "output_path": output_path,
    }


def main() -> None:
    """메인 실행 함수"""
    setup_korean_font()  # 한글 폰트 설정
    print("Pass Filter 적용 및 시각화 프로그램")
    print("find_freq.py 분석 결과 기반 필터 적용")
    print("=" * 60)

    # 데이터 파일 경로
    data_files = PRESSURE_DATA_FILES

    results = []

    # 각 파일 분석
    for file_path in data_files:
        if Path(file_path).exists():
            try:
                result = analyze_file(str(file_path))
                results.append(result)
            except Exception as e:
                print(f"파일 {file_path} 분석 중 오류 발생: {e}")
                import traceback

                traceback.print_exc()
        else:
            print(f"파일을 찾을 수 없습니다: {file_path}")

    # 전체 결과 요약
    if results:
        print(f"\n{'='*60}")
        print("전체 처리 결과 요약")
        print(f"{'='*60}")

        for result in results:
            file_name = Path(result["file_path"]).name
            print(f"\n파일: {file_name}")
            print(f"  시각화 저장: {result['output_path']}")

            # 에너지 분포 분석
            orig_var = np.var(result["original"])
            low_var = np.var(result["low_pass"])
            high_var = np.var(result["high_pass"])

            print("  에너지 분포:")
            print(
                f"    - 저대역 성분 ({VALLEY_PERIOD:.1f}분 이하): {(low_var/orig_var*100):.1f}%"
            )
            print(
                f"    - 고대역 성분 ({VALLEY_PERIOD:.1f}분 이상): {(high_var/orig_var*100):.1f}%"
            )

            # 에너지 보존율 계산 및 검증
            conservation_rate = (low_var + high_var) / orig_var * 100
            print(f"    - 총 보존율: {conservation_rate:.1f}%")

            # 에너지 보존율이 95% 미만이면 경고
            if conservation_rate < 95.0:
                print(
                    f"    ⚠️  경고: 에너지 보존율이 {conservation_rate:.1f}%로 낮습니다."
                )
                print("       필터 설계를 재검토해야 할 수 있습니다.")
            elif conservation_rate > 105.0:
                print(
                    f"    ⚠️  경고: 에너지 보존율이 {conservation_rate:.1f}%로 높습니다."
                )
                print("       신호 중복이 발생했을 수 있습니다.")

        print(f"\n{'='*40}")
        print("V자 최저점 기준 Pass 필터 설정 정보")
        print(f"{'='*40}")
        print("통합된 V자 최저점 설정:")
        print(f"  - V자 최저점: {VALLEY_FREQ:.6f} Hz ({VALLEY_PERIOD:.1f}분 주기)")
        print(f"  - 저대역 차단: {VALLEY_FREQ * LOW_PASS_MARGIN:.6f} Hz (Low Pass)")
        print(f"  - 고대역 차단: {VALLEY_FREQ * HIGH_PASS_MARGIN:.6f} Hz (High Pass)")
        print("필터 설계 원리:")
        print(f"  - 저대역: V자 최저점의 {int(LOW_PASS_MARGIN*100)}% 이하 주파수 통과")
        print(f"  - 고대역: V자 최저점의 {int(HIGH_PASS_MARGIN*100)}% 이상 주파수 통과")

        print("\n생성된 이미지들을 확인하여 V자 최저점 기준 필터 효과를 검토하세요.")


if __name__ == "__main__":
    main()
