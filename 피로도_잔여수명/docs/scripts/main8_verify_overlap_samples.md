# main8: 중첩 검증

**파일명**: `main8_verify_overlap_samples.py`

## 📋 개요
파이프-도로 중첩 결과를 시각적으로 검증합니다.

## 🚀 사용법

### 기본 실행
```bash
python src/main8_verify_overlap_samples.py  # 첫 번째 지역 자동 선택
```

### 특정 지역 검증
```bash
python src/main8_verify_overlap_samples.py 0520
python src/main8_verify_overlap_samples.py 0903
```

### 옵션 사용
```bash
python src/main8_verify_overlap_samples.py --pipe-type sply  # 급수관
python src/main8_verify_overlap_samples.py --sample-size 12  # 샘플 크기
python src/main8_verify_overlap_samples.py --show  # 화면 표시
```

### 일괄 테스트
```bash
./main8_verify_all.sh   # 모든 조합 테스트
./main8_verify_test.sh  # 특정 케이스만
```

## 🎛️ 옵션
- `--pipe-type`: 파이프 유형 (pipe/sply)
- `--sample-size`: 샘플 크기
- `--show`: 화면에 표시

## 📥 입력 파일
- `results/traffic/*_pipe_traffic.csv`: 파이프-도로 매칭 결과
- `results/traffic/*_sply_traffic.csv`: 급수관-도로 매칭 결과

## 📤 출력 파일
- `results/overlap_verification/verification_*_*_samples.png`

## ✨ 주요 기능
- 중첩 분석 결과의 시각적 검증
- 샘플링을 통한 품질 확인
- 파이프와 도로의 실제 위치 표시

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main8_verify_overlap_samples_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main7_pipe_traffic.py`](main7_pipe_traffic.md) - 파이프-도로 중첩 분석
- 다음: [`main9_draw_repair.py`](main9_draw_repair.md) - 복구 작업 시각화