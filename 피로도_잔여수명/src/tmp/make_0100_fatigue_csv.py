"""
0100 지역(사라봉) 피로도 CSV 생성 스크립트

입력:
  - data/raw/export_shp_20250704(0100)/상수관로_사라봉1.shp  (상수관로)
  - data/raw/export_shp_20250704(0100)/급수관로_사라봉1.shp  (급수관로)
  - DB: 61.85.1.119:4306 supply_meter (manage_id=300111, 0100 압력 데이터)

출력:
  - results/tmp/0100_fatigue_merged_zone_fixed.csv

의존성 없는 데이터:
  - 공사이력(K_repair) 없음 → K_repair=0 (K_total에 영향 없음)
  - 교통 정보: data/traffic/0100_pipe_traffic.csv, 0100_sply_traffic.csv
  - 지질 정보(K_soil) 없음 → K_soil=1.0 (기본값)
"""

import sys
import struct
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# 프로젝트 루트 및 src 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from common.config import RESULTS_DIR, RAW_DATA_DIR
from rainflow_processing import process_pipe_data_with_age, calculate_rainflow_by_age
from fatigue_calculations import add_K_material_to_dataframe, calculate_fatigue_damage_dataframe
from repair_loader_k import load_k_repair_mapping, apply_k_repair_to_dataframe, print_k_repair_statistics
from pipe_prop import read_pipe_properties
from fatigue_db_writer import write_0100_to_db

# 경로 설정
EXPORT_DIR = RAW_DATA_DIR / "export_shp_20250704(0100)"
PIPE_PROP_PATH = RAW_DATA_DIR / "PIPE_PROP.csv"
OUTPUT_DIR = RESULTS_DIR / "tmp"
REGION_CODE = "0100"

# 임시 CSV 저장 경로
TEMP_PIPE_LM_CSV = OUTPUT_DIR / "0100_PIPE_LM_temp.csv"
TEMP_SPLY_LS_CSV = OUTPUT_DIR / "0100_SPLY_LS_temp.csv"


def read_dbf_to_dataframe(dbf_path: Path) -> pd.DataFrame:
    """DBF 파일을 읽어 DataFrame으로 반환 (ASCII 컬럼만 유지)"""
    with open(dbf_path, "rb") as f:
        f.read(4)
        num_records = struct.unpack("<I", f.read(4))[0]
        header_size = struct.unpack("<H", f.read(2))[0]
        record_size = struct.unpack("<H", f.read(2))[0]
        f.read(20)

        fields = []
        while True:
            desc = f.read(32)
            if desc[0:1] == b"\r":
                break
            name_bytes = desc[:11].replace(b"\x00", b"")
            try:
                name = name_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                name = name_bytes.decode("latin-1").strip()
            ftype = chr(desc[11])
            length = desc[16]
            fields.append((name, ftype, length))

        f.seek(header_size)

        rows = []
        for _ in range(num_records):
            record = f.read(record_size)
            if not record or record[0:1] == b"\x1a":
                break
            pos = 1
            row = {}
            for fname, ftype, flen in fields:
                val = record[pos : pos + flen]
                try:
                    decoded = val.decode("utf-8").strip()
                except UnicodeDecodeError:
                    decoded = val.decode("cp949", errors="replace").strip()
                row[fname] = decoded
                pos += flen
            rows.append(row)

    df = pd.DataFrame(rows)
    # ASCII 컬럼만 유지 (한글 컬럼 제거)
    ascii_cols = [c for c in df.columns if c.isascii()]
    return df[ascii_cols]


