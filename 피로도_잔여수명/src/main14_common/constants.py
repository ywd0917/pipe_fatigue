"""
K-factor 분석용 상수 정의
main14 시리즈 스크립트에서 공통으로 사용되는 상수들
"""

# K-factor 정의 (CSV 파일 순서와 동일)
BASE_K_FACTORS = [
    "STD_DIP",  # 관경
    "K_age",  # 파이프 연령 계수
    "K_soil",  # 토양 조건 계수
    "K_traffic",  # 교통 하중 계수
    "hoop_stress",  # 원주 응력
    "K_stress",  # 응력 계수
    "K_total",  # 총 위험도 계수
]

# 선택적 K-factor (별도 파일에서 로드)
OPTIONAL_K_FACTORS = ["K_repair"]  # 재작업 계수

# 피로 손상 지수
DAMAGE_FACTOR = "D_final"

# 지역 코드
PARENT_REGION = "0520"

# 거리 임계값 옵션
DEFAULT_DISTANCE = 30

# 출력 형식
P_VALUE_THRESHOLD = 0.05

# K-factor 한글 이름 매핑
FACTOR_NAMES = {
    "STD_DIP": "관경",
    "K_age": "파이프 연령 계수",
    "K_soil": "토양 조건 계수",
    "K_traffic": "교통 하중 계수",
    "hoop_stress": "원주 응력",
    "K_stress": "응력 계수",
    "K_total": "총 위험도 계수",
    "K_repair": "재작업 계수",
    "D_final": "보정손상도",
}
