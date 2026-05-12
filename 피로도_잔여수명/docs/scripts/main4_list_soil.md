# main4: 지질 데이터 분석

**파일명**: `main4_list_soil.py`

## 📋 개요
Lithoidx (지질 인덱스) 데이터를 분석하고 통계를 생성합니다.

## 🚀 사용법

### 전체 lithoidx 리스트
```bash
python src/main4_list_soil.py
```

### 상위 N개만 출력
```bash
python src/main4_list_soil.py --top 10
```

### 특정 lithoidx 검색
```bash
python src/main4_list_soil.py --search 123
python src/main4_list_soil.py --search "화강암"
```

### CSV 파일로 저장
```bash
python src/main4_list_soil.py --csv
```

## 🎛️ 옵션
- `--top N`: 상위 N개만 출력
- `--search`: 특정 lithoidx 또는 키워드 검색
- `--csv`: CSV 파일로 저장

## 📥 입력 파일
- `data/raw/export_shp_*/Litho*.shp`: 지질 데이터

## 📤 출력 파일
- `results/lithoidx_list.csv`: lithoidx 통계 데이터

## ✨ 주요 기능
- Lithoidx 값 집계 및 통계
- 빈도 분석
- 검색 및 필터링
- CSV 내보내기

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main4_list_soil_call_graph.md)
- [K_SOIL 추출 방법](../K_SOIL_extraction_method.md)

## 🔗 연관 스크립트
- 이전: [`main3_draw_soil.py`](main3_draw_soil.md) - 지질 데이터 시각화
- 다음: [`main5_match_K_soil.py`](main5_match_K_soil.md) - 파이프-토양 매칭