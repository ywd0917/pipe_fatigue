"""
좌표 기반 중구역/소구역 번호 수정 스크립트

data/main11e_fix_error/ 내의 CSV 파일을 읽어서
위도/경도 좌표를 이용해 올바른 중구역번호(MDZ_NUM)와 소구역번호(SMZ_NUM)를 할당합니다.

입력:
    - data/main11e_fix_error/*.csv: 위치 정보가 있는 재작업 데이터
    - data/raw/export_shp_*/WEA_MDLZ_AS.shp: 중구역 경계 shapefile
    - data/raw/export_shp_*/WEA_SMLZ_AS.shp: 소구역 경계 shapefile

출력:
    - results/main11g_fix_area_no/[파일명]_구역수정.csv: 구역 번호가 수정된 CSV
    - 통계 리포트 (콘솔 출력)
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from common.config import RAW_DATA_DIR, RESULTS_DIR
from common.korean_font_utils import setup_korean_font


def load_csv_data(file_path: Path) -> pd.DataFrame:
    """
    CSV 파일을 로드하고 필수 컬럼을 검증합니다.

    Args:
        file_path: CSV 파일 경로

    Returns:
        로드된 DataFrame

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: 필수 컬럼이 없을 때
    """
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))

    df = pd.read_csv(file_path, encoding="utf-8-sig")

    # 필수 컬럼 확인
    required_columns = ["위도", "경도", "중구역번호", "소구역번호"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"필수 컬럼 누락: {', '.join(missing)}")

    print(f"CSV 파일 로드 완료: {len(df):,}개 행")
    print(f"컬럼: {', '.join(df.columns)}")

    return df


def load_zone_shapefiles(
    data_dir: Path = RAW_DATA_DIR, region_code: str = "0520"
) -> tuple[gpd.GeoDataFrame | None, gpd.GeoDataFrame | None]:
    """
    중구역(MDLZ)과 소구역(SMLZ) shapefile을 로드합니다.

    Args:
        data_dir: 데이터 디렉토리 경로
        region_code: 지역 코드 (기본값: "0520")

    Returns:
        (mdlz_gdf, smlz_gdf) 튜플
    """
    export_dir = data_dir / f"export_shp_20250704({region_code})"

    # 중구역 shapefile 로드
    mdlz_path = export_dir / "WEA_MDLZ_AS.shp"
    mdlz_gdf = None

    if mdlz_path.exists():
        try:
            mdlz_gdf = gpd.read_file(mdlz_path, encoding="euc-kr")
            if mdlz_gdf.crs is None:
                mdlz_gdf.set_crs("EPSG:5179", inplace=True)
            print(f"MDLZ shapefile 로드: {len(mdlz_gdf)}개 중구역")

            # MDZ_NUM을 문자열로 변환하고 앞에 0 패딩
            if "MDZ_NUM" in mdlz_gdf.columns:
                mdlz_gdf["MDZ_NUM"] = mdlz_gdf["MDZ_NUM"].astype(str).str.zfill(4)

        except Exception as e:
            print(f"경고: MDLZ shapefile 로드 실패 - {e}")
    else:
        print(f"경고: MDLZ shapefile 없음 - {mdlz_path}")

    # 소구역 shapefile 로드
    smlz_path = export_dir / "WEA_SMLZ_AS.shp"
    smlz_gdf = None

    if smlz_path.exists():
        try:
            smlz_gdf = gpd.read_file(smlz_path, encoding="euc-kr")
            if smlz_gdf.crs is None:
                smlz_gdf.set_crs("EPSG:5179", inplace=True)
            print(f"SMLZ shapefile 로드: {len(smlz_gdf)}개 소구역")

            # SMZ_NUM과 MDZ_NUM을 문자열로 변환하고 앞에 0 패딩
            if "SMZ_NUM" in smlz_gdf.columns:
                smlz_gdf["SMZ_NUM"] = smlz_gdf["SMZ_NUM"].astype(str).str.zfill(4)
            if "MDZ_NUM" in smlz_gdf.columns:
                smlz_gdf["MDZ_NUM"] = smlz_gdf["MDZ_NUM"].astype(str).str.zfill(4)

        except Exception as e:
            print(f"경고: SMLZ shapefile 로드 실패 - {e}")
    else:
        print(f"경고: SMLZ shapefile 없음 - {smlz_path}")

    return mdlz_gdf, smlz_gdf


def fix_zone_numbers(
    df: pd.DataFrame,
    mdlz_gdf: gpd.GeoDataFrame | None,
    smlz_gdf: gpd.GeoDataFrame | None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    좌표를 기반으로 구역 번호를 수정합니다.

    Args:
        df: 원본 DataFrame
        mdlz_gdf: 중구역 GeoDataFrame
        smlz_gdf: 소구역 GeoDataFrame

    Returns:
        (수정된 DataFrame, 통계 딕셔너리) 튜플
    """
    stats = {
        "total": len(df),
        "valid_coords": 0,
        "mdz_matched": 0,
        "smz_matched": 0,
        "mdz_changed": 0,
        "smz_changed": 0,
        "mdz_failed": 0,
        "smz_failed": 0,
    }

    # 유효한 좌표만 필터링
    df_valid = df.dropna(subset=["위도", "경도"]).copy()
    df_valid = df_valid[(df_valid["위도"] > 0) & (df_valid["경도"] > 0)]
    stats["valid_coords"] = len(df_valid)

    if stats["valid_coords"] == 0:
        print("경고: 유효한 좌표가 없습니다.")
        return df, stats

    print(f"\n유효한 좌표: {stats['valid_coords']:,}개")

    # WGS84 좌표를 GeoDataFrame으로 변환
    geometry = [
        Point(lon, lat)
        for lon, lat in zip(df_valid["경도"], df_valid["위도"], strict=False)
    ]
    gdf = gpd.GeoDataFrame(df_valid, geometry=geometry, crs="EPSG:4326")

    # EPSG:5179로 변환
    gdf = gdf.to_crs("EPSG:5179")

    # 원본 값 백업 (비교용)
    gdf["중구역번호_원본"] = gdf["중구역번호"].copy()
    gdf["소구역번호_원본"] = gdf["소구역번호"].copy()

    # 매칭 상태 플래그 초기화
    gdf["중구역_매칭"] = False
    gdf["소구역_매칭"] = False

    # 중구역 매칭
    if mdlz_gdf is not None:
        print("\n중구역 매칭 시작...")

        # 공간 조인 (left join으로 모든 점 유지)
        result = gpd.sjoin(
            gdf, mdlz_gdf[["MDZ_NUM", "geometry"]], how="left", predicate="within"
        )

        # 매칭된 경우 MDZ_NUM으로 업데이트
        matched_mask = result["MDZ_NUM"].notna()
        stats["mdz_matched"] = matched_mask.sum()

        # 중구역번호 업데이트 (문자열 타입으로 통일)
        result.loc[matched_mask, "중구역번호"] = result.loc[matched_mask, "MDZ_NUM"]
        result.loc[matched_mask, "중구역_매칭"] = True

        # 변경된 개수 계산
        # 원본이 NaN이거나 다른 값인 경우를 변경으로 간주
        changed_mask = matched_mask & (
            (result["중구역번호_원본"].isna())
            | (result["중구역번호_원본"].astype(str).str.zfill(4) != result["MDZ_NUM"])
        )
        stats["mdz_changed"] = changed_mask.sum()

        gdf = result.copy()

        # index_right 컬럼 제거
        if "index_right" in gdf.columns:
            gdf = gdf.drop(columns=["index_right"])
        if "MDZ_NUM" in gdf.columns:
            gdf = gdf.drop(columns=["MDZ_NUM"])

        print(
            f"중구역 매칭 완료: {stats['mdz_matched']:,}개 ({stats['mdz_matched']/stats['valid_coords']*100:.1f}%)"
        )
        print(f"중구역번호 변경: {stats['mdz_changed']:,}개")

    # 소구역 매칭
    if smlz_gdf is not None:
        print("\n소구역 매칭 시작...")

        # 공간 조인
        result = gpd.sjoin(
            gdf,
            smlz_gdf[["SMZ_NUM", "MDZ_NUM", "geometry"]],
            how="left",
            predicate="within",
        )

        # 매칭된 경우 SMZ_NUM으로 업데이트
        matched_mask = result["SMZ_NUM"].notna()
        stats["smz_matched"] = matched_mask.sum()

        # 소구역번호 업데이트
        result.loc[matched_mask, "소구역번호"] = result.loc[matched_mask, "SMZ_NUM"]
        result.loc[matched_mask, "소구역_매칭"] = True

        # SMLZ의 MDZ_NUM도 사용해서 중구역번호 업데이트 (더 정확함)
        if "MDZ_NUM" in result.columns:
            mdz_from_smlz_mask = matched_mask & result["MDZ_NUM"].notna()
            result.loc[mdz_from_smlz_mask, "중구역번호"] = result.loc[
                mdz_from_smlz_mask, "MDZ_NUM"
            ]

        # 변경된 개수 계산
        changed_mask = matched_mask & (
            (result["소구역번호_원본"].isna())
            | (result["소구역번호_원본"].astype(str).str.zfill(4) != result["SMZ_NUM"])
        )
        stats["smz_changed"] = changed_mask.sum()

        gdf = result.copy()

        # 불필요한 컬럼 제거
        columns_to_drop = ["index_right", "SMZ_NUM", "MDZ_NUM"]
        for col in columns_to_drop:
            if col in gdf.columns:
                gdf = gdf.drop(columns=[col])

        print(
            f"소구역 매칭 완료: {stats['smz_matched']:,}개 ({stats['smz_matched']/stats['valid_coords']*100:.1f}%)"
        )
        print(f"소구역번호 변경: {stats['smz_changed']:,}개")

    # 매칭 실패 통계
    stats["mdz_failed"] = (~gdf["중구역_매칭"]).sum()
    stats["smz_failed"] = (~gdf["소구역_매칭"]).sum()

    # geometry 컬럼 제거 (CSV 저장용)
    result_df = pd.DataFrame(gdf.drop(columns=["geometry"]))

    # 원본 DataFrame의 인덱스 순서 유지
    df_result = df.copy()
    df_result.loc[result_df.index, "중구역번호"] = result_df["중구역번호"]
    df_result.loc[result_df.index, "소구역번호"] = result_df["소구역번호"]

    # 중구역번호를 정수 타입으로 변환 (가능한 경우)
    try:
        # NaN이 아닌 값들을 float로 변환 후 정수로
        mask = df_result["중구역번호"].notna()
        df_result.loc[mask, "중구역번호"] = (
            df_result.loc[mask, "중구역번호"].astype(float).astype(int)
        )
    except (ValueError, TypeError):
        # 변환 실패시 문자열로 유지
        pass

    return df_result, stats


