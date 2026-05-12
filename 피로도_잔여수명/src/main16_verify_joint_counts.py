"""
CNT_JNT (Joint 연결 수) 검증을 위한 시각화 스크립트
- main15에서 계산한 CNT_JNT 값의 정확성을 시각적으로 검증
- 각 CNT_JNT 값별로 최대 5개 샘플을 선택하여 확대 이미지 생성
- 연결점과 연결 타입을 명확히 표시
"""

import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle
from shapely.geometry import LineString, Point

sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font
from src.common.shapefile_loader import load_pipe_shapefile
from src.common.visualization_utils import setup_plot_style


def load_joint_data(csv_path: Path) -> pd.DataFrame:
    """Joint CSV 데이터 로드"""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"Joint 데이터 로드: {len(df)}개 세그먼트")

    # CNT_JNT 통계
    print("\nCNT_JNT 분포:")
    if len(df) > 0 and "CNT_JNT" in df.columns:
        for cnt_jnt, count in sorted(df["CNT_JNT"].value_counts().items()):
            print(f"  - CNT_JNT = {cnt_jnt}: {count:,}개 ({count/len(df)*100:.1f}%)")

    return df


def select_diverse_samples(df: pd.DataFrame, max_per_cnt: int = 5) -> pd.DataFrame:
    """각 CNT_JNT 값별로 다양한 샘플 선택"""
    samples = []

    # 빈 DataFrame 처리
    if len(df) == 0 or "CNT_JNT" not in df.columns:
        return df

    print(f"\n각 CNT_JNT별 최대 {max_per_cnt}개 샘플 선택:")

    # CNT_JNT 값별로 그룹화
    for cnt_jnt in sorted(df["CNT_JNT"].unique()):
        group = df[df["CNT_JNT"] == cnt_jnt]

        # 샘플 수 결정
        n_samples = min(len(group), max_per_cnt)

        if n_samples > 0:
            # 길이별로 정렬하여 다양한 길이 선택
            group_sorted = group.sort_values("SEGMENT_LENGTH")
            indices = np.linspace(0, len(group_sorted) - 1, n_samples, dtype=int)
            selected = group_sorted.iloc[indices]

            samples.append(selected)
            print(
                f"  - CNT_JNT = {cnt_jnt}: {n_samples}개 선택 (전체 {len(group):,}개 중)"
            )

    # 모든 샘플 합치기
    sample_df = pd.concat(samples, ignore_index=True)
    print(f"\n총 {len(sample_df)}개 샘플 선택 완료")

    return sample_df  # type: ignore[no-any-return]


def load_segment_geometries(
    pipe_gdf: gpd.GeoDataFrame, joint_df: pd.DataFrame
) -> dict[str, Any]:
    """세그먼트 geometry 매핑"""
    segment_dict = {}

    for _, row in joint_df.iterrows():
        ftr_idn = row["FTR_IDN"]
        orig_ftr = row["ORIG_FTR_IDN"]
        sub_idn = row["SUB_IDN"]

        # 원본 파이프 찾기
        orig_pipe = pipe_gdf[pipe_gdf["FTR_IDN"] == str(orig_ftr)]
        if len(orig_pipe) == 0:
            continue

        # 세그먼트 재생성 (간단한 방법)
        geometry = orig_pipe.iloc[0].geometry
        if geometry.geom_type == "LineString":
            coords = list(geometry.coords)
            if sub_idn <= len(coords) - 1:
                segment = LineString(
                    [coords[sub_idn - 1], coords[min(sub_idn, len(coords) - 1)]]
                )
                segment_dict[ftr_idn] = {
                    "geometry": segment,
                    "cnt_jnt": row["CNT_JNT"],
                    "length": row["SEGMENT_LENGTH"],
                }

    return segment_dict


