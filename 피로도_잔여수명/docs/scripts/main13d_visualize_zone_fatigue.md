# main13d: 구역별 피로 손상 데이터 시각화

**파일명**: `main13d_visualize_zone_fatigue.py`

## 📋 개요
- main13c에서 생성한 구역별 피로 손상 데이터를 지도 위에 시각화하는 스크립트입니다.
- **시각화 데이터 통계 (총 4,569개 파이프)**:
  - PIPE_LM: 978개 (21.4%)
  - SPLY_LS: 3,591개 (78.6%)
- **구역별 분포**:
  - 0470 지역: 1,142개
  - 0480 지역: 1,523개  
  - 0490 지역: 1,904개
- **시각화 특징**:
  - 구역별 색상 구분 (0470: 빨간색, 0480: 청록색, 0490: 파란색, 0520: 연두색)
  - 파이프 종류별 두께 차별화 (설정 가능한 상수로 조정)
  - 하위 구역 경계선 표시 (점선)

## 🚀 사용법

```bash
# 기본 실행 (기본 크기 16×12 inch)
python src/main13d_visualize_zone_fatigue.py

# 이미지 크기 조정
python src/main13d_visualize_zone_fatigue.py --scale 2    # 2배 크기 (32×24 inch)
python src/main13d_visualize_zone_fatigue.py --scale 0.5  # 0.5배 크기 (8×6 inch)
python src/main13d_visualize_zone_fatigue.py --scale 0.75 # 0.75배 크기 (12×9 inch)

# 디버그 모드
python src/main13d_visualize_zone_fatigue.py --debug

# 입출력 디렉토리 지정
python src/main13d_visualize_zone_fatigue.py \
  --input-dir results/main13c_zone_fatigue_merge \
  --output-dir results/custom_output
```

## 📥 입력 파일
- `results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv`: 구역별 피로 손상 통합 데이터
  - DATA_SRC: 파이프 종류 (PIPE_LM, SPLY_LS)
  - zone: 구역 번호 (0470, 0480, 0490, 0520)
  - FTR_IDN: 파이프 고유 ID
  - K-factors 및 D_final 값
- `data/raw/export_shp_20250704(0520)/WEA_MDLZ_AS.shp`: 0520 지역 경계
- `data/raw/export_shp_20250704(0520)/WEA_SMLZ_AS.shp`: 하위 구역 경계 (0470, 0480, 0490)
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: PIPE_LM geometry
- `data/raw/export_shp_20250704(0520)/V_WTL_SPLY_LS.shp`: SPLY_LS geometry

## 📤 출력 파일
- `results/main13d_visualize_zone_fatigue/zone_fatigue_map.png`: 구역별 피로 손상 시각화 지도
  - 기본 해상도: 300 DPI
  - 크기: --scale 옵션에 따라 가변
  - 파일 크기: 약 200-500KB (scale에 따라 변동)

## ✨ 주요 기능

### 1. 구역 경계 표시
- 0520 전체 지역 경계 (굵은 검은색 선)
- 0470, 0480, 0490 하위 구역 경계 (점선)
- 각 구역 중심에 라벨 표시

### 2. 파이프 시각화
- **zone별 색상 구분**:
  - 0470: #FF6B6B (빨간색 계열)
  - 0480: #4ECDC4 (청록색 계열)
  - 0490: #45B7D1 (파란색 계열)
  - 0520: #95E77E (연두색 계열)
- **파이프 종류별 두께** (상수로 설정 가능):
  - PIPE_LM: 선 두께 1 (기본값, `PIPE_LM_LINE_WIDTH` 상수로 조정 가능)
  - SPLY_LS: 선 두께 0.3 (기본값, `SPLY_LS_LINE_WIDTH` 상수로 조정 가능)

### 3. 통계 정보 표시
- 좌측 상단: 구역별 파이프 수 통계
- 우측 상단: 범례 (구역 색상, 파이프 종류)

### 4. 스케일 조정 기능
- docs/visualization_rules.md 표준 준수
- 양의 실수 모두 가능 (0.25, 1.5, 3.14 등)
- 메모리 효율적인 이미지 생성

### 5. 설정 가능한 상수
파일 상단에서 다음 상수들을 수정하여 시각화 스타일 조정 가능:
- `PIPE_LM_LINE_WIDTH`: PIPE_LM 파이프 선 두께 (기본값: 1)
- `SPLY_LS_LINE_WIDTH`: SPLY_LS 파이프 선 두께 (기본값: 0.3)

## ⚙️ 명령줄 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--input-dir` | main13c 출력 디렉토리 | `results/main13c_zone_fatigue_merge` |
| `--output-dir` | 결과 저장 디렉토리 | `results/main13d_visualize_zone_fatigue` |
| `--scale` | 이미지 크기 배율 | `1.0` |
| `--debug` | 디버그 모드 활성화 | `False` |

## 🔗 관련 문서
- [main13c_zone_fatigue_merge.py](main13c_zone_fatigue_merge.md) - 구역별 피로 손상 데이터 병합 (선행 작업)
- [main13_crop_520.py](main13_crop_520.md) - 520 지역 데이터 추출
- [visualization_rules.md](../visualization_rules.md) - 시각화 표준 가이드

## 📊 처리 성능
- 데이터 로드: 약 0.5초 (4,569개 파이프)
- Geometry 매칭: 약 0.3초
- 시각화 생성: 약 0.5초
- 전체 실행 시간: 약 2-3초

## 💡 사용 팁
1. **큰 이미지가 필요한 경우**: `--scale 2` 이상 사용
2. **웹 게시용**: `--scale 0.5`로 작은 크기 생성
3. **프레젠테이션용**: `--scale 1.5`로 적당한 크기
4. **인쇄용**: `--scale 4`로 고해상도 생성

## ⚠️ 주의사항
- main13c를 먼저 실행하여 입력 데이터 생성 필요
- 메모리 사용량은 scale 값에 비례하여 증가
- scale > 4 사용 시 충분한 메모리 확보 필요 (>8GB)

---

최종 업데이트: 2025-09-02