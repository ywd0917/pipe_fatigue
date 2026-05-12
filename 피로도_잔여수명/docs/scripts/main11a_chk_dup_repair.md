# main11a: 복구 데이터 중복 검사

**파일명**: `main11a_chk_dup_repair.py`

## 📋 개요
복구 작업 CSV 파일에서 접수번호 중복을 검사합니다.

## 🚀 사용법

```bash
python src/main11a_chk_dup_repair.py  # 두 CSV 파일의 접수번호 중복 검사
```

## 📥 입력 파일
- `data/repair/긴급복구.csv`: 긴급복구 데이터
- `data/repair/긴급복구공사관리(0520).csv`: 긴급복구공사관리 데이터

## 📤 출력 파일
- `results/duplicate_check_{timestamp}.csv`: 중복 검사 결과
- 중복유형: 파일 내부 중복 / 파일 간 중복
- 접수번호, 중복횟수, 파일명
- 긴급복구.csv: 684개 접수번호, 파일 내 중복 없음
- 긴급복구공사관리(0520).csv: 254개 접수번호, 파일 내 중복 없음

## ✨ 주요 기능
- '지시번호'가 '계' 또는 '소계'인 행 제외
- 접수번호가 있는 행만 처리
- 각 파일 내 중복 검사
- 두 파일 간 중복 검사
- 중복 상세 정보 출력

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11a_chk_dup_repair_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11*.py`](main11*.md)
- 다음: [`main11b*.py`](main11b*.md)
