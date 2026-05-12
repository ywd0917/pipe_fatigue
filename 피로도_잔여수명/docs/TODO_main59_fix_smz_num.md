# TODO: main59_fix_smz_num.py 개발 계획

## 📋 개요

zone_fatigue_merged.csv에서 zone과 SMZ_NUM이 불일치하는 데이터를 정정하는 스크립트 개발

## 🎯 목표

1. zone과 SMZ_NUM이 다른 93개 행 찾기
2. 해당 행의 FTR_IDN 출력
3. SMZ_NUM을 zone 값으로 대체
4. 정정 통계 리포트 생성

## 📊 현재 상황 분석

### 입력 파일
- **경로**: `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`
- **전체 행 수**: 4,569개
- **전체 컬럼 수**: 54개

### 불일치 현황
- ✅ **일치**: 4,476개 (97.96%)
- ⚠️ **불일치**: 93개 (2.04%)

### zone별 불일치 분포
```
zone 520: 82건 (불일치의 88%)
zone 243: 7건
zone 461: 2건
zone 470: 2건
```

### 잘못된 SMZ_NUM 분포
```
240: 49건 (가장 많음)
580: 28건
210: 7건
60: 1건
230: 1건
243: 3건
461: 2건
470: 2건
700: 1건
```

### 주요 불일치 패턴
```
zone=520 → SMZ_NUM=240: 46건
zone=520 → SMZ_NUM=580: 25건
zone=520 → SMZ_NUM=210: 7건
zone=243 → SMZ_NUM=240: 3건
zone=243 → SMZ_NUM=580: 2건
```

## 🎯 작업 목록

### Phase 1: 스크립트 기본 구조 작성
- [ ] `src/main59_fix_smz_num.py` 파일 생성
- [ ] CSV 로드 함수 작성 (`load_zone_fatigue_data()`)
- [ ] 불일치 검출 로직 작성 (`detect_mismatch()`)
- [ ] SMZ_NUM 대체 로직 작성 (`fix_smz_num()`)
- [ ] main() 함수 작성

### Phase 2: 통계 및 리포트 기능
- [ ] 불일치 FTR_IDN 리스트 출력 함수 (`print_mismatch_ftr_idn()`)
- [ ] zone별 불일치 통계 계산 (`analyze_zone_distribution()`)
- [ ] 원본 SMZ_NUM별 분포 계산 (`analyze_smz_distribution()`)
- [ ] 교차표 생성 (`create_crosstab()`)
- [ ] 리포트 생성 함수 (`generate_report()`)

### Phase 3: 출력 및 검증
- [ ] 정정된 CSV 저장 (`save_fixed_csv()`)
- [ ] 리포트 파일 생성 (`save_report()`)
- [ ] 불일치 FTR_IDN 목록 CSV 저장 (`save_mismatch_list()`)
- [ ] 검증: zone == SMZ_NUM 100% 확인 (`validate_output()`)

### Phase 4: 테스트 및 문서화
- [ ] 테스트 케이스 작성 (`tests/test_main59_fix_smz_num.py`)
- [ ] 스크립트 문서 작성 (`docs/scripts/main59_fix_smz_num.md`)
- [ ] `SCRIPT_IO_REFERENCE.md` 업데이트
- [ ] workflow 다이어그램 업데이트 (필요시)

## 📥 입력/출력

### 입력
- `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`
  - 4,569행 × 54컬럼
  - 주요 컬럼: FTR_IDN, zone, SMZ_NUM

### 출력
1. **정정된 CSV**: `results/main59_fix_smz_num/zone_fatigue_merged_fixed.csv`
   - 4,569행 × 54컬럼 (동일)
   - SMZ_NUM이 zone과 일치하도록 수정

2. **리포트 파일**: `results/main59_fix_smz_num/fix_report.txt`
   - 전체 통계
   - zone별 분포
   - 원본 SMZ_NUM별 분포
   - 교차표 (zone × SMZ_NUM_원본)

