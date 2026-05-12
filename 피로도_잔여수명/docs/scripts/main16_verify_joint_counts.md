# main16: Joint 검증

**파일명**: `main16_verify_joint_counts.py`

## 📋 개요
main15에서 계산한 CNT_JNT (Joint 연결 수) 값의 정확성을 시각적으로 검증합니다.
각 CNT_JNT 값별로 샘플을 선택하여 연결점과 연결 타입을 명확히 표시합니다.

## 🎛️ 옵션
- `--max-samples`: CNT_JNT 값별 최대 샘플 수 (기본값: 5)
- `--output-dir`: 출력 디렉토리 (기본값: results/main16)

## 📥 입력 파일

### Joint 데이터 (필수)
- `results/main15_extract_joint_data/PIPE_LM_JOINT.csv`: PIPE_LM Joint 세그먼트 데이터
- `results/main15_extract_joint_data/SPLY_LS_JOINT.csv`: SPLY_LS Joint 세그먼트 데이터
  - main15_extract_joint_data.py 실행 후 생성된 파일

### Shapefile 데이터 (필수)
- `data/raw/export_shp_*0520*/V_WTL_PIPE_LM.shp`: 파이프 shapefile
- `data/raw/export_shp_*0520*/V_WTL_SPLY_LS.shp`: 급수관 shapefile

### Joint Shapefile (선택사항)
- `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`: PIPE_LM Joint shapefile
- `results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`: SPLY_LS Joint shapefile
  - 존재하면 사용, 없으면 CSV 기반으로 재생성

## 🚀 사용법

```bash
# 기본 실행 (CNT_JNT별 최대 5개 샘플)
python src/main16_verify_joint_counts.py

# 샘플 수 조정
python src/main16_verify_joint_counts.py --max-samples 10

# 출력 디렉토리 지정
python src/main16_verify_joint_counts.py --output-dir results/custom_verification
```

## 📤 출력 파일
- `results/main16/pipe_cnt_{CNT_JNT}_sample_{번호}.png`: 각 샘플별 시각화 이미지
  - 제목: FTR_IDN, CNT_JNT 값, 세그먼트 길이
  - 빨간색 세그먼트: 검증 대상
  - 파란색 원: 연결점
  - 주변 파이프: 회색으로 표시

## ✨ 주요 기능
- CNT_JNT별 샘플 시각화
- 연결점과 타입 표시 (파란색 원)
- 다양한 길이 샘플링 (짧은 것부터 긴 것까지)
- 버퍼 영역 내 모든 파이프 표시
- 연결 타입별 구분 (직접/간접)

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main16_verify_joint_counts_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main15*.py`](main15*.md)
- 다음: [`main16a*.py`](main16a*.md)
