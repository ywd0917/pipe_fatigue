"""
Remaining Life Years 색상 매핑 함수들
생성일: 2025-01-16
"""

import numpy as np
from typing import Tuple, Union


def get_rgb_color_linear(remaining_life: float,
                         vmin: float = 0,
                         vmax: float = 50) -> Tuple[float, float, float]:
    """
    선형 색상 매핑
    0 -> 빨강 (1,0,0)
    vmax -> 초록 (0,1,0)
    """
    if remaining_life <= vmin:
        return (1.0, 0.0, 0.0)
    elif remaining_life >= vmax:
        return (0.0, 1.0, 0.0)
    else:
        t = (remaining_life - vmin) / (vmax - vmin)
        return (1-t, t, 0.0)


def get_rgb_color_log(remaining_life: float,
                      vmax: float = 50) -> Tuple[float, float, float]:
    """
    로그 색상 매핑 (추천)
    log(1+x) 변환으로 낮은 값 구간 세분화
    """
    if remaining_life <= 0:
        return (1.0, 0.0, 0.0)  # 빨강

    # log(1+x) 변환
    t = np.clip(np.log1p(remaining_life) / np.log1p(vmax), 0, 1)

    # 빨강 -> 노랑 -> 초록 그라데이션
    if t < 0.5:
        # 빨강(1,0,0) -> 노랑(1,1,0)
        return (1.0, 2*t, 0.0)
    else:
        # 노랑(1,1,0) -> 초록(0,1,0)
        return (2-2*t, 1.0, 0.0)


def get_rgb_color_hybrid(remaining_life: float) -> Tuple[float, float, float]:
    """
    하이브리드 색상 매핑 (가장 추천)
    위험 구간별 명확한 색상 + 그라데이션
    """
    if remaining_life <= 0:
        return (1.0, 0.0, 0.0)  # 빨강 (즉시 교체)
    elif remaining_life < 5:
        # 빨강 -> 주황 그라데이션
        t = remaining_life / 5
        return (1.0, 0.5 * t, 0.0)
    elif remaining_life < 10:
        # 주황 -> 노랑 그라데이션
        t = (remaining_life - 5) / 5
        return (1.0, 0.5 + 0.5 * t, 0.0)
    elif remaining_life < 30:
        # 노랑 -> 연두 그라데이션
        t = (remaining_life - 10) / 20
        return (1.0 - 0.5 * t, 1.0, 0.0)
    else:
        # 연두 -> 초록 (안전)
        t = np.clip((remaining_life - 30) / 20, 0, 1)
        return (0.5 - 0.5 * t, 1.0, 0.0)


def get_hex_color(rgb: Tuple[float, float, float]) -> str:
    """RGB (0-1) 값을 HEX 색상 코드로 변환"""
    r = int(rgb[0] * 255)
    g = int(rgb[1] * 255)
    b = int(rgb[2] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def get_color_for_remaining_life(remaining_life: float,
                                 method: str = "hybrid") -> str:
    """
    Remaining life 값에 대한 HEX 색상 반환

    Parameters:
    -----------
    remaining_life: 잔존 수명 (년)
    method: "linear", "log", "hybrid" (기본값: hybrid)

    Returns:
    --------
    HEX 색상 코드 (예: "#FF0000")
    """
    if method == "linear":
        rgb = get_rgb_color_linear(remaining_life)
    elif method == "log":
        rgb = get_rgb_color_log(remaining_life)
    else:  # hybrid
        rgb = get_rgb_color_hybrid(remaining_life)

    return get_hex_color(rgb)


# 사용 예시
if __name__ == "__main__":
    test_values = [0, 1, 5, 10, 20, 30, 50, 100]

    print("Remaining Life -> Color Mapping")
    print("="*50)
    print(f"{'Years':<10} {'Linear':<10} {'Log':<10} {'Hybrid':<10}")
    print("-"*40)

    for val in test_values:
        linear = get_color_for_remaining_life(val, "linear")
        log = get_color_for_remaining_life(val, "log")
        hybrid = get_color_for_remaining_life(val, "hybrid")
        print(f"{val:<10} {linear:<10} {log:<10} {hybrid:<10}")
