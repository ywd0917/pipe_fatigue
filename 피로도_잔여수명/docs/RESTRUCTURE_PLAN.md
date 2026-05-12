# main51-55 결과물 폴더 구조화 계획

## 📋 개요

main51~main55 스크립트의 출력 파일을 `results/` 루트에서 각각의 전용 서브 디렉토리로 이동하여 파일 관리를 체계화합니다.

## 🎯 목표

- ✅ 결과 파일을 스크립트별 전용 폴더에 정리
- ✅ 의존 스크립트의 입력 경로 자동 업데이트
- ✅ 문서와 코드 불일치 해소
- ✅ 일관된 출력 패턴 확립 (main56~58과 동일)

## 📊 현재 파일 구조 분석

### main51_find_freq.py (주파수 분석)
**출력 위치:** `results/` (6개 PNG 파일)
```
frequency_spectrum_0243 소구역 압력 데이터.png
frequency_spectrum_0461 소구역 압력 데이터.png
frequency_spectrum_0470 소구역 압력 데이터.png
frequency_spectrum_0480 소구역 압력 데이터.png
frequency_spectrum_0490 소구역 압력 데이터.png
frequency_spectrum_0520 중구역 압력 데이터.png
component_separation_analysis.png (추가 확인 필요)
```
**사용처:** 없음 (독립 분석)

### main52_pass_filter.py (신호 필터링)
**출력 위치:** `results/` (6개 PNG 파일)
```
valley_based_filter_0243 소구역 압력 데이터.png
valley_based_filter_0461 소구역 압력 데이터.png
valley_based_filter_0470 소구역 압력 데이터.png
valley_based_filter_0480 소구역 압력 데이터.png
valley_based_filter_0490 소구역 압력 데이터.png
valley_based_filter_0520 중구역 압력 데이터.png
```
**사용처:** 없음 (독립 분석, pass_filter.py 모듈로 재계산)

### main53_rainflow.py (Rainflow Counting)
**출력 위치:** `results/` (25개 파일)
```
# 히스토그램 (12개 PNG)
rainflow_high_pass_*.png (6개)
rainflow_low_pass_*.png (6개)

# 누적 분포 (12개 PNG)
cumulative_high_pass_*.png (6개)
cumulative_low_pass_*.png (6개)

# 비교 데이터 (1개 CSV)
fatigue_comparison.csv
```
**사용처:** 없음 (시각화 전용)

### main54_pipe_data.py (관망 데이터 처리)
**출력 위치:** `results/` (샘플 CSV)
```
pipe_data_sample.csv (현재 존재 여부 확인 필요)
```
**사용처:** 없음 (탐색용)

### main55_calc_fatigure.py (피로도 계산 - K_repair 미적용)
**출력 위치:** `results/` (2개 CSV)
```
fatigue_pipe_lm_by_age.csv
fatigue_sply_ls_by_age.csv
```
**사용처:**
- `main23_infrastructure_risk.py` (인프라 위험도 평가)
- `main14c_subregion_correlations.py` (참조만, 직접 사용 안 함)

## 🔄 변경 계획

### Phase 1: 현재 상태 확인 및 라인 번호 검증

#### 1.1 파일 존재 여부 확인
```bash
# 이동할 파일 확인
ls -la results/*.png results/*.csv 2>/dev/null | grep -E "(frequency_spectrum|valley_based|rainflow|cumulative|fatigue_comparison|pipe_data_sample|fatigue_pipe_lm_by_age|fatigue_sply_ls_by_age)"
```

#### 1.2 코드 라인 번호 검증
각 Phase의 변경 위치가 실제 코드와 일치하는지 확인:
- [ ] main51_find_freq.py 라인 212-250, 274-413
- [ ] main52_pass_filter.py 라인 48-143
- [ ] main53_rainflow.py 라인 87-90, 149-152, 247-294, 320-322
- [ ] main54_pipe_data.py 라인 46-51, 140-143
- [ ] rainflow_processing.py 라인 669-672
- [ ] main23_infrastructure_risk.py 라인 156-159
- [ ] main14c_subregion_correlations.py 라인 332-333
- [ ] analyze11_remaining_life_distribution.py 라인 26-31

