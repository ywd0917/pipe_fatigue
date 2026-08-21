"""
피로도 계산 결과 DB 저장 모듈

pipe_fatigue 테이블에 계산 결과를 저장합니다.
저장 전 해당 SMZ_NUM + MDZ_NUM 데이터를 삭제 후 재삽입합니다.

구역별 SMZ_NUM / MDZ_NUM:
  0100 → SMZ_NUM=110, MDZ_NUM=100
  0200 → SMZ_NUM=211, MDZ_NUM=200
  0243 → SMZ_NUM=243, MDZ_NUM=520
  0461 → SMZ_NUM=461, MDZ_NUM=520
  0470 → SMZ_NUM=470, MDZ_NUM=520
  0480 → SMZ_NUM=480, MDZ_NUM=520
  0490 → SMZ_NUM=490, MDZ_NUM=520
  0520 → SMZ_NUM=520, MDZ_NUM=520
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import pymysql

# ── DB 접속 정보 (pressure_db_loader와 동일) ────────────────────────────────

_DB_0520 = {
    "host": "59.25.253.40",
    "port": 3334,
    "database": "waterdt",
    "user": "root",
    "password": "water338!@",
    "charset": "utf8mb4",
}

_DB_0100_0200 = {
    "host": "127.0.0.1",
    "port": 4306,
    "database": "waterdt",
    "user": "root",
    "password": "water338!@",
    "charset": "utf8mb4",
}

# ── 구역코드 → (SMZ_NUM, MDZ_NUM, DB설정) ──────────────────────────────────

ZONE_DB_MAP: dict[str, tuple[int, int, dict]] = {
    "0100": (110, 100, _DB_0100_0200),
    "0200": (211, 200, _DB_0100_0200),
    "0243": (243, 520, _DB_0520),
    "0461": (461, 520, _DB_0520),
    "0470": (470, 520, _DB_0520),
    "0480": (480, 520, _DB_0520),
    "0490": (490, 520, _DB_0520),
    "0520": (520, 520, _DB_0520),
}

TABLE_NAME = "pipe_fatigue"

# DB 컬럼 ← DataFrame 컬럼 매핑 (공통 K 계수 및 메타 컬럼)
_COMMON_COL_MAP = {
    "FTR_IDN":             "FTR_IDN",
    "manage_no":           "MNG_CDE",
    "K_material":          "K_material",
    "fatigue_limit":       "fatigue_limit",
    "K_diameter":          "K_diameter",
    "K_age":               "K_age",
    "K_soil":              "K_soil",
    "K_traffic":           "K_traffic",
    "K_vibration":         "K_vibration",
    "hoop_stress":         "hoop_stress",
    "K_stress":            "K_stress",
    "K_repair":            "K_repair",
    "K_total":             "K_total",
}

# 피로도 결과 컬럼 (prefix를 붙여서 사용)
_FATIGUE_RESULT_COLS = [
    "low_total_cycles",
    "high_total_cycles",
    "low_fatigue_damage",
    "high_fatigue_damage",
    "D_base",
    "D_final_org",
    "D_final",
    "remaining_life_years",
]


def _build_conn(db_cfg: dict) -> pymysql.Connection:
    return pymysql.connect(
        host=db_cfg["host"],
        port=db_cfg["port"],
        database=db_cfg["database"],
        user=db_cfg["user"],
        password=db_cfg["password"],
        charset=db_cfg["charset"],
        connect_timeout=10,
    )


def _delete_existing(conn: pymysql.Connection, smz_num: int, mdz_num: int) -> int:
    """해당 SMZ_NUM + MDZ_NUM 데이터 삭제 후 삭제된 행 수 반환"""
    with conn.cursor() as cur:
        cur.execute(
            f"DELETE FROM {TABLE_NAME} WHERE SMZ_NUM = %s AND MDZ_NUM = %s",
            (smz_num, mdz_num),
        )
        deleted = cur.rowcount
    conn.commit()
    return deleted


def _to_none(val) -> Optional[float]:
    """NaN / inf / None → None (DB NULL)"""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return val
    except (TypeError, ValueError):
        return None


def _build_insert_rows(
    df: pd.DataFrame,
    zone_code: str,
    smz_num: int,
    mdz_num: int,
    zone_prefix: str = "",
) -> list[tuple]:
    """
    DataFrame에서 INSERT용 튜플 리스트 생성

    Args:
        df: 피로도 계산 결과 DataFrame
        zone_code: 구역코드 (로그용)
        smz_num: 저장할 SMZ_NUM 값
        mdz_num: 저장할 MDZ_NUM 값
        zone_prefix: 피로도 결과 컬럼 접두사 (0520 지역: "0470_" 형식, 0100/0200: "")
    """
    rows = []
    for _, row in df.iterrows():
        # 공통 K 계수 컬럼
        def get(src_col):
            return _to_none(row.get(src_col))

        ftr_idn = _to_none(row.get("FTR_IDN"))
        manage_no = ftr_idn  # MNG_CDE는 구역 코드(동일값)이므로 FTR_IDN을 manage_no로 사용

        if manage_no is None:
            continue

        # 피로도 결과 컬럼 (prefix 적용)
        def get_fatigue(col):
            return _to_none(row.get(f"{zone_prefix}{col}"))

        try:
            manage_no_str = str(int(float(manage_no)))
        except (ValueError, TypeError):
            manage_no_str = str(manage_no)

        rows.append((
            ftr_idn,
            manage_no_str,
            get("K_material"),
            get("fatigue_limit"),
            get("K_diameter"),
            get("K_age"),
            get("K_soil"),
            get("K_traffic"),
            get("K_vibration"),
            get("hoop_stress"),
            get("K_stress"),
            get("K_repair"),
            get("K_total"),
            get_fatigue("low_total_cycles"),
            get_fatigue("high_total_cycles"),
            get_fatigue("low_fatigue_damage"),
            get_fatigue("high_fatigue_damage"),
            get_fatigue("D_base"),
            get_fatigue("D_final_org"),
            get_fatigue("D_final"),
            get_fatigue("remaining_life_years"),
            smz_num,
            mdz_num,
        ))
    return rows


_INSERT_SQL = f"""
    INSERT INTO {TABLE_NAME} (
        FTR_IDN, manage_no,
        K_material, fatigue_limit, K_diameter, K_age, K_soil,
        K_traffic, K_vibration, hoop_stress, K_stress, K_repair, K_total,
        low_total_cycles, high_total_cycles,
        low_fatigue_damage, high_fatigue_damage,
        D_base, D_final_org, D_final, remaining_life_years,
        SMZ_NUM, MDZ_NUM
    ) VALUES (
        %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s, %s, %s,
        %s, %s
    )
