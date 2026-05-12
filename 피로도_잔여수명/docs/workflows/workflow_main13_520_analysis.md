# 520 지역 분석 파이프라인 (main13 시리즈)

520 지역 데이터 추출 및 K_repair 계산, 구역별 피로 손상 분석 워크플로우입니다.

## 워크플로우 다이어그램

```mermaid
flowchart TB
    subgraph INPUT[" 입력 데이터 "]
        FULL[전체 관망 데이터<br/>PIPE_LM, SPLY_LS]
        REPAIR[복구 이력 데이터<br/>지오코딩된 복구 데이터]
        FATIGUE[피로도 결과<br/>results/main56_calc_fatigure/]
        ZONE[구역 경계<br/>WEA_SMLZ_AS.shp]
    end

    M13[main13_crop_520.py<br/>520 지역 추출]

    subgraph OUT13[" results/main13/ "]
        O13[520_pipe_lm.csv<br/>520_sply_ls.csv]
    end

    M13A[main13a_calculate_k_repair.py<br/>K_repair 계산]

    subgraph OUT13A[" results/main13a_k_repair/ "]
        O13A1[repair_pipe_lm.csv]
        O13A2[repair_sply_ls.csv]
    end

    M13C[main13c_zone_fatigue_merge.py<br/>구역별 피로 손상 병합]

    subgraph OUT13C[" results/main13c/ "]
        O13C[zone_fatigue_merged.csv]
    end

    M13D[main13d_visualize_zone_fatigue.py<br/>구역별 피로 손상 시각화]

    M13F[main13f_visualize_high_k_repair.py<br/>K_repair 상위 파이프 시각화]

    subgraph VIS[" 시각화 출력 "]
        V1[구역별 피로 손상 지도]
        V2[고위험 파이프 지도]
    end

    %% 520 추출
    FULL --> M13
    M13 --> OUT13

    %% K_repair 계산
    REPAIR --> M13A
    OUT13 --> M13A
    M13A --> OUT13A

    %% 구역별 병합
    FATIGUE --> M13C
    ZONE --> M13C
    M13C --> OUT13C

    %% 시각화
    OUT13C --> M13D
    M13D --> V1

    OUT13A --> M13F
    M13F --> V2

    %% 스타일
    style INPUT fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style OUT13 fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style OUT13A fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style OUT13C fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style VIS fill:#fce4ec,stroke:#e91e63,stroke-width:2px
```

## 실행 순서

### 1단계: 520 지역 데이터 추출

```bash
python src/main13_crop_520.py
```

### 2단계: K_repair 계산

```bash
python src/main13a_calculate_k_repair.py
```

### 3단계: 구역별 피로 손상 병합

```bash
# 먼저 main56 실행 필요
python src/main56_calc_fatigure.py

# 구역별 병합
python src/main13c_zone_fatigue_merge.py
```

### 4단계: 시각화

```bash
# 구역별 피로 손상 시각화
python src/main13d_visualize_zone_fatigue.py

# K_repair 상위 파이프 시각화
python src/main13f_visualize_high_k_repair.py
```

## 입출력 파일 요약

| 스크립트 | 입력 | 출력 |
|---------|------|------|
| main13 | 전체 관망 데이터 | results/main13/520_*.csv |
| main13a | 복구 이력 + 520 데이터 | results/main13a_k_repair/repair_*.csv |
| main13c | 피로도 결과 + 구역 경계 | results/main13c/zone_fatigue_merged.csv |
| main13d | 병합된 피로 손상 | 시각화 이미지 |
| main13f | K_repair 결과 | 시각화 이미지 |

## 관련 문서

- [main13a_calculate_k_repair.md](../scripts/main13a_calculate_k_repair.md)
- [main13c_zone_fatigue_merge.md](../scripts/main13c_zone_fatigue_merge.md)
- [피로도 계산 공식](../fatigue_calculation_formula.md)
