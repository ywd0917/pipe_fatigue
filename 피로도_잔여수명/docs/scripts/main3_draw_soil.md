# main3: 지질 데이터 시각화

**파일명**: `main3_draw_soil.py`

## 📋 개요
지질학적 데이터를 시각화하여 토양 분포를 분석합니다.

## 🚀 사용법

### 통합 지질도 생성
```bash
python src/main3_draw_soil.py
```

### 개별 파일 시각화
```bash
python src/main3_draw_soil.py --file Litho --group-by age
python src/main3_draw_soil.py --file Boundary --group-by TYPE
```

### 모든 지질도 자동 생성
```bash
./main3_draw_all.sh
```

## 🎛️ 옵션
- `--file`: 특정 지질 파일 선택 (Litho/Boundary)
- `--group-by`: 그룹화 기준 필드
- `--show`: 화면에 표시
- `--no-interactive`: 비대화형 모드

## 📥 입력 파일
- `data/raw/export_shp_*/Litho*.shp`: 지질 데이터
- `data/raw/export_shp_*/Boundary*.shp`: 경계 데이터

## 📤 출력 파일
- `results/soil_*.png`: 개별 지질도
- `results/soil_integrated.png`: 통합 지질도

## ✨ 주요 기능
- 지질 데이터 시각화
- 토양 유형별 색상 구분
- 통합 지질도 생성
- 범례 자동 생성

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main3_draw_soil_call_graph.md)
- [K_SOIL 추출 방법](../K_SOIL_extraction_method.md)

## 🔗 연관 스크립트
- 이전: [`main2_draw_zone.py`](main2_draw_zone.md) - Zone 영역 시각화
- 다음: [`main4_list_soil.py`](main4_list_soil.md) - 지질 데이터 분석
- 관련: [`main5_match_K_soil.py`](main5_match_K_soil.md) - 파이프-토양 매칭