3. **불일치 목록**: `results/main59_fix_smz_num/mismatch_ftr_idn_list.csv`
   - 불일치 93개 행의 FTR_IDN 목록
   - 컬럼: FTR_IDN, zone, SMZ_NUM_원본, SMZ_NUM_정정후

## 📊 출력 형식

### 콘솔 출력 예시
```
============================================================
main59_fix_smz_num.py - SMZ_NUM 정정 스크립트
============================================================

입력 파일: results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv
  - 전체 행 수: 4,569개
  - zone 컬럼: 존재
  - SMZ_NUM 컬럼: 존재

============================================================
불일치 검출 결과
============================================================

✅ 일치: 4,476개 (97.96%)
⚠️  불일치: 93개 (2.04%)

🔍 불일치 FTR_IDN 목록 (총 93개):
  1. FTR_IDN: 12345 | zone: 520 | SMZ_NUM: 240 → 520
  2. FTR_IDN: 12346 | zone: 520 | SMZ_NUM: 580 → 520
  ...
  93. FTR_IDN: 78901 | zone: 470 | SMZ_NUM: 700 → 470

============================================================
zone별 불일치 분포
============================================================
  zone 520: 82건 (88.17%)
  zone 243: 7건 (7.53%)
  zone 461: 2건 (2.15%)
  zone 470: 2건 (2.15%)

============================================================
원본 SMZ_NUM 분포
============================================================
  240: 49건 (52.69%)
  580: 28건 (30.11%)
  210: 7건 (7.53%)
  243: 3건 (3.23%)
  470: 2건 (2.15%)
  461: 2건 (2.15%)
  60: 1건 (1.08%)
  230: 1건 (1.08%)

============================================================
SMZ_NUM 정정 완료
============================================================
  - 정정된 행 수: 93개
  - 출력 파일: results/main59_fix_smz_num/zone_fatigue_merged_fixed.csv
  - 리포트 파일: results/main59_fix_smz_num/fix_report.txt
  - 불일치 목록: results/main59_fix_smz_num/mismatch_ftr_idn_list.csv

✅ 검증 완료: 모든 행에서 zone == SMZ_NUM
============================================================
```

### fix_report.txt 예시
```
=== main59: SMZ_NUM 정정 리포트 ===
생성 일시: 2025-12-17 16:30:00

📊 처리 통계
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
전체 행 수: 4,569개
일치 행 수: 4,476개 (97.96%)
불일치 행 수: 93개 (2.04%)
정정 완료: 93개

🔍 zone별 정정 분포
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
zone 520: 82건 (88.17%)
zone 243: 7건 (7.53%)
zone 461: 2건 (2.15%)
zone 470: 2건 (2.15%)

📋 정정 전 SMZ_NUM 분포
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
240 → zone별로 정정: 49건 (52.69%)
580 → zone별로 정정: 28건 (30.11%)
210 → zone별로 정정: 7건 (7.53%)
243 → zone별로 정정: 3건 (3.23%)
470 → zone별로 정정: 2건 (2.15%)
461 → zone별로 정정: 2건 (2.15%)
60 → zone별로 정정: 1건 (1.08%)
230 → zone별로 정정: 1건 (1.08%)

📊 교차표 (zone × SMZ_NUM_원본)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
zone\SMZ  60  210  230  240  243  461  470  580  700
  243      0    0    0    3    0    0    2    2    0
  461      0    0    0    0    2    0    0    0    0
  470      0    0    0    0    0    0    0    1    1
  520      1    7    1   46    1    2    0   25    0

✅ 정정 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
출력 파일: results/main59_fix_smz_num/zone_fatigue_merged_fixed.csv
검증 결과: 모든 행에서 zone == SMZ_NUM 보장됨
```

### mismatch_ftr_idn_list.csv 예시
```csv
FTR_IDN,zone,SMZ_NUM_원본,SMZ_NUM_정정후,DATA_SRC
12345,520,240,520,PIPE_LM
12346,520,580,520,SPLY_LS
...
```

## 🔧 참고 스크립트

