"""
Rain Flow Counting 알고리즘 구현
- 피로 해석을 위한 사이클 카운팅 방법
- ASTM E1049 표준을 기반으로 구현
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Any
from pathlib import Path
from common.korean_font_utils import setup_korean_font


def find_peaks_and_valleys(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    데이터에서 모든 방향 전환점(피크와 밸리)을 찾는 함수.
    아주 작은 변화도 감지하며, ASTM E1049 표준에 따라 연속된 동일 값을 처리합니다.

    Args:
        data: 입력 시계열 데이터

    Returns:
        Tuple[np.ndarray, np.ndarray]: (인덱스, 값) 튜플. 방향 전환점의 시퀀스.
    """
    # 1. 데이터가 너무 짧은 경우 처리
    if len(data) < 3:
        # 원본 데이터의 인덱스와 값을 그대로 반환
        return np.arange(len(data)), data

    # 2. 연속된 중복 값 제거 (피로 해석의 표준 전처리)
    # 예: [0, 5, 5, 2] -> [0, 5, 2]
    # 이렇게 하면 평탄한 구간(plateau)을 효과적으로 처리할 수 있습니다.
    unique_indices = [0]
    unique_values = [data[0]]
    for i in range(1, len(data)):
        if data[i] != unique_values[-1]:
            unique_indices.append(i)
            unique_values.append(data[i])

    # 모든 값이 동일하거나 2개 이하의 유니크한 값만 남은 경우,
    # 원본 데이터의 시작과 끝점만 반환
    if len(unique_values) < 3:
        return np.array([0, len(data) - 1]), np.array([data[0], data[-1]])

    # 3. 방향 전환점(turning points) 찾기
    # 첫 점은 항상 전환점입니다.
    turning_point_indices = [unique_indices[0]]
    turning_point_values = [unique_values[0]]

    # 중간점들에 대해 피크 또는 밸리인지 확인
    for i in range(1, len(unique_values) - 1):
        y_prev, y_curr, y_next = (
            unique_values[i - 1],
            unique_values[i],
            unique_values[i + 1],
        )

        # 피크: 현재 값이 양쪽 값보다 큼
        is_peak = (y_curr > y_prev) and (y_curr > y_next)
        # 밸리: 현재 값이 양쪽 값보다 작음
        is_valley = (y_curr < y_prev) and (y_curr < y_next)

        if is_peak or is_valley:
            turning_point_indices.append(unique_indices[i])
            turning_point_values.append(y_curr)

    # 마지막 점은 항상 전환점입니다.
    turning_point_indices.append(unique_indices[-1])
    turning_point_values.append(unique_values[-1])

    return np.array(turning_point_indices), np.array(turning_point_values)


def rain_flow_counting(data: np.ndarray) -> List[Tuple[float, float, float]]:
    """
    Rain Flow Counting 알고리즘 구현

    Args:
        data: 입력 시계열 데이터

    Returns:
        List[Tuple[float, float, int]]: [(범위, 평균, 사이클 수)] 리스트
    """
    # 피크와 밸리 찾기
    indices, values = find_peaks_and_valleys(data)

    if len(values) < 3:
        return []

    # Rain Flow 알고리즘 구현
    cycles = []
    residue = list(values)  # 잔여 피크/밸리 리스트

    while len(residue) >= 3:
        # 연속된 3개 점 검사
        for i in range(len(residue) - 2):
            Y1, Y2, Y3 = residue[i], residue[i + 1], residue[i + 2]

            # Rain Flow 조건 확인
            # 조건: |Y2-Y1| <= |Y3-Y2|이고, Y1과 Y3가 Y2를 기준으로 같은 방향에 있지 않음
            range1 = abs(Y2 - Y1)
            range2 = abs(Y3 - Y2)

            if range1 <= range2:
                # 사이클 발견
                cycle_range = range1
                cycle_mean = (Y1 + Y2) / 2

                # 전체 사이클 (1.0) 또는 반 사이클 (0.5) 결정
                if i == 0 or i == len(residue) - 3:
                    cycle_count = 0.5  # 반 사이클
                else:
                    cycle_count = 1.0  # 전체 사이클

                cycles.append((cycle_range, cycle_mean, cycle_count))

                # 사용된 점들 제거
                residue.pop(i + 1)  # Y2 제거
                break
        else:
            # 더 이상 사이클을 찾을 수 없음
            break

    # 잔여 점들로부터 반 사이클 추출
    for i in range(len(residue) - 1):
        cycle_range = abs(residue[i + 1] - residue[i])
        cycle_mean = (residue[i] + residue[i + 1]) / 2
        cycles.append((cycle_range, cycle_mean, 0.5))

    return cycles


