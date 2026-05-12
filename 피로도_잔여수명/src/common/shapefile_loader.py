"""
Shapefile 로딩을 위한 공통 모듈
각 함수는 하나의 shapefile을 로드하는 단일 책임을 가짐
"""

import re
import warnings
from pathlib import Path
from typing import Any, ClassVar

import geopandas as gpd
import pandas as pd

from src.common.config import REGION_CODE_PATTERN, SUBREGION_MAPPING

# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)


class ShapefileConfig:
    """Shapefile 관련 설정"""

    # 지원되는 파이프 타입
    PIPE_TYPES: ClassVar[dict[str, dict[str, str]]] = {
        "PIPE_LM": {"filename": "V_WTL_PIPE_LM.shp", "ftr_cde": "SA001"},
        "SPLY_LS": {"filename": "V_WTL_SPLY_LS.shp", "ftr_cde": "SA002"},
    }

    # 구역 관련 파일명
    ZONE_FILES: ClassVar[dict[str, str]] = {
        "SMLZ": "WEA_SMLZ_AS.shp",  # 소구역
        "MDLZ": "WEA_MDLZ_AS.shp",  # 중구역
        "LRGZ": "WEA_LRGZ_AS.shp",  # 대구역
    }

    # 기본 CRS
    DEFAULT_CRS = "EPSG:5179"

    # 기본 인코딩
    DEFAULT_ENCODING = "euc-kr"