### main11g_fix_area_no.py
- **목적**: 좌표 기반 구역 번호 수정
- **참고할 부분**:
  - CSV 로드 및 검증 로직
  - 통계 계산 방식
  - 리포트 생성 구조

### main13c_zone_fatigue_merge.py
- **목적**: 구역별 피로 데이터 병합
- **참고할 부분**:
  - zone 생성 로직 (공간 조인)
  - 불일치가 발생하는 배경 이해

## 💡 구현 세부사항

### 함수 구조
```python
def load_zone_fatigue_data(file_path: Path) -> pd.DataFrame:
    """zone_fatigue_merged.csv 로드 및 검증"""

def detect_mismatch(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """일치/불일치 행 분리"""
    # zone과 SMZ_NUM을 문자열로 변환 후 비교
    # 불일치 행만 추출하여 반환

def fix_smz_num(df: pd.DataFrame) -> pd.DataFrame:
    """SMZ_NUM을 zone 값으로 대체"""
    # 원본 백업: SMZ_NUM_원본 컬럼 생성
    # 불일치 행의 SMZ_NUM을 zone으로 덮어쓰기

def analyze_statistics(mismatch_df: pd.DataFrame) -> dict:
    """불일치 통계 분석"""
    # zone별 분포
    # 원본 SMZ_NUM별 분포
    # 교차표 생성

def print_mismatch_ftr_idn(mismatch_df: pd.DataFrame) -> None:
    """불일치 FTR_IDN 목록 콘솔 출력"""

def generate_report(stats: dict, total_rows: int, mismatch_count: int) -> str:
    """텍스트 리포트 생성"""

def validate_output(df: pd.DataFrame) -> bool:
    """zone == SMZ_NUM 100% 확인"""

def save_results(df: pd.DataFrame, mismatch_df: pd.DataFrame, stats: dict, output_dir: Path) -> None:
    """모든 출력 파일 저장"""
```

### 데이터 타입 처리
```python
# zone과 SMZ_NUM을 정수형으로 통일
df['zone'] = df['zone'].astype(int)
df['SMZ_NUM'] = df['SMZ_NUM'].astype(int)

# 비교
mismatch_mask = df['zone'] != df['SMZ_NUM']
```

## ⚠️ 주의사항

1. **데이터 타입**
   - zone: 정수형 (243, 461, 470, 480, 490, 520)
   - SMZ_NUM: 정수형 (앞의 0이 제거되지 않도록 주의)
   - 비교 전 반드시 타입 통일

2. **원본 보존**
   - SMZ_NUM_원본 컬럼 생성하여 원래 값 백업
   - 최종 출력 CSV에는 포함하지 않음 (분석용으로만 사용)

3. **NaN 처리**
   - zone이나 SMZ_NUM이 NaN인 경우 처리 로직 필요
   - 현재 데이터에서는 NaN이 없지만 안전장치 추가

4. **출력 디렉토리**
   - `results/main59_fix_smz_num/` 자동 생성
   - 기존 파일이 있으면 덮어쓰기 경고

## 📅 예상 일정

- **스크립트 작성**: 2시간
  - 기본 구조 및 로직: 1시간
  - 통계 및 리포트: 1시간

- **테스트**: 1시간
  - 단위 테스트 작성: 30분
  - 통합 테스트: 30분

- **문서화**: 1시간
  - 스크립트 문서: 30분
  - SCRIPT_IO_REFERENCE.md 업데이트: 30분

- **총 예상 시간**: 4시간

## 🚀 실행 명령어 (예정)

```bash
# 실행
python src/main59_fix_smz_num.py

# 또는 엔트리 포인트 (설정 후)
fatigue-fix-smz
```

## 📝 후속 작업

1. **main13c 개선 검토**
   - zone 생성 로직 개선 필요성 검토
   - 공간 조인 정확도 향상 방안

2. **원인 분석**
   - 왜 520 zone에서 불일치가 집중되는지 분석
   - 구역 경계 데이터 품질 검토

3. **자동화**
   - main13c 실행 후 자동으로 main59 실행하는 파이프라인 구성
   - workflow 다이어그램 업데이트