def create_rainflow_histogram(
    cycles: List[Tuple[float, float, float]],
    title: str,
    output_path: str,
    bins: int = 20,
) -> str:
    """
    Rain Flow Counting 결과를 히스토그램으로 시각화

    Args:
        cycles: Rain Flow Counting 결과
        title: 그래프 제목
        output_path: 저장 경로
        bins: 히스토그램 구간 수

    Returns:
        str: 저장된 파일 경로
    """
    if not cycles:
        print(f"사이클 데이터가 없어 히스토그램을 생성할 수 없습니다: {title}")
        return ""

    # 한글 폰트 설정
    setup_korean_font()

    # 사이클 데이터 추출
    ranges = [cycle[0] for cycle in cycles]
    means = [cycle[1] for cycle in cycles]
    counts = [cycle[2] for cycle in cycles]

    # 가중 범위 (사이클 수 고려)
    weighted_ranges = []
    for range_val, count in zip(ranges, counts):
        weighted_ranges.extend([range_val] * int(count * 2))  # 0.5 사이클도 고려

    plt.ioff()
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

    # 1. 범위 히스토그램
    ax1.hist(ranges, bins=bins, alpha=0.7, color="blue", edgecolor="black")
    ax1.set_title("사이클 범위 분포", fontsize=12, fontweight="bold")
    ax1.set_xlabel("범위 (Range)")
    ax1.set_ylabel("빈도수")
    ax1.grid(True, alpha=0.3)

    # 2. 가중 범위 히스토그램 (사이클 수 고려)
    if weighted_ranges:
        ax2.hist(weighted_ranges, bins=bins, alpha=0.7, color="red", edgecolor="black")
    ax2.set_title(
        "가중 사이클 범위 분포 (사이클 수 고려)", fontsize=12, fontweight="bold"
    )
    ax2.set_xlabel("범위 (Range)")
    ax2.set_ylabel("가중 빈도수")
    ax2.grid(True, alpha=0.3)

    # 3. 평균값 분포
    ax3.hist(means, bins=bins, alpha=0.7, color="green", edgecolor="black")
    ax3.set_title("사이클 평균값 분포", fontsize=12, fontweight="bold")
    ax3.set_xlabel("평균값 (Mean)")
    ax3.set_ylabel("빈도수")
    ax3.grid(True, alpha=0.3)

    # 4. 범위 vs 평균 산점도
    scatter_colors = ["red" if c == 1.0 else "blue" for c in counts]
    scatter_sizes = [50 if c == 1.0 else 25 for c in counts]
    ax4.scatter(means, ranges, c=scatter_colors, s=scatter_sizes, alpha=0.6)
    ax4.set_title("사이클 범위 vs 평균값", fontsize=12, fontweight="bold")
    ax4.set_xlabel("평균값 (Mean)")
    ax4.set_ylabel("범위 (Range)")
    ax4.grid(True, alpha=0.3)

    # 범례 추가
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="red", alpha=0.6, label="전체 사이클 (1.0)"),
        Patch(facecolor="blue", alpha=0.6, label="반 사이클 (0.5)"),
    ]
    ax4.legend(handles=legend_elements, loc="upper right")

    # 전체 제목
    fig.suptitle(
        f"Rain Flow Counting 분석 결과 - {title}", fontsize=16, fontweight="bold"
    )

    # 통계 정보 텍스트
    total_cycles = sum(counts)
    full_cycles = sum(1 for c in counts if c == 1.0)
    half_cycles = sum(1 for c in counts if c == 0.5)

    stats_text = f"""통계 정보:
총 사이클 수: {total_cycles:.1f}
전체 사이클: {full_cycles}개
반 사이클: {half_cycles}개
평균 범위: {np.mean(ranges):.3f}
최대 범위: {np.max(ranges):.3f}
표준편차: {np.std(ranges):.3f}"""

    fig.text(
        0.02,
        0.02,
        stats_text,
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    plt.tight_layout()
    plt.subplots_adjust(top=0.93, bottom=0.15)

    # 디렉토리 생성 (존재하지 않는 경우)
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 저장
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Rain Flow Counting 히스토그램이 {output_path}에 저장되었습니다.")
    print(f"  - 총 사이클 수: {total_cycles:.1f}")
    print(f"  - 전체 사이클: {full_cycles}개, 반 사이클: {half_cycles}개")
    print(f"  - 평균 범위: {np.mean(ranges):.3f}")

    return output_path


def create_cumulative_rainflow_plot(
    data: np.ndarray,
    cycles: List[Tuple[float, float, float]],
    title: str,
    output_path: str,
    sampling_interval_minutes: float = 5.0,
) -> str:
    """
    누적 Rain Flow Count를 시간에 따라 시각화

    Args:
        data: 원본 시계열 데이터
        cycles: Rain Flow Counting 결과
        title: 그래프 제목
        output_path: 저장 경로
        sampling_interval_minutes: 샘플링 간격 (분)

    Returns:
        str: 저장된 파일 경로
    """
    if not cycles:
        print(f"사이클 데이터가 없어 누적 그래프를 생성할 수 없습니다: {title}")
        return ""

    # 한글 폰트 설정
    setup_korean_font()

    # 피크와 밸리 찾기 (사이클 발생 시점 추정을 위해)
    indices, values = find_peaks_and_valleys(data)

    if len(indices) == 0:
        print(f"피크/밸리를 찾을 수 없어 누적 그래프를 생성할 수 없습니다: {title}")
        return ""

    # 시간 축 생성 (일 단위로 변환)
    total_time_minutes = len(data) * sampling_interval_minutes
    total_time_days = total_time_minutes / (60 * 24)  # 일 단위로 변환

    print(f"  데이터 기간: {total_time_days:.1f}일 ({total_time_minutes/60:.1f}시간)")

    # 사이클 발생 시점 추정 (피크/밸리 인덱스 기반)
    cycle_times = []
    cycle_counts = []

    # 각 사이클에 대해 대략적인 발생 시점 계산
    peak_valley_times = indices * sampling_interval_minutes

    # 사이클을 시간 순서대로 분배 (단순화된 접근)
    if len(peak_valley_times) > 2:
        # 피크/밸리 사이의 시간 간격을 기반으로 사이클 시점 추정
        for i, (cycle_range, cycle_mean, cycle_count) in enumerate(cycles):
            # 사이클 발생 시점을 전체 시간에 균등 분배 (일 단위)
            estimated_time_days = (i + 1) * total_time_days / len(cycles)
            cycle_times.append(estimated_time_days)
            cycle_counts.append(cycle_count)
    else:
        # 피크/밸리가 부족한 경우 균등 분배
        for i, (cycle_range, cycle_mean, cycle_count) in enumerate(cycles):
            estimated_time_days = (i + 1) * total_time_days / len(cycles)
            cycle_times.append(estimated_time_days)
            cycle_counts.append(cycle_count)

    # 누적 사이클 수 계산
    cumulative_counts = np.cumsum(cycle_counts)

    # 시간 축을 0부터 시작하도록 조정 (일 단위)
    cycle_times_array = np.array([0] + cycle_times)
    cumulative_counts = np.array([0] + list(cumulative_counts))

    plt.ioff()
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # 누적 사이클 수 플롯
    if len(cycle_times) <= 10:  # 사이클이 적은 경우 더 큰 마커 사용
        ax.plot(
            cycle_times_array,
            cumulative_counts,
            "b-",
            linewidth=3,
            marker="o",
            markersize=8,
            alpha=0.8,
            label="누적 Rain Flow Count",
        )
        # 각 점에 값 표시
        for i, (x, y) in enumerate(zip(cycle_times_array, cumulative_counts)):
            if i > 0:  # 시작점(0,0) 제외
                ax.annotate(
                    f"{y:.1f}",
                    (x, y),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=10,
                )
    else:
        ax.plot(
            cycle_times_array,
            cumulative_counts,
            "b-",
            linewidth=2,
            marker="o",
            markersize=4,
            alpha=0.8,
            label="누적 Rain Flow Count",
        )

    # 그래프 설정
    ax.set_title(f"누적 Rain Flow Count - {title}", fontsize=16, fontweight="bold")
    ax.set_xlabel("시간 (일)", fontsize=12)
    ax.set_ylabel("누적 사이클 수", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # 통계 정보 텍스트 박스
    total_cycles = cumulative_counts[-1] if len(cumulative_counts) > 0 else 0
    total_time_hours = total_time_minutes / 60
    avg_cycle_rate_per_day = (
        total_cycles / total_time_days if total_time_days > 0 else 0
    )

    stats_text = f"""통계 정보:
총 사이클 수: {total_cycles:.1f}
총 기간: {total_time_days:.1f}일 ({total_time_hours:.0f}시간)
평균 사이클 발생률: {avg_cycle_rate_per_day:.1f} 사이클/일
데이터 포인트: {len(data)}개
샘플링 간격: {sampling_interval_minutes}분"""

    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
        fontsize=10,
    )

    # 레이아웃 조정
    plt.tight_layout()

    # 디렉토리 생성 (존재하지 않는 경우)
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 저장
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"누적 Rain Flow Count 그래프가 {output_path}에 저장되었습니다.")
    print(f"  - 총 사이클 수: {total_cycles:.1f}")
    print(f"  - 평균 사이클 발생률: {avg_cycle_rate_per_day:.1f} 사이클/일")

    return output_path


