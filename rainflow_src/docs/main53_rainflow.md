# main53_rainflow.py

## 개요
압력 데이터의 Rainflow Counting 분석을 통해 상수도 파이프의 피로 손상을 계산하는 스크립트

## 실행 방법
```bash
python main53_rainflow.py
```

## 입력 데이터
**위치:** `data/raw/`

6개 압력 데이터 CSV 파일 (총 ~46 MB):
- 0243 소구역 압력 데이터.csv
- 0461 소구역 압력 데이터.csv
- 0470 소구역 압력 데이터.csv
- 0480 소구역 압력 데이터.csv
- 0490 소구역 압력 데이터.csv
- 0520 중구역 압력 데이터.csv

**데이터 형식:**
- 컬럼: `msrmt_dt` (DateTime), `wtrprsr` (Pressure)
- 샘플링 간격: 5분
- 기간: 2022-08-20 ~ 2025-08-31

## 출력 결과
**위치:** `results/main53/`

### 생성 파일 (25개)
1. **Rainflow 히스토그램** (12개 PNG)
   - `rainflow_low_pass_*.png` (저주파 성분, 6개)
   - `rainflow_high_pass_*.png` (고주파 성분, 6개)

2. **누적 사이클 그래프** (12개 PNG)
   - `cumulative_low_pass_*.png` (6개)
   - `cumulative_high_pass_*.png` (6개)

3. **비교 분석 결과** (1개 CSV)
   - `fatigue_comparison.csv` (18개 행: 6개 파일 × 3개 타입)

## 분석 과정

1. **데이터 로드 및 전처리**
   - CSV 파일 읽기
   - NaN 값 선형 보간
   - 샘플링 주파수 계산

2. **신호 필터링**
   - V자 최저점 기준 (553.5분 = 9.23시간)
   - Low Pass: 장기 운영 패턴 추출
   - High Pass: 단기 변동 및 transient 추출

3. **Rainflow Counting 분석**
   - ASTM E1049 표준 기반
   - 사이클 범위, 평균값, 개수 계산
   - 피로 손상 등가 계산 (Miner's Rule)

4. **결과 시각화 및 저장**
   - 히스토그램 (4개 서브플롯)
   - 누적 사이클 그래프
   - CSV 비교 테이블

## 주요 통계 지표

- **Total_Cycles**: 총 사이클 수
- **Mean_Range**: 평균 사이클 범위
- **Max_Range**: 최대 사이클 범위
- **Std_Range**: 사이클 범위 표준편차
- **Damage_Equivalent**: 피로 손상 등가 (m=3)

## 의존성
```
numpy
pandas
matplotlib
scipy
```

## 관련 모듈

- `utils.py` - NaN 값 보간
- `pass_filter.py` - 신호 필터링 (Butterworth 4차)
- `rain_flow_counting.py` - Rainflow 알고리즘 구현
- `common/config.py` - 경로 및 상수 설정
- `common/korean_font_utils.py` - 한글 폰트 설정
