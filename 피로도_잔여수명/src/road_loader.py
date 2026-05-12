"""
도로 데이터 로딩 및 처리를 위한 특화 모듈
TL_SPRD_MANAGE 도로 데이터를 로드하고 처리하는 비즈니스 로직
"""

import warnings
from pathlib import Path
from typing import Any

import geopandas as gpd

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_road_path(base_dir: Path) -> Path:
    """
    도로 데이터 파일 경로 반환

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)

    Returns:
        TL_SPRD_MANAGE.shp 파일 경로
    """
    # base_dir이 'raw'로 끝나면 상위 디렉토리 사용
    road_dir = base_dir.parent / "road" if base_dir.name == "raw" else base_dir / "road"

    return road_dir / "TL_SPRD_MANAGE.shp"


def validate_road_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    도로 데이터 검증 및 정리

    Args:
        gdf: 원본 GeoDataFrame

    Returns:
        정리된 GeoDataFrame
    """
    # NULL geometry 제거
    null_geom = gdf[gdf.geometry.isnull()].shape[0]
    if null_geom > 0:
        print(f"경고: NULL geometry {null_geom}개 제거")
        gdf = gdf[~gdf.geometry.isnull()]

    # CRS 확인 및 설정
    if gdf.crs is None:
        print("경고: 도로 데이터에 CRS가 없습니다. EPSG:5179로 설정합니다.")
        gdf.set_crs("EPSG:5179", inplace=True)

    return gdf


def load_road_data(
    base_dir: Path, encoding: str = "euc-kr", verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """
    도로 데이터(TL_SPRD_MANAGE) 로드

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)
        encoding: 파일 인코딩 (기본값: euc-kr)
        verbose: 상세 정보 출력 여부

    Returns:
        도로 GeoDataFrame 또는 None (실패 시)
    """
    road_path = get_road_path(base_dir)

    if not road_path.exists():
        if verbose:
            print(f"오류: 도로 데이터를 찾을 수 없습니다: {road_path}")
        return None

    try:
        # 지정된 인코딩으로 읽기 시도
        gdf = gpd.read_file(road_path, encoding=encoding)
    except UnicodeDecodeError:
        # encoding이 맞지 않으면 다른 인코딩 시도
        if verbose:
            print(f"{encoding} 인코딩 실패, utf-8로 재시도")
        try:
            gdf = gpd.read_file(road_path, encoding="utf-8")
        except Exception as e:
            if verbose:
                print(f"오류: 도로 데이터 로드 실패 - {e}")
            return None
    except Exception as e:
        if verbose:
            print(f"오류: 도로 데이터 로드 실패 - {e}")
        return None

    # 데이터 검증 및 정리
    gdf = validate_road_data(gdf)

    if verbose:
        print(f"도로 데이터 로드 완료: {len(gdf)}개의 도로 구간")
        print(f"CRS: {gdf.crs}")
        print(f"컬럼: {list(gdf.columns)}")

    return gdf


def get_road_info(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """
    도로 데이터의 기본 정보 반환

    Args:
        gdf: 도로 GeoDataFrame

    Returns:
        기본 정보를 담은 딕셔너리
    """
    info = {
        "total_features": len(gdf),
        "crs": str(gdf.crs) if (not gdf.empty and gdf.crs) else None,
        "columns": list(gdf.columns),
        "bounds": gdf.total_bounds.tolist() if not gdf.empty else None,
    }

    # BSI_INT_SN 정보
    if "BSI_INT_SN" in gdf.columns:
        info["unique_bsi_int_sn"] = gdf["BSI_INT_SN"].nunique()

    # RDS_MAN_NO 정보
    if "RDS_MAN_NO" in gdf.columns:
        info["unique_rds_man_no"] = gdf["RDS_MAN_NO"].nunique()

    # SIG_CD 정보 (시군구 코드)
    if "SIG_CD" in gdf.columns:
        info["unique_sig_cd"] = gdf["SIG_CD"].nunique()
        info["sig_cd_values"] = sorted(gdf["SIG_CD"].unique().tolist())

    # ROA_CLS_SE 정보 (도로 등급)
    if "ROA_CLS_SE" in gdf.columns:
        info["unique_roa_cls_se"] = gdf["ROA_CLS_SE"].nunique()
        info["roa_cls_se_values"] = sorted(gdf["ROA_CLS_SE"].unique().tolist())

    # ROAD_BT 정보 (도로 폭)
    if "ROAD_BT" in gdf.columns:
        info["road_bt_min"] = gdf["ROAD_BT"].min()
        info["road_bt_max"] = gdf["ROAD_BT"].max()
        info["road_bt_mean"] = gdf["ROAD_BT"].mean()

    return info


def print_road_columns_info(gdf: gpd.GeoDataFrame) -> None:
    """도로 데이터의 컬럼 정보 출력

    Args:
        gdf: 도로 GeoDataFrame
    """
    print("\n=== 도로 데이터 컬럼 정보 ===")
    for col in gdf.columns:
        if col != "geometry":
            print(f"\n{col}:")
            print(f"  - 데이터 타입: {gdf[col].dtype}")
            print(f"  - 고유값 수: {gdf[col].nunique()}")
            if gdf[col].dtype in ["object", "int64", "float64"]:
                print(f"  - 샘플: {gdf[col].head(3).tolist()}")
