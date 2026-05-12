"""
파형 성분 분리를 위한 필터 주파수 탐색 스크립트
- 주된 두 개의 파형 성분 추출을 목적
- 파워 스펙트럼 피크 분석 기반
- Band Pass Filter 설계를 위한 주파수 결정
"""

import pandas as pd
import numpy as np
from numpy.typing import NDArray
from scipy import signal
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.axes import Axes
from pathlib import Path
from typing import Optional, Tuple, Union

# analysis_base에서 공통 타입 및 함수 import
from analysis_base import (
    AnalysisResult,
    FilterComponent,
    FilterDesign,
    FileAnalysisResult,
    analyze_dominant_frequencies,
)

# 한글 폰트 설정 및 유틸리티 함수 import
from common.korean_font_utils import setup_korean_font
from utils import interpolate_nan_values
from common.config import (
    PRESSURE_DATA_FILES,
    RESULTS_DIR,
)


def design_component_separation_filters(
    analysis_result: Optional[AnalysisResult], sampling_rate: float
) -> Optional[FilterDesign]:
    """
    두 개의 주요 성분을 분리하기 위한 필터 설계
    """
    print("성분 분리 필터 설계 중...")

    if not analysis_result or len(analysis_result.dominant_peaks) < 2:
        print("두 개의 주된 성분을 찾을 수 없어 필터 설계를 건너뜁니다.")
        return None

    nyquist = sampling_rate / 2
    peak1 = analysis_result.dominant_peaks[0]  # 가장 강한 성분
    peak2 = analysis_result.dominant_peaks[1]  # 두 번째 강한 성분

    # 주파수 순서로 정렬 (낮은 주파수가 먼저)
    if peak1.frequency > peak2.frequency:
        peak1, peak2 = peak2, peak1

    low_freq = peak1.frequency  # 저주파 성분
    high_freq = peak2.frequency  # 고주파 성분

    print(f"저대역 성분 (낮은 주파수): {low_freq:.6f} Hz ({1/low_freq/60:.1f}분 주기)")
    print(
        f"고대역 성분 (높은 주파수): {high_freq:.6f} Hz ({1/high_freq/60:.1f}분 주기)"
    )

    # 필터 설계를 위한 차단 주파수 계산
    freq_gap = high_freq - low_freq

    # 성분 1 추출용 Low Pass Filter (저주파 성분)
    # 두 성분 사이의 중간점보다 약간 높게 설정
    component1_cutoff = low_freq + freq_gap * 0.6

    # 성분 2 추출용 High Pass Filter (고주파 성분)
    # 두 성분 사이의 중간점보다 약간 낮게 설정
    component2_cutoff = low_freq + freq_gap * 0.4

    # Nyquist 주파수 제한 확인
    component1_cutoff = min(component1_cutoff, nyquist * 0.95)
    component2_cutoff = min(component2_cutoff, nyquist * 0.95)

    filter_design = FilterDesign(
        low_freq_component=FilterComponent(
            target_freq=low_freq,
            target_period_min=1 / low_freq / 60,
            filter_type="low_pass",
            cutoff_freq=component1_cutoff,
            cutoff_period_min=1 / component1_cutoff / 60,
        ),
        high_freq_component=FilterComponent(
            target_freq=high_freq,
            target_period_min=1 / high_freq / 60,
            filter_type="high_pass",
            cutoff_freq=component2_cutoff,
            cutoff_period_min=1 / component2_cutoff / 60,
        ),
    )

    print("\n필터 설계 결과:")
    print(
        f"성분 1 추출 (저주파): Low Pass {component1_cutoff:.6f} Hz ({1/component1_cutoff/60:.1f}분 차단)"
    )
    print(
        f"성분 2 추출 (고주파): High Pass {component2_cutoff:.6f} Hz ({1/component2_cutoff/60:.1f}분 차단)"
    )

    return filter_design


