# main11d: 중복 작업 검출

**파일명**: `main11d_cmp_dup.py`

## 📋 개요
위치추가 CSV 파일들에서 동일 날짜/위치의 중복 작업을 찾습니다.

## 📥 입력 파일
- `results/지상누수_위치추가.csv`: 지상누수 작업 데이터
- `results/지하누수_위치추가.csv`: 지하누수 작업 데이터
- `results/기타공사_위치추가.csv`: 기타공사 작업 데이터
- `results/긴급공사_위치추가.csv`: 긴급공사 작업 데이터
- `results/관리대장_위치추가.csv`: 관리대장 작업 데이터

## 🚀 사용법

```bash
python src/main11d_cmp_dup.py  # 기본 실행 (30m 거리 임계값)
python src/main11d_cmp_dup.py --distance 50  # 50m 거리 임계값
python src/main11d_cmp_dup.py --output-dir custom_dir  # 출력 디렉토리 지정
```

## 🎛️ 옵션
- `--distance`: 중복 판단 거리 임계값 (미터, 기본값: 30)
- `--output-dir`: 출력 디렉토리 (기본값: results)

## 📤 출력 파일
- `results/중복분석_상세.csv`: 중복된 작업 상세 목록
  - 중복유형 (파일내/파일간)
  - 원본 파일명, 행번호
  - 작업일자, 위도, 경도
  - EPSG:5179 좌표 (x, y)

## ✨ 주요 기능
- 동일 날짜 + 근거리(기본 30m) 작업 중복 검출
- WGS84(EPSG:4326) → Korean TM(EPSG:5179) 좌표 변환
- 파일 내 중복과 파일 간 중복 모두 검사
- 중복 그룹별 거리 계산 및 통계
- 필수 컬럼 검증 (작업일시, 위도, 경도)

## 📚 관련 문서
- [함수 호출 그래프](../call_graph/main11d_cmp_dup_call_graph.md)

## 🔗 연관 스크립트
- 이전: [`main11c*.py`](main11c*.md)
- 다음: [`main11e*.py`](main11e*.md)
