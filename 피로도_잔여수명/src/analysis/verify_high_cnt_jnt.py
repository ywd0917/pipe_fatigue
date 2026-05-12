"""
높은 CNT_JNT 값을 가진 세그먼트 검증 스크립트
- CNT_JNT가 높은 세그먼트들의 연결점을 상세 분석
- 겹치는 세그먼트 식별 및 시각화
- 특정 FTR_IDN(178213_18)의 연결점들을 단계별로 확인
"""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.common.config import RESULTS_DIR
from src.common.korean_font_utils import setup_korean_font
from src.common.visualization_utils import setup_plot_style


def load_joint_data_with_geometry() -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    """Joint 데이터와 geometry 로드 (PIPE_LM과 SPLY_LS 모두)"""
    joint_dfs = []
    joint_gdfs = []

    # PIPE_LM Joint 데이터 로드
    pipe_lm_joint_csv = RESULTS_DIR / "PIPE_LM_JOINT.csv"
    pipe_lm_joint_shp = RESULTS_DIR / "shapefiles" / "PIPE_LM_JOINT.shp"

    if pipe_lm_joint_csv.exists() and pipe_lm_joint_shp.exists():
        print("PIPE_LM Joint 데이터 로드 중...")
        pipe_lm_df = pd.read_csv(pipe_lm_joint_csv, encoding="utf-8-sig")
        pipe_lm_df["PIPE_TYPE"] = "PIPE_LM"
        joint_dfs.append(pipe_lm_df)

        pipe_lm_gdf = gpd.read_file(pipe_lm_joint_shp)
        pipe_lm_gdf["PIPE_TYPE"] = "PIPE_LM"
        joint_gdfs.append(pipe_lm_gdf)
        print(
            f"PIPE_LM Joint 로드: CSV {len(pipe_lm_df)}개, Shapefile {len(pipe_lm_gdf)}개"
        )
    else:
        print("경고: PIPE_LM Joint 파일을 찾을 수 없습니다.")

    # SPLY_LS Joint 데이터 로드
    sply_ls_joint_csv = RESULTS_DIR / "SPLY_LS_JOINT.csv"
    sply_ls_joint_shp = RESULTS_DIR / "shapefiles" / "SPLY_LS_JOINT.shp"

    if sply_ls_joint_csv.exists() and sply_ls_joint_shp.exists():
        print("SPLY_LS Joint 데이터 로드 중...")
        sply_ls_df = pd.read_csv(sply_ls_joint_csv, encoding="utf-8-sig")
        sply_ls_df["PIPE_TYPE"] = "SPLY_LS"
        joint_dfs.append(sply_ls_df)

        sply_ls_gdf = gpd.read_file(sply_ls_joint_shp)
        sply_ls_gdf["PIPE_TYPE"] = "SPLY_LS"
        joint_gdfs.append(sply_ls_gdf)
        print(
            f"SPLY_LS Joint 로드: CSV {len(sply_ls_df)}개, Shapefile {len(sply_ls_gdf)}개"
        )
    else:
        print("경고: SPLY_LS Joint 파일을 찾을 수 없습니다.")

    # 통합 데이터 생성
    if not joint_dfs:
        raise FileNotFoundError("Joint 데이터 파일을 찾을 수 없습니다.")

    joint_df = pd.concat(joint_dfs, ignore_index=True)
    joint_gdf = pd.concat(joint_gdfs, ignore_index=True)

    print(
        f"통합 Joint 데이터: CSV {len(joint_df)}개, Shapefile {len(joint_gdf)}개 세그먼트"
    )

    return joint_df, joint_gdf


def find_high_cnt_jnt_segments(
    joint_df: pd.DataFrame, min_cnt_jnt: int = 15
) -> pd.DataFrame:
    """높은 CNT_JNT 값을 가진 세그먼트 찾기"""
    high_cnt_segments = joint_df[joint_df["CNT_JNT"] >= min_cnt_jnt].copy()
    high_cnt_segments = high_cnt_segments.sort_values("CNT_JNT", ascending=False)

    print(f"\nCNT_JNT >= {min_cnt_jnt}인 세그먼트: {len(high_cnt_segments)}개")
    if len(high_cnt_segments) > 0:
        print("상위 10개:")
        print(
            high_cnt_segments[
                ["FTR_IDN", "ORIG_FTR_IDN", "CNT_JNT", "SEGMENT_LENGTH"]
            ].head(10)
        )

    return high_cnt_segments