def apply_component_filters(
    data: NDArray[np.float64],
    filter_design: Optional[FilterDesign],
    sampling_rate: float,
) -> Tuple[Optional[NDArray[np.float64]], Optional[NDArray[np.float64]]]:
    """
    설계된 필터를 적용하여 성분 분리
    """
    if not filter_design:
        return None, None

    nyquist = sampling_rate / 2

    # 성분 1 추출 (Low Pass)
    cutoff1 = filter_design.low_freq_component.cutoff_freq
    b1, a1 = signal.butter(4, cutoff1 / nyquist, btype="low")
    component1 = signal.filtfilt(b1, a1, data)

    # 성분 2 추출 (High Pass)
    cutoff2 = filter_design.high_freq_component.cutoff_freq
    b2, a2 = signal.butter(4, cutoff2 / nyquist, btype="high")
    component2 = signal.filtfilt(b2, a2, data)

    print("성분 분리 완료:")
    print(f"  성분 1 (저대역) 표준편차: {np.std(component1):.4f}")
    print(f"  성분 2 (고대역) 표준편차: {np.std(component2):.4f}")

    return component1, component2


def add_vertical_lines_to_plot(
    ax: Axes,
    analysis_result: Optional[AnalysisResult],
    max_freq: Optional[float] = None,
    show_freq_in_label: bool = True,
) -> None:
    """그래프에 주요 피크와 최소값 세로선 추가"""
    if not analysis_result:
        return

    # 주요 피크 표시
    if analysis_result.dominant_peaks:
        for i, peak in enumerate(analysis_result.dominant_peaks):
            if max_freq is None or peak.frequency <= max_freq:
                color = "red" if i == 0 else "orange"
                if show_freq_in_label:
                    label = f"성분 {i+1}: {peak.frequency:.6f} Hz ({peak.period_minutes:.1f}분)"
                else:
                    label = f"성분 {i+1}: {peak.period_minutes:.1f}분 주기"

                ax.axvline(
                    peak.frequency,
                    color=color,
                    linestyle="--",
                    linewidth=2,
                    label=label,
                )

    # 최소값 표시
    if analysis_result.min_valley_right:
        min_valley = analysis_result.min_valley_right
        if max_freq is None or min_valley["frequency"] <= max_freq:
            if show_freq_in_label:
                label = f'최소값: {min_valley["frequency"]:.6f} Hz ({min_valley["period_minutes"]:.1f}분)'
            else:
                label = f'최소값: {min_valley["period_minutes"]:.1f}분 주기'

            ax.axvline(
                min_valley["frequency"],
                color="green",
                linestyle=":",
                linewidth=2,
                label=label,
            )


def setup_plot_formatting(
    ax: Axes,
    title: str,
    xlabel: str = "Frequency (Hz)",
    ylabel: str = "Power Spectral Density",
) -> None:
    """그래프 기본 포맷팅 설정"""
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)


def plot_frequency_spectrum(
    frequencies: NDArray[np.float64],
    psd: NDArray[np.float64],
    analysis_result: Optional[AnalysisResult],
    filter_design: Optional[FilterDesign],
    file_name: str,
    output_dir: Optional[Path] = None,
) -> str:
    """
    주파수 스펙트럼 그래프를 개별 파일로 저장
    """
    # 한글 폰트 및 matplotlib 설정
    setup_korean_font()
    matplotlib.rcParams['axes.unicode_minus'] = False
    
    if output_dir is None:
        output_dir = RESULTS_DIR / "main51"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.ioff()

    # 주파수 스펙트럼 전용 그래프
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 1. 로그 스케일 파워 스펙트럼
    axes[0].loglog(frequencies[1:], psd[1:], "b-", alpha=0.7, linewidth=1.5)
    add_vertical_lines_to_plot(axes[0], analysis_result, show_freq_in_label=True)
    setup_plot_formatting(axes[0], "Power Spectrum (Log Scale)")

    # 2. 선형 스케일 파워 스펙트럼 (저주파 영역)
    max_freq_plot = 0.0002  # 0.0002 Hz까지만 표시 (약 83분 주기)
    freq_mask = frequencies <= max_freq_plot

    axes[1].plot(frequencies[freq_mask], psd[freq_mask], "b-", alpha=0.7, linewidth=1.5)
    add_vertical_lines_to_plot(
        axes[1], analysis_result, max_freq=max_freq_plot, show_freq_in_label=False
    )
    setup_plot_formatting(
        axes[1], "Power Spectrum - Low Frequency Region (Linear Scale)"
    )

    # 전체 제목
    fig.suptitle(
        f"Frequency Spectrum Analysis - {file_name}", fontsize=16, fontweight="bold"
    )

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)

    # 파일명에서 확장자 제거하고 저장
    base_name = Path(file_name).stem
    spectrum_output = f"{output_dir}/frequency_spectrum_{base_name}.png"
    plt.savefig(spectrum_output, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"주파수 스펙트럼이 {spectrum_output}에 저장되었습니다.")
    return spectrum_output


