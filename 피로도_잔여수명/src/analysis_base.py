"""
주파수 분석 기본 모듈
- 공통 데이터 클래스 및 분석 함수 제공
- main51_find_freq.py와 main52_pass_filter.py에서 공통으로 사용
"""

import numpy as np
from numpy.typing import NDArray
from scipy import signal
from typing import Optional, Dict, Tuple, List, TypedDict
from dataclasses import dataclass


# 타입 정의
@dataclass
class PeakInfo:
    frequency: float
    period_minutes: float
    power: float
    prominence: float
    rank: int

    @property
    def period_hours(self) -> float:
        """주기를 시간 단위로 반환"""
        return self.period_minutes / 60

    @property
    def period_seconds(self) -> float:
        """주기를 초 단위로 반환"""
        return self.period_minutes * 60

    @classmethod
    def from_frequency(
        cls, frequency: float, power: float, prominence: float, rank: int
    ) -> "PeakInfo":
        """주파수로부터 PeakInfo 생성"""
        return cls(
            frequency=frequency,
            period_minutes=1 / frequency / 60,
            power=power,
            prominence=prominence,
            rank=rank,
        )

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        return f"Peak {self.rank}: {self.frequency:.6f} Hz ({self.period_minutes:.1f}분 주기)"


@dataclass
class FilterComponent:
    target_freq: float
    target_period_min: float
    filter_type: str
    cutoff_freq: float
    cutoff_period_min: float


@dataclass
class FilterDesign:
    low_freq_component: FilterComponent
    high_freq_component: FilterComponent

    def validate(self) -> bool:
        """필터 설계가 유효한지 검증"""
        # 저대역 필터는 low pass여야 함
        if self.low_freq_component.filter_type != "low_pass":
            return False

        # 고대역 필터는 high pass여야 함
        if self.high_freq_component.filter_type != "high_pass":
            return False

        # cutoff 주파수가 양수여야 함
        if self.low_freq_component.cutoff_freq <= 0:
            return False
        if self.high_freq_component.cutoff_freq <= 0:
            return False

        # 저대역 cutoff이 고대역 cutoff보다 커야 함 (주파수 관점에서)
        if self.low_freq_component.cutoff_freq <= self.high_freq_component.cutoff_freq:
            return False

        return True

    def get_cutoff_summary(self) -> str:
        """차단 주파수 요약 정보 반환"""
        return (
            f"Low Pass: {self.low_freq_component.cutoff_freq:.6f} Hz "
            f"({self.low_freq_component.cutoff_period_min:.1f}분), "
            f"High Pass: {self.high_freq_component.cutoff_freq:.6f} Hz "
            f"({self.high_freq_component.cutoff_period_min:.1f}분)"
        )


@dataclass
class AnalysisResult:
    all_peaks: List[PeakInfo]
    dominant_peaks: List[PeakInfo]
    frequencies: NDArray[np.float64]
    psd: NDArray[np.float64]
    min_valley_right: Optional[Dict[str, float]] = None

    def has_two_components(self) -> bool:
        """두 개 이상의 주요 성분이 있는지 확인"""
        return len(self.dominant_peaks) >= 2

    def get_main_periods(self) -> List[float]:
        """주요 성분들의 주기를 분 단위로 반환"""
        return [peak.period_minutes for peak in self.dominant_peaks]

    def get_frequency_range(self) -> Tuple[float, float]:
        """주파수 범위 반환 (최소, 최대)"""
        if len(self.frequencies) == 0:
            return 0.0, 0.0
        return float(np.min(self.frequencies)), float(np.max(self.frequencies))

    def get_power_range(self) -> Tuple[float, float]:
        """파워 스펙트럼 범위 반환 (최소, 최대)"""
        if len(self.psd) == 0:
            return 0.0, 0.0
        return float(np.min(self.psd)), float(np.max(self.psd))


class FileAnalysisResult(TypedDict):
    analysis_result: Optional[AnalysisResult]
    filter_design: Optional[FilterDesign]
    component1: Optional[NDArray[np.float64]]
    component2: Optional[NDArray[np.float64]]