#### 1.3 백업 (선택사항)
```bash
# results/ 디렉토리 백업 (권장)
cp -r results results.backup.$(date +%Y%m%d_%H%M%S)
```

---

### Phase 2: main51 출력 폴더 구조화

#### 2.1 코드 변경
**파일:** `src/main51_find_freq.py`

**변경 위치 1:** `visualize_frequency_analysis()` 함수 (라인 212-250)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main51_find_freq"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

**변경 위치 2:** `visualize_component_separation()` 함수 (라인 274-413)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main51_find_freq"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

#### 2.2 문서 변경
**파일:** `docs/scripts/main51_find_freq.md`

**변경:** 출력 파일 경로 (라인 30-38)
```markdown
# Before
- `results/frequency_spectrum_0470_소구역_압력_데이터.png`
- `results/frequency_spectrum_0520_중구역_압력_데이터.png`
- `results/component_separation_analysis.png`

# After
- `results/main51_find_freq/frequency_spectrum_0470_소구역_압력_데이터.png`
- `results/main51_find_freq/frequency_spectrum_0520_중구역_압력_데이터.png`
- `results/main51_find_freq/component_separation_analysis.png`
```

---

### Phase 3: main52 출력 폴더 구조화

#### 3.1 코드 변경
**파일:** `src/main52_pass_filter.py`

**변경 위치:** `create_pass_filter_visualization()` 함수 (라인 48-143)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)
output_dir.mkdir(exist_ok=True)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main52_pass_filter"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

#### 3.2 문서 변경
**파일:** `docs/scripts/main52_pass_filter.md`

**변경:** 출력 파일 경로 (라인 28-35)
```markdown
# Before
- `results/valley_based_filter_0470_소구역_압력_데이터.png`
- `results/valley_based_filter_0520_중구역_압력_데이터.png`

# After
- `results/main52_pass_filter/valley_based_filter_0470_소구역_압력_데이터.png`
- `results/main52_pass_filter/valley_based_filter_0520_중구역_압력_데이터.png`
```

---

### Phase 4: main53 출력 폴더 구조화

#### 4.1 코드 변경
**파일:** `src/main53_rainflow.py`

**변경 위치 1:** `perform_rainflow_analysis()` 함수 (라인 87-90)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main53_rainflow"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

**변경 위치 2:** `create_cumulative_analysis()` 함수 (라인 149-152)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main53_rainflow"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

**변경 위치 3:** `save_comparison_results()` 함수 (라인 247-294)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main53_rainflow"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

**변경 위치 4:** `main()` 함수 (라인 320-322)
```python
# Before
output_dir = RESULTS_DIR
Path(output_dir).mkdir(exist_ok=True)

# After
output_dir = RESULTS_DIR / "main53_rainflow"
Path(output_dir).mkdir(parents=True, exist_ok=True)
```

#### 4.2 문서 변경
**파일:** `docs/scripts/main53_rainflow.md`

**변경:** 출력 파일 경로 (라인 31-49)
```markdown
# Before
### 히스토그램 그래프
- `results/rainflow_original_0470_소구역_압력_데이터.png`
...

# After
### 히스토그램 그래프
- `results/main53_rainflow/rainflow_original_0470_소구역_압력_데이터.png`
...

### 비교 분석 데이터
- `results/main53_rainflow/fatigue_comparison.csv`
```

---

### Phase 5: main54 출력 폴더 구조화

#### 5.1 코드 변경
**파일:** `src/main54_pipe_data.py`

**변경 위치:** `save_sample_data()` 함수 (라인 46-51)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
else:
    output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main54_pipe_data"
else:
    output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

**변경 위치 2:** `process_and_analyze_all_files()` 함수 (라인 140-143)
```python
# Before
if output_dir is None:
    output_dir = RESULTS_DIR
output_dir = Path(output_dir)

# After
if output_dir is None:
    output_dir = RESULTS_DIR / "main54_pipe_data"
output_dir = Path(output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
```

#### 5.2 문서 변경
**파일:** `docs/scripts/main54_pipe_data.md`