def plot_component_analysis(
    data: NDArray[np.float64],
    sampling_rate: float,
    analysis_result: Optional[AnalysisResult],
    frequencies: NDArray[np.float64],
    psd: NDArray[np.float64],
    filter_design: Optional[FilterDesign],
    component1: Optional[NDArray[np.float64]],
    component2: Optional[NDArray[np.float64]],
    output_dir: Optional[Path] = None,
) -> None:
    """
    성분 분석 결과 시각화
    """
    # 한글 폰트 및 matplotlib 설정
    setup_korean_font()
    matplotlib.rcParams['axes.unicode_minus'] = False

    if output_dir is None:
        output_dir = RESULTS_DIR / "main51"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.ioff()

    fig, axes = plt.subplots(3, 2, figsize=(16, 14))

    # 1. 파워 스펙트럼과 주요 피크
    axes[0, 0].loglog(frequencies[1:], psd[1:], "b-", alpha=0.7)

    if analysis_result and analysis_result.dominant_peaks:
        for i, peak in enumerate(analysis_result.dominant_peaks):
            color = "red" if i == 0 else "orange"
            axes[0, 0].axvline(
                peak.frequency,
                color=color,
                linestyle="--",
                label=f"성분 {i+1}: {peak.frequency:.6f} Hz",
            )

    axes[0, 0].set_xlabel("Frequency (Hz)")
    axes[0, 0].set_ylabel("Power Spectral Density")
    axes[0, 0].set_title("Power Spectrum with Dominant Components")
    axes[0, 0].legend()
    axes[0, 0].grid(True)

    # 2. 선형 스케일 파워 스펙트럼 (저주파 영역)
    max_freq_plot = sampling_rate / 20  # Nyquist의 1/10까지만 표시
    freq_mask = frequencies <= max_freq_plot

    axes[0, 1].plot(frequencies[freq_mask], psd[freq_mask], "b-", alpha=0.7)

    if analysis_result and analysis_result.dominant_peaks:
        for i, peak in enumerate(analysis_result.dominant_peaks):
            if peak.frequency <= max_freq_plot:
                color = "red" if i == 0 else "orange"
                axes[0, 1].axvline(
                    peak.frequency,
                    color=color,
                    linestyle="--",
                    label=f"성분 {i+1}: {peak.period_minutes:.1f}분",
                )

    axes[0, 1].set_xlabel("Frequency (Hz)")
    axes[0, 1].set_ylabel("Power Spectral Density")
    axes[0, 1].set_title("Low Frequency Region (Linear Scale)")
    axes[0, 1].legend()
    axes[0, 1].grid(True)

    # 3. 원본 시계열 (처음 2000개 포인트)
    n_points = min(2000, len(data))
    time_axis = np.arange(n_points) * 5 / 60  # 시간 (시간 단위)

    axes[1, 0].plot(time_axis, data[:n_points], "k-", alpha=0.8, linewidth=1)
    axes[1, 0].set_xlabel("Time (hours)")
    axes[1, 0].set_ylabel("Pressure")
    axes[1, 0].set_title("Original Signal")
    axes[1, 0].grid(True)

    # 4. 분리된 성분들
    if component1 is not None and component2 is not None:
        axes[1, 1].plot(
            time_axis,
            component1[:n_points],
            "r-",
            alpha=0.8,
            label="성분 1 (저대역)",
            linewidth=1,
        )
        axes[1, 1].plot(
            time_axis,
            component2[:n_points],
            "b-",
            alpha=0.8,
            label="성분 2 (고대역)",
            linewidth=1,
        )
        axes[1, 1].set_xlabel("Time (hours)")
        axes[1, 1].set_ylabel("Pressure")
        axes[1, 1].set_title("Separated Components")
        axes[1, 1].legend()
        axes[1, 1].grid(True)
    else:
        axes[1, 1].text(
            0.5,
            0.5,
            "Component separation\nnot available",
            ha="center",
            va="center",
            transform=axes[1, 1].transAxes,
        )
        axes[1, 1].set_title("Separated Components")

    # 5. 성분 1 상세 (저주파)
    if component1 is not None:
        axes[2, 0].plot(time_axis, component1[:n_points], "r-", alpha=0.8, linewidth=1)
        if filter_design:
            period = filter_design.low_freq_component.target_period_min
            axes[2, 0].set_title(f"Component 1 (Low Freq, ~{period:.1f}min period)")
        else:
            axes[2, 0].set_title("Component 1 (Low Frequency)")
        axes[2, 0].set_xlabel("Time (hours)")
        axes[2, 0].set_ylabel("Pressure")
        axes[2, 0].grid(True)
    else:
        axes[2, 0].text(
            0.5,
            0.5,
            "Component 1\nnot available",
            ha="center",
            va="center",
            transform=axes[2, 0].transAxes,
        )

    # 6. 성분 2 상세 (고주파)
    if component2 is not None:
        axes[2, 1].plot(time_axis, component2[:n_points], "b-", alpha=0.8, linewidth=1)
        if filter_design:
            period = filter_design.high_freq_component.target_period_min
            axes[2, 1].set_title(f"Component 2 (High Freq, ~{period:.1f}min period)")
        else:
            axes[2, 1].set_title("Component 2 (High Frequency)")
        axes[2, 1].set_xlabel("Time (hours)")
        axes[2, 1].set_ylabel("Pressure")
        axes[2, 1].grid(True)
    else:
        axes[2, 1].text(
            0.5,
            0.5,
            "Component 2\nnot available",
            ha="center",
            va="center",
            transform=axes[2, 1].transAxes,
        )

    plt.tight_layout()
    plt.savefig(
        f"{output_dir}/component_separation_analysis.png", dpi=300, bbox_inches="tight"
    )
    plt.close()

    print(
        f"성분 분리 분석 그래프가 {output_dir}/component_separation_analysis.png에 저장되었습니다."
    )