class ShapefileLoader:
    """Shapefile 로딩 클래스"""

    def __init__(self, data_dir: Path, verbose: bool = True):
        """
        Args:
            data_dir: 데이터 디렉토리
            verbose: 상세 정보 출력 여부
        """
        self.data_dir = Path(data_dir)
        self.verbose = verbose

    def find_export_directory(self, region_code: str) -> Path | None:
        """
        지정된 region_code에 해당하는 export 디렉토리 찾기

        Args:
            region_code: 지역 코드

        Returns:
            export 디렉토리 경로 또는 None
        """
        for export_dir in self.data_dir.iterdir():
            if export_dir.is_dir() and export_dir.name.startswith("export_shp_"):
                match = re.search(REGION_CODE_PATTERN, export_dir.name)
                if match and match.group(1) == region_code:
                    return export_dir
        return None

    def load_shapefile(
        self,
        file_path: Path,
        encoding: str | None = None,
        crs: str | None = None,
        additional_fields: dict[str, Any] | None = None,
    ) -> gpd.GeoDataFrame | None:
        """
        일반적인 shapefile 로딩 함수

        Args:
            file_path: shapefile 경로
            encoding: 인코딩 (기본값: euc-kr)
            crs: 좌표계 (None이면 기본값 사용)
            additional_fields: 추가할 필드들

        Returns:
            GeoDataFrame 또는 None
        """
        if not file_path.exists():
            if self.verbose:
                print(f"파일을 찾을 수 없습니다: {file_path}")
            return None

        try:
            # shapefile 로드
            gdf = gpd.read_file(
                file_path, encoding=encoding or ShapefileConfig.DEFAULT_ENCODING
            )

            # CRS 설정
            if gdf.crs is None and crs:
                gdf.set_crs(crs or ShapefileConfig.DEFAULT_CRS, inplace=True)

            # 추가 필드 설정
            if additional_fields:
                for field, value in additional_fields.items():
                    gdf[field] = value

            if self.verbose:
                print(f"Shapefile 로드 완료: {file_path.name} ({len(gdf)}개 객체)")

            return gdf

        except Exception as e:
            if self.verbose:
                print(f"Shapefile 로드 실패 ({file_path}): {e}")
            return None

    def load_pipe_shapefile(
        self, region_code: str, pipe_type: str = "PIPE_LM"
    ) -> gpd.GeoDataFrame | None:
        """
        지정된 region_code와 pipe_type에 해당하는 shapefile 로드

        Args:
            region_code: 지역 코드 (예: 0520, 0903)
            pipe_type: 파이프 타입 ("PIPE_LM" 또는 "SPLY_LS")

        Returns:
            GeoDataFrame 또는 None (실패 시)
        """
        if pipe_type not in ShapefileConfig.PIPE_TYPES:
            if self.verbose:
                print(f"오류: 지원하지 않는 파이프 타입 - {pipe_type}")
                print(f"지원하는 타입: {list(ShapefileConfig.PIPE_TYPES.keys())}")
            return None

        # export 디렉토리 찾기
        export_dir = self.find_export_directory(region_code)
        if not export_dir:
            if self.verbose:
                print(f"{region_code} 지역의 export 디렉토리를 찾을 수 없습니다.")
            return None

        # shapefile 경로
        pipe_config = ShapefileConfig.PIPE_TYPES[pipe_type]
        shp_path = export_dir / pipe_config["filename"]

        # 추가 필드
        additional_fields = {"FTR_CDE": pipe_config["ftr_cde"], "PIPE_TYPE": pipe_type}

        return self.load_shapefile(
            shp_path,
            crs=ShapefileConfig.DEFAULT_CRS,
            additional_fields=additional_fields,
        )

    def get_zone_shapefile_path(
        self, region_code: str, zone_type: str = "SMLZ"
    ) -> Path | None:
        """
        지정된 region_code와 zone_type에 해당하는 shapefile 경로 찾기

        Args:
            region_code: 지역 코드
            zone_type: 구역 타입 (SMLZ, MDLZ, LRGZ)

        Returns:
            shapefile 경로 또는 None
        """
        if zone_type not in ShapefileConfig.ZONE_FILES:
            if self.verbose:
                print(f"오류: 지원하지 않는 구역 타입 - {zone_type}")
                print(f"지원하는 타입: {list(ShapefileConfig.ZONE_FILES.keys())}")
            return None

        export_dir = self.find_export_directory(region_code)
        if not export_dir:
            return None

        zone_path = export_dir / ShapefileConfig.ZONE_FILES[zone_type]
        return zone_path if zone_path.exists() else None

    def load_all_zone_shapefiles(
        self, zone_type: str = "MDLZ"
    ) -> gpd.GeoDataFrame | None:
        """
        모든 export 폴더의 특정 구역 shapefile을 로드하고 병합

        Args:
            zone_type: 구역 타입 (SMLZ, MDLZ, LRGZ)

        Returns:
            병합된 GeoDataFrame 또는 None
        """
        if zone_type not in ShapefileConfig.ZONE_FILES:
            if self.verbose:
                print(f"오류: 지원하지 않는 구역 타입 - {zone_type}")
            return None

        gdfs = []
        zone_filename = ShapefileConfig.ZONE_FILES[zone_type]

        # 모든 export 디렉토리 찾기
        for export_dir in self.data_dir.iterdir():
            if export_dir.is_dir() and export_dir.name.startswith("export_shp_"):
                zone_path = export_dir / zone_filename

                if zone_path.exists():
                    # 지역 코드 추출
                    match = re.search(REGION_CODE_PATTERN, export_dir.name)
                    region_code = match.group(1) if match else None

                    # shapefile 로드
                    gdf = self.load_shapefile(
                        zone_path,
                        crs=ShapefileConfig.DEFAULT_CRS,
                        additional_fields=(
                            {"REGION_CODE": region_code} if region_code else None
                        ),
                    )

                    if gdf is not None:
                        gdfs.append(gdf)

        # 병합
        if gdfs:
            combined_gdf = pd.concat(gdfs, ignore_index=True)
            combined_gdf = gpd.GeoDataFrame(combined_gdf, crs=gdfs[0].crs)

            if self.verbose:
                print(f"\n전체 {zone_type}: {len(combined_gdf)}개 구역")
                if "REGION_CODE" in combined_gdf.columns:
                    for region, count in (
                        combined_gdf["REGION_CODE"].value_counts().items()
                    ):
                        print(f"  - {region}: {count}개")

            return combined_gdf

        if self.verbose:
            print(f"{zone_type} 파일을 찾을 수 없습니다.")
        return None


