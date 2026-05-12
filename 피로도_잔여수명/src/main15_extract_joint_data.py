"""
PIPE_LM과 SPLY_LS shapefile에서 LineString을 세그먼트로 분리하여 저장
- 0520 지역의 PIPE_LM, SPLY_LS shapefile 로드
- 각 LineString을 개별 세그먼트로 분리
- 각 세그먼트에 SUB_IDN 부여 (1, 2, 3...)
- 새로운 FTR_IDN 생성: {원본_FTR_IDN}_{SUB_IDN}
- CSV와 SHP 파일로 저장
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.semicircle_detection import (
    MIN_SEGMENTS_FOR_SEMICIRCLE,
    is_semicircular_pattern,
)
from src.common.shapefile_loader import load_pipe_shapefile


def split_linestring_with_semicircle_detection(
    geometry: Any,
) -> tuple[list[LineString], set[int]]:
    """
    LineString을 개별 선분으로 분리하되, 반원형 패턴은 하나로 유지

    Args:
        geometry: LineString 또는 MultiLineString geometry

    Returns:
        개별 LineString 세그먼트 리스트 (반원형은 병합됨)
    """
    if geometry.geom_type == "MultiLineString":
        all_segments = []
        all_merged_indices: set[int] = set()
        for line in geometry.geoms:
            segments, merged_indices = split_linestring_with_semicircle_detection(line)
            all_segments.extend(segments)
            # 인덱스 조정
            offset = len(all_segments) - len(segments)
            all_merged_indices.update(idx + offset for idx in merged_indices)
        return all_segments, all_merged_indices

    if geometry.geom_type != "LineString":
        return [], set()

    coords = list(geometry.coords)
    if len(coords) < 2:
        return [], set()

    # 먼저 모든 세그먼트를 분리
    all_segments = []
    for i in range(len(coords) - 1):
        segment = LineString([coords[i], coords[i + 1]])
        all_segments.append(segment)

    if len(all_segments) < MIN_SEGMENTS_FOR_SEMICIRCLE:
        return all_segments, set()

    # 반원형 패턴을 찾아서 병합
    result_segments = []
    merged_segment_indices = set()  # 병합된 세그먼트의 인덱스 추적
    i = 0

    while i < len(all_segments):
        # 현재 위치에서 가능한 최대 반원형 패턴 찾기
        found_semicircle = False

        # 다양한 길이의 세그먼트 그룹을 확인 (긴 것부터)
        for length in range(
            min(len(all_segments) - i, 15), MIN_SEGMENTS_FOR_SEMICIRCLE - 1, -1
        ):
            test_segments = all_segments[i : i + length]
            is_semi, _ = is_semicircular_pattern(test_segments)

            if is_semi:
                # 반원형 패턴을 하나의 LineString으로 병합
                all_coords = [test_segments[0].coords[0]]
                for seg in test_segments:
                    all_coords.append(seg.coords[1])

                merged_line = LineString(all_coords)
                result_segments.append(merged_line)
                merged_segment_indices.add(len(result_segments) - 1)

                i += length
                found_semicircle = True
                break

        if not found_semicircle:
            # 반원형이 아니면 그냥 추가
            result_segments.append(all_segments[i])
            i += 1

    return result_segments, merged_segment_indices


def process_pipe_segments(
    pipe_gdf: gpd.GeoDataFrame, pipe_type: str, verbose: bool = True
) -> gpd.GeoDataFrame | None:
    """
    파이프 GeoDataFrame의 모든 LineString을 세그먼트로 분리하고 처리
    반원형 패턴은 분리하지 않고 앞쪽 세그먼트에 병합

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)
        verbose: 상세 정보 출력 여부

    Returns:
        세그먼트로 분리된 GeoDataFrame 또는 None
    """
    if pipe_gdf is None or len(pipe_gdf) == 0:
        if verbose:
            print(f"경고: {pipe_type} 데이터가 비어있습니다.")
        return None

    # FTR_IDN 컬럼 존재 확인
    if "FTR_IDN" not in pipe_gdf.columns:
        if verbose:
            print(f"오류: {pipe_type}에 FTR_IDN 컬럼이 없습니다.")
            print(f"사용 가능한 컬럼: {list(pipe_gdf.columns)}")
        return None

    if verbose:
        print(f"\n=== {pipe_type} 세그먼트 분리 시작 (반원형 패턴 보존) ===")
        print(f"원본 객체 수: {len(pipe_gdf):,}개")

    # 모든 세그먼트 수집
    segment_records = []
    total_segments = 0
    semicircle_count = 0

    for idx, row in pipe_gdf.iterrows():
        if row.geometry is None:
            continue

        # FTR_IDN을 정수로 변환
        try:
            original_ftr_idn = int(float(row["FTR_IDN"]))
        except (ValueError, TypeError):
            if verbose:
                print(f"경고: FTR_IDN 변환 실패 (행 {idx}): {row['FTR_IDN']}")
            continue

        # LineString을 세그먼트로 분리 (반원형 패턴 감지 포함)
        segments, merged_indices = split_linestring_with_semicircle_detection(
            row.geometry
        )

        # 반원형 패턴이 병합되었는지 확인
        original_segments = []
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            original_segments.append(LineString([coords[i], coords[i + 1]]))

        if len(segments) < len(original_segments):
            semicircle_count += 1

        # 각 세그먼트에 대해 새로운 레코드 생성
        for sub_idx, segment in enumerate(segments, 1):
            # 새로운 FTR_IDN 생성: {원본_FTR_IDN}_{SUB_IDN}
            new_ftr_idn = f"{original_ftr_idn}_{sub_idx}"

            # 레코드 생성 (원본 속성 복사 + 새로운 속성 추가)
            new_record = row.to_dict()
            new_record["geometry"] = segment
            new_record["ORIG_FTR_IDN"] = original_ftr_idn  # 원본 FTR_IDN 보관
            new_record["SUB_IDN"] = sub_idx
            new_record["FTR_IDN"] = new_ftr_idn  # 새로운 FTR_IDN
            new_record["SEGMENT_LENGTH"] = segment.length  # 세그먼트 길이
            new_record["IS_SEMICIRCULAR"] = (
                sub_idx - 1
            ) in merged_indices  # 반원형 패턴 여부
            new_record["PIPE_TYPE"] = pipe_type  # 파이프 타입 (통합 계산용)

            segment_records.append(new_record)
            total_segments += 1

    if not segment_records:
        if verbose:
            print("경고: 생성된 세그먼트가 없습니다.")
        return None

    # GeoDataFrame 생성
    segments_gdf = gpd.GeoDataFrame(segment_records, crs=pipe_gdf.crs)

    # CNT_JNT 계산
    if verbose:
        print("\nJoint 연결 수 계산 중...")

    segments_gdf = calculate_joint_counts(segments_gdf, verbose=verbose)

    if verbose:
        print("세그먼트 분리 완료:")
        print(f"  - 원본 객체: {len(pipe_gdf):,}개")
        print(f"  - 생성된 세그먼트: {total_segments:,}개")
        print(f"  - 평균 세그먼트/객체: {total_segments/len(pipe_gdf):.1f}개")
        print(f"  - 반원형 패턴이 병합된 파이프: {semicircle_count}개")

        # 세그먼트 길이 통계
        lengths = segments_gdf["SEGMENT_LENGTH"].values
        print("\n세그먼트 길이 통계:")
        print(f"  - 최소: {lengths.min():.2f}m")
        print(f"  - 최대: {lengths.max():.2f}m")
        print(f"  - 평균: {lengths.mean():.2f}m")
        print(f"  - 중앙값: {np.median(lengths):.2f}m")

    return segments_gdf


def calculate_joint_counts(
    segments_gdf: gpd.GeoDataFrame, verbose: bool = True
) -> gpd.GeoDataFrame:
    """
    각 세그먼트의 joint 연결 수 계산
    - 파이프 끝단에서 다른 파이프와 만날 때: +1
    - 파이프 중간에서 T자로 만날 때: +1
    - 파이프 중간에서 +자로 만날 때: +2

    Args:
        segments_gdf: 세그먼트 GeoDataFrame
        verbose: 상세 정보 출력 여부

    Returns:
        CNT_JNT 컬럼이 추가된 GeoDataFrame
    """
    # 빈 GeoDataFrame 처리
    if len(segments_gdf) == 0:
        return segments_gdf

    # CNT_JNT 초기화
    segments_gdf["CNT_JNT"] = 0

    # 공간 인덱스 생성
    spatial_index = STRtree(list(segments_gdf.geometry))

    # 각 세그먼트의 시작점과 끝점 저장
    segment_endpoints = {}
    for idx, row in segments_gdf.iterrows():
        coords = list(row.geometry.coords)
        start_point = Point(coords[0])
        end_point = Point(coords[-1])
        segment_endpoints[idx] = {
            "start": start_point,
            "end": end_point,
            "orig_ftr": row["ORIG_FTR_IDN"],
            "sub_idn": row["SUB_IDN"],
            "is_semicircular": row.get("IS_SEMICIRCULAR", False),
        }

    # 각 세그먼트에 대해 연결 계산
    for idx, row in segments_gdf.iterrows():
        if verbose and idx % 1000 == 0:
            print(f"  처리 중: {idx}/{len(segments_gdf)}")

        cnt_jnt = 0
        current_info = segment_endpoints[idx]
        current_geom = row.geometry

        # 현재 세그먼트의 버퍼 영역 내의 다른 세그먼트 찾기
        buffer = current_geom.buffer(0.001)  # 1mm 버퍼
        nearby_indices = spatial_index.query(buffer)

        for other_idx in nearby_indices:
            if other_idx == idx:
                continue

            other_row = segments_gdf.iloc[other_idx]
            other_info = segment_endpoints[other_idx]

            # 자기 자신과의 연결만 제외 (모든 세그먼트 간 연결을 동등하게 계산)

            # 1. 끝점 연결 확인 (파이프 끝단에서 만남) - 반원형도 포함
            # 현재 세그먼트의 끝점이 다른 세그먼트의 끝점과 만남
            if (
                current_info["start"].distance(other_info["start"]) < 0.001
                or current_info["start"].distance(other_info["end"]) < 0.001
                or current_info["end"].distance(other_info["start"]) < 0.001
                or current_info["end"].distance(other_info["end"]) < 0.001
            ):
                cnt_jnt += 1
                continue

            # 반원형 세그먼트는 T자 및 +자 연결 계산에서 제외
            if current_info.get("is_semicircular", False) or other_info.get(
                "is_semicircular", False
            ):
                continue

            # 2. T자 연결 확인
            other_geom = other_row.geometry

            # 2-1. 다른 세그먼트의 끝점이 현재 세그먼트 중간에 있는 경우
            if (
                current_geom.distance(other_info["start"]) < 0.001
                or current_geom.distance(other_info["end"]) < 0.001
            ):
                # 끝점이 아닌 중간에 있는지 확인
                if (
                    current_info["start"].distance(other_info["start"]) > 0.001
                    and current_info["end"].distance(other_info["start"]) > 0.001
                ):
                    cnt_jnt += 1
                    continue
                if (
                    current_info["start"].distance(other_info["end"]) > 0.001
                    and current_info["end"].distance(other_info["end"]) > 0.001
                ):
                    cnt_jnt += 1
                    continue

            # 2-2. 현재 세그먼트의 끝점이 다른 세그먼트 중간에 있는 경우
            if (
                other_geom.distance(current_info["start"]) < 0.001
                or other_geom.distance(current_info["end"]) < 0.001
            ):
                # 현재 세그먼트의 시작점이 다른 세그먼트 중간에 있는지 확인
                if (
                    current_info["start"].distance(other_geom) < 0.001
                    and current_info["start"].distance(other_info["start"]) > 0.001
                    and current_info["start"].distance(other_info["end"]) > 0.001
                ):
                    cnt_jnt += 1
                    continue
                # 현재 세그먼트의 끝점이 다른 세그먼트 중간에 있는지 확인
                if (
                    current_info["end"].distance(other_geom) < 0.001
                    and current_info["end"].distance(other_info["start"]) > 0.001
                    and current_info["end"].distance(other_info["end"]) > 0.001
                ):
                    cnt_jnt += 1
                    continue

            # 3. +자 연결 확인 (두 세그먼트가 중간에서 교차)
            if current_geom.intersects(other_geom):
                intersection = current_geom.intersection(other_geom)
                if intersection.geom_type == "Point":
                    # 교차점이 양쪽 세그먼트의 끝점이 아닌지 확인
                    int_point = Point(intersection.coords[0])
                    if (
                        int_point.distance(current_info["start"]) > 0.001
                        and int_point.distance(current_info["end"]) > 0.001
                        and int_point.distance(other_info["start"]) > 0.001
                        and int_point.distance(other_info["end"]) > 0.001
                    ):
                        cnt_jnt += 2

        segments_gdf.at[idx, "CNT_JNT"] = cnt_jnt

    if verbose:
        print("\nJoint 연결 수 계산 완료:")
        print(f"  - CNT_JNT = 0: {len(segments_gdf[segments_gdf['CNT_JNT'] == 0])}개")
        print(f"  - CNT_JNT = 1: {len(segments_gdf[segments_gdf['CNT_JNT'] == 1])}개")
        print(f"  - CNT_JNT = 2: {len(segments_gdf[segments_gdf['CNT_JNT'] == 2])}개")
        print(f"  - CNT_JNT >= 3: {len(segments_gdf[segments_gdf['CNT_JNT'] >= 3])}개")

    return segments_gdf


def save_segment_data(
    segments_gdf: gpd.GeoDataFrame,
    pipe_type: str,
    output_dir: Path,
    verbose: bool = True,
) -> bool:
    """
    세그먼트 데이터를 CSV와 SHP 파일로 저장

    Args:
        segments_gdf: 세그먼트 GeoDataFrame
        pipe_type: 파이프 타입
        output_dir: 출력 디렉토리
        verbose: 상세 정보 출력 여부

    Returns:
        저장 성공 여부
    """
    try:
        # CSV 파일 저장 (geometry 제외)
        csv_path = output_dir / f"{pipe_type}_JOINT.csv"
        csv_columns = [
            "FTR_IDN",
            "ORIG_FTR_IDN",
            "SUB_IDN",
            "SEGMENT_LENGTH",
            "IS_SEMICIRCULAR",
            "CNT_JNT",
        ]
        csv_data = segments_gdf[csv_columns].copy()
        csv_data.to_csv(csv_path, index=False, encoding="utf-8-sig")

        if verbose:
            print(f"\nCSV 저장 완료: {csv_path}")
            print(f"  - 저장된 레코드 수: {len(csv_data):,}개")

        # Shapefile 저장
        shp_dir = output_dir / "shapefiles"
        shp_dir.mkdir(parents=True, exist_ok=True)
        shp_path = shp_dir / f"{pipe_type}_JOINT.shp"

        # Shapefile 컬럼명 제한 (10자) 대응
        shp_gdf = segments_gdf.copy()
        shp_gdf = shp_gdf.rename(
            columns={"ORIG_FTR_IDN": "ORIG_FTR", "SEGMENT_LENGTH": "SEG_LENGTH"}
        )

        # 필요한 컬럼만 선택하여 저장
        shp_columns = [
            "FTR_IDN",
            "ORIG_FTR",
            "SUB_IDN",
            "SEG_LENGTH",
            "CNT_JNT",
            "geometry",
        ]
        # 기존 컬럼 중 유지할 것들 추가 (10자 이내)
        for col in ["FTR_CDE", "HJD_CDE", "CRT_YMD"]:
            if col in shp_gdf.columns:
                shp_columns.append(col)

        shp_gdf = shp_gdf[shp_columns]
        shp_gdf.to_file(shp_path, encoding="utf-8")

        if verbose:
            print(f"Shapefile 저장 완료: {shp_path}")
            print(f"  - 저장된 객체 수: {len(shp_gdf):,}개")

        return True

    except Exception as e:
        if verbose:
            print(f"오류: 파일 저장 실패 - {e}")
        return False


def process_pipe_type(
    pipe_type: str, region_code: str = "0520", verbose: bool = True
) -> bool:
    """
    특정 파이프 타입 처리 - LineString을 세그먼트로 분리

    Args:
        pipe_type: 파이프 타입 (PIPE_LM 또는 SPLY_LS)
        region_code: 지역 코드
        verbose: 상세 정보 출력 여부

    Returns:
        처리 성공 여부
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"{pipe_type} 데이터 처리 시작...")

    # shapefile 로드
    pipe_gdf = load_pipe_shapefile(
        RAW_DATA_DIR, region_code, pipe_type, verbose=verbose
    )

    if pipe_gdf is None:
        if verbose:
            print(f"경고: {pipe_type} shapefile을 로드할 수 없습니다.")
        return False

    # LineString을 세그먼트로 분리
    segments_gdf = process_pipe_segments(pipe_gdf, pipe_type, verbose=verbose)

    if segments_gdf is None:
        return False

    # CSV와 Shapefile 저장
    return save_segment_data(segments_gdf, pipe_type, RESULTS_DIR, verbose=verbose)