def analyze_file(
    file_path: Union[str, Path], interpolation_method: str = "linear"
) -> FileAnalysisResult:
    """파일별 성분 분리 분석"""
    print(f"\n{'='*60}")
    print(f"파일 분석 시작: {file_path}")
    print(f"{'='*60}")

    # 데이터 로드 시 예외 처리
    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"CSV 파일이 비어있습니다: {file_path}")
    except pd.errors.ParserError as e:
        raise pd.errors.ParserError(f"CSV 파일 파싱 실패: {file_path}. 원인: {e!s}")

    # 필수 컬럼 확인
    if "msrmt_dt" not in df.columns:
        raise KeyError(
            f"필수 컬럼 'msrmt_dt'가 없습니다. 사용 가능한 컬럼: {list(df.columns)}"
        )
    if "wtrprsr" not in df.columns:
        raise KeyError(
            f"필수 컬럼 'wtrprsr'이 없습니다. 사용 가능한 컬럼: {list(df.columns)}"
        )

    # 날짜 변환 시 예외 처리
    try:
        df["msrmt_dt"] = pd.to_datetime(df["msrmt_dt"])
    except (ValueError, TypeError) as e:
        raise ValueError(f"날짜 형식 변환 실패: {e!s}")

    df = df.sort_values("msrmt_dt").reset_index(drop=True)

    print(f"원본 데이터 크기: {df.shape}")
    print(f"NaN 개수: {df['wtrprsr'].isna().sum()}")

    # 데이터 검증
    if len(df) == 0:
        raise ValueError("데이터프레임이 비어있습니다")

    if df["wtrprsr"].isna().all():
        raise ValueError("모든 압력 데이터가 NaN입니다")

    # NaN 값 보간
    try:
        pressure_data = interpolate_nan_values(
            np.array(df["wtrprsr"].values),
            pd.DatetimeIndex(df["msrmt_dt"]),
            interpolation_method,
        )
    except Exception as e:
        raise ValueError(f"데이터 보간 중 오류 발생: {e!s}")

    # 샘플링 주파수
    sampling_rate = 1 / 300  # 5분 간격
    print(f"샘플링 주파수: {sampling_rate:.6f} Hz")

    # 주된 주파수 성분 분석
    analysis_result, frequencies, psd = analyze_dominant_frequencies(
        pressure_data, sampling_rate
    )

    # 필터 설계
    filter_design = design_component_separation_filters(analysis_result, sampling_rate)

    # 성분 분리
    component1, component2 = apply_component_filters(
        pressure_data, filter_design, sampling_rate
    )

    # 결과 출력
    print(f"\n{'='*40}")
    print("성분 분리 결과")
    print(f"{'='*40}")

    if filter_design:
        print("필터 설계 성공:")
        print(
            f"  성분 1 추출: Low Pass {filter_design.low_freq_component.cutoff_freq:.6f} Hz"
        )
        print(
            f"    → {filter_design.low_freq_component.target_period_min:.1f}분 주기 성분 추출"
        )
        print(
            f"  성분 2 추출: High Pass {filter_design.high_freq_component.cutoff_freq:.6f} Hz"
        )
        print(
            f"    → {filter_design.high_freq_component.target_period_min:.1f}분 주기 성분 추출"
        )
    else:
        print("필터 설계 실패: 두 개의 주된 성분을 찾을 수 없습니다.")

    # 주파수 스펙트럼 개별 저장
    file_name = Path(file_path).name
    plot_frequency_spectrum(frequencies, psd, analysis_result, filter_design, file_name)

    # 시각화
    plot_component_analysis(
        pressure_data,
        sampling_rate,
        analysis_result,
        frequencies,
        psd,
        filter_design,
        component1,
        component2,
    )

    return {
        "analysis_result": analysis_result,
        "filter_design": filter_design,
        "component1": component1,
        "component2": component2,
    }