**변경:** 출력 파일 경로 (라인 38-45)
```markdown
# Before
### 샘플 데이터
- `results/pipe_lm_sample.csv`
  - PIPE_LM 데이터의 대표 샘플 (1000건)

- `results/sply_ls_sample.csv`
  - SPLY_LS 데이터의 대표 샘플 (1000건)

# After
### 샘플 데이터
- `results/main54_pipe_data/pipe_lm_sample.csv`
  - PIPE_LM 데이터의 대표 샘플 (1000건)

- `results/main54_pipe_data/sply_ls_sample.csv`
  - SPLY_LS 데이터의 대표 샘플 (1000건)
```

---

### Phase 6: main55 출력 폴더 구조화

#### 6.1 코드 변경
**파일:** `src/rainflow_processing.py`

**변경 위치:** `process_all_pipe_data_with_rainflow()` 함수 (라인 669-672)
```python
# Before
output_filename = f"fatigue_{file_stem}_by_age.csv"
output_path = RESULTS_DIR / output_filename

# After
output_dir = RESULTS_DIR / "main55_calc_fatigure"
output_dir.mkdir(parents=True, exist_ok=True)
output_filename = f"fatigue_{file_stem}_by_age.csv"
output_path = output_dir / output_filename
```

#### 6.2 문서 변경
**파일:** `docs/scripts/main55_calc_fatigure.md`

**변경:** 출력 디렉토리 및 파일 경로 (라인 66-76)
```markdown
# Before
출력 디렉토리: `results/main55/`

### fatigue_pipe_lm.csv (84개 컬럼)
### fatigue_sply_ls.csv (84개 컬럼)

# After
출력 디렉토리: `results/main55_calc_fatigure/`

### fatigue_pipe_lm_by_age.csv (84개 컬럼)
### fatigue_sply_ls_by_age.csv (84개 컬럼)
```

---

### Phase 7: 의존 스크립트 업데이트

#### 7.1 main57_merge_fatigue.py 확인

**현재 상태:** main56만 참조 (src/main57_merge_fatigue.py 라인 272-274)
```python
main56_dir = RESULTS_DIR / "main56_calc_fatigure"
pipe_lm_path = main56_dir / "fatigue_pipe_lm.csv"
sply_ls_path = main56_dir / "fatigue_sply_ls.csv"
```

**변경 불필요** - main57은 main56만 사용하므로 변경 없음
- main56은 이미 별도 디렉토리(`results/main56_calc_fatigure/`) 사용
- main55의 경로 변경이 main57에 영향 없음

#### 7.2 main23_infrastructure_risk.py 업데이트

**파일:** `src/main23_infrastructure_risk.py`

**변경 위치:** 파일 경로 리스트 (라인 156-159)
```python
# Before
"results/fatigue_pipe_lm_by_age.csv",
"results/fatigue_sply_ls_by_age.csv",

# After
"results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv",
"results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv",
```

#### 7.3 main14c_subregion_correlations.py 업데이트

**파일:** `src/main14c_subregion_correlations.py`

**변경 위치:** 에러 메시지 (라인 332-333)
```python
# Before
print("   - fatigue_pipe_lm_by_age.csv")
print("   - fatigue_sply_ls_by_age.csv")

# After
print("   - results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv")
print("   - results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv")
```

#### 7.4 main13c_zone_fatigue_merge.py 확인

**파일:** `src/main13c_zone_fatigue_merge.py`

**현재 상태:** main56만 참조 (라인 26, 313-316)
```python
FATIGUE_DATA_DIR = RESULTS_DIR / "main56_calc_fatigure"  # 라인 26

# 라인 313-316
fatigue_pipe_lm = load_fatigue_csv(
    FATIGUE_DATA_DIR / "fatigue_pipe_lm.csv", "PIPE_LM"
)
fatigue_sply_ls = load_fatigue_csv(
    FATIGUE_DATA_DIR / "fatigue_sply_ls.csv", "SPLY_LS"
)
```

