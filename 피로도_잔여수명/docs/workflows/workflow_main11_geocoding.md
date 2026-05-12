# 지오코딩 파이프라인 (main11 시리즈)

복구 작업 데이터의 주소를 좌표로 변환하고 병합하는 워크플로우입니다.

## 워크플로우 다이어그램

```mermaid
flowchart TB
    subgraph INPUT[" 입력 데이터 "]
        E1[긴급공사 파일들<br/>지상누수, 지하누수, 기타공사]
        E2[관리대장 파일들<br/>복구 관리 대장]
        ADDR[주소 데이터]
    end

    subgraph MERGE_STEP[" 데이터 병합 "]
        M11A[main11a_chk_dup_repair.py<br/>긴급공사 병합 + 중복검사]
        M11B[main11b_merge_n_add2loc.py<br/>관리대장 병합]
    end

    subgraph GEOCODE[" 지오코딩 "]
        M11[main11_convert_addr2loc.py<br/>주소→좌표 변환]
        M11C[main11c_cvrt_addr2loc.py<br/>주소 지오코딩]
    end

    subgraph VALIDATE[" 검증 및 보정 "]
        M11D[main11d_cmp_dup.py<br/>중복 비교 분석]
        M11F[main11f_check_indoor.py<br/>실내 위치 검증]
        M11G[main11g_fix_area_no.py<br/>구역번호 수정]
    end

    subgraph FINAL[" 최종 병합 "]
        M11E[main11e_merge_all_repairs.py<br/>전체 복구 데이터 병합]
    end

    subgraph OUTPUT[" 출력 데이터 "]
        O1[병합된 긴급공사.csv]
        O2[병합된 관리대장.csv]
        O3[좌표 추가된 데이터.csv]
        O4[전체 복구 데이터.csv]
        O5[구역번호 수정된 데이터.csv]
    end

    %% 병합 흐름
    E1 --> M11A
    E2 --> M11B
    M11A --> O1
    M11B --> O2

    %% 지오코딩 흐름
    ADDR --> M11
    ADDR --> M11C
    O1 --> M11C
    O2 --> M11C
    M11 --> O3
    M11C --> O3

    %% 검증 흐름
    O3 --> M11D
    O3 --> M11F

    %% 최종 병합
    O3 --> M11E
    M11E --> O4

    %% 구역번호 수정
    O4 --> M11G
    M11G --> O5

    %% 스타일
    style INPUT fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style MERGE_STEP fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style GEOCODE fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style VALIDATE fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    style FINAL fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style OUTPUT fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
```

## 실행 순서

### 1단계: 데이터 병합

```bash
# 긴급공사 파일 병합 (중복 검사 포함)
python src/main11a_chk_dup_repair.py

# 관리대장 파일 병합
python src/main11b_merge_n_add2loc.py
```

### 2단계: 지오코딩

```bash
# 주소를 좌표로 변환
python src/main11_convert_addr2loc.py

# 또는 별도 지오코딩
python src/main11c_cvrt_addr2loc.py
```

### 3단계: 검증

```bash
# 중복 비교 분석
python src/main11d_cmp_dup.py

# 실내 위치 검증
python src/main11f_check_indoor.py
```

### 4단계: 최종 병합

```bash
# 전체 복구 데이터 병합
python src/main11e_merge_all_repairs.py
```

### 5단계: 구역번호 수정

```bash
# 좌표 기반 중구역/소구역 번호 수정
python src/main11g_fix_area_no.py
```

## 입출력 파일 요약

| 스크립트 | 입력 | 출력 |
|---------|------|------|
| main11a | 긴급공사 파일들 | 병합된 긴급공사.csv |
| main11b | 관리대장 파일들 | 병합된 관리대장.csv |
| main11/11c | 주소 데이터 | 좌표 추가된 데이터 |
| main11d | 좌표 데이터 | 중복 분석 결과 |
| main11e | 개별 복구 데이터 | 전체 병합 복구 데이터 |
| main11f | 좌표 데이터 | 실내 검증 결과 |
| main11g | 복구 데이터 | 구역번호 수정된 데이터 |

## 관련 문서

- [지오코딩 사용법](../geocoding_usage.md)
- [지오코딩 최적화](../geocoding_optimization.md)
