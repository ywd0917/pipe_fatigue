"""
관망 데이터 상수 정의
- 파이프 타입 및 MOP 코드 상수
- Literal 타입을 사용한 타입 안전성 보장
"""

from typing import Literal, Dict

# 파이프 타입 리터럴 정의
PipeTypeValue = Literal[
    "STS",  # 스테인리스 스틸
    "EPS",  # 확장 폴리스티렌
    "ST",  # 스틸
    "CI",  # 주철
    "GP",  # 아연도금강관
    "PE",  # 폴리에틸렌
    "PFP",  # 플라스틱 복합관
    "DTC",  # 덕타일 주철관
    "DT",  # 덕타일
    "PVC",  # 폴리염화비닐
    "PB",  # 폴리부틸렌
    "DTEP",  # 덕타일 에폭시
    "HIVP",  # 고밀도 폴리에틸렌
    "SPOL",  # 강화 폴리올레핀
    "ETC",  # 기타 (MOP_CDE=99, 계산 시 GP 값 사용)
]

# MOP 코드 리터럴 정의
MOPCodeValue = Literal[1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 16, 22, 99]

# MOP 코드 → 파이프 타입 매핑
MOP_CODE_MAPPING: Dict[MOPCodeValue, PipeTypeValue] = {
    1: "STS",
    2: "EPS",
    3: "ST",
    4: "CI",
    6: "GP",
    7: "PE",
    8: "PFP",
    9: "DTC",
    10: "DT",
    11: "PVC",
    13: "PB",
    14: "DTEP",
    16: "HIVP",
    22: "SPOL",
    99: "ETC",  # 기타 타입 (보수적 계산을 위해 GP 값 사용)
}

# 역방향 매핑 (필요시)
PIPE_TYPE_TO_MOP_CODE: Dict[PipeTypeValue, MOPCodeValue] = {
    v: k for k, v in MOP_CODE_MAPPING.items()
}