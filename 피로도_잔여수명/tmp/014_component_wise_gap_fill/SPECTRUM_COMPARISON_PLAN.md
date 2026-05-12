# 스펙트럼 비교 분석 계획서

## 📌 프로젝트 개요

### 목적
Project 014의 Random Phase 합성 방법이 원본 데이터의 스펙트럼 특성을 얼마나 잘 보존하는지 시각적으로 확인하고 정량적으로 평가

### 배경
- Random Phase IFFT는 magnitude spectrum은 완벽히 보존하지만 phase를 랜덤화
- 이론적으로는 PSD가 동일해야 하나 실제로는 차이 발생 가능
- 고주파 성분의 CCR이 낮은(~0.78) 원인 파악 필요

### 핵심 질문
1. Random Phase 합성이 원본의 스펙트럼 특성을 얼마나 잘 보존하는가?
2. 어느 주파수 대역에서 차이가 발생하는가?
3. CCR이 낮은 원인이 스펙트럼 차이와 관련이 있는가?

## 🔍 분석 범위

### 대상 데이터
1. **원본 데이터**: 0243 소구역 압력 데이터 (231,372 points)
   - 파일: `/data/raw/0243 소구역 압력 데이터.csv`
   - 샘플링: 5분 간격 (300초)

2. **합성 데이터**: Random Phase IFFT로 생성한 gap filling 결과
   - 7일 gap (10,080 points)
   - 14일 gap (20,160 points)
   - 24일 gap (34,560 points)

### 비교 대상
- **전체 신호** 스펙트럼
- **저주파 성분** (< 1/553.5분 = 3.01e-5 Hz)
- **고주파 성분** (> 1/553.5분)

## 📊 분석 방법론

### 1. 스펙트럼 계산

#### FFT 파라미터
```python
# Sampling parameters
fs = 1/300  # Hz (5분 간격 = 300초)
nperseg = 2048  # FFT window size
noverlap = nperseg // 2  # 50% overlap

# Frequency range
f_min = 1e-7  # Hz (최소 주파수)
f_max = fs/2  # Hz (Nyquist frequency = 1.67e-3 Hz)

# V-valley frequency
f_vvalley = 1/(553.5*60)  # Hz = 3.01e-5 Hz
```

#### PSD 계산 방법
- **Method 1**: `scipy.signal.welch()` - 안정적인 스펙트럼 추정
- **Method 2**: Direct FFT - 세밀한 주파수 해상도
- **Normalization**: 총 에너지로 정규화하여 공정한 비교

### 2. 시각화 전략

#### 그래프 유형별 세부 계획

##### **Type A: 전체 스펙트럼 비교 (Log-Log Scale)**
```
목적: 전 주파수 대역에서의 스펙트럼 형태 비교
X축: Frequency (Hz) - log scale [1e-7, 1.67e-3]
Y축: PSD (Pa²/Hz) - log scale
요소:
- 원본 (파란색 실선)
- Random Phase (빨간색 점선)
- V-valley frequency (녹색 수직선)
- 범례 및 격자
```

##### **Type B: 저주파 영역 확대 (Linear Scale)**
```
목적: V-valley 주변 저주파 특성 상세 비교
X축: Frequency (Hz) - linear scale [0, 2e-4]
Y축: PSD (Pa²/Hz) - linear scale
요소:
- 원본과 합성 데이터 오버레이
- V-valley (3.01e-5 Hz) 표시
- 차이가 큰 영역 음영 처리
```

##### **Type C: 성분별 스펙트럼 (Panel Plot)**
```
목적: 저주파/고주파 성분 독립 비교
Layout: 2x2 그리드
- Top-left: 저주파 원본
- Top-right: 저주파 Random Phase
- Bottom-left: 고주파 원본
- Bottom-right: 고주파 Random Phase
각 panel: log-log scale
```

##### **Type D: 스펙트럼 차이 분석**
```
목적: 주파수별 차이 정량화
Upper panel: Absolute difference |PSD_orig - PSD_synth|
Lower panel: Relative difference (%) = 100 * |PSD_orig - PSD_synth| / PSD_orig
X축: Frequency (Hz) - log scale
Highlight: 차이가 10% 이상인 영역
```

### 3. 정량적 평가 지표