def process_all_pipes_jointly(region_code: str, verbose: bool = True) -> bool:
    """
    PIPE_LM과 SPLY_LS를 통합하여 Joint 계산 후 분리 저장

    Args:
        region_code: 지역 코드
        verbose: 상세 정보 출력 여부

    Returns:
        처리 성공 여부
    """
    if verbose:
        print(f"\n{'='*60}")
        print("PIPE_LM과 SPLY_LS 통합 Joint 계산 시작...")

    # 1. 두 타입 로드
    pipe_lm_gdf = load_pipe_shapefile(
        RAW_DATA_DIR, region_code, "PIPE_LM", verbose=verbose
    )
    sply_ls_gdf = load_pipe_shapefile(
        RAW_DATA_DIR, region_code, "SPLY_LS", verbose=verbose
    )

    if pipe_lm_gdf is None:
        if verbose:
            print("경고: PIPE_LM shapefile을 로드할 수 없습니다.")
        return False

    if sply_ls_gdf is None:
        if verbose:
            print("경고: SPLY_LS shapefile을 로드할 수 없습니다.")
        return False

    # 2. 세그먼트 분리 (PIPE_TYPE 추가됨)
    if verbose:
        print("\nPIPE_LM 세그먼트 분리 중...")
    pipe_lm_segments = process_pipe_segments(pipe_lm_gdf, "PIPE_LM", verbose=verbose)

    if verbose:
        print("\nSPLY_LS 세그먼트 분리 중...")
    sply_ls_segments = process_pipe_segments(sply_ls_gdf, "SPLY_LS", verbose=verbose)

    if pipe_lm_segments is None or sply_ls_segments is None:
        return False

    # 3. 통합하여 Joint 계산
    if verbose:
        print("\n통합 Joint 계산 중...")
        print(f"  - PIPE_LM: {len(pipe_lm_segments)}개 세그먼트")
        print(f"  - SPLY_LS: {len(sply_ls_segments)}개 세그먼트")
        print(
            f"  - 총 합계: {len(pipe_lm_segments) + len(sply_ls_segments)}개 세그먼트"
        )

    all_segments = pd.concat([pipe_lm_segments, sply_ls_segments], ignore_index=True)
    all_segments = calculate_joint_counts(all_segments, verbose=verbose)

    # 4. PIPE_TYPE으로 분리하여 저장 (PIPE_TYPE 컬럼 제외)
    if verbose:
        print("\n결과 분리 및 저장 중...")

    pipe_lm_result = all_segments[all_segments["PIPE_TYPE"] == "PIPE_LM"].copy()
    sply_ls_result = all_segments[all_segments["PIPE_TYPE"] == "SPLY_LS"].copy()

    # PIPE_TYPE 컬럼 제거 (CSV 저장용)
    pipe_lm_result = pipe_lm_result.drop(columns=["PIPE_TYPE"])
    sply_ls_result = sply_ls_result.drop(columns=["PIPE_TYPE"])

    if verbose:
        print(f"  - PIPE_LM 결과: {len(pipe_lm_result)}개 세그먼트")
        print(f"  - SPLY_LS 결과: {len(sply_ls_result)}개 세그먼트")

    # 저장
    output_dir = RESULTS_DIR / "main15_extract_joint_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    pipe_lm_success = save_segment_data(
        pipe_lm_result, "PIPE_LM", output_dir, verbose=verbose
    )
    sply_ls_success = save_segment_data(
        sply_ls_result, "SPLY_LS", output_dir, verbose=verbose
    )

    return pipe_lm_success and sply_ls_success


