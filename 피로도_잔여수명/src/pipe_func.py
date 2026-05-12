"""
관망 데이터 유틸리티 함수들
- 파이프 타입 및 MOP 코드 관련 함수
- 검증, 변환, 조회 기능 제공
"""

from pipe_const import PipeTypeValue, MOPCodeValue, MOP_CODE_MAPPING


def get_pipe_type_from_mop_code(mop_code: MOPCodeValue) -> PipeTypeValue:
    """MOP 코드에서 파이프 타입 반환

    Args:
        mop_code: MOP 코드 값

    Returns:
        해당하는 파이프 타입

    Raises:
        KeyError: 유효하지 않은 MOP 코드인 경우
    """
    return MOP_CODE_MAPPING[mop_code]


def validate_pipe_type(pipe_type: str) -> bool:
    """파이프 타입 유효성 검증

    Args:
        pipe_type: 검증할 파이프 타입 문자열

    Returns:
        유효한 파이프 타입이면 True, 아니면 False
    """
    return pipe_type in MOP_CODE_MAPPING.values()


def validate_mop_code(mop_code: int) -> bool:
    """MOP 코드 유효성 검증

    Args:
        mop_code: 검증할 MOP 코드

    Returns:
        유효한 MOP 코드이면 True, 아니면 False
    """
    return mop_code in MOP_CODE_MAPPING.keys()


def get_all_pipe_types() -> list[PipeTypeValue]:
    """모든 파이프 타입 반환

    Returns:
        파이프 타입 리스트
    """
    return list(MOP_CODE_MAPPING.values())


def get_all_mop_codes() -> list[MOPCodeValue]:
    """모든 MOP 코드 반환

    Returns:
        MOP 코드 리스트
    """
    return list(MOP_CODE_MAPPING.keys())


def get_pipe_type_description(pipe_type: PipeTypeValue) -> str:
    """파이프 타입의 한글 설명 반환

    Args:
        pipe_type: 파이프 타입

    Returns:
        파이프 타입의 한글 설명
    """
    descriptions = {
        "STS": "스테인리스 스틸",
        "EPS": "확장 폴리스티렌",
        "ST": "스틸",
        "CI": "주철",
        "GP": "아연도금강관",
        "PE": "폴리에틸렌",
        "PFP": "플라스틱 복합관",
        "DTC": "덕타일 주철관",
        "DT": "덕타일",
        "PVC": "폴리염화비닐",
        "PB": "폴리부틸렌",
        "DTEP": "덕타일 에폭시",
        "HIVP": "고밀도 폴리에틸렌",
        "SPOL": "강화 폴리올레핀",
        "ETC": "기타 (보수적 계산용)",
    }
    return descriptions.get(pipe_type, "알 수 없는 타입")


def get_mop_code_from_pipe_type(pipe_type: PipeTypeValue) -> MOPCodeValue:
    """파이프 타입에서 MOP 코드 반환

    Args:
        pipe_type: 파이프 타입

    Returns:
        해당하는 MOP 코드

    Raises:
        KeyError: 유효하지 않은 파이프 타입인 경우
    """
    from pipe_const import PIPE_TYPE_TO_MOP_CODE

    return PIPE_TYPE_TO_MOP_CODE[pipe_type]