def analyze_rainflow_cycles(cycles: List[Tuple[float, float, float]]) -> Dict[str, Any]:
    """
    Rain Flow Counting 결과 분석

    Args:
        cycles: Rain Flow Counting 결과

    Returns:
        Dict[str, Any]: 분석 결과 딕셔너리
    """
    if not cycles:
        return {
            "total_cycles": 0,
            "full_cycles": 0,
            "half_cycles": 0,
            "mean_range": 0,
            "max_range": 0,
            "std_range": 0,
            "damage_equivalent": 0,
        }

    ranges = [cycle[0] for cycle in cycles]
    means = [cycle[1] for cycle in cycles]
    counts = [cycle[2] for cycle in cycles]

    total_cycles = sum(counts)
    full_cycles = sum(1 for c in counts if c == 1.0)
    half_cycles = sum(1 for c in counts if c == 0.5)

    # 피로 손상 등가 계산 (Miner's rule, m=3 가정)
    m = 3  # 피로 지수
    damage_equivalent = sum(count * (range_val**m) for range_val, _, count in cycles)

    return {
        "total_cycles": total_cycles,
        "full_cycles": full_cycles,
        "half_cycles": half_cycles,
        "mean_range": np.mean(ranges),
        "max_range": np.max(ranges),
        "std_range": np.std(ranges),
        "damage_equivalent": damage_equivalent,
        "ranges": ranges,
        "means": means,
        "counts": counts,
    }