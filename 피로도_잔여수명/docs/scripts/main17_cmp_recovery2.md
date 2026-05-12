# main17: 파이프 네트워크 통합 시각화

**파일명**: `main17_cmp_repair2.py`

## 📋 개요
main15에서 생성한 Joint 데이터와 main13에서 생성한 복구 작업 데이터를 통합 시각화합니다.
CNT_JNT(파이프 연결 복잡도)와 복구 작업 위치의 관계를 시각적으로 분석합니다.

## 🎯 옵션
- `--input-dir`: 입력 디렉토리 (기본값: results)
- `--output-dir`: 출력 디렉토리 (기본값: results)
- `--all`: 모든 복구 타입을 하나의 이미지로 통합

## 📥 입력 파일

### Joint Shapefile (필수)
- `results/shapefiles/PIPE_LM_JOINT.shp`: PIPE_LM Joint shapefile
- `results/shapefiles/SPLY_LS_JOINT.shp`: SPLY_LS Joint shapefile
  - main15_extract_joint_data.py 실행 후 생성된 파일
  - CNT_JNT 필드 포함 (연결 복잡도)

### 복구 작업 데이터 (필수)
- `results/지상누수_520_위치추가.csv`: 지상누수 복구 작업 데이터
- `results/지하누수_520_위치추가.csv`: 지하누수 복구 작업 데이터
- `results/기타공사_520_위치추가.csv`: 기타공사 복구 작업 데이터
  - main13_crop_520.py 실행 후 생성된 파일
  - 필수 필드: 위도, 경도

## 🚀 사용법

```bash
# 각 복구 타입별 개별 이미지 생성 (기본)
python src/main17_cmp_repair2.py

# 모든 복구 타입 통합 이미지 생성
python src/main17_cmp_repair2.py --all

# 입출력 디렉토리 지정
python src/main17_cmp_repair2.py --input-dir data/processed --output-dir results/main17
```

## 📤 출력 파일

### 기본 모드 (--all 없이)
- `results/pipe_repair_지상누수.png`: PIPE+SPLY 네트워크와 지상누수 복구 위치
- `results/pipe_repair_지하누수.png`: PIPE+SPLY 네트워크와 지하누수 복구 위치
- `results/pipe_repair_기타공사.png`: PIPE+SPLY 네트워크와 기타공사 복구 위치

### 통합 모드 (--all)
- `results/pipe_repair_all.png`: 모든 파이프와 모든 복구 작업 통합 시각화

## ✨ 주요 기능

### CNT_JNT 색상 코딩
- CNT_JNT = 0: 파란색 (연결 없음)
- CNT_JNT = 1: 초록색 (단순 연결)
- CNT_JNT = 2: 노란색
- CNT_JNT = 3: 주황색
- CNT_JNT = 4: 빨간색
- CNT_JNT = 5: 보라색
- CNT_JNT ≥ 6: 검은색 (매우 복잡)

### 복구 작업 표시
- 지상누수: 진한 핑크색 점
- 지하누수: 파란색 점
- 기타공사: 갈색 점

### 파이프 타입 구분
- PIPE_LM: 두꺼운 선 (1.5pt)
- SPLY_LS: 얇은 선 (0.5pt)

## 📦 이미지 사양
- 해상도: 300 DPI
- 크기: 32 x 24 인치
- 파이프 투명도: 70%
- 복구 위치 투명도: 60%

## 📊 통계 분석
시각화와 함께 다음 통계를 출력:
- CNT_JNT별 파이프 세그먼트 수
- 복구 타입별 위치 수
- 파이프 타입별 통계

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main17_cmp_repair2_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main16_verify_joint_counts.py`](main16_verify_joint_counts.md) - Joint 검증
- 이전: [`main13_crop_520.py`](main13_crop_520.md) - 복구 데이터 준비
- 다음: [`main18_analyze_duplicate_repairs.py`](main18_analyze_duplicate_repairs.md)