def find_min_valley_right(
    analysis_result: Optional[AnalysisResult],
) -> Optional[Dict[str, float]]:
    """첫 번째와 두 번째 피크 중 오른쪽 피크에서 값이 다시 올라가기 직전 위치 찾기"""
    if not analysis_result or len(analysis_result.dominant_peaks) < 2:
        return None

    frequencies = analysis_result.frequencies
    psd = analysis_result.psd

    # 첫 번째와 두 번째 피크의 주파수
    peak1_freq = analysis_result.dominant_peaks[0].frequency
    peak2_freq = analysis_result.dominant_peaks[1].frequency

    # 오른쪽 피크 (더 높은 주파수) 선택
    right_peak_freq = max(peak1_freq, peak2_freq)

    # 오른쪽 피크의 인덱스 찾기
    right_peak_idx = np.argmin(np.abs(frequencies - right_peak_freq))

    # 오른쪽 피크 이후의 데이터만 고려
    if right_peak_idx >= len(frequencies) - 3:  # 충분한 데이터가 없으면 None 반환
        return None

    # 오른쪽 피크에서 오른쪽으로 하나씩 체크
    valley_idx = int(right_peak_idx)

    # 오른쪽 피크부터 시작해서 오른쪽으로 이동하면서 값이 다시 올라가기 직전 찾기
    for i in range(int(right_peak_idx) + 1, len(psd) - 1):
        current_psd = psd[i]
        next_psd = psd[i + 1]

        # 현재 값이 다음 값보다 작고, 다음 값이 올라가기 시작하면 valley
        if current_psd < next_psd:
            valley_idx = i
            break

        # 계속 내려가고 있으면 valley_idx 업데이트
        valley_idx = i

    valley_freq = frequencies[valley_idx]
    valley_psd = psd[valley_idx]
    valley_period = 1 / valley_freq / 60

    print(f"\n오른쪽 피크({right_peak_freq:.6f} Hz) 오른쪽 V자 최저점:")
    print(f"  주파수: {valley_freq:.6f} Hz ({valley_period:.1f}분 주기)")
    print(f"  PSD 값: {valley_psd:.2e}")
    print(f"  위치: 오른쪽 피크에서 {valley_idx - right_peak_idx}번째 지점")

    return {
        "frequency": valley_freq,
        "period_minutes": valley_period,
        "psd_value": valley_psd,
    }


def analyze_dominant_frequencies(
    data: NDArray[np.float64], sampling_rate: float
) -> Tuple[Optional[AnalysisResult], NDArray[np.float64], NDArray[np.float64]]:
    """
    주된 주파수 성분 분석 - 두 개의 주요 파형 성분 식별
    """
    print("주된 주파수 성분 분석 중...")

    # 파워 스펙트럼 계산
    nperseg = min(len(data) // 2, 4096)
    frequencies, psd = signal.welch(
        data, fs=sampling_rate, nperseg=nperseg, noverlap=nperseg // 2
    )

    # DC 성분 제거
    freq_no_dc = frequencies[1:]
    psd_no_dc = psd[1:]

    # 빈 배열 체크
    if len(psd_no_dc) == 0:
        print("경고: PSD 데이터가 비어있습니다.")
        return None, frequencies, psd

    # 피크 검출 파라미터 계산
    max_psd = np.max(psd_no_dc)
    min_distance = max(1, len(psd_no_dc) // 200)  # 최소 1 이상 보장

    # 피크 검출 - 주요 파형 성분 식별 (더 완화된 기준)
    peaks, properties = signal.find_peaks(
        psd_no_dc,
        prominence=max_psd * 0.005,  # 1% → 0.5%로 더 완화
        distance=min_distance,  # 거리 기준 더 완화 (최소 1)
        height=max_psd * 0.005,
    )  # 높이 기준도 완화

    if len(peaks) == 0:
        print("경고: 명확한 피크를 찾을 수 없습니다.")
        return None, frequencies, psd

    # 피크들을 파워 크기순으로 정렬
    peak_powers = psd_no_dc[peaks]
    sorted_indices = np.argsort(peak_powers)[::-1]

    # 상위 피크들 분석
    analysis_result = AnalysisResult(
        all_peaks=[], dominant_peaks=[], frequencies=freq_no_dc, psd=psd_no_dc
    )

    print(f"검출된 피크 개수: {len(peaks)}")

    for i, peak_idx in enumerate(sorted_indices):
        peak_freq = freq_no_dc[peaks[peak_idx]]
        peak_power = peak_powers[peak_idx]
        peak_prominence = properties["prominences"][peak_idx]

        peak_info = PeakInfo.from_frequency(
            frequency=peak_freq,
            power=peak_power,
            prominence=peak_prominence,
            rank=i + 1,
        )

        analysis_result.all_peaks.append(peak_info)

        if i < 5:  # 상위 5개만 출력
            print(
                f"  피크 {i+1}: {peak_freq:.6f} Hz ({peak_info.period_minutes:.1f}분 주기), "
                f"파워: {peak_power:.2e}"
            )

    # 주된 두 개 성분 선택
    if len(analysis_result.all_peaks) >= 2:
        # 첫 번째와 두 번째 피크
        analysis_result.dominant_peaks = analysis_result.all_peaks[:2]

        print("\n주된 두 개 주파수 성분:")
        for i, peak in enumerate(analysis_result.dominant_peaks):
            print(
                f"  성분 {i+1}: {peak.frequency:.6f} Hz ({peak.period_minutes:.1f}분 주기)"
            )

    elif len(analysis_result.all_peaks) == 1:
        # 하나의 주된 피크만 있는 경우
        analysis_result.dominant_peaks = analysis_result.all_peaks[:1]
        print("\n주된 주파수 성분 (1개만 검출):")
        print(
            f"  성분 1: {analysis_result.dominant_peaks[0].frequency:.6f} Hz "
            f"({analysis_result.dominant_peaks[0].period_minutes:.1f}분 주기)"
        )

    # 첫 번째 피크 오른쪽의 가장 낮은 피크 값 찾기 (통합된 함수 사용)
    min_valley_result = find_min_valley_right(analysis_result)
    if min_valley_result:
        analysis_result.min_valley_right = min_valley_result

    return analysis_result, frequencies, psd
