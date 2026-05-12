# main5: 파이프-토양 매칭

**파일명**: `main5_match_K_soil.py`

## 📋 개요
파이프라인과 토양 데이터를 매칭하여 K_SOIL 값을 할당합니다.

## 🚀 사용법

### 모든 버전 처리
```bash
python src/main5_match_K_soil.py
```

### 특정 버전만 처리
```bash
python src/main5_match_K_soil.py --version 0520
```

## 📥 입력 파일
- `data/raw/export_shp_*/V_WTL_PIPE_LM.shp`: 파이프 데이터
- `data/raw/export_shp_*/V_WTL_SPLY_LS.shp`: 급수관 데이터
- `data/raw/export_shp_*/Litho*.shp`: 지질 데이터

## 📤 출력 파일
- `results/lithoidx_list_with_K_SOIL.csv`: K_SOIL 매핑 테이블
- `results/*_pipe_soil.csv`: 파이프-토양 매칭 결과
- `results/*_supply_soil.csv`: 급수관-토양 매칭 결과

## ✨ 주요 기능
- Lithoidx-K_SOIL 매핑 테이블 생성
- 파이프/급수관과 토양 데이터 공간 매칭
- 최대 10개까지 교차 지역 처리
- 가중 평균 K_SOIL 계산

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main5_match_K_soil_call_graph.md)
- [K_SOIL 추출 방법](../K_SOIL_extraction_method.md)

## 🔗 연관 스크립트
- 이전: [`main4_list_soil.py`](main4_list_soil.md) - 지질 데이터 분석
- 다음: [`main6_draw_road.py`](main6_draw_road.md) - 도로 네트워크 시각화