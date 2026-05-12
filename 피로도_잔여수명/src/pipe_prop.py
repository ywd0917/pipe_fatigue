"""
파이프 속성 데이터 처리 모듈
PIPE_PROP.csv 파일을 읽고 파이프 타입별 속성 정보를 제공
"""

import pandas as pd
from typing import Dict, Optional
import warnings

from common.config import PIPE_PROP_PATH

warnings.filterwarnings("ignore")


def read_pipe_properties(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    PIPE_PROP.csv 파일을 읽어서 파이프 속성 정보를 반환
    각 셀의 첫 번째 줄만 컬럼명으로 사용하고, 두 번째 줄은 주석으로 처리

    Args:
        file_path: PIPE_PROP.csv 파일 경로

    Returns:
        pd.DataFrame: 파이프 속성 정보
    
    Raises:
        FileNotFoundError: PIPE_PROP.csv 파일이 없을 때
    """
    # file_path가 없으면 config에서 기본값 사용
    if file_path is None:
        file_path = str(PIPE_PROP_PATH)
    
    # 파일 존재 확인
    from pathlib import Path
    if not Path(file_path).exists():
        raise FileNotFoundError(str(file_path))

    print(f"\n{'='*60}")
    print(f"파이프 속성 데이터 로드: {file_path}")
    print(f"{'='*60}")

    try:
        # CSV 파일 읽기
        df = pd.read_csv(file_path)

        # 컬럼명에서 첫 번째 줄만 추출 (개행문자로 분리된 경우)
        new_columns = []
        for col in df.columns:
            if "\n" in str(col):
                # 첫 번째 줄만 사용
                first_line = str(col).split("\n")[0].strip()
                new_columns.append(first_line)
            else:
                new_columns.append(str(col).strip())

        df.columns = new_columns

        print("파이프 속성 데이터 로드 완료:")
        print(f"  - 총 파이프 타입 수: {len(df)}")
        print(f"  - 컬럼 수: {len(df.columns)}")
        print(f"  - 컬럼명: {list(df.columns)}")

        # 파이프 타입별 수명계수 출력
        if "type" in df.columns and "KmaterialK" in df.columns:
            print("\n파이프 타입별 수명계수:")
            for _, row in df.iterrows():
                print(f"  - {row['type']}: {row['KmaterialK']}")

        return df

    except Exception as e:
        print(f"파이프 속성 데이터 로드 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


def get_pipe_property(
    pipe_properties: pd.DataFrame, pipe_type: str, property_name: str
) -> Optional[float]:
    """
    특정 파이프 타입의 특정 속성값을 반환

    Args:
        pipe_properties: 파이프 속성 데이터프레임
        pipe_type: 파이프 타입 (예: 'ST', 'DTC', 'PVC' 등)
        property_name: 속성명 (예: 'KmaterialK', 'service_life', 'design_pressure' 등)

    Returns:
        Optional[float]: 속성값 (없으면 None)
    """
    if pipe_properties.empty:
        return None

    if (
        "type" not in pipe_properties.columns
        or property_name not in pipe_properties.columns
    ):
        return None

    # 해당 파이프 타입의 행 찾기
    pipe_row = pipe_properties[pipe_properties["type"] == pipe_type]

    if pipe_row.empty:
        return None

    return pipe_row[property_name].iloc[0]


def get_all_pipe_properties_summary(
    pipe_properties: pd.DataFrame,
) -> Dict[str, Dict[str, float]]:
    """
    모든 파이프 타입의 속성 정보를 요약하여 반환

    Args:
        pipe_properties: 파이프 속성 데이터프레임

    Returns:
        Dict[str, Dict[str, float]]: 파이프 타입별 속성 정보
    """
    if pipe_properties.empty:
        return {}

    summary = {}

    for _, row in pipe_properties.iterrows():
        pipe_type = row.get("type", "Unknown")

        pipe_info = {}
        for col in pipe_properties.columns:
            if col != "type" and col != "name" and col != "desc" and col != "설명":
                try:
                    # 숫자형 데이터만 포함
                    value = pd.to_numeric(row[col], errors="coerce")
                    if pd.notna(value):
                        pipe_info[col] = float(value)
                except Exception:
                    pass

        summary[pipe_type] = pipe_info

    return summary


if __name__ == "__main__":
    # 테스트 코드
    print("파이프 속성 모듈 테스트")

    # PIPE_PROP.csv 파일 읽기
    pipe_props = read_pipe_properties()  # Uses default from config

    if not pipe_props.empty:
        # 특정 파이프 속성 조회 테스트
        st_fatigue = get_pipe_property(pipe_props, "ST", "KmaterialK")
        print(f"\nST 파이프의 수명계수: {st_fatigue}")

        # 전체 속성 요약 테스트
        summary = get_all_pipe_properties_summary(pipe_props)
        print("\n전체 파이프 속성 요약:")
        for pipe_type, properties in summary.items():
            print(f"  {pipe_type}: {properties}")