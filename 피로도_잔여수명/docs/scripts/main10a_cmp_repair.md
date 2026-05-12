# main10a: 피로 손상 통합 시각화

**파일명**: `main10a_cmp_repair.py`

## 📋 개요
- 파이프 피로 손상(D_final)과 복구 작업을 통합 시각화합니다.
- `main10_cmp_repair.py`를 개선함. 누수공사 데이터로 `K_repair` 를 반영한 피로도로 처리.
- `fatigue-damage`프로젝트의 `main6_...py`를 실행처리 한 후에 진행해야 함! (main13b...md 참고)

## 🎛️ 옵션
- `--regions`: 분석할 지역 코드 목록 (기본값: 0520 0903)
- `--output-dir`: 출력 디렉토리 (기본값: results/main10a)
- `--show`: 그래프를 화면에 표시
- `--no-repair`: 복구 작업 점 표시 안함
- `--no-interactive`: 비대화형 모드로 실행

## 📥 입력 파일

### 피로 손상 데이터
- `results/main56_calc_fatigure/fatigue_pipe_lm.csv`: 파이프 피로 손상 데이터
- `results/main56_calc_fatigure/fatigue_sply_ls.csv`: 급수관 피로 손상 데이터

### Shapefile 데이터
- `data/raw/export_shp_*{지역}*/V_WTL_PIPE_LM.shp`: 파이프 shapefile
- `data/raw/export_shp_*{지역}*/V_WTL_SPLY_LS.shp`: 급수관 shapefile
- `data/raw/export_shp_*{지역}*/WEA_SMLZ_AS.shp`: 소구역 경계 (배경)

### 복구 작업 데이터 (선택사항)
- 다양한 위치의 복구 작업 CSV 파일들
- load_all_repair_data 함수로 자동 탐색 및 로드

## 🚀 사용법

```bash
# 기본 실행 (0520, 0903 지역)
python src/main10a_cmp_repair.py

# 특정 지역만 분석
python src/main10a_cmp_repair.py --regions 0520

# 여러 지역 분석
python src/main10a_cmp_repair.py --regions 0520 0903 0470

# 복구 작업 제외하고 피로 손상만 표시
python src/main10a_cmp_repair.py --no-repair

# 결과를 화면에 표시
python src/main10a_cmp_repair.py --show

# 출력 디렉토리 지정
python src/main10a_cmp_repair.py --output-dir results/custom_output

# 비대화형 모드로 실행
python src/main10a_cmp_repair.py --no-interactive
```

## 📤 출력 파일
- `results/main10a/{지역}_pipe_fatigue_with_repair.png`: 피로 손상 + 복구 작업 통합 이미지
- `results/main10a/{지역}_pipe_fatigue_only.png`: 피로 손상만 표시 (--no-repair 옵션 사용시)

## ✨ 주요 기능
- D_final 값에 따른 파이프 색상 코딩
- 로그 스케일 컬러맵 적용 (1e-5 ~ 1e-1)
- 복구 작업 위치 점으로 오버레이
- SMLZ 배경 지도 표시
- 지역별 통합 분석
- 피로 손상 통계 정보 표시

## 📊 시각화 요소
- **파이프 색상**: D_final 값에 따른 그라데이션 (파란색→노란색→빨간색)
- **복구 작업 점**: 작업 유형별 색상 구분
- **배경**: SMLZ(소구역) 경계선
- **컬러바**: 로그 스케일 D_final 값 범위 표시
- **통계 정보**: 피로 손상 통계 텍스트 박스

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main10a_cmp_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main9_draw_repair.py`](main9_draw_repair.md) - 복구 작업 시각화
- 다음: [`main11_convert_addr2loc.py`](main11_convert_addr2loc.md) - 주소 지오코딩