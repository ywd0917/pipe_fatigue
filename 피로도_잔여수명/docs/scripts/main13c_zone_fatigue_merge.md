# main13c: 구역별 피로 손상 데이터 병합

**파일명**: `main13c_zone_fatigue_merge.py`

## 📋 개요
- main56에서 생성된 지역별 피로 손상 데이터와 파이프 shapefile을 공간 조인하여, 각 파이프가 실제로 위치한 구역의 피로도 값만 남기는 통합 스크립트입니다.
- **핵심 기능**: 파이프의 물리적 위치를 기반으로 해당 구역의 D_final_org 값만 추출
- **처리 데이터 통계 (총 4,569개 파이프)**:
  - PIPE_LM: 978개 (21.4%)
  - SPLY_LS: 3,591개 (78.6%)
- **구역별 분포**:
  - 0243 지역: 724개 (15.8%)
  - 0461 지역: 918개 (20.1%)
  - 0470 지역: 984개 (21.5%)
  - 0480 지역: 759개 (16.6%)
  - 0490 지역: 1,102개 (24.1%)
  - 0520 지역: 82개 (1.8%)
- **주요 특징**:
  - 피로 손상 CSV의 지역별 컬럼 중 실제 위치 구역만 선택
  - Representative point 기반 공간 조인으로 구역 판별
  - 소구역(0243, 0461, 0470, 0480, 0490) 우선, 중구역(0520) 차선

## 🚀 사용법

```bash
# 기본 실행
python src/main13c_zone_fatigue_merge.py

# 특정 Export 디렉토리 지정
python src/main13c_zone_fatigue_merge.py \
  --export-dir data/raw/export_shp_20250704(0520)

# 출력 파일 지정
python src/main13c_zone_fatigue_merge.py \
  --output results/custom/zone_merged.csv

# 디버그 모드
python src/main13c_zone_fatigue_merge.py --debug
```

## 📥 입력 파일
### main56 피로 데이터 (지역별 컬럼 포함)
- `results/main56_calc_fatigure/fatigue_pipe_lm.csv`: PIPE_LM 피로 손상 계산 결과
  - 각 파이프마다 6개 지역의 D_final_org 값 존재
  - 컬럼명 형식: `{지역코드}_{변수명}` (예: 0520_D_final_org, 0470_remaining_life_years)
  - K-factors는 지역별로 동일 (지역 prefix 없음)
- `results/main56_calc_fatigure/fatigue_sply_ls.csv`: SPLY_LS 피로 손상 계산 결과
  - PIPE_LM과 동일한 구조

### Shapefile 데이터
- `raw_data/export_shp_*/V_WTL_PIPE_LM.shp`: PIPE_LM 파이프 위치 (LineString)
- `raw_data/export_shp_*/V_WTL_SPLY_LS.shp`: SPLY_LS 파이프 위치 (LineString)
- `raw_data/export_shp_*/WEA_MDLZ_AS.shp`: 중구역 경계 (0520)
- `raw_data/export_shp_*/WEA_SMLZ_AS.shp`: 소구역 경계 (0243, 0461, 0470, 0480, 0490)

## 📤 출력 파일
- `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`: 구역별 피로 손상 통합 데이터

### 출력 파일 구조
```csv
DATA_SRC,zone,FTR_IDN,FTR_CDE,...,D_final_org,remaining_life_years,...
PIPE_LM,0520,142051,WL1,...,0.4483,1.172,...
PIPE_LM,0470,415766,WL1,...,0.3948,1.040,...
SPLY_LS,0520,123456,WL2,...,0.2134,5.234,...
```

### 주요 컬럼
- **DATA_SRC**: 파이프 종류 (PIPE_LM, SPLY_LS)
- **zone**: 파이프가 실제 위치한 구역 코드
- **FTR_IDN**: 파이프 고유 ID
- **D_final_org**: 해당 구역의 피로도 값 (지역 prefix 제거됨)
- **remaining_life_years**: 해당 구역의 잔여수명 (지역 prefix 제거됨)
- **K-factors**: K_age, K_soil, K_traffic 등 (지역 무관)
- **MET_IDN**: SPLY_LS 데이터에만 존재, CLS_YMD 다음 위치
- geometry는 포함하지 않음 (파일 크기 최적화)

## ✨ 주요 기능

### 1. 피로 손상 데이터 로드
- fatigue_pipe_lm.csv, fatigue_sply_ls.csv 읽기
- 각 파이프의 6개 지역별 D_final_org 값 모두 로드
- K-factors는 지역 무관 (prefix 없음)

### 2. 파이프 Shapefile 로드
- V_WTL_PIPE_LM.shp, V_WTL_SPLY_LS.shp geometry
- FTR_IDN을 키로 사용하여 피로 데이터와 조인

### 3. 공간 조인으로 구역 판별
- 파이프 대표점(representative_point) 계산
- 소구역 우선 확인 (0243, 0461, 0470, 0480, 0490)
- 소구역에 없으면 중구역(0520) 확인
- 판별 불가시 "UNKNOWN" 할당

### 4. 구역별 컬럼 필터링
- 각 파이프의 zone에 맞는 지역별 컬럼만 선택
- 예: zone=0520인 파이프는 0520_D_final_org, 0520_remaining_life_years만 유지
- 지역 prefix 제거: 0520_D_final_org → D_final_org

### 5. 데이터 통합
- PIPE_LM과 SPLY_LS 데이터 합치기
- DATA_SRC 컬럼으로 파이프 종류 구분
- **원본 CSV 컬럼 순서 유지**:
  - 기본 컬럼: MET_IDN이 CLS_YMD 다음 위치
  - Zone 컬럼: 원본 CSV와 동일한 순서로 출력