**변경 불필요** - main13c는 main56만 사용하므로 변경 없음
- main56은 이미 별도 디렉토리(`results/main56_calc_fatigure/`) 사용
- main55의 경로 변경이 main13c에 영향 없음

#### 7.5 analysis/analyze11_remaining_life_distribution.py 업데이트

**파일:** `src/analysis/analyze11_remaining_life_distribution.py`

**변경 위치:** 파일 경로 리스트 (라인 26-31)
```python
# Before
file_paths = [
    "results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv",
    "results/fatigue_pipe_lm_by_age.csv",
    "results/fatigue_sply_ls_by_age.csv",
    "results/main57_merge_fatigue/merged_fatigue_analysis.csv"
]

# After
file_paths = [
    "results/main13c_zone_fatigue_merge/zone_fatigue_merged.csv",
    "results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv",
    "results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv",
    "results/main57_merge_fatigue/merged_fatigue_analysis.csv"
]
```

**참고:** 이 스크립트는 여러 경로를 순차적으로 시도하는 보조 분석 도구이므로, 경로 변경 시에도 다른 파일을 찾을 수 있어 영향도가 낮습니다.

---

### Phase 8: 기존 파일 이동

#### 8.1 개선된 마이그레이션 스크립트 작성

**새 파일:** `scripts/migrate_results_structure.sh`

```bash
#!/bin/bash

# main51-55 결과 파일을 새 폴더 구조로 이동
# 실행 전에 백업 권장: cp -r results results.backup

set -e  # 에러 발생 시 중단

echo "=== main51-55 결과 파일 구조 재정리 ==="
echo ""

# main51
echo "📁 main51_find_freq 처리 중..."
mkdir -p results/main51_find_freq
if ls results/frequency_spectrum_*.png 1> /dev/null 2>&1; then
    mv results/frequency_spectrum_*.png results/main51_find_freq/
    echo "  ✓ frequency_spectrum_*.png 이동 완료"
else
    echo "  ⚠ frequency_spectrum_*.png 없음 (이미 이동 또는 미생성)"
fi
if [ -f results/component_separation_analysis.png ]; then
    mv results/component_separation_analysis.png results/main51_find_freq/
    echo "  ✓ component_separation_analysis.png 이동 완료"
else
    echo "  ⚠ component_separation_analysis.png 없음"
fi

# main52
echo ""
echo "📁 main52_pass_filter 처리 중..."
mkdir -p results/main52_pass_filter
if ls results/valley_based_filter_*.png 1> /dev/null 2>&1; then
    mv results/valley_based_filter_*.png results/main52_pass_filter/
    echo "  ✓ valley_based_filter_*.png 이동 완료"
else
    echo "  ⚠ valley_based_filter_*.png 없음 (이미 이동 또는 미생성)"
fi

# main53
echo ""
echo "📁 main53_rainflow 처리 중..."
mkdir -p results/main53_rainflow
moved=0
if ls results/rainflow_*.png 1> /dev/null 2>&1; then
    mv results/rainflow_*.png results/main53_rainflow/
    echo "  ✓ rainflow_*.png 이동 완료"
    ((moved++))
fi
if ls results/cumulative_*.png 1> /dev/null 2>&1; then
    mv results/cumulative_*.png results/main53_rainflow/
    echo "  ✓ cumulative_*.png 이동 완료"
    ((moved++))
fi
if [ -f results/fatigue_comparison.csv ]; then
    mv results/fatigue_comparison.csv results/main53_rainflow/
    echo "  ✓ fatigue_comparison.csv 이동 완료"
    ((moved++))
fi
if [ $moved -eq 0 ]; then
    echo "  ⚠ main53 파일 없음 (이미 이동 또는 미생성)"
fi

# main54
echo ""
echo "📁 main54_pipe_data 처리 중..."
mkdir -p results/main54_pipe_data
if [ -f results/pipe_data_sample.csv ]; then
    mv results/pipe_data_sample.csv results/main54_pipe_data/
    echo "  ✓ pipe_data_sample.csv 이동 완료"
else
    echo "  ⚠ pipe_data_sample.csv 없음 (이미 이동 또는 미생성)"
fi

# main55
echo ""
echo "📁 main55_calc_fatigure 처리 중..."
mkdir -p results/main55_calc_fatigure
moved=0
if [ -f results/fatigue_pipe_lm_by_age.csv ]; then
    mv results/fatigue_pipe_lm_by_age.csv results/main55_calc_fatigure/
    echo "  ✓ fatigue_pipe_lm_by_age.csv 이동 완료"
    ((moved++))
fi
if [ -f results/fatigue_sply_ls_by_age.csv ]; then
    mv results/fatigue_sply_ls_by_age.csv results/main55_calc_fatigure/
    echo "  ✓ fatigue_sply_ls_by_age.csv 이동 완료"
    ((moved++))
fi
if [ $moved -eq 0 ]; then
    echo "  ⚠ main55 파일 없음 (이미 이동 또는 미생성)"
fi

echo ""
echo "=== 이동 완료 ==="
echo ""
echo "📂 새 폴더 구조:"
ls -la results/main5*/ 2>/dev/null || echo "  (생성된 폴더 없음)"
```

