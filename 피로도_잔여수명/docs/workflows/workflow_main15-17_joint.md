# Joint 분석 파이프라인 (main15-17)

파이프 Joint 데이터 추출, 검증, 복구 작업과의 상관관계 분석 워크플로우입니다.

## 워크플로우 다이어그램

```mermaid
flowchart TB
    subgraph INPUT[" 입력 데이터 "]
        PIPE[관망 데이터<br/>PIPE_LM, SPLY_LS]
        REPAIR[복구 데이터<br/>지오코딩된 복구 이력]
    end

    M15[main15_extract_joint_data.py<br/>Joint 데이터 추출]

    subgraph OUT15[" results/main15_extract_joint_data/ "]
        O15_1[joint_pipe_lm.csv]
        O15_2[joint_sply_ls.csv]
    end

    M16[main16_verify_joint_counts.py<br/>Joint 수 검증]

    subgraph OUT16[" 검증 결과 "]
        O16[검증 보고서]
    end

    M17[main17_cmp_recovery2.py<br/>Joint + 복구 비교 분석]

    subgraph OUT17[" 분석 결과 "]
        O17[비교 분석 결과]
    end

    M17A[main17a_duplicate_cnt_jnt_correlation.py<br/>중복 재작업-CNT_JNT 상관관계]

    subgraph OUT17A[" 상관관계 분석 "]
        O17A[상관관계 결과]
    end

    M17A2[main17a2_distance_sensitivity.py<br/>거리별 민감도 분석]

    subgraph OUT17A2[" 민감도 분석 "]
        O17A2[10m~100m 민감도 결과]
    end

    %% Joint 추출
    PIPE --> M15
    M15 --> OUT15

    %% 검증
    OUT15 --> M16
    M16 --> OUT16

    %% 비교 분석
    OUT15 --> M17
    REPAIR --> M17
    M17 --> OUT17

    %% 상관관계 분석
    OUT15 --> M17A
    REPAIR --> M17A
    M17A --> OUT17A

    %% 민감도 분석
    OUT15 --> M17A2
    REPAIR --> M17A2
    M17A2 --> OUT17A2

    %% 스타일
    style INPUT fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style OUT15 fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style OUT16 fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style OUT17 fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style OUT17A fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    style OUT17A2 fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
```

## 실행 순서

### 1단계: Joint 데이터 추출

```bash
python src/main15_extract_joint_data.py
```

### 2단계: Joint 수 검증

```bash
python src/main16_verify_joint_counts.py
```

### 3단계: 복구 작업 비교 분석

```bash
python src/main17_cmp_recovery2.py
```

### 4단계: 상관관계 분석

```bash
# 중복 재작업과 CNT_JNT 상관관계
python src/main17a_duplicate_cnt_jnt_correlation.py

# 거리별 민감도 분석 (10m~100m)
python src/main17a2_distance_sensitivity.py
```

## 입출력 파일 요약

| 스크립트 | 입력 | 출력 |
|---------|------|------|
| main15 | PIPE_LM, SPLY_LS | results/main15_extract_joint_data/*.csv |
| main16 | main15 결과 | 검증 보고서 |
| main17 | Joint 데이터 + 복구 데이터 | 비교 분석 결과 |
| main17a | Joint 데이터 + 복구 데이터 | 상관관계 분석 결과 |
| main17a2 | Joint 데이터 + 복구 데이터 | 거리별 민감도 결과 |

## 관련 문서

- [Joint 연결 수 계산](../joint_calculation.md)
- [main15_extract_joint_data.md](../scripts/main15_extract_joint_data.md)
- [main16_verify_joint_counts.md](../scripts/main16_verify_joint_counts.md)
