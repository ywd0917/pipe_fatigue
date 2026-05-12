"""
520 지역 재작업 데이터 통합 스크립트
지상누수, 지하누수, 기타공사 데이터를 통합하여 공간 분석용 데이터 생성
"""

import os

import numpy as np
import pandas as pd
from pyproj import Transformer


def prepare_520_repair_data():
    """520 지역 재작업 데이터 통합"""

    # 데이터 파일 경로
    files = [
        "results/지상누수_520_위치추가.csv",
        "results/지하누수_520_위치추가.csv",
        "results/기타공사_520_위치추가.csv",
    ]

    all_data = []

    for file_path in files:
        if os.path.exists(file_path):
            print(f"Loading: {file_path}")
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 재작업 유형 추가
            if "지상누수" in file_path:
                df["repair_type"] = "ground_leak"
            elif "지하누수" in file_path:
                df["repair_type"] = "underground_leak"
            else:
                df["repair_type"] = "other_repair"

            all_data.append(df)

    # 데이터 통합
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Total records: {len(combined_df)}")

    # 좌표 변환 (WGS84 -> EPSG:5186)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5186", always_xy=True)

    valid_coords = []
    for idx, row in combined_df.iterrows():
        try:
            if pd.notna(row["경도"]) and pd.notna(row["위도"]):
                lon = float(row["경도"])
                lat = float(row["위도"])
                if 124 < lon < 132 and 33 < lat < 43:  # Korea bounds
                    x, y = transformer.transform(lon, lat)
                    valid_coords.append({"idx": idx, "x": x, "y": y})
        except:
            continue

    # 좌표 추가
    coord_df = pd.DataFrame(valid_coords)
    combined_df["x"] = np.nan
    combined_df["y"] = np.nan

    for _, row in coord_df.iterrows():
        combined_df.loc[row["idx"], "x"] = row["x"]
        combined_df.loc[row["idx"], "y"] = row["y"]

    # 유효한 좌표만 필터링
    final_df = combined_df.dropna(subset=["x", "y"])
    final_df = final_df[(final_df["x"] > 0) & (final_df["y"] > 0)]

    print(f"Valid records with coordinates: {len(final_df)}")

    # CNT_JNT 추가 (더미 데이터 - 실제 데이터가 있으면 조인)
    np.random.seed(42)
    final_df["CNT_JNT"] = np.random.randint(1, 20, size=len(final_df))

    # 저장
    output_path = "data/520_area/repairs_with_location_520_v3.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Saved to: {output_path}")
    print(f"Columns: {list(final_df.columns)}")

    return final_df


if __name__ == "__main__":
    df = prepare_520_repair_data()
    print("\nData summary:")
    print(f"- Date range: {df['작업종료일'].min()} ~ {df['작업종료일'].max()}")
    print(f"- X range: {df['x'].min():.0f} ~ {df['x'].max():.0f}")
    print(f"- Y range: {df['y'].min():.0f} ~ {df['y'].max():.0f}")
    print(f"- Repair types: {df['repair_type'].value_counts().to_dict()}")