#### 8.2 스크립트 실행
```bash
chmod +x scripts/migrate_results_structure.sh
./scripts/migrate_results_structure.sh
```

---

### Phase 9: 변경사항 실행 테스트

#### 9.1 출력 경로 변경 테스트
각 스크립트를 실행하여 새 경로에 파일이 생성되는지 확인:
```bash
# 개별 스크립트 테스트 (선택적)
python src/main51_find_freq.py  # results/main51_find_freq/ 확인
python src/main52_pass_filter.py  # results/main52_pass_filter/ 확인
python src/main53_rainflow.py  # results/main53_rainflow/ 확인
python src/main54_pipe_data.py  # results/main54_pipe_data/ 확인
python src/main55_calc_fatigure.py  # results/main55_calc_fatigure/ 확인
```

#### 9.2 입력 경로 변경 테스트
의존 스크립트가 새 경로에서 파일을 정상적으로 읽는지 확인:
```bash
python src/main23_infrastructure_risk.py  # main55 출력 읽기 확인
python src/main14c_subregion_correlations.py  # main55 출력 참조 확인
python src/analysis/analyze11_remaining_life_distribution.py  # main55 출력 읽기 확인
```

#### 9.3 변경 불필요 스크립트 확인
```bash
python src/main57_merge_fatigue.py  # main56만 사용, 영향 없음 확인
python src/main13c_zone_fatigue_merge.py  # main56만 사용, 영향 없음 확인
```

---

### Phase 10: 문서 업데이트

#### 10.1 워크플로우 문서
**파일:** `docs/workflows/workflow_main51-58_fatigue.md`

**변경 1:** Mermaid 다이어그램 출력 노드 (라인 36-48)
```markdown
# Before
subgraph OUT55[" results/main55/ "]
    O55_1[fatigue_pipe_lm.csv]
    O55_2[fatigue_sply_ls.csv]
end

# After
subgraph OUT51[" results/main51_find_freq/ "]
    O51[frequency_spectrum_*.png]
end

subgraph OUT52[" results/main52_pass_filter/ "]
    O52[valley_based_filter_*.png]
end

subgraph OUT53[" results/main53_rainflow/ "]
    O53_1[rainflow_*.png]
    O53_2[cumulative_*.png]
    O53_3[fatigue_comparison.csv]
end

subgraph OUT54[" results/main54_pipe_data/ "]
    O54[pipe_data_sample.csv]
end

subgraph OUT55[" results/main55_calc_fatigure/ "]
    O55_1[fatigue_pipe_lm_by_age.csv]
    O55_2[fatigue_sply_ls_by_age.csv]
end
```

**변경 2:** 입출력 파일 요약 테이블 (라인 138-149)
```markdown
# Before
| main51 | 압력 데이터 | 주파수 분석 결과 |
| main52 | 압력 데이터 | 필터링된 데이터 |
| main53 | 필터링된 데이터 | Rainflow 결과 |
| main54 | PIPE_LM, SPLY_LS | 처리된 파이프 데이터 |
| main55 | 토양/교통 데이터 | results/main55/*.csv |

# After
| main51 | 압력 데이터 | results/main51_find_freq/*.png |
| main52 | 압력 데이터 | results/main52_pass_filter/*.png |
| main53 | 필터링된 데이터 | results/main53_rainflow/*.png, *.csv |
| main54 | PIPE_LM, SPLY_LS | results/main54_pipe_data/*.csv |
| main55 | 토양/교통 데이터 | results/main55_calc_fatigure/fatigue_*_by_age.csv |
```

