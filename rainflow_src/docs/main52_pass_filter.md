# main52_pass_filter.py

## 개요
V자 최저점 기준 Pass Filter 적용 및 시각화 - main51에서 찾은 V자 최저점을 cutoff 주파수로 사용하여 저대역/고대역 성분 분리

## 실행 방법
```bash
python main52_pass_filter.py
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
**위치:** `results/main52/`

### 생성 파일 (6개 PNG)
- `valley_based_filter_*.png` (각 지역별)
- 4개 라인 겹침 플롯:
  1. 원본 데이터 (검정)
  2. 저대역 성분 (빨강, Low Pass)
  3. 고대역 성분 (파랑, High Pass)
  4. 합성 신호 (녹색, Low+High)

## 분석 과정

1. **데이터 전처리**
   - CSV 파일 읽기
   - 시간순 정렬
   - NaN 값 선형 보간

2. **V자 최저점 기준 필터 적용**
   - Cutoff 주파수: 0.000030 Hz (553.5분) - main51 결과 사용
   - Low Pass Filter: 저주파 성분 추출
   - High Pass Filter: 고주파 성분 추출
   - Butterworth 4차 필터 (zero-phase filtfilt)

3. **시각화**
   - 동적 범위 설정: 전체의 20% 지점부터 1000개 샘플
   - 4개 신호 겹쳐서 표시
   - 통계 정보 텍스트 박스

4. **에너지 분석**
   - 원본 대비 각 성분의 에너지 비율
   - 에너지 보존율 계산 및 검증
   - 경고: 95% 미만 (에너지 손실) 또는 105% 초과 (중복 발생)

## 주요 결과 해석

### V자 최저점 필터 설계
- **표준 Cutoff**: 553.5분 (9.23시간)
- **Low Pass Margin**: 120% (664.2분 이하 통과)
- **High Pass Margin**: 80% (442.8분 이상 통과)

### 에너지 분포 분석
일반적 결과:
- 저대역 성분: 80-90% (일주기/반일주기 패턴)
- 고대역 성분: 10-20% (노이즈 및 급격한 변동)
- 총 보존율: 95-105% (필터 품질 지표)

### 신호 품질 검증
- **원본 vs 합성 상관계수**: 0.99 이상 (우수)
- 상관계수 < 0.95 시: 필터 설계 재검토 필요

## 의존성
```
numpy
pandas
matplotlib
scipy
```

## 관련 모듈

- `pass_filter.py` - V자 최저점 기준 필터 적용
- `utils.py` - NaN 값 보간
- `common/config.py` - 경로 및 V자 최저점 상수
- `common/korean_font_utils.py` - 한글 폰트 설정

## 연계 스크립트

- **main51_find_freq.py** - V자 최저점 탐색 (선행 작업)
- **main53_rainflow.py** - 필터링된 성분으로 피로 손상 계산 (후속 작업)