def main() -> None:
    """메인 실행 함수"""
    # 한글 폰트 및 matplotlib 설정
    setup_korean_font()
    matplotlib.rcParams['axes.unicode_minus'] = False
    
    print("파형 성분 분리를 위한 필터 주파수 탐색 프로그램")
    print("목적: 주된 두 개의 파형 성분 추출")

    data_files = PRESSURE_DATA_FILES

    all_results = {}

    for file_path in data_files:
        if Path(file_path).exists():
            try:
                result = analyze_file(file_path)
                all_results[file_path] = result
            except FileNotFoundError as e:
                print(f"파일을 찾을 수 없습니다: {file_path}")
                print(f"  오류: {e}")
            except pd.errors.EmptyDataError as e:
                print(f"파일이 비어있습니다: {file_path}")
                print(f"  오류: {e}")
            except pd.errors.ParserError as e:
                print(f"CSV 파일 파싱 오류: {file_path}")
                print(f"  오류: {e}")
            except ValueError as e:
                print(f"데이터 처리 중 값 오류: {file_path}")
                print(f"  오류: {e}")
            except KeyError as e:
                print(f"필수 컬럼을 찾을 수 없습니다: {file_path}")
                print(f"  오류: {e}")
            except Exception as e:
                print(f"예상치 못한 오류 발생: {file_path}")
                print(f"  오류 타입: {type(e).__name__}")
                print(f"  오류 메시지: {e}")
                import traceback

                traceback.print_exc()
        else:
            print(f"파일을 찾을 수 없습니다: {file_path}")

    # 전체 결과 요약
    if all_results:
        print(f"\n{'='*60}")
        print("전체 성분 분리 결과 요약")
        print(f"{'='*60}")

        for file_path, result in all_results.items():
            file_name = Path(file_path).name
            print(f"\n파일: {file_name}")

            if result["filter_design"]:
                fd = result["filter_design"]
                print(
                    f"  성분 1 (저대역): {fd.low_freq_component.target_period_min:.1f}분 주기"
                )
                print(f"    → Low Pass {fd.low_freq_component.cutoff_freq:.6f} Hz 사용")
                print(
                    f"  성분 2 (고대역): {fd.high_freq_component.target_period_min:.1f}분 주기"
                )
                print(
                    f"    → High Pass {fd.high_freq_component.cutoff_freq:.6f} Hz 사용"
                )
            else:
                print("  성분 분리 실패: 두 개의 주된 성분을 찾을 수 없음")

            # 오른쪽 V자 최저점 정보 출력
            if result["analysis_result"] and result["analysis_result"].min_valley_right:
                valley = result["analysis_result"].min_valley_right
                print(
                    f"  오른쪽 V자 최저점: {valley['frequency']:.6f} Hz ({valley['period_minutes']:.1f}분 주기)"
                )
                print(f"    → PSD 값: {valley['psd_value']:.2e}")

        print(f"\n{'='*40}")
        print("사용법 안내")
        print(f"{'='*40}")
        print("1. 성분 1 추출: Low Pass Filter 사용")
        print("2. 성분 2 추출: High Pass Filter 사용")
        print("3. 각 성분을 개별적으로 피로 분석에 적용 가능")
        print("4. 두 성분의 합성 효과 분석도 가능")


if __name__ == "__main__":
    main()