**변경 3:** 워크플로우 다이어그램의 main57 연결 관계 명확화
```markdown
# 변경 전: OUT55와 OUT56 모두 M57로 연결
OUT55 --> M57
OUT56 --> M57

# 변경 후: OUT56만 M57로 연결 (실제 코드와 일치)
OUT56 --> M57

# 이유: main57은 main56의 출력만 사용 (코드 참조: src/main57_merge_fatigue.py:272)
```

#### 10.2 main23_infrastructure_risk.md 업데이트 (필수)
**파일:** `docs/scripts/main23_infrastructure_risk.md`

**현재 상태:** 입력 파일 정보 없음 (라인 14-15만 출력 정보)
```markdown
## 📤 출력 파일
- `results/spatial_analysis/infrastructure_risk/`
```

**변경 방법:** 라인 14 앞에 입력 파일 섹션 삽입
```markdown
## 📥 입력 파일

### 피로 손상 데이터
- `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv` - PIPE_LM 피로 손상 데이터
  - K-factors 및 D_final 값 포함
  - 지역별(0243, 0461, 0470, 0480, 0490, 0520) 피로 분석 결과
- `results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv` - SPLY_LS 피로 손상 데이터
  - K-factors 및 D_final 값 포함
  - 지역별 피로 분석 결과

### GIS 데이터
- `data/raw/export_shp_*/` - GIS shapefile 데이터
- (기타 공간 분석 입력 데이터)

## 📤 출력 파일
- `results/spatial_analysis/infrastructure_risk/`
```

**중요:** 스크립트 문서는 입출력 파일이 명시되어야 하는 규칙에 따라 **필수 변경**

#### 10.3 main14c_subregion_correlations.md 업데이트 (필수)
**파일:** `docs/scripts/main14c_subregion_correlations.md`

**현재 상태:** 구 경로(`data/pipe_fatigue/`) 사용 중
```markdown
## 📥 입력 파일
- `results/지상누수_520_위치추가.csv`: 지상누수 재작업 위치
- `results/지하누수_520_위치추가.csv`: 지하누수 재작업 위치
- `data/pipe_fatigue/fatigue_pipe_lm_by_age.csv`: 파이프 K-factors 및 D_final 데이터
- `data/pipe_fatigue/fatigue_sply_ls_by_age.csv`: 급수관 K-factors 및 D_final 데이터
- `data/raw/export_shp_20250704(0520)/V_WTL_PIPE_LM.shp`: 파이프 LineString geometry
```

**변경:** 입력 파일 경로 (라인 21-22)
```markdown
# Before
- `data/pipe_fatigue/fatigue_pipe_lm_by_age.csv`: 파이프 K-factors 및 D_final 데이터
- `data/pipe_fatigue/fatigue_sply_ls_by_age.csv`: 급수관 K-factors 및 D_final 데이터

# After
- `results/main55_calc_fatigure/fatigue_pipe_lm_by_age.csv`: 파이프 K-factors 및 D_final 데이터
- `results/main55_calc_fatigure/fatigue_sply_ls_by_age.csv`: 급수관 K-factors 및 D_final 데이터
```

**중요:**
- 이 문서는 구 경로(`data/pipe_fatigue/`)를 사용하므로 **필수 변경**
- 실제 코드는 이미 올바른 경로를 사용 중이므로 문서만 업데이트

#### 10.4 main13c_zone_fatigue_merge.md 확인
**파일:** `docs/scripts/main13c_zone_fatigue_merge.md`

**현재 상태:** 이미 올바른 경로 사용 (라인 43, 47)
```markdown
- `results/main56_calc_fatigure/fatigue_pipe_lm.csv`
- `results/main56_calc_fatigure/fatigue_sply_ls.csv`
```

