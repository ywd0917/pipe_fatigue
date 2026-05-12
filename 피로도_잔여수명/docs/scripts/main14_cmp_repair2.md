# main14: 피로 손상-누수공사 재작업 통합 시각화

**파일명**: `main14_cmp_repair2.py`

## 📋 개요
파이프 피로 손상(D_final)과 520 지역 재작업 위치를 통합 시각화합니다.

## 🎛️ 옵션
- `--region`: 지역 코드 (기본값: 0520)
- `--output-dir`: 출력 디렉토리 (기본값: results/main14)
- `--all`: 모든 재작업 타입을 하나의 이미지에 표시 **(기본값: True)**
- `--individual`: 각 재작업 타입별 개별 이미지 생성
- `--show`: 그래프를 화면에 표시
- `--no-interactive`: 비대화형 모드

## 📥 입력 파일

### 재작업 데이터 (필수)
- `results/main13_crop_520/누수공사_통합_520_위치추가.csv`: **통합 재작업 데이터**
  - 지상누수, 지하누수, 긴급공사, 관리대장 포함
  - main13_crop_520.py를 먼저 실행하여 생성 필요

### 피로 손상 데이터
- `results/main56_calc_fatigure/fatigue_pipe_lm.csv`: 파이프 피로 손상 데이터
- `results/main56_calc_fatigure/fatigue_sply_ls.csv`: 급수관 피로 손상 데이터

### Shapefile 데이터
- `data/raw/export_shp_*0520*/V_WTL_PIPE_LM.shp`: 파이프 shapefile
- `data/raw/export_shp_*0520*/V_WTL_SPLY_LS.shp`: 급수관 shapefile
- `data/raw/export_shp_*0520*/WEA_SMLZ_AS.shp`: 소구역 경계 (배경)

## 🚀 사용법

```bash
# 기본 실행 (모든 재작업 타입을 하나의 이미지에 표시)
python src/main14_cmp_repair2.py

# 특정 지역 분석
python src/main14_cmp_repair2.py --region 0520

# 개별 재작업 타입별 이미지 생성
python src/main14_cmp_repair2.py --individual

# 모든 타입 통합 + 개별 이미지 모두 생성
python src/main14_cmp_repair2.py --all --individual

# 결과를 화면에 표시
python src/main14_cmp_repair2.py --show
```

## 📤 출력 파일
- `results/main14/all_repair_520_pipe_fatigue.png`: 모든 재작업 통합 (기본)
- `results/main14/지상누수_520_pipe_fatigue.png`: 지상누수 + 피로 손상 (--individual 옵션시)
- `results/main14/지하누수_520_pipe_fatigue.png`: 지하누수 + 피로 손상 (--individual 옵션시)
- `results/main14/긴급공사_520_pipe_fatigue.png`: 긴급공사 + 피로 손상 (--individual 옵션시)
- `results/main14/관리대장_520_pipe_fatigue.png`: 관리대장 + 피로 손상 (--individual 옵션시)

## ✨ 주요 기능
- D_final 값에 따른 파이프 색상 코딩 (로그 스케일)
- 재작업 위치 점으로 표시 (타입별 색상 구분)
- SMLZ 배경 지도 표시
- 피로 손상 통계 정보 표시

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main14_cmp_repair2_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main13*.py`](main13*.md)
- 다음: [`main14a*.py`](main14a*.md)
