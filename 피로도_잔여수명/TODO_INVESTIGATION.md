# Results 폴더 파일 삭제 원인 조사

## 발생한 문제
- pytest 실행 후 results 폴더의 파일들이 모두 삭제됨
- duplicate_4plus_statistics.txt 파일만 남아있음
- 시점: pytest --ignore=tests/main14_common -v --tb=short 실행 후

## 의심 목록 (우선순위 순)

### 1. ⚠️ pytest 실행 중 results 폴더에 접근한 테스트 파일들
다음 테스트 파일들이 RESULTS_DIR 또는 results 경로를 사용함:
- [x] **test_main14b2_distance_sensitivity.py** - ⚠️ **원인 발견!** 
  - 171번 줄: `Path("results")` 직접 사용
  - 실제 results 폴더에 파일 생성 후 삭제
  - **수정 완료**: tmp_path 사용하도록 변경
- [ ] **test_main13a_calculate_k_repair.py** - RESULTS_DIR import 확인 필요
- [ ] **test_common_config.py** - ProjectConfig 테스트, RESULTS_DIR 초기화 관련
- [ ] **test_main8_verify_overlap_samples.py** - results 폴더 접근 가능성
- [ ] **test_main15_extract_joint_data.py** - results 폴더 접근 가능성

### 2. 🔍 tearDown 메서드 관련
다음 테스트들이 tearDown에서 디렉토리를 삭제함:
- [ ] test_main23_hotspot_infrastructure.py - `shutil.rmtree(self.temp_dir)`
- [ ] test_main13a_calculate_k_repair.py - `shutil.rmtree(self.test_dir)`
- [ ] test_main19a.py - `shutil.rmtree(self.temp_dir)`
- [ ] test_common_geocoding_singleton.py - `shutil.rmtree(self.temp_dir)`

**확인 사항**: temp_dir이나 test_dir이 실수로 results를 가리키는지?

### 3. 📁 ProjectConfig 초기화 관련
- [ ] src/common/config.py:48 - `self.RESULTS_DIR.mkdir(exist_ok=True)`
- [ ] 이 코드가 실제로 파일을 삭제하는지 재확인
- [ ] 테스트 중 ProjectConfig가 여러 번 재초기화되는지

### 4. 🧪 main18 관련 테스트
- [ ] test_main18_analyze_duplicate_repairs.py가 실제 results 폴더를 사용하는지
- [ ] duplicate_4plus_statistics.txt가 언제 생성되었는지
- [ ] save_results 함수가 mock되지 않고 실제로 실행되었는지

### 5. 💾 Coverage 관련
- [ ] pytest의 --cov-report=html이 results 폴더에 영향을 주는지
- [ ] htmlcov 디렉토리 생성 과정에서 다른 폴더가 영향받는지

### 6. 🗑️ 명시적인 삭제 코드
- [ ] run_tests.py:214 - `Path(path).unlink()` 코드 확인
- [ ] 어떤 경로가 삭제 대상인지 확인

### 7. 🔄 임시 디렉토리 사용 패턴
- [ ] tmp_path, tempfile.mkdtemp()가 results를 가리키는 경우가 있는지
- [ ] 테스트에서 results를 임시 디렉토리로 사용하는지

## 조사 방법

### Step 1: 각 테스트 파일의 results 폴더 접근 코드 확인
```python
# 찾아볼 패턴들:
- RESULTS_DIR 변수 사용
- Path("results") 또는 Path("./results")
- output_dir = results 관련
- 임시 디렉토리가 results로 설정되는 경우
```

### Step 2: tearDown 메서드 상세 분석
```python
# 각 tearDown에서:
- self.temp_dir의 실제 경로 확인
- shutil.rmtree() 호출 전 경로 검증
```

### Step 3: 실제 테스트 실행 추적
```bash
# 한 테스트씩 실행하며 results 폴더 모니터링
pytest tests/test_xxx.py -v
ls -la results/  # 각 테스트 후 확인
```

### Step 4: main18 테스트 격리 실행
```bash
# main18 테스트만 단독 실행
pytest tests/test_main18_analyze_duplicate_repairs.py -v
# results 폴더 상태 확인
```

## 현재까지 확인된 사실

1. ✅ pytest --ignore=tests/main14_common 실행 시 1023개 테스트 통과
2. ✅ results 폴더는 .gitignore에 포함되어 git 추적 안됨
3. ✅ 31개의 main 스크립트가 src.common.config를 import
4. ✅ ProjectConfig 초기화 시 results 폴더 생성 (mkdir(exist_ok=True))
5. ✅ duplicate_4plus_statistics.txt는 main18_analyze_duplicate_repairs.py가 생성

## 🎯 원인 발견 및 해결

### 발견된 문제
`test_main14b2_distance_sensitivity.py`의 `test_run_main14b_success` 메서드에서:
- **Line 171**: `Path("results")` 직접 사용 - 실제 results 폴더에 접근
- **Line 172**: `mkdir(parents=True, exist_ok=True)` - results 폴더 재생성
- **Line 188-193**: finally 블록에서 생성한 파일 삭제

### 수정 내용
```python
# 변경 전
csv_file = Path("results") / "0520_repair_k_factors_matched.csv"

# 변경 후  
csv_file = tmp_path / "results" / "0520_repair_k_factors_matched.csv"
```

### 영향
- pytest 실행 시 실제 results 폴더를 건드리지 않음
- 테스트는 임시 디렉토리(tmp_path)에서만 작업
- results 폴더의 기존 파일들이 보호됨

## 다음 단계

1. ✅ test_main14b2_distance_sensitivity.py 수정 완료
2. 다른 테스트 파일들도 동일한 문제가 있는지 확인
3. pytest 재실행하여 문제 해결 확인