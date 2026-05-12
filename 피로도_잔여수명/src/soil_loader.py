"""
토양(지질) 데이터 로딩 및 처리를 위한 특화 모듈
Geology 데이터를 로드하고 처리하는 비즈니스 로직
"""

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


def get_soil_path(base_dir: Path) -> Path:
    """
    토양 데이터 파일 경로 반환

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)

    Returns:
        Geology_250K_Litho.shp 파일 경로
    """
    # base_dir이 'raw'로 끝나면 상위 디렉토리 사용
    soil_dir = base_dir.parent / "soil" if base_dir.name == "raw" else base_dir / "soil"

    return soil_dir / "Geology_250K_Litho.shp"


def validate_soil_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    토양 데이터 검증 및 정리

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
        print("경고: 토양 데이터에 CRS가 없습니다. EPSG:5179로 설정합니다.")
        gdf.set_crs("EPSG:5179", inplace=True)

    return gdf


def load_soil_data(
    base_dir: Path, encoding: str = "utf-8", verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """
    토양 데이터(Geology_250K_Litho) 로드

    Args:
        base_dir: 기본 디렉토리 (data 또는 data/raw)
        encoding: 파일 인코딩 (기본값: utf-8)
        verbose: 상세 정보 출력 여부

    Returns:
        토양 GeoDataFrame 또는 None (실패 시)
    """
    soil_path = get_soil_path(base_dir)

    if not soil_path.exists():
        if verbose:
            print(f"오류: 토양 데이터를 찾을 수 없습니다: {soil_path}")
        return None

    try:
        # 지정된 인코딩으로 읽기
        gdf = gpd.read_file(soil_path, encoding=encoding)

        # 데이터 검증 및 정리
        gdf = validate_soil_data(gdf)

        if verbose:
            lithoidx_count = (
                gdf["lithoidx"].nunique() if "lithoidx" in gdf.columns else 0
            )
            print(
                f"토양 데이터 로드 완료: {len(gdf)}개 객체, "
                f"{lithoidx_count}개 고유 lithoidx"
            )

        return gdf

    except Exception as e:
        if verbose:
            print(f"오류: 토양 데이터 로드 실패 - {e}")
        return None


def get_soil_info(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """
    토양 데이터의 기본 정보 반환

    Args:
        gdf: 토양 GeoDataFrame

    Returns:
        기본 정보를 담은 딕셔너리
    """
    info = {
        "total_features": len(gdf),
        "crs": str(gdf.crs) if gdf.crs else None,
        "columns": list(gdf.columns),
        "bounds": gdf.total_bounds.tolist() if not gdf.empty else None,
    }

    # lithoidx 정보
    if "lithoidx" in gdf.columns:
        info["unique_lithoidx"] = gdf["lithoidx"].nunique()
        info["lithoidx_values"] = sorted(gdf["lithoidx"].unique().tolist())

    # lithoname 정보
    if "lithoname" in gdf.columns:
        info["unique_lithonames"] = gdf["lithoname"].nunique()

    # age 정보
    if "age" in gdf.columns:
        info["unique_ages"] = gdf["age"].nunique()
        info["age_values"] = sorted(gdf["age"].unique().tolist())

    return info


def get_file_type_from_path(file_path: Path) -> str:
    """파일 경로에서 타입 추출

    Args:
        file_path: 파일 경로

    Returns:
        파일 타입 (boundary, fault, frame, litho)
    """
    if "Boudary" in file_path.name:
        return "boundary"
    if "Fault" in file_path.name:
        return "fault"
    if "Frame" in file_path.name:
        return "frame"
    if "Litho" in file_path.name:
        return "litho"
    return "unknown"


@dataclass
class LithoidxStatistics:
    """Lithoidx 통계 정보를 담는 데이터 클래스"""

    total_lithoidx: int
    total_objects: int
    total_area: float
    avg_objects_per_lithoidx: float
    max_objects_lithoidx: pd.Series
    max_area_lithoidx: pd.Series
    age_distribution: dict[str, int] = field(default_factory=dict)
    map_coverage: set[str] = field(default_factory=set)


def analyze_lithoidx(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """lithoidx별 정보 분석

    Args:
        gdf: 토양 GeoDataFrame

    Returns:
        lithoidx별 분석 결과 DataFrame
    """
    results = []

    # lithoidx로 그룹화
    grouped = gdf.groupby("lithoidx")

    for lithoidx, group in grouped:
        # 각 lithoidx에 대한 정보 수집
        info = {
            "lithoidx": lithoidx,
            "count": len(group),
            "lithoname": (
                group["lithoname"].iloc[0] if "lithoname" in group.columns else "N/A"
            ),
            "total_area": (
                group["shape_area"].sum() if "shape_area" in group.columns else 0
            ),
            "avg_area": (
                group["shape_area"].mean() if "shape_area" in group.columns else 0
            ),
            "total_length": (
                group["shape_len"].sum() if "shape_len" in group.columns else 0
            ),
        }

        # age 분포 계산
        if "age" in group.columns:
            age_counts = group["age"].value_counts()
            info["unique_ages"] = len(age_counts)
            info["ages"] = ", ".join(
                [f"{age}({count})" for age, count in age_counts.items()]
            )
        else:
            info["unique_ages"] = 0
            info["ages"] = "N/A"

        # mapname 목록
        if "mapname" in group.columns:
            unique_maps = group["mapname"].unique()
            info["map_count"] = len(unique_maps)
            info["maps"] = ", ".join(sorted(unique_maps))
        else:
            info["map_count"] = 0
            info["maps"] = "N/A"

        results.append(info)

    # DataFrame으로 변환하고 면적 기준 내림차순 정렬
    df = pd.DataFrame(results)
    df = df.sort_values("total_area", ascending=False)
    df["rank"] = range(1, len(df) + 1)

    return df


def generate_lithoidx_statistics(df: pd.DataFrame) -> LithoidxStatistics:
    """전체 통계 요약 생성

    Args:
        df: lithoidx 분석 결과 DataFrame

    Returns:
        전체 통계 정보
    """
    stats = LithoidxStatistics(
        total_lithoidx=len(df),
        total_objects=int(df["count"].sum()),
        total_area=float(df["total_area"].sum()),
        avg_objects_per_lithoidx=float(df["count"].mean()),
        max_objects_lithoidx=df.loc[df["count"].idxmax()].copy(),  # type: ignore
        max_area_lithoidx=df.loc[df["total_area"].idxmax()].copy(),  # type: ignore
    )

    # age 분포 집계
    for ages_str in df["ages"]:
        if ages_str != "N/A":
            for age_info in ages_str.split(", "):
                if "(" in age_info:
                    age = age_info.split("(")[0]
                    count = int(age_info.split("(")[1].rstrip(")"))
                    if age in stats.age_distribution:
                        stats.age_distribution[age] += count
                    else:
                        stats.age_distribution[age] = count

    # 도엽 커버리지
    for maps_str in df["maps"]:
        if maps_str != "N/A":
            stats.map_coverage.update(maps_str.split(", "))

    return stats


def search_lithoidx(df: pd.DataFrame, search_term: str) -> pd.DataFrame:
    """특정 lithoidx 또는 암상명 검색

    Args:
        df: lithoidx 분석 결과 DataFrame
        search_term: 검색어

    Returns:
        검색 결과 DataFrame
    """
    # lithoidx로 검색
    if search_term.isdigit():
        idx = int(search_term)
        result = df[df["lithoidx"] == idx]
    else:
        # 암상명으로 검색 (부분 일치)
        result = df[df["lithoname"].str.contains(search_term, case=False, na=False)]

    return result


def load_k_soil_data(results_dir: Path) -> pd.DataFrame | None:
    """K_SOIL 데이터 로드

    Args:
        results_dir: 결과 디렉토리

    Returns:
        K_SOIL DataFrame 또는 None
    """
    k_soil_path = results_dir / "lithoidx_list_with_K_SOIL.csv"

    if not k_soil_path.exists():
        print(f"경고: K_SOIL 데이터를 찾을 수 없습니다: {k_soil_path}")
        return None

    try:
        df = pd.read_csv(k_soil_path, encoding="utf-8-sig")
        print(f"K_SOIL 데이터 로드 완료: {len(df)}개 lithoidx")
        return df[["lithoidx", "lithoname", "K_SOIL"]]
    except Exception as e:
        print(f"오류: K_SOIL 데이터 로드 실패 - {e}")
        return None


def spatial_join_with_soil(
    pipeline_gdf: gpd.GeoDataFrame,
    soil_gdf: gpd.GeoDataFrame,
    k_soil_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """파이프라인과 토양 데이터 공간 조인

    Args:
        pipeline_gdf: 파이프라인 GeoDataFrame
        soil_gdf: 토양 GeoDataFrame
        k_soil_df: K_SOIL 정보 DataFrame (선택적)

    Returns:
        FTR_IDN별 lithoidx 매칭 결과 DataFrame
    """
    # CRS 일치 확인
    if pipeline_gdf.crs != soil_gdf.crs:
        print("CRS 불일치 감지. 토양 데이터를 파이프라인 CRS로 변환합니다.")
        soil_gdf = soil_gdf.to_crs(pipeline_gdf.crs)

    # 공간 조인 수행 (intersects 사용)
    joined = gpd.sjoin(
        pipeline_gdf[["FTR_IDN", "geometry"]],
        soil_gdf[["lithoidx", "geometry"]],
        how="left",
        predicate="intersects",
    )

    # 중복 제거 (하나의 파이프가 여러 토양과 교차할 수 있음)
    # 가장 많이 교차하는 lithoidx 선택
    result = []

    for ftr_idn, group in joined.groupby("FTR_IDN"):
        if "lithoidx" in group.columns and not group["lithoidx"].isna().all():
            # 가장 빈번한 lithoidx 선택
            lithoidx_counts = group["lithoidx"].value_counts()
            if not lithoidx_counts.empty:
                most_common_lithoidx = lithoidx_counts.index[0]
                result.append({"FTR_IDN": ftr_idn, "lithoidx": most_common_lithoidx})
            else:
                result.append({"FTR_IDN": ftr_idn, "lithoidx": None})
        else:
            result.append({"FTR_IDN": ftr_idn, "lithoidx": None})

    result_df = pd.DataFrame(result)

    # K_SOIL 정보 병합
    if k_soil_df is not None:
        result_df = result_df.merge(k_soil_df, on="lithoidx", how="left")

    return result_df


def save_soil_matching_result(
    df: pd.DataFrame, output_path: Path, verbose: bool = True
) -> None:
    """토양 매칭 결과를 CSV 파일로 저장

    Args:
        df: 저장할 DataFrame
        output_path: 출력 경로
        verbose: 상세 정보 출력 여부
    """
    # FTR_IDN을 정수로 변환
    df["FTR_IDN"] = df["FTR_IDN"].astype(int)

    # 컬럼 순서 정리 (K_SOIL 정보가 있는 경우)
    if "K_SOIL" in df.columns:
        columns = ["FTR_IDN", "lithoidx", "lithoname", "K_SOIL"]
        df = df[columns]

    # NaN을 빈 문자열로 변환
    df = df.fillna("")

    # CSV 저장
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    if verbose:
        print(f"CSV 저장 완료: {output_path}")
        print(f"  - 총 {len(df)}개 FTR_IDN")
        print(f"  - 매칭된 항목: {len(df[df['lithoidx'] != ''])}개")
        print(f"  - 매칭 안됨: {len(df[df['lithoidx'] == ''])}개")
