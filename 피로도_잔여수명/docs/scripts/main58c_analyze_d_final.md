# main58c_analyze_d_final.py

## 개요
D_final(누적 피로도) 값을 기반으로 파이프 위험도를 분석하고 5단계 위험도 분류를 수행하는 스크립트입니다.

## 주요 기능

### 1. 데이터 로드 및 전처리
- `fatigue_pipe_lm_by_age.csv`, `fatigue_sply_ls_by_age.csv` 파일 로드
- 지역별(243, 461, 470, 480, 490, 520) 필터링
- D_final 컬럼 검증 및 정제

### 2. 5단계 위험도 분류
```python
@dataclass
class RiskThresholds:
    immediate: float = 0.200      # 즉시교체 (> 0.200)
    very_critical: float = 0.100  # 매우위험 (0.100 - 0.200)
    critical: float = 0.060       # 위험 (0.060 - 0.100)
    warning: float = 0.030        # 주의 (0.030 - 0.060)
    safe: float = 0.030           # 안전 (< 0.030)
```

### 3. 통계 분석
- 지역별 D_final 통계 (평균, 중앙값, 95분위수, 최대값)
- 파이프 타입별(PIPE_LM, SPLY_LS) 분석
- 위험 파이프 식별 및 순위화

### 4. 시각화

#### 4.1 전체 위험도 분포
- `risk_analysis.png`:
  - 5단계 위험도 파이 차트
  - 위험도별 개수 막대 그래프
  - 누적 생존 곡선
  - 지역별/타입별 위험도 분포

#### 4.2 지역별 D_final 분포
- `d_final_distribution_by_region.png`:
  - 6개 지역별 히스토그램
  - PIPE_LM vs SPLY_LS 비교

#### 4.3 전체 D_final 분포
- `d_final_distribution.png`:
  - 전체 히스토그램
  - 지역별 박스플롯
  - 타입별 박스플롯
  - 전체 위험도 파이 차트

## 출력 파일

### CSV 파일
- `critical_pipes.csv`: 위험(critical) 이상 등급 파이프 목록
  - FTR_IDN, 지역, 타입, D_final, 위험등급
- `regional_statistics.csv`: 지역별 통계 요약

### 보고서
- `analysis_report.md`: 마크다운 형식의 종합 분석 보고서
  - 요약 통계
  - 지역별 분석 결과
  - 위험 파이프 현황
  - 권장사항

### 시각화
- `risk_analysis.png`: 종합 위험도 분석 차트
- `d_final_distribution_by_region.png`: 지역별 분포 차트
- `d_final_distribution.png`: 전체 분포 분석 차트

## 실행 방법

```bash
python src/main58c_analyze_d_final.py
```

### 명령행 옵션
- `--input-dir`: 입력 파일 디렉토리 (기본값: results/fatigue_analysis_results)
- `--output-dir`: 출력 디렉토리 (기본값: results/main58c_analyze_d_final)
- `--zones`: 분석할 지역 코드 (기본값: 243,461,470,480,490,520)

## 의존성
- pandas
- numpy
- matplotlib
- seaborn
- scipy

## 관련 스크립트
- [main58_analyze_remaining_life.py](main58_analyze_remaining_life.md): D_final_org 기반 분석
- [main58a_direct_analysis.py](main58a_direct_analysis.md): 잔여 수명 연도 기반 분석
- [main58b_analyze_overlap.py](main58b_analyze_overlap.md): main58과 main58a 결과 비교

## 주요 차이점
- **D_final vs D_final_org**: 
  - D_final: 누적 피로도 (시간에 따른 손상 누적)
  - D_final_org: 원본 피로도 (초기 상태)
- **임계값 조정**: 실제 D_final 범위(0~0.766)에 맞춰 5단계 분류 임계값 최적화
- **위험도 해석**: D_final이 높을수록 누적 손상이 심각하여 즉각적인 조치 필요