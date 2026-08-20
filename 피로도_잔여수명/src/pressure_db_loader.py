"""
압력 데이터 DB 로딩 모듈

supply_meter 테이블에서 구역별 압력 데이터를 조회합니다.

DB 구성:
  0520 지역 (0243/0461/0470/0480/0490/0520): 59.25.253.40:4334
  0100/0200 지역:                              61.85.1.119:4306

매핑:
  구역코드 → manage_id → DB 호스트
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import pymysql

# ── DB 접속 정보 ────────────────────────────────────────────────────────────

_DB_0520 = {
    "host": "59.25.253.40",
    "port": 4334,
    "database": "waterdt",
    "user": "root",
    "password": "water338!@",
    "charset": "utf8mb4",
}

_DB_0100_0200 = {
    "host": "61.85.1.119",
    "port": 4306,
    "database": "waterdt",
    "user": "root",
    "password": "water338!@",
    "charset": "utf8mb4",
}

# ── 구역코드 → (manage_id, DB설정) 매핑 ────────────────────────────────────

REGION_DB_MAP: dict[str, tuple[int, dict]] = {
    "0100": (300111, _DB_0100_0200),
    "0200": (300027, _DB_0100_0200),
    "0243": (235,    _DB_0520),
    "0461": (39232,  _DB_0520),
    "0470": (39235,  _DB_0520),
    "0480": (39233,  _DB_0520),
    "0490": (39234,  _DB_0520),
    "0520": (39227,  _DB_0520),
}


def load_pressure_from_db(
    region_code: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """
    DB에서 압력 데이터를 조회하여 DataFrame으로 반환

    Args:
        region_code: 구역 코드 (예: "0520", "0100")
        start_date: 조회 시작일 (None이면 최근 1년)
        end_date: 조회 종료일 (None이면 현재)

    Returns:
        DataFrame with columns: manage_id, msrmt_dt, wtrprsr
        (기존 CSV 포맷과 동일)

    Raises:
        ValueError: 지원하지 않는 구역코드
        pymysql.Error: DB 연결/쿼리 오류
    """
    if region_code not in REGION_DB_MAP:
        raise ValueError(
            f"지원하지 않는 구역코드: {region_code}. "
            f"지원 목록: {list(REGION_DB_MAP.keys())}"
        )

    manage_id, db_cfg = REGION_DB_MAP[region_code]

    # 날짜 기본값 설정
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date.replace(year=end_date.year - 1)

    print(f"\n[DB] {region_code} 구역 압력 데이터 조회")
    print(f"  manage_id : {manage_id}")
    print(f"  host      : {db_cfg['host']}:{db_cfg['port']}")
    print(f"  기간      : {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

    query = """
        SELECT manage_id, msrmt_dt, wtrprsr
        FROM supply_meter
        WHERE manage_id = %s
          AND msrmt_dt BETWEEN %s AND %s
          AND wtrprsr IS NOT NULL
        ORDER BY msrmt_dt
    """

    conn = pymysql.connect(
        host=db_cfg["host"],
        port=db_cfg["port"],
        database=db_cfg["database"],
        user=db_cfg["user"],
        password=db_cfg["password"],
        charset=db_cfg["charset"],
        connect_timeout=10,
    )
    try:
        df = pd.read_sql(
            query,
            conn,
            params=(manage_id, start_date, end_date),
            parse_dates=["msrmt_dt"],
        )
    finally:
        conn.close()

    print(f"  조회 결과 : {len(df):,}행")
    if df.empty:
        print(f"  경고: 데이터가 없습니다.")
        return df

    print(f"  기간 확인 : {df['msrmt_dt'].min()} ~ {df['msrmt_dt'].max()}")
    return df
