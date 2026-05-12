# main15: 파이프 세그먼트 분리

**파일명**: `main15_extract_joint_data.py`

## 📋 개요
파이프를 세그먼트로 분리하고 Joint 연결 수를 계산합니다.

## 🚀 사용법

```bash
python src/main15_extract_joint_data.py
```

## 📥 입력 파일
- `data/raw/export_shp_*0520*/V_WTL_PIPE_LM.shp`: 파이프 네트워크 shapefile
- 필수 필드: FTR_IDN, geometry (LineString)

## 📤 출력 파일

### CSV 파일
- `results/main15_extract_joint_data/PIPE_LM_JOINT.csv`: PIPE_LM Joint 세그먼트 데이터
- `results/main15_extract_joint_data/SPLY_LS_JOINT.csv`: SPLY_LS Joint 세그먼트 데이터
  - FTR_IDN: 세그먼트 고유 ID
  - ORIG_FTR_IDN: 원본 파이프 ID
  - SUB_IDN: 세그먼트 번호 (1, 2, 3...)
  - SEGMENT_LENGTH: 세그먼트 길이 (m)
  - IS_SEMICIRCULAR: 반원형 여부
  - CNT_JNT: Joint 연결 수

### Shapefile
- `results/main15_extract_joint_data/shapefiles/PIPE_LM_JOINT.shp`: PIPE_LM Joint shapefile
- `results/main15_extract_joint_data/shapefiles/SPLY_LS_JOINT.shp`: SPLY_LS Joint shapefile

## ✨ 주요 기능
- LineString을 개별 세그먼트로 분리
- SUB_IDN 부여 (1, 2, 3...)
- CNT_JNT (연결 수) 계산

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main15_extract_joint_data_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main14*.py`](main14*.md)
- 다음: [`main15a*.py`](main15a*.md)