#### 주요 메트릭
| 지표 | 수식 | 목표값 | 의미 |
|------|------|--------|------|
| **Spectral Correlation** | `corr(PSD_orig, PSD_synth)` | > 0.95 | 전체 형태 유사도 |
| **RMSE (normalized)** | `√(mean((PSD_orig - PSD_synth)²)) / mean(PSD_orig)` | < 0.1 | 정규화 평균 오차 |
| **Energy Preservation** | `∑PSD_synth / ∑PSD_orig` | 0.95-1.05 | 에너지 보존율 |
| **Peak Frequency Match** | `|f_peak_orig - f_peak_synth|` | < 1e-6 Hz | 주요 주파수 일치도 |
| **Spectral Entropy Ratio** | `H(PSD_synth) / H(PSD_orig)` | 0.9-1.1 | 복잡도 보존 |
| **Wasserstein Distance** | `W(PSD_orig, PSD_synth)` | < 0.05 | 분포 거리 |

#### 주파수 대역별 분석
```python
bands = {
    'VLF': (0, 1e-5),       # Very Low Frequency
    'LF': (1e-5, 3.01e-5),  # Low Frequency (< V-valley)
    'MF': (3.01e-5, 1e-4),  # Mid Frequency (> V-valley)
    'HF': (1e-4, 1.67e-3)   # High Frequency
}

# 각 대역별로 에너지 비율 계산
for band_name, (f_low, f_high) in bands.items():
    energy_ratio = integrate_psd(f_low, f_high)
```

## 🗂️ 구현 계획

### 파일 구조
```
tmp/014_component_wise_gap_fill/
├── scripts/
│   └── compare_spectrum.py      # 메인 분석 스크립트
├── results/
│   └── spectrum_comparison/
│       ├── figures/
│       │   ├── spectrum_full_7d.png
│       │   ├── spectrum_full_14d.png
│       │   ├── spectrum_full_24d.png
│       │   ├── spectrum_lowfreq_7d.png
│       │   ├── spectrum_lowfreq_14d.png
│       │   ├── spectrum_lowfreq_24d.png
│       │   ├── spectrum_components_7d.png
│       │   ├── spectrum_components_14d.png
│       │   ├── spectrum_components_24d.png
│       │   ├── spectrum_difference_7d.png
│       │   ├── spectrum_difference_14d.png
│       │   └── spectrum_difference_24d.png
│       ├── data/
│       │   ├── psd_original.npy
│       │   ├── psd_random_phase_7d.npy
│       │   ├── psd_random_phase_14d.npy
│       │   ├── psd_random_phase_24d.npy
│       │   └── frequencies.npy
│       └── reports/
│           ├── spectrum_metrics.json
│           └── spectrum_analysis_report.md
└── SPECTRUM_COMPARISON_PLAN.md  # 이 문서
```

### 주요 함수 설계

```python
def load_and_prepare_data(area_code='0243', gap_days=7):
    """
    원본 데이터 로드 및 gap 생성

    Returns:
        data_with_gap: gap이 있는 신호
        gap_start, gap_end: gap 위치
        true_gap: gap 영역의 실제 데이터
    """

def perform_random_phase_synthesis(data, gap_start, gap_end):
    """
    Random Phase IFFT 합성

    Returns:
        filled_signal: gap이 채워진 신호
        synthesized_gap: 합성된 gap 데이터만
    """

def compute_psd(signal, fs=1/300, method='welch', nperseg=2048):
    """
    Power Spectral Density 계산

    Parameters:
        method: 'welch' or 'fft'
    Returns:
        frequencies, psd
    """

def plot_spectrum_comparison(freq_orig, psd_orig, freq_synth, psd_synth,
                           plot_type='full', gap_days=7, save_path=None):
    """
    스펙트럼 비교 그래프 생성

    Parameters:
        plot_type: 'full', 'lowfreq', 'components', 'difference'
    """

def calculate_spectral_metrics(psd_orig, psd_synth, freq):
    """
    정량적 평가 지표 계산

    Returns:
        dict with all metrics
    """

def analyze_frequency_bands(psd_orig, psd_synth, freq, bands):
    """
    주파수 대역별 분석

    Returns:
        band_metrics: 각 대역별 에너지, 상관계수 등
    """

def generate_comparison_report(metrics, band_metrics, save_path):
    """
    분석 보고서 생성 (Markdown)
    """
```