def analyze_segment_connections_detailed(
    target_ftr_idn: str, joint_gdf: gpd.GeoDataFrame, tolerance: float = 0.001
) -> dict[str, Any]:
    """특정 세그먼트의 연결점들을 상세 분석 (겹치는 세그먼트 식별 포함)"""
    # 대상 세그먼트 찾기
    target_segment = joint_gdf[joint_gdf["FTR_IDN"] == target_ftr_idn]
    if len(target_segment) == 0:
        raise ValueError(f"FTR_IDN {target_ftr_idn}을 찾을 수 없습니다.")

    target_row = target_segment.iloc[0]
    target_geom = target_row.geometry
    target_start = Point(target_geom.coords[0])
    target_end = Point(target_geom.coords[-1])

    print(f"\n=== {target_ftr_idn} 연결점 상세 분석 ===")
    print(f"세그먼트 길이: {target_geom.length:.3f}m")
    print(f"시작점: ({target_start.x:.6f}, {target_start.y:.6f})")
    print(f"끝점: ({target_end.x:.6f}, {target_end.y:.6f})")

    # 공간 인덱스 생성
    spatial_index = STRtree(list(joint_gdf.geometry))

    # 더 넓은 범위로 검색
    buffer = target_geom.buffer(tolerance * 20)
    nearby_indices = spatial_index.query(buffer)

    connections: dict[str, list[dict[str, Any]]] = {
        "end_to_end": [],  # 끝점 연결
        "t_junction": [],  # T자 연결
        "cross": [],  # +자 연결 (교차)
        "overlapping": [],  # 겹치는 세그먼트
        "near_miss": [],  # 거의 연결되지만 tolerance 밖
    }

    # 연결점별로 그룹화
    connection_points = defaultdict(list)
    total_cnt_jnt = 0

    for other_idx in nearby_indices:
        other_row = joint_gdf.iloc[other_idx]
        if other_row["FTR_IDN"] == target_ftr_idn:  # 자기 자신 제외
            continue

        other_geom = other_row.geometry
        other_start = Point(other_geom.coords[0])
        other_end = Point(other_geom.coords[-1])

        connection_info = {
            "ftr_idn": other_row["FTR_IDN"],
            "orig_ftr": other_row.get("ORIG_FTR", "N/A"),
            "length": other_geom.length,
            "geometry": other_geom,
            "start": other_start,
            "end": other_end,
            "connection_type": None,
            "connection_point": None,
            "distance": None,
            "cnt_jnt_contribution": 0,
        }

        # 1. 겹치는 세그먼트 확인 (완전히 같은 위치)
        if target_geom.distance(other_geom) < tolerance / 10:  # 매우 가까운 경우
            connection_info["connection_type"] = "overlapping"
            connection_info["distance"] = target_geom.distance(other_geom)
            connection_info["connection_point"] = target_geom.centroid
            connections["overlapping"].append(connection_info)
            continue

        # 2. 끝점 연결 확인
        distances = [
            (
                "target_start_to_other_start",
                target_start.distance(other_start),
                target_start,
            ),
            (
                "target_start_to_other_end",
                target_start.distance(other_end),
                target_start,
            ),
            ("target_end_to_other_start", target_end.distance(other_start), target_end),
            ("target_end_to_other_end", target_end.distance(other_end), target_end),
        ]

        min_distance = min(distances, key=lambda x: x[1])

        if min_distance[1] < tolerance:
            connection_info["connection_type"] = "end_to_end"
            connection_info["distance"] = min_distance[1]
            connection_info["connection_point"] = min_distance[2]
            connection_info["cnt_jnt_contribution"] = 1

            # 연결점별로 그룹화
            point_key = f"{min_distance[2].x:.6f},{min_distance[2].y:.6f}"
            connection_points[point_key].append(connection_info)

            connections["end_to_end"].append(connection_info)
            total_cnt_jnt += 1
            continue

        # 3. T자 연결 확인
        # 3-1. 다른 세그먼트의 끝점이 대상 세그먼트 중간에
        start_to_target = target_geom.distance(other_start)
        end_to_target = target_geom.distance(other_end)

        if start_to_target < tolerance and (
            target_start.distance(other_start) > tolerance
            and target_end.distance(other_start) > tolerance
        ):
            connection_info["connection_type"] = "t_junction"
            connection_info["distance"] = start_to_target
            connection_info["connection_point"] = target_geom.interpolate(
                target_geom.project(other_start)
            )
            connection_info["cnt_jnt_contribution"] = 1

            point_key = f"{connection_info['connection_point'].x:.6f},{connection_info['connection_point'].y:.6f}"
            connection_points[point_key].append(connection_info)

            connections["t_junction"].append(connection_info)
            total_cnt_jnt += 1
            continue

        if end_to_target < tolerance and (
            target_start.distance(other_end) > tolerance
            and target_end.distance(other_end) > tolerance
        ):
            connection_info["connection_type"] = "t_junction"
            connection_info["distance"] = end_to_target
            connection_info["connection_point"] = target_geom.interpolate(
                target_geom.project(other_end)
            )
            connection_info["cnt_jnt_contribution"] = 1

            point_key = f"{connection_info['connection_point'].x:.6f},{connection_info['connection_point'].y:.6f}"
            connection_points[point_key].append(connection_info)

            connections["t_junction"].append(connection_info)
            total_cnt_jnt += 1
            continue

        # 3-2. 대상 세그먼트의 끝점이 다른 세그먼트 중간에
        target_start_to_other = other_geom.distance(target_start)
        target_end_to_other = other_geom.distance(target_end)

        if target_start_to_other < tolerance and (
            target_start.distance(other_start) > tolerance
            and target_start.distance(other_end) > tolerance
        ):
            connection_info["connection_type"] = "t_junction"
            connection_info["distance"] = target_start_to_other
            connection_info["connection_point"] = target_start
            connection_info["cnt_jnt_contribution"] = 1

            point_key = f"{target_start.x:.6f},{target_start.y:.6f}"
            connection_points[point_key].append(connection_info)

            connections["t_junction"].append(connection_info)
            total_cnt_jnt += 1
            continue

        if target_end_to_other < tolerance and (
            target_end.distance(other_start) > tolerance
            and target_end.distance(other_end) > tolerance
        ):
            connection_info["connection_type"] = "t_junction"
            connection_info["distance"] = target_end_to_other
            connection_info["connection_point"] = target_end
            connection_info["cnt_jnt_contribution"] = 1

            point_key = f"{target_end.x:.6f},{target_end.y:.6f}"
            connection_points[point_key].append(connection_info)

            connections["t_junction"].append(connection_info)
            total_cnt_jnt += 1
            continue

        # 4. +자 연결 확인 (중간에서 교차)
        if target_geom.intersects(other_geom):
            intersection = target_geom.intersection(other_geom)
            if intersection.geom_type == "Point":
                int_point = Point(intersection.coords[0])
                # 교차점이 양쪽 세그먼트의 끝점이 아닌지 확인
                if (
                    int_point.distance(target_start) > tolerance
                    and int_point.distance(target_end) > tolerance
                    and int_point.distance(other_start) > tolerance
                    and int_point.distance(other_end) > tolerance
                ):
                    connection_info["connection_type"] = "cross"
                    connection_info["distance"] = 0.0
                    connection_info["connection_point"] = int_point
                    connection_info["cnt_jnt_contribution"] = 2

                    point_key = f"{int_point.x:.6f},{int_point.y:.6f}"
                    connection_points[point_key].append(connection_info)

                    connections["cross"].append(connection_info)
                    total_cnt_jnt += 2  # +자는 2개로 계산
                    continue

        # 5. Near miss (거의 연결되지만 tolerance 밖)
        if min_distance[1] < tolerance * 10:
            connection_info["connection_type"] = "near_miss"
            connection_info["distance"] = min_distance[1]
            connections["near_miss"].append(connection_info)

    # 연결점별 통계 출력
    print("\n연결점별 분석:")
    for i, (point_key, conn_list) in enumerate(connection_points.items(), 1):
        if len(conn_list) > 1:
            print(f"  연결점 #{i} ({point_key}): {len(conn_list)}개 세그먼트 연결")
            for conn in conn_list:
                print(
                    f"    - {conn['ftr_idn']} ({conn['connection_type']}, {conn['distance']:.4f}m)"
                )

    # 결과 요약
    print("\n연결점 분석 결과:")
    print(f"  - 끝점 연결: {len(connections['end_to_end'])}개")
    print(f"  - T자 연결: {len(connections['t_junction'])}개")
    print(
        f"  - +자 연결: {len(connections['cross'])}개 (CNT_JNT +{len(connections['cross'])*2})"
    )
    print(f"  - 겹치는 세그먼트: {len(connections['overlapping'])}개")
    print(f"  - 거의 연결: {len(connections['near_miss'])}개")
    print(f"  - 계산된 CNT_JNT: {total_cnt_jnt}")

    return {
        "target_ftr_idn": target_ftr_idn,
        "target_geometry": target_geom,
        "target_start": target_start,
        "target_end": target_end,
        "connections": connections,
        "connection_points": dict(connection_points),
        "calculated_cnt_jnt": total_cnt_jnt,
        "tolerance": tolerance,
    }


