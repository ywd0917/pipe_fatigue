# main2: Zone 영역 시각화

**파일명**: `main2_draw_zone.py`

## 📋 개요
다양한 Zone 레벨(LRGZ, MDLZ, SCDZ, SMLZ)의 지리적 영역을 시각화합니다.

## 🚀 사용법

### 개별 Zone 시각화
```bash
python src/main2_draw_zone.py --zone lrgz  # 대구역
python src/main2_draw_zone.py --zone mdlz  # 중구역
python src/main2_draw_zone.py --zone scdz  # 중간구역
python src/main2_draw_zone.py --zone smlz  # 소구역
```

### 특정 파일 시각화
```bash
python src/main2_draw_zone.py --file V_WTL_PIPE_LM.shp
```

### 모든 Zone 자동 생성
```bash
./main2_draw_all.sh
```

## 🎛️ 옵션
- `--zone`: Zone 레벨 선택 (lrgz/mdlz/scdz/smlz)
- `--file`: 특정 shapefile 시각화
- `--output`: 출력 파일 경로
- `--show`: 화면에 표시
- `--no-interactive`: 비대화형 모드

## 📥 입력 파일
- `data/raw/export_shp_*/` 디렉토리의 Zone shapefile

## 📤 출력 파일
- `results/zone_*.png`: Zone별 시각화 이미지
- `results/*_PIPE_LM.png`: 파이프 네트워크 이미지

## ✨ 주요 기능
- Zone 레벨별 지리적 영역 시각화
- 경계선 및 라벨 표시
- 파이프 네트워크 오버레이
- 한글 폰트 자동 설정

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main2_draw_zone_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main1_read_gis_files.py`](main1_read_gis_files.md) - GIS 데이터 읽기
- 다음: [`main3_draw_soil.py`](main3_draw_soil.md) - 지질 데이터 시각화