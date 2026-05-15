"""
0100(사라봉) 지역 교통 정보 CSV 생성 스크립트

data/traffic_shp/N3L_A0020000_50.shp (도로중심선)와
data/raw/export_shp_20250704(0100)/ 의 관로 shp를 공간 조인하여
data/traffic/0100_pipe_traffic.csv, 0100_sply_traffic.csv 생성

로컬에서 실행:
    cd 피로도_잔여수명
    uv run python src/tmp/make_0100_traffic_csv.py
"""

import shutil
import warnings
from pathlib import Path

import geopandas as gpd

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent.parent
ROAD_SHP = BASE_DIR / "data" / "traffic_shp" / "N3L_A0020000_50.shp"
PIPE_SHP = BASE_DIR / "data" / "raw" / "export_shp_20250704(0100)" / "상수관로_사라봉1.shp"
SPLY_SHP = BASE_DIR / "data" / "raw" / "export_shp_20250704(0100)" / "급수관로_사라봉1.shp"
OUTPUT_DIR = BASE_DIR / "data" / "traffic"


def load_road(path: Path) -> gpd.GeoDataFrame:
    """N3L_A0020000 도로 shapefile 로드 후 컬럼 표준화."""
    print(f"도로 데이터 로드: {path}")
    gdf = gpd.read_file(path)
    print(f"  행 수: {len(gdf)}, CRS: {gdf.crs}")

    # N3L → 기존 traffic_analyzer.py 호환 컬럼명으로 변환
    gdf = gdf.rename(columns={
        "RVWD": "ROAD_BT",   # 도로폭
        "RDNM": "RN",        # 도로명
        "RDNU": "RN_CD",     # 도로번호
        "RDDV": "ROA_CLS_SE",  # 도로구분
    })
    gdf["SIG_CD"] = None  # perform_spatial_join에서 선택하는 컬럼 (미사용)

    missing = [c for c in ["ROAD_BT", "RN", "RN_CD", "ROA_CLS_SE"] if c not in gdf.columns]
    if missing:
        raise RuntimeError(f"도로 shapefile에 필요한 컬럼 없음: {missing}")

    # ROAD_BT NaN → 0 처리
    gdf["ROAD_BT"] = gdf["ROAD_BT"].fillna(0.0)
    print(f"  도로폭 범위: {gdf['ROAD_BT'].min():.1f} ~ {gdf['ROAD_BT'].max():.1f}m")
    return gdf


def load_pipe(path: Path, label: str) -> gpd.GeoDataFrame:
    """관로 shapefile 로드. CPG 인코딩 오류 자동 우회."""
    cpg_path = path.with_suffix(".cpg")
    backup = None

    if cpg_path.exists():
        original_enc = cpg_path.read_text().strip()
        if original_enc.upper() not in ("EUC-KR", "EUC_KR"):
            backup = cpg_path.read_bytes()
            cpg_path.write_text("EUC-KR")

    try:
        gdf = gpd.read_file(path)
    finally:
        if backup is not None:
            cpg_path.write_bytes(backup)

    print(f"{label} 로드 완료: {len(gdf)}개 관로, CRS: {gdf.crs}")
    if "FTR_IDN" not in gdf.columns:
        raise RuntimeError(f"{label}에 FTR_IDN 컬럼 없음")
    return gdf[["FTR_IDN", "geometry"]]


def create_buffers(road_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """도로폭의 절반(최소 3m, 최대 20m)을 버퍼로 생성."""
    print("도로 버퍼 생성 중...")
    road_gdf = road_gdf.copy()
    road_gdf["buffer_dist"] = road_gdf["ROAD_BT"].apply(
        lambda w: max(3.0, min(20.0, w * 0.5))
    )
    road_gdf["buffered_geometry"] = road_gdf.apply(
        lambda r: r.geometry.buffer(r["buffer_dist"], cap_style="round"), axis=1
    )
    buf = road_gdf.set_geometry("buffered_geometry")
    print(f"  평균 버퍼: {road_gdf['buffer_dist'].mean():.1f}m")
    return buf


def spatial_join_and_select(
    pipe_gdf: gpd.GeoDataFrame, road_buf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """공간 조인 후 도로폭 기준 우선순위 적용."""
    road_cols = ["RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE", "SIG_CD", "buffered_geometry"]
    available = [c for c in road_cols if c in road_buf.columns]
    overlaps = gpd.sjoin(pipe_gdf, road_buf[available], how="left", predicate="intersects")

    matched = overlaps["RN_CD"].notna().sum()
    print(f"  매칭: {matched}/{len(pipe_gdf)} ({matched/len(pipe_gdf)*100:.1f}%)")

    # 여러 도로와 중첩 시 도로폭 큰 것 우선 선택
    sort_cols = [c for c in ["ROAD_BT", "ROA_CLS_SE", "RN_CD"] if c in overlaps.columns]
    ascending = [False, True, True][: len(sort_cols)]
    result = (
        overlaps.sort_values(by=["FTR_IDN"] + sort_cols, ascending=[True] + ascending)
        .drop_duplicates(subset=["FTR_IDN"], keep="first")
    )
    return result


def save_csv(df: gpd.GeoDataFrame, output_path: Path) -> None:
    out_cols = ["FTR_IDN", "RN_CD", "RN", "ROAD_BT", "ROA_CLS_SE"]
    out = df[[c for c in out_cols if c in df.columns]].copy()
    out["FTR_IDN"] = out["FTR_IDN"].astype(float).astype(int)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  저장: {output_path} ({len(out)}개 레코드)")


def main() -> None:
    print("=" * 60)
    print("0100(사라봉) 교통 정보 CSV 생성")
    print("=" * 60)

    if not ROAD_SHP.exists():
        raise FileNotFoundError(f"도로 shapefile 없음: {ROAD_SHP}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 도로 데이터 로드 및 버퍼 생성
    road_gdf = load_road(ROAD_SHP)

    # CRS 통일 (도로 기준)
    road_crs = road_gdf.crs

    road_buf = create_buffers(road_gdf)

    # 1. 상수관로 (PIPE_LM)
    print("\n[1/2] 상수관로 처리...")
    pipe_gdf = load_pipe(PIPE_SHP, "상수관로")
    pipe_gdf = pipe_gdf.to_crs(road_crs)
    result_pipe = spatial_join_and_select(pipe_gdf, road_buf)
    save_csv(result_pipe, OUTPUT_DIR / "0100_pipe_traffic.csv")

    # 2. 급수관로 (SPLY_LS)
    print("\n[2/2] 급수관로 처리...")
    sply_gdf = load_pipe(SPLY_SHP, "급수관로")
    sply_gdf = sply_gdf.to_crs(road_crs)
    result_sply = spatial_join_and_select(sply_gdf, road_buf)
    save_csv(result_sply, OUTPUT_DIR / "0100_sply_traffic.csv")

    print("\n완료!")
    print(f"결과 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
