"""
K_SOIL 데이터 로딩 및 매핑 모듈

이 모듈은 FTR_IDN과 K_SOIL 값을 매핑하는 기능을 제공합니다.
_soil.csv 파일들에서 데이터를 읽어와 효율적인 조회를 위한 딕셔너리를 생성합니다.
"""

import pandas as pd
from typing import Dict
from common.config import RAW_DATA_DIR, DATA_DIR


def load_soil_data() -> Dict[str, Dict[int, float]]:
    """
    모든 soil CSV 파일을 로드하여 매핑 딕셔너리 반환

    Returns:
        Dict[str, Dict[int, float]]: 다음 구조의 딕셔너리
            {
                '0520_pipe': {FTR_IDN: K_SOIL, ...},
                '0520_supply': {FTR_IDN: K_SOIL, ...},
                '0903_pipe': {FTR_IDN: K_SOIL, ...},
                '0903_supply': {FTR_IDN: K_SOIL, ...}
            }
    """
    soil_data = {}

    # soil 파일 목록
    soil_files = [
        ("0520_pipe", "0520_pipe_soil.csv"),
        ("0520_supply", "0520_supply_soil.csv"),
        ("0903_pipe", "0903_pipe_soil.csv"),
        ("0903_supply", "0903_supply_soil.csv"),
    ]

    for key, filename in soil_files:
        file_path = RAW_DATA_DIR / filename
        if file_path.exists():
            print(f"Loading K_SOIL data from {filename}...")
            try:
                df = pd.read_csv(file_path, encoding="utf-8-sig")
                # FTR_IDN을 int로 변환하고 K_SOIL과 매핑
                soil_mapping = {}
                for _, row in df.iterrows():
                    try:
                        ftr_idn = int(row["FTR_IDN"])
                        k_soil = float(row["K_SOIL"])
                        soil_mapping[ftr_idn] = k_soil
                    except (ValueError, KeyError) as e:
                        print(f"  Warning: Error processing row in {filename}: {e}")
                        continue

                soil_data[key] = soil_mapping
                print(
                    f"  Loaded {len(soil_mapping):,} FTR_IDN → K_SOIL mappings from {filename}"
                )
            except Exception as e:
                print(f"  Error loading {filename}: {e}")
                soil_data[key] = {}
        else:
            print(f"  Warning: {filename} not found at {file_path}")
            soil_data[key] = {}

    # 통합 매핑 생성 (모든 파일의 데이터를 합침)
    all_mappings = {}
    for key, mapping in soil_data.items():
        all_mappings.update(mapping)
    soil_data["all"] = all_mappings

    print(f"\nTotal unique FTR_IDN → K_SOIL mappings: {len(all_mappings):,}")

    return soil_data


def get_k_soil_for_dataframe(
    df: pd.DataFrame,
    file_type: str = "pipe",
    region: str = "0520",
    default_value: float = 1.0,
) -> pd.Series:
    """
    데이터프레임의 FTR_IDN을 기준으로 K_SOIL 값을 조회하여 Series 반환

    Args:
        df: FTR_IDN 컬럼을 포함한 데이터프레임
        file_type: 'pipe' 또는 'supply'
        region: '0520' 또는 '0903'
        default_value: 매핑되지 않은 FTR_IDN에 대한 기본값

    Returns:
        pd.Series: K_SOIL 값들
    """
    # FTR_IDN 컬럼 확인
    if "FTR_IDN" not in df.columns:
        print(
            "Warning: FTR_IDN column not found in dataframe. Using default K_SOIL value."
        )
        return pd.Series(default_value, index=df.index)

    # soil 데이터 로드
    soil_data = load_soil_data()

    # 적절한 매핑 선택
    mapping_key = f"{region}_{file_type}"
    if mapping_key not in soil_data:
        print(f"Warning: Mapping key '{mapping_key}' not found. Using all mappings.")
        mapping = soil_data.get("all", {})
    else:
        mapping = soil_data[mapping_key]

    # FTR_IDN을 사용하여 K_SOIL 매핑
    k_soil_values = []
    mapped_count = 0
    unmapped_count = 0
    unmapped_ftr_idns = set()

    for idx, row in df.iterrows():
        try:
            ftr_idn = int(row["FTR_IDN"])
            if ftr_idn in mapping:
                k_soil_values.append(mapping[ftr_idn])
                mapped_count += 1
            else:
                k_soil_values.append(default_value)
                unmapped_count += 1
                unmapped_ftr_idns.add(ftr_idn)
        except (ValueError, TypeError):
            k_soil_values.append(default_value)
            unmapped_count += 1

    # 통계 출력
    print("\nK_SOIL mapping statistics:")
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
            f"WARNING: {len(unmapped_ftr_idns)} unique FTR_IDNs not found in K_SOIL mapping!"
        )
        print(f"{'='*60}")

        if len(unmapped_ftr_idns) <= 20:
            print(f"Unmapped FTR_IDNs: {sorted(unmapped_ftr_idns)}")
        else:
            # 처음 20개만 표시
            sorted_unmapped = sorted(unmapped_ftr_idns)
            print(f"First 20 unmapped FTR_IDNs: {sorted_unmapped[:20]}")
            print(f"... and {len(unmapped_ftr_idns) - 20} more")

        # 매핑되지 않은 FTR_IDN을 파일로 저장하는 옵션
        unmapped_file = DATA_DIR / "unmapped_ftr_idns.txt"
        with open(unmapped_file, "w") as f:
            f.write(f"Unmapped FTR_IDNs (Total: {len(unmapped_ftr_idns)})\n")
            f.write(f"Generated from: {mapping_key}\n")
            f.write(f"{'='*50}\n")
            for ftr_idn in sorted(unmapped_ftr_idns):
                f.write(f"{ftr_idn}\n")
        print(f"\nFull list saved to: {unmapped_file}")

    # K_SOIL 값 분포
    k_soil_series = pd.Series(k_soil_values, index=df.index)
    value_counts = k_soil_series.value_counts().sort_index()
    print("\nK_SOIL value distribution:")
    for value, count in value_counts.items():
        print(f"  - K_SOIL = {value}: {count:,} rows ({count/len(df)*100:.1f}%)")

    return k_soil_series


def get_k_soil_by_ftr_idn(
    ftr_idn: int, file_type: str = "pipe", region: str = "0520"
) -> float:
    """
    단일 FTR_IDN에 대한 K_SOIL 값 조회

    Args:
        ftr_idn: FTR_IDN 값
        file_type: 'pipe' 또는 'supply'
        region: '0520' 또는 '0903'

    Returns:
        float: K_SOIL 값 (없으면 1.0)
    """
    soil_data = load_soil_data()
    mapping_key = f"{region}_{file_type}"

    if mapping_key in soil_data:
        return soil_data[mapping_key].get(ftr_idn, 1.0)
    else:
        # 전체 매핑에서 검색
        return soil_data.get("all", {}).get(ftr_idn, 1.0)


if __name__ == "__main__":
    # 모듈 테스트
    print("Testing soil_loader module...")
    print("=" * 80)

    # 데이터 로드 테스트
    soil_data = load_soil_data()

    print("\n" + "=" * 80)
    print("Module test completed.")