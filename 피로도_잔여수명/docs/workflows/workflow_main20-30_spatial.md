# 공간 통계 분석 파이프라인 (main20-30)

핫스팟 분석, 시공간 큐브, 예측 모델 등 공간 통계 분석 워크플로우입니다.

## 워크플로우 다이어그램

```mermaid
flowchart TB
    subgraph INPUT[" 입력 데이터 "]
        FATIGUE[피로도 데이터<br/>zone_fatigue_merged.csv]
        REPAIR[복구 이력 데이터]
        ZONE[구역 경계 데이터]
    end

    subgraph PREP[" 전처리 및 최적화 "]
        M20[main20_optimize_parameters.py<br/>파라미터 최적화]
        M21[main21_kfactors_dfinal_grid.py<br/>K-factors/D_final 그리드 생성]
    end

    subgraph HOTSPOT[" 핫스팟 분석 "]
        M22[main22_spatial_hotspots.py<br/>공간 핫스팟]
        M23[main23_infrastructure_risk.py<br/>인프라 위험도 평가]
    end

    subgraph SPACETIME[" 시공간 분석 "]
        M24[main24_spacetime_cube.py<br/>시공간 큐브 생성]
        M25[main25_emerging_hotspots.py<br/>출현 핫스팟 탐지]
    end

    subgraph PRIORITY[" 우선순위 및 예측 "]
        M26[main26_maintenance_priority.py<br/>유지보수 우선순위]
        M26I[main26_integrated_spatial.py<br/>통합 공간 분석]
        M27[main27_kfactors_evolution.py<br/>K-factors 진화]
        M28[main28_kfactors_prediction.py<br/>K-factors 예측]
        M29[main29_integrated_priority.py<br/>통합 우선순위]
    end

    subgraph REPORT[" 검증 및 보고 "]
        M30[main30_validation_report.py<br/>검증 보고서 생성]
    end

    subgraph OUTPUT[" 출력 "]
        O_GRID[그리드 데이터]
        O_HOTSPOT[핫스팟 결과]
        O_CUBE[시공간 큐브]
        O_PRIORITY[우선순위 목록]
        O_REPORT[검증 보고서]
    end

    %% 전처리 흐름
    FATIGUE --> M20
    FATIGUE --> M21
    M20 --> M21
    M21 --> O_GRID

    %% 핫스팟 분석
    O_GRID --> M22
    O_GRID --> M23
    M22 --> O_HOTSPOT
    M23 --> O_HOTSPOT

    %% 시공간 분석
    REPAIR --> M24
    M24 --> O_CUBE
    O_CUBE --> M25

    %% 우선순위 및 예측
    O_HOTSPOT --> M26
    O_HOTSPOT --> M26I
    O_GRID --> M27
    M27 --> M28
    M26 --> M29
    M28 --> M29
    M29 --> O_PRIORITY

    %% 검증 보고서
    O_HOTSPOT --> M30
    O_CUBE --> M30
    O_PRIORITY --> M30
    M30 --> O_REPORT

    %% 스타일
    style INPUT fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style PREP fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style HOTSPOT fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style SPACETIME fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style PRIORITY fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    style REPORT fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
    style OUTPUT fill:#f5f5f5,stroke:#9e9e9e,stroke-width:2px
```

## 실행 순서

### 1단계: 전처리 및 최적화

```bash
# 파라미터 최적화
python src/main20_optimize_parameters.py

# 그리드 생성
python src/main21_kfactors_dfinal_grid.py
```

### 2단계: 핫스팟 분석

```bash
# 공간 핫스팟
python src/main22_spatial_hotspots.py

# 인프라 위험도 평가
python src/main23_infrastructure_risk.py
```

### 3단계: 시공간 분석

```bash
# 시공간 큐브 생성
python src/main24_spacetime_cube.py

# 출현 핫스팟 탐지
python src/main25_emerging_hotspots.py
```

### 4단계: 우선순위 및 예측

```bash
# 유지보수 우선순위
python src/main26_maintenance_priority.py

# 통합 공간 분석
python src/main26_integrated_spatial.py

# K-factors 진화 분석
python src/main27_kfactors_evolution.py

# K-factors 예측
python src/main28_kfactors_prediction.py

# 통합 우선순위
python src/main29_integrated_priority.py
```

### 5단계: 검증 보고서

```bash
python src/main30_validation_report.py
```

## 입출력 파일 요약

| 스크립트 | 입력 | 출력 |
|---------|------|------|
| main20 | 피로도 데이터 | 최적화된 파라미터 |
| main21 | 피로도 데이터 | 그리드 데이터 |
| main22 | 그리드 데이터 | 핫스팟 결과 |
| main23 | 그리드 데이터 | 위험도 평가 결과 |
| main24 | 복구 이력 | 시공간 큐브 |
| main25 | 시공간 큐브 | 출현 핫스팟 |
| main26 | 핫스팟 결과 | 우선순위 목록 |
| main27 | 그리드 데이터 | K-factors 진화 결과 |
| main28 | K-factors 진화 | 예측 결과 |
| main29 | 우선순위 + 예측 | 통합 우선순위 |
| main30 | 모든 분석 결과 | 검증 보고서 |

## 관련 문서

- [공간분석 완료 보고서](../spatial_analysis_completion_report.md)
- [분석 결과 요약](../analysis_results_summary.md)