# 기존 함수들과의 호환성을 위한 래퍼 함수들
def load_pipe_shapefile(
    data_dir: Path,
    region_code: str,
    pipe_type: str = "PIPE_LM",
    verbose: bool = True,
) -> gpd.GeoDataFrame | None:
    """기존 함수와의 호환성을 위한 래퍼"""
    loader = ShapefileLoader(data_dir, verbose)
    return loader.load_pipe_shapefile(region_code, pipe_type)


def get_smlz_shapefile_path(data_dir: Path, region_code: str) -> Path | None:
    """기존 함수와의 호환성을 위한 래퍼"""
    loader = ShapefileLoader(data_dir, verbose=False)
    return loader.get_zone_shapefile_path(region_code, "SMLZ")


def get_mdlz_shapefile_path(data_dir: Path, region_code: str) -> Path | None:
    """기존 함수와의 호환성을 위한 래퍼"""
    loader = ShapefileLoader(data_dir, verbose=False)
    return loader.get_zone_shapefile_path(region_code, "MDLZ")


def load_all_mdlz_shapefiles(
    data_dir: Path, verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """기존 함수와의 호환성을 위한 래퍼"""
    loader = ShapefileLoader(data_dir, verbose)
    return loader.load_all_zone_shapefiles("MDLZ")


# 하위 지역 지원 함수들
def is_subregion(region_code: str) -> bool:
    """하위 지역인지 확인"""
    return region_code in SUBREGION_MAPPING


def get_parent_region(region_code: str) -> str:
    """하위 지역의 부모 지역 반환"""
    if region_code in SUBREGION_MAPPING:
        return SUBREGION_MAPPING[region_code]["parent"]
    return region_code


def get_subregion_label(region_code: str) -> str:
    """하위 지역 라벨 반환"""
    if region_code in SUBREGION_MAPPING:
        return SUBREGION_MAPPING[region_code]["label"]
    return ""


def get_subregion_boundary(smlz_path: Path, label: str) -> gpd.GeoDataFrame | None:
    """WEA_SMLZ_AS에서 특정 라벨의 지역 경계 추출

    Args:
        smlz_path: WEA_SMLZ_AS.shp 파일 경로
        label: 추출할 지역 라벨 (예: '47', '48', '49')

    Returns:
        해당 라벨의 지역 경계 GeoDataFrame
    """
    try:
        gdf = gpd.read_file(smlz_path, encoding="euc-kr")

        # CRS 설정
        if gdf.crs is None:
            gdf.set_crs("EPSG:5179", inplace=True)

        # 특정 라벨 필터링
        filtered = gdf[gdf["SMZ_LBL"] == label]

        if len(filtered) == 0:
            print(f"경고: 라벨 '{label}'을 찾을 수 없습니다.")
            return None

        return filtered

    except Exception as e:
        print(f"오류: 지역 경계 추출 실패 - {e}")
        return None


def filter_pipes_by_region(
    pipe_gdf: gpd.GeoDataFrame, region_boundary: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """지역 경계 내의 파이프만 필터링

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        region_boundary: 지역 경계 GeoDataFrame

    Returns:
        필터링된 파이프 GeoDataFrame
    """
    try:
        # 공간 조인으로 경계 내 파이프 필터링
        filtered = gpd.sjoin(pipe_gdf, region_boundary, predicate="within", how="inner")

        # 중복 컬럼 제거 (sjoin으로 생성된 index_right 등)
        columns_to_keep = pipe_gdf.columns.tolist()
        return filtered[columns_to_keep]

    except Exception as e:
        print(f"오류: 파이프 필터링 실패 - {e}")
        return pipe_gdf
