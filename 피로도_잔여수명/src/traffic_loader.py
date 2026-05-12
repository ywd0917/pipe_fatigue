"""
K_traffic 데이터 로딩 및 매핑 모듈

이 모듈은 FTR_IDN과 ROAD_BT(도로 폭)를 기반으로 K_traffic 값을 계산합니다.
traffic/*.csv 파일들에서 데이터를 읽어와 도로 폭에 따른 교통 계수를 적용합니다.
"""

import pandas as pd
from enum import IntEnum
from typing import Dict, Set, Tuple
from common.config import DATA_DIR, RESULTS_DIR


class RoadWidthCategory(IntEnum):
    """도로 폭 카테고리 정의"""

    WIDE = 30  # 광로 (30m 이상)
    MEDIUM = 15  # 중로 (15m 이상)
    NARROW = 8  # 소로 (8m 이상)
    PEDESTRIAN = 0  # 보행로 (8m 미만)

    @property
    def korean_name(self) -> str:
        """한글 이름 반환"""
        names = {
            RoadWidthCategory.WIDE: "광로",
            RoadWidthCategory.MEDIUM: "중로",
            RoadWidthCategory.NARROW: "소로",
            RoadWidthCategory.PEDESTRIAN: "보행로",
        }
        return names[self]

    @property
    def k_traffic(self) -> float:
        """도로 폭 카테고리별 K_traffic 계수 반환"""
        coefficients = {
            RoadWidthCategory.WIDE: 1.6,  # 중장비 반복 통행
            RoadWidthCategory.MEDIUM: 1.4,  # 중형 이상 차량 통행
            RoadWidthCategory.NARROW: 1.2,  # 소형 차량 통행
            RoadWidthCategory.PEDESTRIAN: 1.0,  # 없음/보행자도로
        }
        return coefficients[self]

    @property
    def description(self) -> str:
        """도로 폭 카테고리별 설명 반환"""
        descriptions = {
            RoadWidthCategory.WIDE: "중장비 반복 통행",
            RoadWidthCategory.MEDIUM: "중형 이상 차량 통행",
            RoadWidthCategory.NARROW: "소형 차량 통행",
            RoadWidthCategory.PEDESTRIAN: "없음/보행자도로",
        }
        return descriptions[self]

    def __str__(self) -> str:
        """문자열 표현 - 사용자가 제공한 주석 사용"""
        if self == RoadWidthCategory.WIDE:
            return "중장비 반복 통행"
        elif self == RoadWidthCategory.MEDIUM:
            return "중형 이상 차량 통행"
        elif self == RoadWidthCategory.NARROW:
            return "소형 차량 통행"
        elif self == RoadWidthCategory.PEDESTRIAN:
            return "없음/보행자도로"

    @classmethod
    def from_road_width(cls, width: float) -> "RoadWidthCategory":
        """도로 폭으로부터 카테고리 결정"""
        if pd.isna(width) or width < 0:
            return cls.PEDESTRIAN

        if width >= cls.WIDE:
            return cls.WIDE
        elif width >= cls.MEDIUM:
            return cls.MEDIUM
        elif width >= cls.NARROW:
            return cls.NARROW
        else:
            return cls.PEDESTRIAN


# 전역 변수: 매핑되지 않은 도로 정보 저장
_unmapped_roads: Dict[str, Set[int]] = {}


def calculate_k_traffic(road_bt: float) -> float:
    """
    도로 폭(ROAD_BT)에 따른 K_traffic 값 계산

    Args:
        road_bt: 도로 폭 (미터)

    Returns:
        float: K_traffic 계수
    """
    category = RoadWidthCategory.from_road_width(road_bt)
    return category.k_traffic