def save_results(
    df: pd.DataFrame, stats: dict[str, int], input_file: Path, output_dir: Path
) -> None:
    """
    결과를 CSV 파일로 저장하고 통계를 출력합니다.

    Args:
        df: 결과 DataFrame
        stats: 통계 딕셔너리
        input_file: 입력 파일 경로
        output_dir: 출력 디렉토리 경로
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # 출력 파일명 생성
    output_filename = input_file.stem + "_구역수정.csv"
    output_path = output_dir / output_filename

    # CSV 저장
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    # 통계 출력
    print("\n" + "=" * 60)
    print("=== main11g_fix_area_no.py 실행 결과 ===")
    print("=" * 60)

    print(f"\n입력 파일: {input_file.name}")
    print(f"- 전체 레코드: {stats['total']:,}건")
    print(f"- 유효한 좌표: {stats['valid_coords']:,}건")

    print("\n구역 매칭 결과:")
    if stats["valid_coords"] > 0:
        print(
            f"- 중구역 매칭 성공: {stats['mdz_matched']:,}건 ({stats['mdz_matched']/stats['valid_coords']*100:.1f}%)"
        )
        print(
            f"- 소구역 매칭 성공: {stats['smz_matched']:,}건 ({stats['smz_matched']/stats['valid_coords']*100:.1f}%)"
        )
        print(
            f"- 매칭 실패: 중구역 {stats['mdz_failed']:,}건, 소구역 {stats['smz_failed']:,}건"
        )

    print("\n수정 내역:")
    print(f"- 중구역번호 변경: {stats['mdz_changed']:,}건")
    print(f"- 소구역번호 변경: {stats['smz_changed']:,}건")

    print(f"\n출력 파일: {output_path}")
    print("=" * 60)


def main() -> None:
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="좌표 기반 중구역/소구역 번호 수정 스크립트"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="입력 CSV 파일 경로 (기본값: data/main11e_fix_error/*.csv 자동 탐색)",
    )
    parser.add_argument(
        "--region", type=str, default="0520", help="지역 코드 (기본값: 0520)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="출력 디렉토리 경로 (기본값: results/main11g_fix_area_no/)",
    )

    args = parser.parse_args()

    # 한글 폰트 설정 (시각화를 위해)
    setup_korean_font()

    # 입력 파일 결정
    if args.input:
        input_files = [Path(args.input)]
    else:
        # 기본 디렉토리에서 CSV 파일 탐색
        input_dir = Path("data/main11e_fix_error")
        if not input_dir.exists():
            print(f"❌ 오류: 입력 디렉토리를 찾을 수 없습니다: {input_dir}")
            sys.exit(1)

        input_files = list(input_dir.glob("*.csv"))
        if not input_files:
            print(f"❌ 오류: {input_dir}에 CSV 파일이 없습니다.")
            sys.exit(1)

    # 출력 디렉토리 결정
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else RESULTS_DIR / "main11g_fix_area_no"
    )

    # Shapefile 로드
    print(f"Shapefile 로드 중 (지역코드: {args.region})...")
    mdlz_gdf, smlz_gdf = load_zone_shapefiles(region_code=args.region)

    if mdlz_gdf is None and smlz_gdf is None:
        print("❌ 오류: MDLZ와 SMLZ shapefile을 모두 찾을 수 없습니다.")
        sys.exit(1)

    # 각 입력 파일 처리
    for input_file in input_files:
        print(f"\n처리 중: {input_file.name}")
        print("-" * 60)

        try:
            # CSV 로드
            df = load_csv_data(input_file)

            # 구역 번호 수정
            df_fixed, stats = fix_zone_numbers(df, mdlz_gdf, smlz_gdf)

            # 결과 저장
            save_results(df_fixed, stats, input_file, output_dir)

        except FileNotFoundError as e:
            print(f"❌ 오류: 파일을 찾을 수 없습니다: {e}")
            continue
        except ValueError as e:
            print(f"❌ 오류: {e}")
            continue
        except Exception as e:
            print(f"❌ 예기치 않은 오류: {e}")
            import traceback

            traceback.print_exc()
            continue

    print("\n✅ 모든 파일 처리 완료")


if __name__ == "__main__":
    main()
