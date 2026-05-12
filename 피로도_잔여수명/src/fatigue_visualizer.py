"""
피로 손상 데이터 시각화를 위한 특화 모듈
파이프 피로 손상 시각화 관련 비즈니스 로직
"""

from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib import cm

# 파이프 두께 설정
PIPE_LM_LINEWIDTH = 1.0  # PIPE_LM 파이프 두께
SPLY_LS_LINEWIDTH = 0.3  # SPLY_LS 파이프 두께

# 로그 스케일 범위
FATIGUE_VMIN = 0.0001  # 10^-4
FATIGUE_VMAX = 1.0  # 10^0


def create_fatigue_colormap() -> mcolors.LinearSegmentedColormap:
    """피로 손상 정도에 따른 컬러맵 생성

    0 (안전) -> 1 (위험)
    파란색 -> 초록색 -> 노란색 -> 주황색 -> 빨간색

    Returns:
        LinearSegmentedColormap
    """
    colors = ["#0000FF", "#00FF00", "#FFFF00", "#FFA500", "#FF0000"]
    n_bins = 100
    return mcolors.LinearSegmentedColormap.from_list("fatigue", colors, N=n_bins)


def prepare_fatigue_data(
    pipe_gdf: gpd.GeoDataFrame, fatigue_dict: dict[str, float]
) -> gpd.GeoDataFrame:
    """파이프 GeoDataFrame에 피로 손상 데이터 추가

    Args:
        pipe_gdf: 파이프 GeoDataFrame
        fatigue_dict: {FTR_IDN: D_final} 딕셔너리

    Returns:
        피로 손상 데이터가 추가된 GeoDataFrame
    """
    # FTR_IDN을 문자열로 변환
    pipe_gdf["FTR_IDN_str"] = ""

    if pipe_gdf["FTR_IDN"].dtype == "float64":
        # NaN이 아닌 값들만 변환
        mask = pipe_gdf["FTR_IDN"].notna()
        pipe_gdf.loc[mask, "FTR_IDN_str"] = (
            pipe_gdf.loc[mask, "FTR_IDN"].astype(int).astype(str)
        )
    else:
        pipe_gdf["FTR_IDN_str"] = pipe_gdf["FTR_IDN"].astype(str)

    # 피로 손상 값 매핑
    pipe_gdf["fatigue_damage"] = pipe_gdf["FTR_IDN_str"].map(fatigue_dict)

    # 매칭되지 않은 데이터 확인
    unmatched = pipe_gdf["fatigue_damage"].isna().sum()
    if unmatched > 0:
        print(f"경고: 피로 손상 데이터가 없는 파이프 {unmatched}개")
        # NaN을 FATIGUE_VMIN으로 대체 (LogNorm에서 0은 처리 불가)
        pipe_gdf["fatigue_damage"] = pipe_gdf["fatigue_damage"].fillna(FATIGUE_VMIN)

    # 0 값을 FATIGUE_VMIN으로 대체 (LogNorm에서 0은 처리 불가)
    pipe_gdf["fatigue_damage"] = pipe_gdf["fatigue_damage"].replace(0, FATIGUE_VMIN)

    # 실제 범위 출력
    actual_min = pipe_gdf["fatigue_damage"][pipe_gdf["fatigue_damage"] > 0].min()
    actual_max = pipe_gdf["fatigue_damage"].max()
    print(f"실제 피로 손상 범위: {actual_min:.6f} ~ {actual_max:.6f}")
    print(f"로그 스케일 범위: {FATIGUE_VMIN:.6f} ~ {FATIGUE_VMAX:.6f}")

    return pipe_gdf


def plot_fatigue_pipes(
    ax: Any,
    pipe_gdf: gpd.GeoDataFrame,
    cmap: mcolors.LinearSegmentedColormap,
    norm: mcolors.LogNorm,
) -> None:
    """파이프 피로 손상 시각화

    Args:
        ax: matplotlib axes
        pipe_gdf: 피로 손상 데이터가 포함된 파이프 GeoDataFrame
        cmap: 컬러맵
        norm: 정규화 객체
    """
    # PIPE_LM과 SPLY_LS 분리
    pipe_lm_gdf = pipe_gdf[pipe_gdf.get("PIPE_TYPE", "") == "PIPE_LM"]
    sply_ls_gdf = pipe_gdf[pipe_gdf.get("PIPE_TYPE", "") == "SPLY_LS"]

    # PIPE_LM 그리기 (굵게)
    if len(pipe_lm_gdf) > 0:
        pipe_lm_gdf.plot(
            column="fatigue_damage",
            ax=ax,
            cmap=cmap,
            linewidth=PIPE_LM_LINEWIDTH,
            norm=norm,
            legend=False,
            zorder=2,
        )

    # SPLY_LS 그리기 (얇게)
    if len(sply_ls_gdf) > 0:
        sply_ls_gdf.plot(
            column="fatigue_damage",
            ax=ax,
            cmap=cmap,
            linewidth=SPLY_LS_LINEWIDTH,
            norm=norm,
            legend=False,
            zorder=3,  # PIPE_LM 위에 표시
        )