def load_traffic_data() -> Dict[str, Dict[int, Tuple[float, float]]]:
    """
    모든 traffic CSV 파일을 로드하여 매핑 딕셔너리 반환

    Returns:
        Dict[str, Dict[int, Tuple[float, float]]]: 다음 구조의 딕셔너리
            {
                '0520_pipe': {FTR_IDN: (ROAD_BT, K_traffic), ...},
                '0520_supply': {FTR_IDN: (ROAD_BT, K_traffic), ...},
                '0903_pipe': {FTR_IDN: (ROAD_BT, K_traffic), ...},
                '0903_supply': {FTR_IDN: (ROAD_BT, K_traffic), ...}
            }
    """
    traffic_data = {}
    traffic_dir = DATA_DIR / "traffic"

    # traffic 파일 목록
    traffic_files = [
        ("0520_pipe", "0520_pipe_traffic.csv"),
        ("0520_supply", "0520_sply_traffic.csv"),
        ("0903_pipe", "0903_pipe_traffic.csv"),
        ("0903_supply", "0903_sply_traffic.csv"),
    ]

    for key, filename in traffic_files:
        file_path = traffic_dir / filename
        if file_path.exists():
            print(f"Loading traffic data from {filename}...")
            try:
                df = pd.read_csv(file_path, encoding="utf-8-sig")
                # FTR_IDN을 키로, (ROAD_BT, K_traffic)를 값으로 하는 딕셔너리 생성
                traffic_mapping = {}
                for _, row in df.iterrows():
                    try:
                        ftr_idn = int(row["FTR_IDN"])
                        road_bt = (
                            float(row["ROAD_BT"]) if pd.notna(row["ROAD_BT"]) else 0.0
                        )
                        k_traffic = calculate_k_traffic(road_bt)
                        traffic_mapping[ftr_idn] = (road_bt, k_traffic)
                    except (ValueError, KeyError) as e:
                        print(f"  Warning: Error processing row in {filename}: {e}")
                        continue

                traffic_data[key] = traffic_mapping
                print(
                    f"  Loaded {len(traffic_mapping):,} FTR_IDN → K_traffic mappings from {filename}"
                )

                # K_traffic 분포 출력
                k_traffic_counts: Dict[float, int] = {}
                for _, (_, k_traffic) in traffic_mapping.items():
                    k_traffic_counts[k_traffic] = k_traffic_counts.get(k_traffic, 0) + 1

                print(f"  K_traffic distribution in {filename}:")
                for k_val in sorted(k_traffic_counts.keys(), reverse=True):
                    count = k_traffic_counts[k_val]
                    percentage = count / len(traffic_mapping) * 100

                    # 해당하는 카테고리 찾기
                    for category in RoadWidthCategory:
                        if abs(category.k_traffic - k_val) < 0.001:  # 부동소수점 비교
                            print(
                                f"    - K_traffic = {k_val} ({category!s}): {count:,} ({percentage:.1f}%)"
                            )
                            break

            except Exception as e:
                print(f"  Error loading {filename}: {e}")
                traffic_data[key] = {}
        else:
            print(f"  Warning: {filename} not found at {file_path}")
            traffic_data[key] = {}

    # 통합 매핑 생성
    all_mappings = {}
    for key, mapping in traffic_data.items():
        all_mappings.update(mapping)
    traffic_data["all"] = all_mappings

    print(f"\nTotal unique FTR_IDN → K_traffic mappings: {len(all_mappings):,}")

    return traffic_data


def get_k_traffic_for_dataframe(
    df: pd.DataFrame,
    file_type: str = "pipe",
    region: str = "0520",
    default_value: float = RoadWidthCategory.PEDESTRIAN.k_traffic,
) -> pd.Series:
    """
    데이터프레임의 FTR_IDN을 기준으로 K_traffic 값을 조회하여 Series 반환

    Args:
        df: FTR_IDN 컬럼을 포함한 데이터프레임
        file_type: 'pipe' 또는 'supply'
        region: '0520' 또는 '0903'
        default_value: 매핑되지 않은 FTR_IDN에 대한 기본값

    Returns:
        pd.Series: K_traffic 값들
    """
    # FTR_IDN 컬럼 확인
    if "FTR_IDN" not in df.columns:
        print(
            "Warning: FTR_IDN column not found in dataframe. Using default K_traffic value."
        )
        return pd.Series(default_value, index=df.index)

    # traffic 데이터 로드
    traffic_data = load_traffic_data()

    # supply 파일명 처리 (sply로 저장되어 있음)
    if file_type == "supply":
        mapping_key = f"{region}_supply"
    else:
        mapping_key = f"{region}_{file_type}"

    if mapping_key not in traffic_data:
        print(f"Warning: Mapping key '{mapping_key}' not found. Using all mappings.")
        mapping = traffic_data.get("all", {})
    else:
        mapping = traffic_data[mapping_key]

    # FTR_IDN을 사용하여 K_traffic 매핑
    k_traffic_values = []
    mapped_count = 0
    unmapped_count = 0
    unmapped_ftr_idns = set()

    for idx, row in df.iterrows():
        try:
            ftr_idn = int(row["FTR_IDN"])
            if ftr_idn in mapping:
                _, k_traffic = mapping[ftr_idn]
                k_traffic_values.append(k_traffic)
                mapped_count += 1
            else:
                k_traffic_values.append(default_value)
                unmapped_count += 1
                unmapped_ftr_idns.add(ftr_idn)
        except (ValueError, TypeError):
            k_traffic_values.append(default_value)
            unmapped_count += 1

    # 전역 변수에 매핑되지 않은 정보 저장
    if mapping_key not in _unmapped_roads:
        _unmapped_roads[mapping_key] = set()
    _unmapped_roads[mapping_key].update(unmapped_ftr_idns)

    # 통계 출력
    print("\nK_traffic mapping statistics:")
    print(f"  - Total rows: {len(df):,}")
    print(
        f"  - Successfully mapped: {mapped_count:,} ({mapped_count/len(df)*100:.1f}%)"
    )
    print(
        f"  - Used default value: {unmapped_count:,} ({unmapped_count/len(df)*100:.1f}%)"
    )

    # 매핑되지 않은 FTR_IDN 경고
    if unmapped_ftr_idns:
        print(f"\n{'='*60}")
        print(
            f"WARNING: {len(unmapped_ftr_idns)} unique FTR_IDNs not found in traffic mapping!"
        )
        print(f"File type: {mapping_key}")
        print(f"{'='*60}")

        if len(unmapped_ftr_idns) <= 20:
            print(f"Unmapped FTR_IDNs: {sorted(unmapped_ftr_idns)}")
        else:
            sorted_unmapped = sorted(unmapped_ftr_idns)
            print(f"First 20 unmapped FTR_IDNs: {sorted_unmapped[:20]}")
            print(f"... and {len(unmapped_ftr_idns) - 20} more")

    # K_traffic 값 분포
    k_traffic_series = pd.Series(k_traffic_values, index=df.index)
    value_counts = k_traffic_series.value_counts().sort_index(ascending=False)
    print("\nK_traffic value distribution:")
    for value, count in value_counts.items():
        # 해당하는 카테고리 찾기
        for category in RoadWidthCategory:
            if (
                isinstance(value, (int, float))
                and abs(category.k_traffic - value) < 0.001
            ):  # 부동소수점 비교
                print(
                    f"  - K_traffic = {value} ({category!s}): {count:,} rows ({count/len(df)*100:.1f}%)"
                )
                break

    return k_traffic_series