## ⚙️ 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--export-dir` | Export shapefile 디렉토리 | 자동 탐색 (0520) |
| `--output` | 출력 CSV 파일 경로 | `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv` |
| `--debug` | 디버그 모드 활성화 | `False` |

## 🔗 관련 문서

### 업스트림 스크립트 (입력 데이터 생성)
- [main56_calc_fatigure.py](main56_calc_fatigure.md) - 지역별 피로도 계산 및 D_final_org 생성
- [main13_crop_520.py](main13_crop_520.md) - 520 지역 shapefile 추출

### 다운스트림 스크립트 (이 스크립트의 출력 사용)
- [main58b_analyze_overlap.py](main58b_analyze_overlap.md) - 위험 파이프 중복 분석 (D_final vs 잔여수명)
- [main13d_visualize_zone_fatigue.py](main13d_visualize_zone_fatigue.md) - 구역별 파이프 시각화
- main58_analyze_remaining_life.py - D_final 기준 위험도 분석
- main58a_analyze_remaining_life_by_years.py - 잔여수명 기준 분석

## 📊 처리 성능
- 피로 데이터 로드: 약 0.1초
- Shapefile 로드: 약 0.3초
- 공간 조인: 약 0.5초
- 전체 실행 시간: 약 1-2초

## 💡 구역 판별 로직

### determine_zone() 함수
```python
def determine_zone(pipe_geometry, boundaries):
    # 1. 파이프 대표점 계산
    point = pipe_geometry.representative_point()

    # 2. 소구역 우선 확인
    for region in ["0243", "0461", "0470", "0480", "0490"]:
        if region in boundaries:
            for _, boundary in boundaries[region].iterrows():
                if boundary.geometry.contains(point):
                    return region

    # 3. 중구역 확인
    if "0520" in boundaries:
        for _, boundary in boundaries["0520"].iterrows():
            if boundary.geometry.contains(point):
                return "0520"

    return "UNKNOWN"
```

### filter_zone_columns() 함수
```python
def filter_zone_columns(df):
    # 각 행의 zone에 맞는 컬럼만 유지
    for zone in df['zone'].unique():
        # 예: zone=0520인 행들은 0520_로 시작하는 컬럼만 유지
        zone_cols = [col for col in df.columns
                    if col.startswith(f"{zone}_")]

        # prefix 제거: 0520_D_final_org → D_final_org
        rename_dict = {col: col.replace(f"{zone}_", "")
                      for col in zone_cols}
```

## ⚠️ 주의사항

### 데이터 처리 관련
- **입력 데이터 구조**: main56 출력은 파이프당 6개 지역 데이터를 모두 포함
- **실제 위치 기반 선택**: 공간 조인으로 파이프의 물리적 위치 구역만 선택
- **FTR_IDN 매칭**: shapefile과 피로 데이터 간 FTR_IDN 일치 필수
- **UNKNOWN 처리**: 구역 판별 실패 시 기본 컬럼만 유지

### 기술적 제약
- **CRS 일관성**: 모든 shapefile은 EPSG:5179 좌표계 사용
- **인코딩**: shapefile은 cp949, CSV는 utf-8-sig 인코딩
- **메모리 사용**: 대용량 shapefile 처리 시 충분한 메모리 필요
- **geometry 제외**: 출력 CSV에 geometry 포함 안 함 (시각화는 main13d 사용)

### 컬럼 관련
- **MET_IDN 컬럼**: SPLY_LS 데이터에만 존재, PIPE_LM 행에서는 빈 값
- **지역 prefix 제거**: 출력 시 지역 코드 prefix 자동 제거

## 🔧 최근 개선사항
### v2025.01.03 - Zone 컬럼 순서 수정 ([#53](https://github.com/jungdam-dev/fatigue-qgis/issues/53), [PR #54](https://github.com/jungdam-dev/fatigue-qgis/pull/54))
- **문제**: Zone별 컬럼 그룹이 알파벳 순으로 정렬되어 원본 CSV와 순서가 달랐음
- **수정**: `sorted()` 호출을 제거하여 원본 DataFrame 컬럼 순서 유지
- **결과**: 원본 CSV 순서와 동일 (low_total_cycles → high_total_cycles → low_fatigue_damage → high_fatigue_damage → D_base → D_final_org → D_final → remaining_life_years)
- **테스트**: Zone 컬럼 순서 검증 테스트 케이스 추가

### v2025.01.03 - MET_IDN 컬럼 위치 수정 ([#51](https://github.com/jungdam-dev/fatigue-qgis/issues/51), [PR #52](https://github.com/jungdam-dev/fatigue-qgis/pull/52))
- **문제**: MET_IDN 컬럼이 원본 CSV와 다른 위치에 출력되었음 (위치 45 → K_total 다음)
- **수정**: MET_IDN이 원본 CSV 순서대로 위치 20에 출력 (CLS_YMD 다음, GU_CDE 앞)
- **구현**: `filter_zone_columns` 함수에 `expected_basic_order` 추가하여 컬럼 순서 보장
- **테스트**: MET_IDN 위치 검증 테스트 케이스 추가

### v2025.09.25 - 데이터 구조 이해 개선
- **핵심 개념**: main56 출력은 파이프당 6개 지역의 D_final_org 값을 모두 포함
- **공간 조인 목적**: 파이프의 실제 물리적 위치에 해당하는 구역 데이터만 추출
- **main58b 통합**: 이 스크립트의 출력을 사용하여 더 정확한 위치 기반 분석 가능
- **문서화**: 입력 데이터 구조와 처리 로직을 명확히 문서화

---

최종 업데이트: 2025-09-25 (데이터 구조 문서화 강화)