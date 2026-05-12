# main1: GIS 데이터 읽기

**파일명**: `main1_read_gis_files.py`

## 📋 개요
GIS shapefile 데이터를 읽고 기본 정보를 출력합니다.

## 🚀 사용법

```bash
python src/main1_read_gis_files.py
```

## 📥 입력 파일
- `data/raw/export_shp_*/` 디렉토리의 모든 `.shp` 파일

## 📤 출력
- 콘솔 출력: 파일별 레코드 수 및 필드 정보

## ✨ 주요 기능
- 모든 export_shp_* 디렉토리의 shapefile 읽기
- 파일별 레코드 수 및 필드 정보 출력
- FTR_IDN 통계 (최소, 최대, 고유값 수)

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main1_read_gis_files_call_graph.md)
- [GIS 데이터 필드 정의](../GIS_DATA_FIELDS.md)

## 🔗 연관 스크립트
- 다음 단계: [`main2_draw_zone.py`](main2_draw_zone.md) - Zone 영역 시각화
- 다음 단계: [`main5_match_K_soil.py`](main5_match_K_soil.md) - 파이프-토양 매칭