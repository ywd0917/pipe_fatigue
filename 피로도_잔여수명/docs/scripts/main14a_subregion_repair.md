# main14a: 하위 지역 분석

**파일명**: `main14a_subregion_repair.py`

## 📋 개요
0470, 0480, 0490 하위 지역별 피로 손상 시각화입니다.

## 🎛️ 옵션
- `--region`: 하위 지역 코드 (0470, 0480, 0490 중 선택, 기본값: 0470)
- `--output-dir`: 출력 디렉토리 (기본값: results/main14a)
- `--all`: 모든 재작업 타입을 하나의 이미지에 표시 **(기본값: True)**
- `--individual`: 각 재작업 타입별 개별 이미지 생성
- `--show`: 그래프를 화면에 표시

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
- `data/raw/export_shp_*{하위지역}*/WEA_SMLZ_AS.shp`: 하위 지역 경계 (0470, 0480, 0490)

## ✨ 주요 기능
- WEA_SMLZ_AS.shp에서 경계 추출
- 하위 지역 경계 빨간색 표시
- 부모 지역(0520) 데이터에서 공간 필터링
- 통합 CSV 파일 우선 사용 (main13_crop_520 결과)
- 4가지 재작업 타입 지원 (지상누수, 지하누수, 긴급공사, 관리대장)

## 🚀 사용법

```bash
# 기본 실행 (모든 재작업 타입 통합)
python src/main14a_subregion_repair.py --region 0470
python src/main14a_subregion_repair.py --region 0480
python src/main14a_subregion_repair.py --region 0490

# 개별 재작업 타입별 이미지 생성
python src/main14a_subregion_repair.py --region 0470 --individual
python src/main14a_subregion_repair.py --region 0480 --individual
python src/main14a_subregion_repair.py --region 0490 --individual
```

## 📤 출력 파일
- `results/main14a/all_repair_{지역}_pipe_fatigue.png`: 모든 재작업 통합 (기본)
- `results/main14a/{복구타입}_{지역}_pipe_fatigue.png`: 개별 타입 (--individual 옵션시)

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main14a_subregion_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main14*.py`](main14*.md)
- 다음: [`main14b*.py`](main14b*.md)