def print_unmapped_roads_summary() -> None:
    """
    프로그램 종료 시 매핑되지 않은 도로 정보 요약 출력 및 파일 저장
    """
    if not _unmapped_roads:
        return

    print("\n" + "=" * 80)
    print("WARNING: Unmapped Road Information Summary")
    print("=" * 80)

    total_unmapped = sum(len(ftr_idns) for ftr_idns in _unmapped_roads.values())
    print(f"Total unmapped FTR_IDNs: {total_unmapped:,}")
    print("\nBy file type:")

    for mapping_key in sorted(_unmapped_roads.keys()):
        ftr_idns = _unmapped_roads[mapping_key]
        if ftr_idns:
            print(f"  - {mapping_key}: {len(ftr_idns):,} unmapped")

    # 파일로 저장
    unmapped_file = RESULTS_DIR / "unmapped_traffic_ftr_idns.txt"
    with open(unmapped_file, "w") as f:
        f.write("Unmapped Traffic FTR_IDNs\n")
        f.write(f"Total: {total_unmapped:,}\n")
        f.write(f"{'='*50}\n\n")

        for mapping_key in sorted(_unmapped_roads.keys()):
            ftr_idns = _unmapped_roads[mapping_key]
            if ftr_idns:
                f.write(f"\n{mapping_key} ({len(ftr_idns):,} unmapped):\n")
                f.write("-" * 30 + "\n")
                for ftr_idn in sorted(ftr_idns):
                    f.write(f"{ftr_idn}\n")

    print(f"\nDetailed list saved to: {unmapped_file}")
    print("=" * 80)


def get_k_traffic_by_ftr_idn(
    ftr_idn: int, file_type: str = "pipe", region: str = "0520"
) -> float:
    """
    단일 FTR_IDN에 대한 K_traffic 값 조회

    Args:
        ftr_idn: FTR_IDN 값
        file_type: 'pipe' 또는 'supply'
        region: '0520' 또는 '0903'

    Returns:
        float: K_traffic 값 (없으면 기본값)
    """
    traffic_data = load_traffic_data()

    if file_type == "supply":
        mapping_key = f"{region}_supply"
    else:
        mapping_key = f"{region}_{file_type}"

    if mapping_key in traffic_data:
        if ftr_idn in traffic_data[mapping_key]:
            _, k_traffic = traffic_data[mapping_key][ftr_idn]
            return k_traffic

    # 전체 매핑에서 검색
    if ftr_idn in traffic_data.get("all", {}):
        _, k_traffic = traffic_data["all"][ftr_idn]
        return k_traffic

    return RoadWidthCategory.PEDESTRIAN.k_traffic


if __name__ == "__main__":
    # 모듈 테스트
    print("Testing traffic_loader module...")
    print("=" * 80)

    # 데이터 로드 테스트
    traffic_data = load_traffic_data()

    # K_traffic 계산 테스트
    print("\n" + "=" * 80)
    print("K_traffic calculation test:")
    test_widths = [40, 30, 25, 15, 10, 8, 5, 0, None]
    for width in test_widths:
        if width is not None:
            k_traffic = calculate_k_traffic(float(width))
            category = RoadWidthCategory.from_road_width(float(width))
        else:
            k_traffic = calculate_k_traffic(float("nan"))
            category = RoadWidthCategory.from_road_width(float("nan"))
        print(f"  ROAD_BT = {width}m → K_traffic = {k_traffic} ({category!s})")

    print("\n" + "=" * 80)
    print("Module test completed.")