**변경 불필요** - main13c는 main56 경로를 사용하므로 영향 없음

#### 10.5 INDEX.md 업데이트
**파일:** `docs/INDEX.md`

스크립트 설명에 정확한 출력 경로 추가 (라인 90-101)

---

### Phase 11: 최종 검증 및 커밋

#### 11.1 코드 라인 번호 검증
문서에 명시된 라인 번호가 실제 코드와 일치하는지 최종 확인:
```bash
# 각 파일의 Before 코드가 실제 존재하는지 확인
grep -n "output_dir = RESULTS_DIR" src/main51_find_freq.py
grep -n "output_dir = RESULTS_DIR" src/main52_pass_filter.py
grep -n "output_dir = RESULTS_DIR" src/main53_rainflow.py
grep -n "output_dir = RESULTS_DIR" src/main54_pipe_data.py
grep -n "output_path = RESULTS_DIR" src/rainflow_processing.py
```

#### 11.2 경로 일관성 검증
구 경로 잔존 여부 최종 확인:
```bash
# 코드에서 구 경로 확인
grep -r "results/fatigue_pipe_lm_by_age.csv" src/
grep -r "results/fatigue_sply_ls_by_age.csv" src/

# 문서에서 구 경로 확인
grep -r "results/fatigue_pipe_lm_by_age.csv" docs/
grep -r "data/pipe_fatigue/" docs/
```

#### 11.3 체크리스트

**코드 변경 검증 (8개 파일)**
- [ ] main51_find_freq.py: 출력 경로 변경 완료
- [ ] main52_pass_filter.py: 출력 경로 변경 완료
- [ ] main53_rainflow.py: 출력 경로 변경 완료
- [ ] main54_pipe_data.py: 출력 경로 변경 완료
- [ ] rainflow_processing.py: main55 출력 경로 변경 완료
- [ ] main23_infrastructure_risk.py: main55 입력 경로 변경 완료
- [ ] main14c_subregion_correlations.py: main55 참조 경로 변경 완료
- [ ] analyze11_remaining_life_distribution.py: main55 입력 경로 변경 완료

**문서 변경 검증 (10개 파일)**
- [ ] main51_find_freq.md: 출력 경로 업데이트
- [ ] main52_pass_filter.md: 출력 경로 업데이트
- [ ] main53_rainflow.md: 출력 경로 업데이트
- [ ] main54_pipe_data.md: 출력 경로 업데이트
- [ ] main55_calc_fatigure.md: 출력 경로 및 파일명 업데이트
- [ ] main23_infrastructure_risk.md: 입력 파일 섹션 추가
- [ ] main14c_subregion_correlations.md: 입력 경로 업데이트
- [ ] main13c_zone_fatigue_merge.md: 경로 확인 (변경 불필요)
- [ ] workflow_main51-58_fatigue.md: 다이어그램 및 테이블 업데이트
- [ ] INDEX.md: 스크립트 설명 업데이트

**실행 테스트 검증**
- [ ] main51-55 실행 테스트 완료
- [ ] main23, main14c, analyze11 실행 테스트 완료
- [ ] main57, main13c 영향 없음 확인

**Git 커밋**
- [ ] Phase별 커밋 완료
- [ ] 최종 변경사항 검토

---

## 📝 변경 요약

### 코드 변경 (8개 파일)
1. `src/main51_find_freq.py` - 출력 디렉토리 경로 (2곳)
2. `src/main52_pass_filter.py` - 출력 디렉토리 경로 (1곳)
3. `src/main53_rainflow.py` - 출력 디렉토리 경로 (4곳)
4. `src/main54_pipe_data.py` - 출력 디렉토리 경로 (2곳)
5. `src/rainflow_processing.py` - main55 출력 디렉토리 (1곳)
6. `src/main23_infrastructure_risk.py` - main55 입력 경로 (2곳)
7. `src/main14c_subregion_correlations.py` - main55 참조 메시지 (2곳)
8. `src/analysis/analyze11_remaining_life_distribution.py` - main55 입력 경로 (2곳)