"""


def _bulk_insert(conn: pymysql.Connection, rows: list[tuple]) -> None:
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany(_INSERT_SQL, rows)
    conn.commit()


def write_zone_to_db(
    df: pd.DataFrame,
    zone_code: str,
    zone_prefix: str = "",
) -> None:
    """
    단일 구역 피로도 결과를 DB에 저장

    Args:
        df: 피로도 계산 결과 DataFrame
        zone_code: "0100", "0200", "0243", ..., "0520"
        zone_prefix: 0520 지역처럼 컬럼 앞에 구역코드가 붙는 경우 사용 (예: "0470_")
                     0100/0200처럼 직접 컬럼인 경우 "" (빈 문자열)
    """
    if zone_code not in ZONE_DB_MAP:
        raise ValueError(f"지원하지 않는 구역코드: {zone_code}")

    smz_num, mdz_num, db_cfg = ZONE_DB_MAP[zone_code]

    print(f"\n[DB 저장] 구역={zone_code} | SMZ_NUM={smz_num} | MDZ_NUM={mdz_num}")
    print(f"  host: {db_cfg['host']}:{db_cfg['port']}")

    # D_final 컬럼이 존재하는지 확인
    d_final_col = f"{zone_prefix}D_final"
    if d_final_col not in df.columns:
        print(f"  경고: {d_final_col} 컬럼이 없습니다. 건너뜁니다.")
        return

    # D_final 및 모든 K 계수가 non-null인 행만 저장
    _K_COLS = [
        "K_material", "K_diameter", "K_age", "K_soil",
        "K_traffic", "K_vibration", "K_stress", "K_repair", "K_total",
    ]
    cols_to_check = [d_final_col] + [c for c in _K_COLS if c in df.columns]
    valid_df = df[df[cols_to_check].notna().all(axis=1)].copy()
    excluded = len(df) - len(valid_df)
    if excluded:
        print(f"  제외된 행 (K 계수 또는 D_final null): {excluded:,}행")
    if valid_df.empty:
        print(f"  경고: 유효한 행이 없습니다. 건너뜁니다.")
        return

    conn = _build_conn(db_cfg)
    try:
        deleted = _delete_existing(conn, smz_num, mdz_num)
        print(f"  기존 데이터 삭제: {deleted:,}행")

        rows = _build_insert_rows(valid_df, zone_code, smz_num, mdz_num, zone_prefix)
        _bulk_insert(conn, rows)
        print(f"  저장 완료: {len(rows):,}행")
    finally:
        conn.close()


def write_0520_to_db(df: pd.DataFrame) -> None:
    """
    0520 지역 피로도 결과 (zone-prefix 컬럼 구조)를 구역별로 DB 저장

    df에는 0243_D_final, 0461_D_final, ... 형식의 컬럼이 있어야 합니다.
    """
    zones = ["0243", "0461", "0470", "0480", "0490", "0520"]
    print(f"\n{'='*60}")
    print("0520 지역 피로도 결과 DB 저장")
    print(f"{'='*60}")
    for zone in zones:
        prefix = f"{zone}_"
        write_zone_to_db(df, zone, zone_prefix=prefix)


def write_0100_to_db(df: pd.DataFrame) -> None:
    """0100 지역 피로도 결과 DB 저장 (컬럼에 prefix 없음)"""
    print(f"\n{'='*60}")
    print("0100 지역 피로도 결과 DB 저장")
    print(f"{'='*60}")
    write_zone_to_db(df, "0100", zone_prefix="")


def write_0200_to_db(df: pd.DataFrame) -> None:
    """0200 지역 피로도 결과 DB 저장 (컬럼에 prefix 없음)"""
    print(f"\n{'='*60}")
    print("0200 지역 피로도 결과 DB 저장")
    print(f"{'='*60}")
    write_zone_to_db(df, "0200", zone_prefix="")