def analyze_connections(
    segment: LineString, nearby_segments: list[LineString], tolerance: float = 0.001
) -> dict[str, int]:
    """세그먼트의 연결 타입 분석 (main15 로직과 동일하게)"""
    connections = {
        "end_to_end": 0,  # 끝단 연결
        "t_junction": 0,  # T자 연결
        "cross": 0,  # +자 연결
    }

    seg_start = Point(segment.coords[0])
    seg_end = Point(segment.coords[-1])

    for other in nearby_segments:
        if other.equals(segment):
            continue

        other_start = Point(other.coords[0])
        other_end = Point(other.coords[-1])

        # 1. 끝단 연결 확인 (파이프 끝단에서 만남)
        if (
            seg_start.distance(other_start) < tolerance
            or seg_start.distance(other_end) < tolerance
            or seg_end.distance(other_start) < tolerance
            or seg_end.distance(other_end) < tolerance
        ):
            connections["end_to_end"] += 1
            continue

        # 2-1. T자 연결 확인 (다른 세그먼트의 끝점이 이 세그먼트 중간에)
        if (
            segment.distance(other_start) < tolerance
            or segment.distance(other_end) < tolerance
        ):
            # 끝점이 아닌 중간에 있는지 확인
            if (
                seg_start.distance(other_start) > tolerance
                and seg_end.distance(other_start) > tolerance
                and segment.distance(other_start) < tolerance
            ):
                connections["t_junction"] += 1
                continue
            if (
                seg_start.distance(other_end) > tolerance
                and seg_end.distance(other_end) > tolerance
                and segment.distance(other_end) < tolerance
            ):
                connections["t_junction"] += 1
                continue

        # 2-2. T자 연결 확인 (이 세그먼트의 끝점이 다른 세그먼트 중간에)
        if other.distance(seg_start) < tolerance or other.distance(seg_end) < tolerance:
            # 이 세그먼트의 시작점이 다른 세그먼트 중간에
            if (
                seg_start.distance(other) < tolerance
                and seg_start.distance(other_start) > tolerance
                and seg_start.distance(other_end) > tolerance
            ):
                connections["t_junction"] += 1
                continue
            # 이 세그먼트의 끝점이 다른 세그먼트 중간에
            if (
                seg_end.distance(other) < tolerance
                and seg_end.distance(other_start) > tolerance
                and seg_end.distance(other_end) > tolerance
            ):
                connections["t_junction"] += 1
                continue

        # 3. +자 연결 확인 (두 세그먼트가 중간에서 교차)
        if segment.intersects(other):
            intersection = segment.intersection(other)
            if intersection.geom_type == "Point":
                int_point = Point(intersection.coords[0])
                if (
                    int_point.distance(seg_start) > tolerance
                    and int_point.distance(seg_end) > tolerance
                    and int_point.distance(other_start) > tolerance
                    and int_point.distance(other_end) > tolerance
                ):
                    connections["cross"] += 1

    return connections