def main() -> None:
    """메인 실행 함수"""
    print("PIPE_LM과 SPLY_LS 통합 Joint 계산 시작...")
    print(f"데이터 디렉토리: {RAW_DATA_DIR}")

    # 결과 디렉토리 설정 및 생성
    output_dir = RESULTS_DIR / "main15_extract_joint_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"결과 디렉토리: {output_dir}")

    # 통합 처리 실행
    success = process_all_pipes_jointly(region_code="0520", verbose=True)

    # 최종 결과 요약
    print(f"\n{'='*60}")
    print("처리 완료 요약:")

    if success:
        print("  - 통합 Joint 계산: 성공")
        print("\n✅ PIPE_LM과 SPLY_LS 통합 처리 성공!")
        print("\n생성된 파일:")

        # 파일 존재 확인 및 출력
        pipe_types = ["PIPE_LM", "SPLY_LS"]
        for pipe_type in pipe_types:
            csv_path = output_dir / f"{pipe_type}_JOINT.csv"
            shp_path = output_dir / "shapefiles" / f"{pipe_type}_JOINT.shp"
            if csv_path.exists():
                print(f"  - CSV: {csv_path}")
            if shp_path.exists():
                print(f"  - SHP: {shp_path}")
    else:
        print("\n❌ 통합 Joint 계산 실패")
        print("로그를 확인하여 오류 원인을 파악하세요.")


if __name__ == "__main__":
    main()