def add_fatigue_colorbar(
    ax: Any, cmap: mcolors.LinearSegmentedColormap, norm: mcolors.LogNorm
) -> Any:
    """피로 손상 컬러바 추가

    Args:
        ax: matplotlib axes
        cmap: 컬러맵
        norm: 정규화 객체

    Returns:
        Colorbar 객체
    """
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("피로 손상 지수 (D_final, 로그 스케일)", fontsize=12)

    # 주요 값에 레이블 추가
    tick_values = [0.0001, 0.001, 0.01, 0.1, 1.0]
    cbar.set_ticks(tick_values)
    cbar.set_ticklabels(["0.0001", "0.001", "0.01", "0.1", "1.0"])

    return cbar


def calculate_fatigue_statistics(pipe_gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """파이프 피로 손상 통계 계산

    Args:
        pipe_gdf: 피로 손상 데이터가 포함된 파이프 GeoDataFrame

    Returns:
        통계 정보 딕셔너리
    """
    return {
        "total_pipes": len(pipe_gdf),
        "pipe_lm_count": len(pipe_gdf[pipe_gdf.get("PIPE_TYPE", "") == "PIPE_LM"]),
        "sply_ls_count": len(pipe_gdf[pipe_gdf.get("PIPE_TYPE", "") == "SPLY_LS"]),
        "mean_damage": pipe_gdf["fatigue_damage"].mean(),
        "max_damage": pipe_gdf["fatigue_damage"].max(),
        "min_damage": (
            pipe_gdf["fatigue_damage"][pipe_gdf["fatigue_damage"] > 0].min()
            if any(pipe_gdf["fatigue_damage"] > 0)
            else 0
        ),
        "damaged_pipes": len(
            pipe_gdf[pipe_gdf["fatigue_damage"] > 0.01]
        ),  # 기준값 초과
    }


def format_fatigue_stats_text(
    stats: dict[str, Any], repair_points: int | None = None
) -> str:
    """통계 정보를 텍스트로 포맷팅

    Args:
        stats: 통계 정보 딕셔너리
        repair_points: 복구 작업 점 개수 (선택적)

    Returns:
        포맷팅된 텍스트
    """
    text = (
        f"총 파이프: {stats['total_pipes']}개\n"
        f"  - PIPE_LM: {stats['pipe_lm_count']}개\n"
        f"  - SPLY_LS: {stats['sply_ls_count']}개\n"
        f"평균 손상: {stats['mean_damage']:.4f}\n"
        f"최대 손상: {stats['max_damage']:.4f}"
    )

    if repair_points is not None and repair_points > 0:
        text += f"\n\n복구 작업: {repair_points}건"

    return text


def plot_smlz_background(ax: Any, smlz_file: Path) -> gpd.GeoDataFrame | None:
    """SMLZ 배경 그리기

    Args:
        ax: matplotlib axes
        smlz_file: SMLZ 파일 경로

    Returns:
        SMLZ GeoDataFrame 또는 None
    """
    if not smlz_file or not smlz_file.exists():
        return None

    try:
        smlz_gdf = gpd.read_file(smlz_file, encoding="euc-kr")
        # CRS 설정
        if smlz_gdf.crs is None:
            smlz_gdf.set_crs("EPSG:5179", inplace=True)

        smlz_gdf.plot(
            ax=ax,
            facecolor="lightgray",
            edgecolor="darkgray",
            linewidth=0.5,
            alpha=0.3,
            zorder=0,
        )

        print(f"SMLZ 배경 추가: {len(smlz_gdf)}개 영역")
        return smlz_gdf

    except Exception as e:
        print(f"SMLZ 로드 실패: {e}")
        return None


def create_log_norm() -> mcolors.LogNorm:
    """로그 정규화 객체 생성

    Returns:
        LogNorm 객체
    """
    return mcolors.LogNorm(vmin=FATIGUE_VMIN, vmax=FATIGUE_VMAX)