## 📈 예상 결과 및 해석

### 예상 관찰 사항

1. **Magnitude 보존**
   - 이론: Random Phase는 magnitude spectrum 완벽 보존
   - 예상: 전체 에너지는 유사하나 세부 형태 차이
   - 확인점: Welch method의 averaging 효과로 인한 smoothing

2. **고주파 차이**
   - 문제: 고주파 CCR 낮음 (0.78)
   - 예상 원인: Phase randomization으로 인한 temporal structure 손실
   - 확인점: 고주파 대역 (>1e-4 Hz) PSD 차이

3. **저주파 특성**
   - 예상: 저주파는 상대적으로 잘 보존
   - 이유: 긴 주기 특성은 phase에 덜 민감
   - 확인점: V-valley 주변 스펙트럼

4. **Edge Effects**
   - Gap 경계에서의 불연속성
   - Edge smoothing 적용 효과 확인

### 시사점 도출

1. **Random Phase 한계**
   - 어느 주파수 대역에서 문제가 큰지 확인
   - CCR과 스펙트럼 차이의 상관관계
   - Phase 정보 손실의 영향

2. **개선 방향**
   - 특정 주파수 대역 phase 보존 필요성
   - GARCH/SV 접근법의 타당성 검증
   - Hybrid 방법의 가능성

## ⏱️ 실행 계획

| 단계 | 작업 | 예상 시간 |
|------|------|----------|
| 1 | main51 코드 분석 및 참조 | 10분 |
| 2 | compare_spectrum.py 작성 | 20분 |
| 3 | 7일 gap 데이터 분석 실행 | 10분 |
| 4 | 14일, 24일 gap 추가 분석 | 10분 |
| 5 | 그래프 생성 및 저장 | 10분 |
| 6 | 메트릭 계산 및 보고서 작성 | 10분 |
| **총계** | | **70분** |

## ✅ 체크리스트

- [ ] main51_find_freq.py 코드 구조 파악
- [ ] 원본 데이터 로드 및 전처리
- [ ] Random Phase synthesis 함수 구현
- [ ] PSD 계산 함수 구현 (Welch method)
- [ ] 4가지 유형 그래프 생성 함수
- [ ] 정량적 메트릭 계산
- [ ] 주파수 대역별 분석
- [ ] 7일 gap 테스트
- [ ] 14일, 24일 gap 확장
- [ ] 최종 보고서 작성

## 📝 참고사항

### main51 프로젝트 참조점
- FFT 파라미터 설정 방법
- 그래프 스타일 (log-log scale)
- V-valley frequency 표시 방법
- 주파수 범위 설정

### 주의사항
- Edge effect 고려 (gap 경계)
- Window function 선택 (Hann window 권장)
- 충분한 frequency resolution 확보
- Aliasing 방지

### 확장 가능성
- IAAFT 결과도 추가 비교
- Coherence, Phase spectrum 분석
- Wavelet transform 비교
- Cross-spectrum 분석

## 🎯 성공 기준

### 필수 달성 목표
1. **시각화**: 4가지 유형 그래프 모두 생성
2. **정량화**: 6가지 메트릭 모두 계산
3. **문서화**: 분석 보고서 작성

### 품질 기준
- 그래프 해상도: 300 DPI 이상
- 코드 재현성: Random seed 고정
- 문서 완성도: 모든 섹션 작성

## 📚 참고 문헌

1. **스펙트럼 분석**
   - Welch, P. (1967). "The use of fast Fourier transform for the estimation of power spectra"
   - Stoica, P. & Moses, R. (2005). "Spectral Analysis of Signals"

2. **Random Phase Surrogates**
   - Theiler, J. et al. (1992). "Testing for nonlinearity in time series"
   - Schreiber, T. & Schmitz, A. (1996). "Improved surrogate data for nonlinearity tests"

3. **피로 분석**
   - ASTM E1049: Standard practices for cycle counting in fatigue analysis
   - Miner, M.A. (1945). "Cumulative damage in fatigue"

---

**작성일**: 2025-12-12
**프로젝트**: Project 014 - Component-wise Gap Filling
**담당자**: Claude AI Assistant
**상태**: 계획 수립 완료, 구현 대기