def visualize_connection_analysis(
    analysis_result: dict[str, Any], joint_gdf: gpd.GeoDataFrame, output_dir: Path
) -> None:
    """연결점 분석 결과 시각화"""
    setup_korean_font()

    target_ftr_idn = analysis_result["target_ftr_idn"]
    target_geom = analysis_result["target_geometry"]
    connections = analysis_result["connections"]
    connection_points = analysis_result["connection_points"]
    calculated_cnt_jnt = analysis_result["calculated_cnt_jnt"]

    # 플롯 설정
    fig, ax = setup_plot_style(figsize=(20, 20))

    # 대상 세그먼트 중심으로 영역 설정
    bounds = target_geom.bounds
    x_range = bounds[2] - bounds[0]
    y_range = bounds[3] - bounds[1]
    margin = max(x_range, y_range, 50) * 1.5  # 넓은 영역

    x_center = (bounds[0] + bounds[2]) / 2
    y_center = (bounds[1] + bounds[3]) / 2

    # 주변 모든 세그먼트 그리기 (파이프 타입별 색상)
    nearby_segments = joint_gdf.cx[
        x_center - margin : x_center + margin, y_center - margin : y_center + margin
    ]

    for _, seg in nearby_segments.iterrows():
        if seg.geometry and seg["FTR_IDN"] != target_ftr_idn:
            x, y = seg.geometry.xy
            # PIPE_LM은 연한 회색, SPLY_LS는 연한 파란색
            color = "lightblue" if seg.get("PIPE_TYPE") == "SPLY_LS" else "lightgray"
            ax.plot(x, y, color=color, linewidth=1.0, alpha=0.3, zorder=1)

    # 대상 세그먼트 강조 (두꺼운 빨간색)
    x, y = target_geom.xy
    ax.plot(
        x,
        y,
        color="red",
        linewidth=8.0,
        alpha=0.9,
        zorder=5,
        label=f"대상 세그먼트 ({target_ftr_idn})",
    )

    # 시작점과 끝점 표시
    ax.plot(x[0], y[0], "o", color="red", markersize=15, zorder=6, label="시작점")
    ax.plot(x[-1], y[-1], "s", color="red", markersize=15, zorder=6, label="끝점")

    # 연결된 세그먼트들 표시
    colors = {
        "end_to_end": "blue",
        "t_junction": "green",
        "cross": "orange",
        "overlapping": "purple",
        "near_miss": "pink",
    }

    connection_counts = {}

    for conn_type, conn_list in connections.items():
        if not conn_list:
            continue

        color = colors[conn_type]
        connection_counts[conn_type] = len(conn_list)

        for i, conn in enumerate(conn_list):
            # 연결된 세그먼트 그리기
            conn_x, conn_y = conn["geometry"].xy
            linewidth = 5.0 if conn_type == "overlapping" else 4.0
            ax.plot(
                conn_x, conn_y, color=color, linewidth=linewidth, alpha=0.8, zorder=4
            )

            # 연결점 표시
            if conn["connection_point"]:
                ax.plot(
                    conn["connection_point"].x,
                    conn["connection_point"].y,
                    "o",
                    color=color,
                    markersize=10,
                    alpha=0.9,
                    zorder=7,
                )

    # 연결점 번호 표시
    for i, (point_key, conn_list) in enumerate(connection_points.items(), 1):
        if len(conn_list) > 0:
            first_conn = conn_list[0]
            if first_conn["connection_point"]:
                ax.annotate(
                    f"{i}\n({len(conn_list)}개)",
                    (
                        first_conn["connection_point"].x,
                        first_conn["connection_point"].y,
                    ),
                    fontsize=12,
                    ha="center",
                    va="center",
                    fontweight="bold",
                    bbox=dict(boxstyle="circle,pad=0.3", facecolor="yellow", alpha=0.8),
                    zorder=8,
                )

    # 경계 설정
    ax.set_xlim(x_center - margin, x_center + margin)
    ax.set_ylim(y_center - margin, y_center + margin)

    # 제목 및 라벨
    ax.set_title(
        f"{target_ftr_idn} 연결점 상세 분석\n(계산된 CNT_JNT: {calculated_cnt_jnt})",
        fontsize=18,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("X 좌표", fontsize=14)
    ax.set_ylabel("Y 좌표", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")

    # 범례
    legend_elements = [
        mpatches.Patch(color="red", label=f"대상 세그먼트 ({target_ftr_idn})"),
        mpatches.Circle((0, 0), 1, color="red", label="세그먼트 끝점"),
        mpatches.Patch(color="lightgray", label="주변 파이프 (PIPE_LM)"),
        mpatches.Patch(color="lightblue", label="주변 파이프 (SPLY_LS)"),
    ]

    type_names = {
        "end_to_end": "끝점 연결",
        "t_junction": "T자 연결",
        "cross": "+자 연결",
        "overlapping": "겹치는 세그먼트",
        "near_miss": "거의 연결",
    }

    for conn_type, color in colors.items():
        if conn_type in connection_counts:
            count = connection_counts[conn_type]
            legend_elements.append(
                mpatches.Patch(
                    color=color, label=f"{type_names[conn_type]} ({count}개)"
                )
            )

    ax.legend(
        handles=legend_elements, loc="upper right", bbox_to_anchor=(1, 1), fontsize=12
    )

    # 정보 텍스트 (파이프 타입 포함)
    target_segment_row = joint_gdf[joint_gdf["FTR_IDN"] == target_ftr_idn]
    pipe_type = (
        target_segment_row.iloc[0].get("PIPE_TYPE", "UNKNOWN")
        if len(target_segment_row) > 0
        else "UNKNOWN"
    )
    info_text = f"FTR_IDN: {target_ftr_idn}\n"
    info_text += f"타입: {pipe_type}\n"
    info_text += f"길이: {target_geom.length:.3f}m\n"
    info_text += f"계산된 CNT_JNT: {calculated_cnt_jnt}\n\n"

    for conn_type, count in connection_counts.items():
        info_text += f"{type_names[conn_type]}: {count}개\n"

    info_text += f"\n연결점 수: {len(connection_points)}개"

    ax.text(
        0.02,
        0.98,
        info_text,
        transform=ax.transAxes,
        fontsize=12,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    # 저장
    output_path = output_dir / f"connection_analysis_{target_ftr_idn}.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"연결점 분석 이미지 저장: {output_path}")
    plt.close()


def export_connection_details(
    analysis_result: dict[str, Any], output_dir: Path
) -> None:
    """연결점 상세 정보를 CSV로 내보내기"""
    target_ftr_idn = analysis_result["target_ftr_idn"]
    connections = analysis_result["connections"]
    connection_points = analysis_result["connection_points"]

    # 모든 연결 정보를 하나의 리스트로 합치기
    all_connections = []

    for conn_type, conn_list in connections.items():
        for conn in conn_list:
            all_connections.append(
                {
                    "target_ftr_idn": target_ftr_idn,
                    "connected_ftr_idn": conn["ftr_idn"],
                    "connected_orig_ftr": conn["orig_ftr"],
                    "connection_type": conn["connection_type"],
                    "distance": conn["distance"],
                    "cnt_jnt_contribution": conn.get("cnt_jnt_contribution", 0),
                    "connected_length": conn["length"],
                    "connection_point_x": (
                        conn["connection_point"].x if conn["connection_point"] else None
                    ),
                    "connection_point_y": (
                        conn["connection_point"].y if conn["connection_point"] else None
                    ),
                }
            )

    # DataFrame 생성 및 저장
    if all_connections:
        df = pd.DataFrame(all_connections)
        csv_path = output_dir / f"connection_details_{target_ftr_idn}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"연결점 상세 정보 저장: {csv_path}")

    # 연결점별 요약도 저장
    point_summary = []
    for i, (point_key, conn_list) in enumerate(connection_points.items(), 1):
        coords = point_key.split(",")
        point_summary.append(
            {
                "point_number": i,
                "point_x": float(coords[0]),
                "point_y": float(coords[1]),
                "connected_segments": len(conn_list),
                "segment_list": ", ".join([conn["ftr_idn"] for conn in conn_list]),
            }
        )

    if point_summary:
        point_df = pd.DataFrame(point_summary)
        point_csv_path = output_dir / f"connection_points_summary_{target_ftr_idn}.csv"
        point_df.to_csv(point_csv_path, index=False, encoding="utf-8-sig")
        print(f"연결점 요약 저장: {point_csv_path}")


def main() -> None:
    """메인 실행 함수"""
    print("=== 높은 CNT_JNT 값 검증 분석 시작 ===")

    # 출력 디렉토리 생성
    output_dir = RESULTS_DIR / "high_cnt_jnt_verification"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Joint 데이터 로드
        joint_df, joint_gdf = load_joint_data_with_geometry()

        # 2. 높은 CNT_JNT 값을 가진 세그먼트 찾기
        high_cnt_segments = find_high_cnt_jnt_segments(joint_df, min_cnt_jnt=15)

        # 3. 특정 세그먼트 분석 (178213_18)
        target_ftr_idn = "178213_18"

        # 해당 FTR_IDN이 존재하는지 확인
        if target_ftr_idn not in joint_df["FTR_IDN"].values:
            print(f"경고: {target_ftr_idn}을 찾을 수 없습니다.")
            if len(high_cnt_segments) > 0:
                # 가장 높은 CNT_JNT를 가진 세그먼트 사용
                target_ftr_idn = high_cnt_segments.iloc[0]["FTR_IDN"]
                print(f"가장 높은 CNT_JNT를 가진 세그먼트로 대체: {target_ftr_idn}")
            else:
                print("분석할 높은 CNT_JNT 세그먼트가 없습니다.")
                return

        # 4. 연결점 상세 분석
        analysis_result = analyze_segment_connections_detailed(
            target_ftr_idn, joint_gdf
        )

        # 5. 시각화
        visualize_connection_analysis(analysis_result, joint_gdf, output_dir)

        # 6. 상세 정보 내보내기
        export_connection_details(analysis_result, output_dir)

        # 7. 결과 요약
        recorded_cnt_jnt = joint_df[joint_df["FTR_IDN"] == target_ftr_idn][
            "CNT_JNT"
        ].iloc[0]
        calculated_cnt_jnt = analysis_result["calculated_cnt_jnt"]

        print("\n=== 최종 검증 결과 ===")
        print(f"세그먼트: {target_ftr_idn}")
        print(f"기록된 CNT_JNT: {recorded_cnt_jnt}")
        print(f"계산된 CNT_JNT: {calculated_cnt_jnt}")
        print(f"차이: {abs(recorded_cnt_jnt - calculated_cnt_jnt)}")

        if recorded_cnt_jnt == calculated_cnt_jnt:
            print("✅ CNT_JNT 값이 정확합니다!")
        else:
            print("⚠️ CNT_JNT 값에 차이가 있습니다.")
            print("   겹치는 세그먼트나 계산 오류가 있을 수 있습니다.")

        print(f"\n결과 저장 위치: {output_dir}")
        print("생성된 파일:")
        print(f"  - 시각화: connection_analysis_{target_ftr_idn}.png")
        print(f"  - 연결 상세: connection_details_{target_ftr_idn}.csv")
        print(f"  - 연결점 요약: connection_points_summary_{target_ftr_idn}.csv")

    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