def visualize_segment(
    idx: int,
    total: int,
    ftr_idn: str,
    segment_info: dict[str, Any],
    pipe_gdf: gpd.GeoDataFrame,
    segments_gdf: gpd.GeoDataFrame,
    output_dir: Path,
) -> None:
    """개별 세그먼트 시각화"""
    segment = segment_info["geometry"]
    cnt_jnt = segment_info["cnt_jnt"]
    length = segment_info["length"]

    print(f"\n[{idx}/{total}] {ftr_idn} (CNT_JNT={cnt_jnt}, 길이={length:.2f}m)")

    # 플롯 설정
    fig, ax = setup_plot_style(figsize=(12, 12))

    # 버퍼 크기 계산
    buffer_size = max(50, length * 2)  # 최소 50m

    # main15 방식으로 연결된 세그먼트 찾기
    from shapely.strtree import STRtree

    spatial_index = STRtree(list(segments_gdf.geometry))

    # 현재 세그먼트 정보
    seg_start = Point(segment.coords[0])
    seg_end = Point(segment.coords[-1])
    current_row = segments_gdf[segments_gdf["FTR_IDN"] == ftr_idn].iloc[0]

    # 연결된 세그먼트 찾기 (main15 로직과 동일)
    buffer = segment.buffer(0.001)  # 1mm 버퍼
    nearby_indices = spatial_index.query(buffer)

    connected_segments = []
    connection_count = 0

    for other_idx in nearby_indices:
        other_row = segments_gdf.iloc[other_idx]
        if other_row["FTR_IDN"] == ftr_idn:  # 자기 자신은 제외
            continue

        # 반원형으로 병합된 세그먼트의 내부 연결은 제외
        # (같은 원본 파이프의 병합된 세그먼트들 간의 연결)
        if (
            current_row.get("IS_SEMICIRCULAR", False)
            and other_row.get("IS_SEMICIRCULAR", False)
            and current_row["ORIG_FTR_IDN"] == other_row["ORIG_FTR_IDN"]
        ):
            continue

        other_geom = other_row.geometry
        other_start = Point(other_geom.coords[0])
        other_end = Point(other_geom.coords[-1])

        # 1. 끝점 연결 확인
        if (
            seg_start.distance(other_start) < 0.001
            or seg_start.distance(other_end) < 0.001
            or seg_end.distance(other_start) < 0.001
            or seg_end.distance(other_end) < 0.001
        ):
            connected_segments.append(other_geom)
            connection_count += 1
            continue

        # 2-1. T자 연결 (다른 세그먼트의 끝점이 이 세그먼트 중간에)
        if segment.distance(other_start) < 0.001 or segment.distance(other_end) < 0.001:
            if (
                seg_start.distance(other_start) > 0.001
                and seg_end.distance(other_start) > 0.001
            ):
                connected_segments.append(other_geom)
                connection_count += 1
                continue
            if (
                seg_start.distance(other_end) > 0.001
                and seg_end.distance(other_end) > 0.001
            ):
                connected_segments.append(other_geom)
                connection_count += 1
                continue

        # 2-2. T자 연결 (이 세그먼트의 끝점이 다른 세그먼트 중간에)
        if (
            other_geom.distance(seg_start) < 0.001
            or other_geom.distance(seg_end) < 0.001
        ):
            if (
                seg_start.distance(other_geom) < 0.001
                and seg_start.distance(other_start) > 0.001
                and seg_start.distance(other_end) > 0.001
            ):
                connected_segments.append(other_geom)
                connection_count += 1
                continue
            if (
                seg_end.distance(other_geom) < 0.001
                and seg_end.distance(other_start) > 0.001
                and seg_end.distance(other_end) > 0.001
            ):
                connected_segments.append(other_geom)
                connection_count += 1
                continue

        # 3. +자 연결 (중간에서 교차)
        if segment.intersects(other_geom):
            intersection = segment.intersection(other_geom)
            if intersection.geom_type == "Point":
                int_point = Point(intersection.coords[0])
                if (
                    int_point.distance(seg_start) > 0.001
                    and int_point.distance(seg_end) > 0.001
                    and int_point.distance(other_start) > 0.001
                    and int_point.distance(other_end) > 0.001
                ):
                    connected_segments.append(other_geom)
                    connection_count += 2  # +자는 2개로 계산

    # 연결된 세그먼트들의 전체 범위 계산
    all_segments = [segment, *connected_segments]
    all_bounds = None

    for seg in all_segments:
        seg_bounds = seg.bounds  # (minx, miny, maxx, maxy)
        if all_bounds is None:
            all_bounds = list(seg_bounds)
        else:
            all_bounds[0] = min(all_bounds[0], seg_bounds[0])  # minx
            all_bounds[1] = min(all_bounds[1], seg_bounds[1])  # miny
            all_bounds[2] = max(all_bounds[2], seg_bounds[2])  # maxx
            all_bounds[3] = max(all_bounds[3], seg_bounds[3])  # maxy

    # 여백 추가 (전체 범위의 10%)
    if all_bounds is not None:
        width = all_bounds[2] - all_bounds[0]
        height = all_bounds[3] - all_bounds[1]
        margin = max(width, height) * 0.1
        margin = max(margin, 10)  # 최소 10m 여백

        # 새로운 경계 설정
        bounds = [
            all_bounds[0] - margin,
            all_bounds[1] - margin,
            all_bounds[2] + margin,
            all_bounds[3] + margin,
        ]
    else:
        # 기본 경계 설정
        bounds = [-100, -100, 100, 100]

    # 주변 파이프 다시 가져오기
    nearby_pipes = pipe_gdf.cx[bounds[0] : bounds[2], bounds[1] : bounds[3]]

    # 주변 파이프 그리기 (파이프 타입별 색상)
    for _, pipe in nearby_pipes.iterrows():
        if pipe.geometry:
            x, y = pipe.geometry.xy
            # PIPE_LM은 회색, SPLY_LS는 연한 파란색
            color = "lightblue" if pipe.get("PIPE_TYPE") == "SPLY_LS" else "gray"
            alpha = 0.6 if pipe.get("PIPE_TYPE") == "SPLY_LS" else 0.5
            ax.plot(x, y, color=color, linewidth=1.5, alpha=alpha)

    # 연결된 세그먼트 초록색으로 그리기
    for conn_seg in connected_segments:
        x, y = conn_seg.xy
        ax.plot(x, y, color="green", linewidth=3.0, alpha=0.7, zorder=4)

    # 현재 세그먼트 강조 (빨간색)
    x, y = segment.xy
    ax.plot(x, y, color="red", linewidth=4.0, alpha=0.9, zorder=5)

    # 세그먼트 끝점 표시
    ax.plot(x[0], y[0], "o", color="blue", markersize=8, zorder=6)
    ax.plot(x[-1], y[-1], "s", color="blue", markersize=8, zorder=6)

    # 시각화를 위한 연결 분석 (제거 예정)
    nearby_geometries = [
        pipe.geometry for _, pipe in nearby_pipes.iterrows() if pipe.geometry
    ]

    # 연결점 표시 (노란색 원)
    connection_points = []

    # 끝점 연결 표시
    seg_start = Point(segment.coords[0])
    seg_end = Point(segment.coords[-1])

    for geom in nearby_geometries:
        if geom.equals(segment):
            continue

        # 시작점 연결
        if geom.distance(seg_start) < 0.001:
            connection_points.append(seg_start)

        # 끝점 연결
        if geom.distance(seg_end) < 0.001:
            connection_points.append(seg_end)

        # 중간 연결점
        if segment.intersects(geom):
            intersection = segment.intersection(geom)
            if intersection.geom_type == "Point":
                connection_points.append(Point(intersection.coords[0]))

    # 연결점 그리기
    for point in connection_points:
        circle = Circle(
            (point.x, point.y), buffer_size / 50, color="yellow", alpha=0.2, zorder=7
        )
        ax.add_patch(circle)

    # 경계 설정
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    # 제목 및 라벨
    ax.set_title(
        f"{ftr_idn} - CNT_JNT={cnt_jnt} (연결된 세그먼트: {len(connected_segments)}개)",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("X 좌표", fontsize=10)
    ax.set_ylabel("Y 좌표", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # 범례
    legend_elements = [
        mpatches.Patch(color="red", label="검증 세그먼트"),
        mpatches.Patch(
            color="green", label=f"연결된 세그먼트 ({len(connected_segments)}개)"
        ),
        mpatches.Patch(color="gray", label="주변 파이프 (PIPE_LM)"),
        mpatches.Patch(color="lightblue", label="주변 파이프 (SPLY_LS)"),
        mpatches.Circle((0, 0), 1, color="yellow", alpha=0.2, label="연결점"),
        mpatches.Circle((0, 0), 1, color="blue", label="세그먼트 끝점"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    # 정보 텍스트 (파이프 타입 포함)
    current_segment_row = segments_gdf[segments_gdf["FTR_IDN"] == ftr_idn]
    pipe_type = (
        current_segment_row.iloc[0].get("PIPE_TYPE", "UNKNOWN")
        if len(current_segment_row) > 0
        else "UNKNOWN"
    )
    info_text = f"길이: {length:.2f}m\nFTR_IDN: {ftr_idn}\n타입: {pipe_type}"
    ax.text(
        0.02,
        0.98,
        info_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )

    # 저장
    output_path = output_dir / f"joint_verify_{idx:02d}_{ftr_idn}_CNT{cnt_jnt}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    # 결과 출력
    if connection_count == cnt_jnt:
        print("  ✓ CNT_JNT 검증 성공 (main15 로직으로 재계산)")
    else:
        print(f"  ⚠ CNT_JNT 불일치: 계산={connection_count}, 기록={cnt_jnt}")
    print(f"  - 연결된 세그먼트: {len(connected_segments)}개")


def main() -> None:
    """메인 실행 함수"""
    print("=== CNT_JNT 검증 시각화 시작 ===")

    # 한글 폰트 설정
    setup_korean_font()

    # 출력 디렉토리 생성
    output_dir = RESULTS_DIR / "main16"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Joint 데이터 로드 (PIPE_LM과 SPLY_LS 모두)
    joint_dfs = []

    # PIPE_LM Joint 데이터 로드
    pipe_lm_joint_csv = RESULTS_DIR / "main15_extract_joint_data" / "PIPE_LM_JOINT.csv"
    if pipe_lm_joint_csv.exists():
        print("PIPE_LM Joint 데이터 로드 중...")
        pipe_lm_joint_df = load_joint_data(pipe_lm_joint_csv)
        pipe_lm_joint_df["PIPE_TYPE"] = "PIPE_LM"
        joint_dfs.append(pipe_lm_joint_df)
    else:
        print(f"경고: {pipe_lm_joint_csv} 파일을 찾을 수 없습니다.")

    # SPLY_LS Joint 데이터 로드
    sply_ls_joint_csv = RESULTS_DIR / "main15_extract_joint_data" / "SPLY_LS_JOINT.csv"
    if sply_ls_joint_csv.exists():
        print("SPLY_LS Joint 데이터 로드 중...")
        sply_ls_joint_df = load_joint_data(sply_ls_joint_csv)
        sply_ls_joint_df["PIPE_TYPE"] = "SPLY_LS"
        joint_dfs.append(sply_ls_joint_df)
    else:
        print(f"경고: {sply_ls_joint_csv} 파일을 찾을 수 없습니다.")

    # 통합 Joint 데이터 생성
    if not joint_dfs:
        print("오류: Joint 데이터 파일을 찾을 수 없습니다.")
        return

    joint_df = pd.concat(joint_dfs, ignore_index=True)
    print(
        f"\n통합 Joint 데이터: PIPE_LM {len(joint_dfs[0]) if len(joint_dfs) > 0 else 0}개, SPLY_LS {len(joint_dfs[1]) if len(joint_dfs) > 1 else 0}개"
    )
    print(f"총 {len(joint_df)}개 세그먼트")

    # 2. 샘플 선택
    sample_df = select_diverse_samples(joint_df, max_per_cnt=5)

    # 3. Shapefile 로드 (PIPE_LM과 SPLY_LS 모두)
    print("\nPIPE_LM shapefile 로드 중...")
    pipe_lm_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "PIPE_LM")
    if pipe_lm_gdf is None:
        print("오류: PIPE_LM shapefile을 로드할 수 없습니다.")
        return

    print("SPLY_LS shapefile 로드 중...")
    sply_ls_gdf = load_pipe_shapefile(RAW_DATA_DIR, "0520", "SPLY_LS")
    if sply_ls_gdf is None:
        print("경고: SPLY_LS shapefile을 로드할 수 없습니다. PIPE_LM만 사용합니다.")
        pipe_gdf = pipe_lm_gdf
    else:
        # 두 타입을 하나로 통합 (시각화용)
        pipe_lm_gdf["PIPE_TYPE"] = "PIPE_LM"
        sply_ls_gdf["PIPE_TYPE"] = "SPLY_LS"
        pipe_gdf = pd.concat([pipe_lm_gdf, sply_ls_gdf], ignore_index=True)

    # 4. 세그먼트 geometry 매핑
    print("\n세그먼트 geometry 매핑 중...")

    # Joint shapefile들이 있으면 사용, 없으면 CSV 기반으로 재생성
    pipe_lm_joint_shp = (
        RESULTS_DIR / "main15_extract_joint_data" / "shapefiles" / "PIPE_LM_JOINT.shp"
    )
    sply_ls_joint_shp = (
        RESULTS_DIR / "main15_extract_joint_data" / "shapefiles" / "SPLY_LS_JOINT.shp"
    )

    if pipe_lm_joint_shp.exists():
        print("PIPE_LM Joint shapefile 로드...")
        pipe_lm_segments_gdf = gpd.read_file(pipe_lm_joint_shp)
        pipe_lm_segments_gdf["PIPE_TYPE"] = "PIPE_LM"

        # SPLY_LS Joint shapefile도 로드 시도
        if sply_ls_joint_shp.exists():
            print("SPLY_LS Joint shapefile 로드...")
            sply_ls_segments_gdf = gpd.read_file(sply_ls_joint_shp)
            sply_ls_segments_gdf["PIPE_TYPE"] = "SPLY_LS"
            segments_gdf = pd.concat(
                [pipe_lm_segments_gdf, sply_ls_segments_gdf], ignore_index=True
            )
        else:
            segments_gdf = pipe_lm_segments_gdf

        # 샘플과 매칭
        segment_dict = {}
        for _, row in sample_df.iterrows():
            ftr_idn = row["FTR_IDN"]
            matching = segments_gdf[segments_gdf["FTR_IDN"] == ftr_idn]
            if len(matching) > 0:
                segment_dict[ftr_idn] = {
                    "geometry": matching.iloc[0].geometry,
                    "cnt_jnt": row["CNT_JNT"],
                    "length": row["SEGMENT_LENGTH"],
                }
    else:
        print("Joint shapefile이 없어 geometry 재생성...")
        segment_dict = load_segment_geometries(pipe_gdf, sample_df)

    # 5. 각 샘플 시각화
    print(f"\n총 {len(segment_dict)}개 샘플 시각화 진행...")

    idx = 1
    for ftr_idn, segment_info in segment_dict.items():
        visualize_segment(
            idx,
            len(segment_dict),
            ftr_idn,
            segment_info,
            pipe_gdf,
            segments_gdf,
            output_dir,
        )
        idx += 1

    print("\n시각화 완료!")
    print(f"결과 저장 위치: {output_dir}")

    # 요약 통계
    print("\n=== 검증 요약 ===")
    print(f"총 {len(segment_dict)}개 샘플 검증 완료")
    print("각 이미지에서 CNT_JNT 값과 실제 연결 수를 비교하여 확인하세요.")


if __name__ == "__main__":
    main()