**변경 불필요 (참고용):**
- `src/main57_merge_fatigue.py` - main56만 사용
- `src/main13c_zone_fatigue_merge.py` - main56만 사용

### 문서 변경 (10개 파일)

**출력 경로 문서 (main51-55)**
1. `docs/scripts/main51_find_freq.md` - 출력 경로 업데이트
2. `docs/scripts/main52_pass_filter.md` - 출력 경로 업데이트
3. `docs/scripts/main53_rainflow.md` - 출력 경로 업데이트
4. `docs/scripts/main54_pipe_data.md` - 출력 경로 업데이트
5. `docs/scripts/main55_calc_fatigure.md` - 출력 경로 및 파일명 업데이트

**입력 경로 문서 (main55 사용 스크립트)**
6. `docs/scripts/main23_infrastructure_risk.md` - 입력 파일 섹션 추가 (필수, 라인 14 앞에 삽입)
7. `docs/scripts/main14c_subregion_correlations.md` - 입력 경로 업데이트 (필수, 라인 21-22)

**참조 문서 (main56 사용, 변경 불필요)**
8. `docs/scripts/main13c_zone_fatigue_merge.md` - 이미 올바른 경로 사용 (확인용)

**워크플로우 및 인덱스**
9. `docs/workflows/workflow_main51-58_fatigue.md` - 다이어그램 및 테이블, main57 연결 수정
10. `docs/INDEX.md` - 스크립트 설명 업데이트

**주의사항:**
- workflow 다이어그램에서 OUT55 → M57 연결 제거 (main57은 main56만 사용)
- **모든 스크립트 문서는 입출력 파일이 명시되어야 함** (프로젝트 규칙)
- main23: 입력 정보 없음 → 입력 섹션 추가 필수
- main14c: 구 경로(`data/pipe_fatigue/`) 사용 → 경로 변경 필수

### 새 파일 생성 (1개)
1. `scripts/migrate_results_structure.sh` - 개선된 파일 이동 스크립트 (피드백 포함)

---

## 🎯 기대 효과

1. **일관된 폴더 구조**: main56-58과 동일한 패턴 (`results/main{N}/`)
2. **가독성 향상**: results/ 루트 디렉토리 정리 (파일 → 서브 폴더로 분류)
3. **유지보수 용이**: 스크립트별 출력물 명확히 구분
4. **문서-코드 일치**: 모든 불일치 해소
5. **안전한 마이그레이션**: 명확한 피드백과 에러 처리

---

## 🔄 Phase 실행 순서

1. **Phase 1**: 현재 상태 확인 및 라인 번호 검증
2. **Phase 2-6**: 코드 및 문서 변경 (main51-55)
3. **Phase 7**: 의존 스크립트 업데이트 (main23, main14c, analyze11)
4. **Phase 8**: 기존 파일 이동 (마이그레이션 스크립트 실행)
5. **Phase 9**: 변경사항 실행 테스트
6. **Phase 10**: 워크플로우 및 INDEX.md 문서 업데이트
7. **Phase 11**: 최종 검증 및 커밋

---

## ⚠️ 주의사항

1. **Phase 순서 준수**: 코드 변경 → 파일 이동 → 테스트 → 문서 순서로 진행
2. **라인 번호 검증**: Phase 1에서 문서의 라인 번호가 실제 코드와 일치하는지 확인
3. **백업**: Phase 1에서 백업 권장
4. **Git 커밋**: Phase별로 커밋하여 롤백 가능하도록 관리
5. **의존성 확인**: 다음 스크립트들이 정상 동작하는지 Phase 9에서 확인
   - main23_infrastructure_risk.py (main55 출력 사용)
   - main14c_subregion_correlations.py (main55 출력 참조)
   - analysis/analyze11_remaining_life_distribution.py (main55 출력 사용)
   - main57_merge_fatigue.py (main56 출력 사용, 영향 없음)
   - main13c_zone_fatigue_merge.py (main56 출력 사용, 영향 없음)

---

최종 업데이트: 2025-12-10 (Phase 순서 재배치 및 검증 강화)