def convert_shp_to_pipe_csv(shp_path: Path, pipe_type: str, output_csv: Path) -> None:
    """
    Shapefile → 파이프 CSV 변환
    """
    dbf_path = shp_path.with_suffix(".dbf")
    print(f"\n{pipe_type} shapefile → CSV 변환: {shp_path.name}")

    df = read_dbf_to_dataframe(dbf_path)
    print(f"  읽은 행 수: {len(df)}, 컬럼: {list(df.columns)}")

    required_cols = [
        "FTR_CDE", "FTR_IDN", "HJD_CDE", "SHT_NUM", "MNG_CDE",
        "MOP_CDE", "STD_DIP", "BYC_LEN", "JHT_CDE", "LOW_DEP", "HGH_DEP",
        "CNT_NUM", "SYS_CHK", "PIP_LBL", "AVG_DEP", "IQT_CDE", "IST_YMD",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
            print(f"  컬럼 없음 → NaN 추가: {col}")

    for col in ["FTR_IDN", "STD_DIP", "BYC_LEN", "LOW_DEP", "HGH_DEP", "AVG_DEP"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop(columns=["fid"], errors="ignore")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"  저장 완료: {output_csv} ({len(df)}행)")


def run_fatigue_pipeline(
    pipe_csv: Path,
    pipe_type: str,
    pipe_properties: pd.DataFrame,
    repair_data: dict,
) -> pd.DataFrame:
    """
    단일 파이프 CSV에 대해 전체 피로도 파이프라인 실행
    """
    print(f"\n{'='*60}")
    print(f"{pipe_type} 피로도 파이프라인 실행")
    print(f"{'='*60}")

    pipe_df = process_pipe_data_with_age(str(pipe_csv), pipe_type)
    if pipe_df.empty:
        print(f"경고: {pipe_type} 데이터가 비어있습니다.")
        return pd.DataFrame()

    # 사라봉 shapefile PIP_LBL 포맷은 "YYYY/TYPE/..." (기존 "DIA-TYPE-YR" 포맷과 다름)
    if "PIP_TYPE" in pipe_df.columns and pipe_df["PIP_TYPE"].isna().all():
        if "PIP_LBL" in pipe_df.columns:
            _slash_type = pipe_df["PIP_LBL"].str.split("/").str[1].str.strip()
            _type_map = {
                "DCIP": "DTC",
                "HI-3P": "PE",
                "SP": "ST",
                "CIP": "CI",
                "PFP": "PFP",
                "PE": "PE",
            }
            pipe_df["PIP_TYPE"] = _slash_type.map(_type_map)
            valid_cnt = pipe_df["PIP_TYPE"].notna().sum()
            print(f"  PIP_TYPE 재추출 완료: {valid_cnt}/{len(pipe_df)} 행")

    # Rain Flow Counting (DB에서 0100 압력 데이터 조회)
    result_df = calculate_rainflow_by_age(pipe_df, pipe_type, ["0100"], use_db=True)

    result_df = add_K_material_to_dataframe(result_df, pipe_properties, pipe_type)

    result_df = apply_k_repair_to_dataframe(result_df, pipe_type, repair_data)
    print_k_repair_statistics(result_df, pipe_type)

    if f"{REGION_CODE}_high_total_cycles" in result_df.columns:
        result_df = calculate_fatigue_damage_dataframe(
            result_df, REGION_CODE, data_type="pressure", use_k_total=True
        )

        if f"{REGION_CODE}_D_final" in result_df.columns:
            result_df[f"{REGION_CODE}_remaining_life_years"] = result_df.apply(
                lambda row: (
                    (1 - row[f"{REGION_CODE}_D_final"]) / row[f"{REGION_CODE}_D_final"]
                    if 0 < row[f"{REGION_CODE}_D_final"] < 1
                    else 0
                ),
                axis=1,
            )

        for band in ["high", "low"]:
            old_col = f"{REGION_CODE}_{band}_fatigue_intermediate"
            new_col = f"{REGION_CODE}_{band}_fatigue_damage"
            if old_col in result_df.columns:
                result_df[new_col] = result_df[old_col]
                del result_df[old_col]

    result_df = result_df.drop(columns=["K_total_without_repair"], errors="ignore")

    dup_cols = [c for c in result_df.columns if c.endswith(".1")]
    if dup_cols:
        result_df = result_df.drop(columns=dup_cols)

    return result_df


def apply_zone_and_rename(df: pd.DataFrame, pipe_type: str) -> pd.DataFrame:
    """zone=0100 설정 후 0100_ prefix 제거"""
    df = df.copy()
    df["zone"] = str(REGION_CODE)
    df["DATA_SRC"] = pipe_type

    region_cols = {c: c.replace(f"{REGION_CODE}_", "") for c in df.columns if c.startswith(f"{REGION_CODE}_")}
    df = df.rename(columns=region_cols)

    cols = ["DATA_SRC", "zone"] + [c for c in df.columns if c not in ("DATA_SRC", "zone")]
    df = df[cols]

    return df


def main() -> None:
    print("0100 지역(사라봉) 피로도 CSV 생성")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pipe_lm_shp = EXPORT_DIR / "상수관로_사라봉1.shp"
    sply_ls_shp = EXPORT_DIR / "급수관로_사라봉1.shp"

    for path in [pipe_lm_shp, sply_ls_shp]:
        if not path.exists():
            raise FileNotFoundError(f"입력 파일 없음: {path}")
    print(f"입력 파일 확인 완료")

    convert_shp_to_pipe_csv(pipe_lm_shp, "PIPE_LM", TEMP_PIPE_LM_CSV)
    convert_shp_to_pipe_csv(sply_ls_shp, "SPLY_LS", TEMP_SPLY_LS_CSV)

    pipe_properties = read_pipe_properties(str(PIPE_PROP_PATH))
    if pipe_properties.empty:
        raise RuntimeError("파이프 속성 데이터를 로드할 수 없습니다.")

    repair_data = load_k_repair_mapping(strict=False)

    pipe_lm_result = run_fatigue_pipeline(TEMP_PIPE_LM_CSV, "PIPE_LM", pipe_properties, repair_data)
    sply_ls_result = run_fatigue_pipeline(TEMP_SPLY_LS_CSV, "SPLY_LS", pipe_properties, repair_data)

    results = []
    if not pipe_lm_result.empty:
        results.append(apply_zone_and_rename(pipe_lm_result, "PIPE_LM"))
    if not sply_ls_result.empty:
        results.append(apply_zone_and_rename(sply_ls_result, "SPLY_LS"))

    if not results:
        raise RuntimeError("피로도 계산 결과가 없습니다.")

    merged = pd.concat(results, ignore_index=True)

    if "SMZ_NUM" not in merged.columns:
        merged["SMZ_NUM"] = merged["zone"]
    else:
        merged["SMZ_NUM"] = merged["SMZ_NUM"].fillna(merged["zone"])

    for col in ["GIS_IDN", "FTC_CDE", "CLS_YMD", "GU_CDE",
                "MDZ_NUM", "LGZ_NUM", "WTP_CDE", "FNS_YMD", "MET_IDN"]:
        if col not in merged.columns:
            merged[col] = None

    output_file = OUTPUT_DIR / "0100_fatigue_merged_zone_fixed.csv"
    merged.to_csv(output_file, index=False, encoding="utf-8-sig")

    write_0100_to_db(merged)

    print(f"\n{'='*80}")
    print(f"완료! 결과 저장: {output_file}")
    print(f"  - 전체 행 수: {len(merged):,}")
    print(f"  - 전체 컬럼 수: {len(merged.columns)}")
    print(f"  - PIPE_LM: {(merged['DATA_SRC'] == 'PIPE_LM').sum():,}개")
    print(f"  - SPLY_LS: {(merged['DATA_SRC'] == 'SPLY_LS').sum():,}개")
    if "D_final" in merged.columns:
        valid = merged["D_final"].dropna()
        print(f"  - D_final 유효값: {len(valid):,}개, 평균: {valid.mean():.4f}")


if __name__ == "__main__":
    main()
