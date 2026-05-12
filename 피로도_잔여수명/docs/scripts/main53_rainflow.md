# main53_rainflow.py - Rainflow 계수법 피로 분석

## 개요
압력 데이터에 Rainflow Counting 알고리즘을 적용하여 피로 손상 평가를 위한 사이클 카운팅을 수행하는 스크립트입니다.

## 주요 기능
- **Rainflow 알고리즘**: ASTM E1049 표준 기반 사이클 계수
- **응력 범위 계산**: 피크-밸리 기반 응력 진폭 산출
- **사이클 히스토그램**: 응력 범위별 발생 빈도 분석
- **피로 손상 평가**: Miner's Rule 기반 누적 손상 계산
- **성분별 분석**: 원본, 저대역, 고대역 신호 각각 분석
- **비교 분석**: 지역별, 성분별 피로 특성 비교

## 입력 파일
- `data/raw/0470 소구역 압력 데이터.csv`
  - 0470 지역의 5분 간격 압력 측정 데이터
  
- `data/raw/0520 중구역 압력 데이터.csv`
  - 0520 지역의 5분 간격 압력 측정 데이터

### 입력 데이터 형식
```csv
DateTime,Pressure
2023-01-01 00:00:00,4.5
2023-01-01 00:05:00,4.3
...
```

## 출력 파일

### 히스토그램 그래프
- `results/main53_rainflow/rainflow_original_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/rainflow_low_pass_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/rainflow_high_pass_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/rainflow_original_0520_중구역_압력_데이터.png`
- `results/main53_rainflow/rainflow_low_pass_0520_중구역_압력_데이터.png`
- `results/main53_rainflow/rainflow_high_pass_0520_중구역_압력_데이터.png`

### 누적 분포 그래프
- `results/main53_rainflow/cumulative_original_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/cumulative_low_pass_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/cumulative_high_pass_0470_소구역_압력_데이터.png`
- `results/main53_rainflow/cumulative_original_0520_중구역_압력_데이터.png`
- `results/main53_rainflow/cumulative_low_pass_0520_중구역_압력_데이터.png`
- `results/main53_rainflow/cumulative_high_pass_0520_중구역_압력_데이터.png`

### 비교 분석 데이터
- `results/main53_rainflow/fatigue_comparison.csv`
  - 모든 분석 결과의 종합 비교 테이블

## 분석 결과 (2023년 데이터)

### 0470 소구역
- **원본 데이터**: 62,204.5 사이클
- **저대역 (Low Pass)**: 2,760.5 사이클
- **고대역 (High Pass)**: 71,052.0 사이클

### 0520 중구역
- **원본 데이터**: 48,534.5 사이클
- **저대역 (Low Pass)**: 2,457.0 사이클
- **고대역 (High Pass)**: 54,758.5 사이클

## 데이터 처리 흐름
1. 압력 데이터 로드 (원본 및 필터링된 데이터)
2. Rain Flow Counting 수행
3. 사이클 히스토그램 생성
4. 피로 손상 지표 계산
5. 비교 분석 결과 저장

## 알고리즘 세부사항

### 1. Rainflow Counting
```python
from rainflow import count_cycles

# 사이클 카운팅
cycles = count_cycles(pressure_data, nbins=50)
```

### 2. 주요 통계
- **총 사이클 수**: 연간 피로 사이클 횟수 (full cycles + half cycles/2)
- **평균 응력 범위**: 사이클들의 평균 진폭
- **최대 응력 범위**: 가장 큰 진폭의 사이클
- **표준편차**: 응력 범위의 변동성

### 3. 피로 손상 지표
- **누적 손상**: Palmgren-Miner 법칙 적용
- **등가 응력**: 피로 손상 관점의 대표 응력
- **손상 밀도**: 시간당 피로 손상률

## 필터링 효과

### 저대역 성분 (Low Pass)
- 장주기 운영 패턴 반영
- 일주조/반일주조 성분 포함
- 적은 사이클 수, 큰 진폭

### 고대역 성분 (High Pass)
- 단주기 압력 변동 반영
- 과도 현상 및 노이즈 포함
- 많은 사이클 수, 작은 진폭

## 실행 방법

```bash
# 프로젝트 루트에서 실행
python -m main53_rainflow

# 또는 설치된 명령어 사용
fatigue-rainflow
```

## 의존성
- `pandas`: 데이터 처리
- `numpy`: 수치 계산
- `scipy.signal`: 신호 처리
- `rainflow`: Rainflow counting 알고리즘
- `matplotlib`: 시각화

## 관련 모듈
- `rain_flow_counting.py`: Rainflow 알고리즘 구현
- `pass_filter.py`: 신호 필터링
- `korean_font_utils.py`: 한글 폰트 설정
- `utils.py`: 데이터 전처리

## 활용
- 사이클 카운팅 결과는 main5, main6에서 피로 손상 계산에 활용
- S-N 곡선과 결합하여 피로 수명 예측
- 성분별 피로 기여도 평가

## 참고사항
- Rainflow counting은 ASTM E1049 표준 준수
- 저대역과 고대역의 피로 특성이 크게 다름
- 고대역 성분은 피로 손상에 10배 가중치 적용 (main5, main6)