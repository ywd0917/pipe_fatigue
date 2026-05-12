"""
반원형 패턴 감지 공통 모듈
- 연속된 짧은 세그먼트가 반원형을 이루는지 판별
- 각도 변화 분석을 통한 곡선 패턴 인식
"""

import numpy as np
from shapely.geometry import LineString

# 반원형 패턴 탐지 상수들
MIN_SEGMENTS_FOR_SEMICIRCLE = 4  # 반원형으로 인정하는 최소 세그먼트 수
MAX_ANGLE_VARIATION = 0.3  # 각 세그먼트 간 각도 변화의 최대 변동 (라디안)
MIN_TOTAL_ANGLE = np.pi / 3  # 전체 회전 각도의 최소값 (60도)
MAX_TOTAL_ANGLE = np.pi * 1.5  # 전체 회전 각도의 최대값 (270도)
MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE = (
    1.0  # 반원형 패턴으로 간주할 최대 세그먼트 길이 (미터)
)


def calculate_angle(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """두 점 사이의 각도 계산 (라디안)"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return float(np.arctan2(dy, dx))


def angle_difference(angle1: float, angle2: float) -> float:
    """두 각도 사이의 차이 계산 (-π ~ π)"""
    diff = angle2 - angle1
    while diff > np.pi:
        diff -= 2 * np.pi
    while diff < -np.pi:
        diff += 2 * np.pi
    return diff


def is_semicircular_pattern(
    segments: list[LineString],
    min_segments: int = MIN_SEGMENTS_FOR_SEMICIRCLE,
    max_angle_variation: float = MAX_ANGLE_VARIATION,
    min_total_angle: float = MIN_TOTAL_ANGLE,
    max_total_angle: float = MAX_TOTAL_ANGLE,
    max_segment_length: float = MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE,
) -> tuple[bool, float]:
    """
    연속된 세그먼트가 반원형 패턴을 이루는지 확인
    (반원형 패턴은 1m 이내의 짧은 세그먼트들에서만 검사)

    Args:
        segments: 연속된 LineString 세그먼트 리스트
        min_segments: 최소 세그먼트 수
        max_angle_variation: 각 세그먼트 간 각도 변화의 최대 변동
        min_total_angle: 전체 회전 각도의 최소값
        max_total_angle: 전체 회전 각도의 최대값
        max_segment_length: 반원형 패턴으로 간주할 최대 세그먼트 길이 (기본값: MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE)

    Returns:
        (반원형 여부, 전체 회전 각도)
    """
    if len(segments) < min_segments:
        return False, 0.0

    # 모든 세그먼트가 최대 길이 이내인지 확인
    for seg in segments:
        if seg.length > max_segment_length:
            return False, 0.0

    # 각 세그먼트의 방향 계산
    angles = []
    for seg in segments:
        coords = list(seg.coords)
        if len(coords) >= 2:
            angle = calculate_angle(coords[0], coords[-1])
            angles.append(angle)

    if len(angles) < min_segments:
        return False, 0.0

    # 연속된 각도 변화 계산
    angle_changes = []
    for i in range(1, len(angles)):
        change = angle_difference(angles[i - 1], angles[i])
        angle_changes.append(change)

    # 모든 각도 변화가 같은 방향인지 확인
    if len(angle_changes) == 0:
        return False, 0.0

    # 각도 변화의 부호가 일정한지 확인
    signs = [np.sign(change) for change in angle_changes if abs(change) > 0.01]
    if len(signs) == 0 or not all(s == signs[0] for s in signs):
        return False, 0.0

    # 각도 변화의 표준편차가 작은지 확인
    angle_changes_abs = [abs(change) for change in angle_changes]
    if np.std(angle_changes_abs) > max_angle_variation:
        return False, 0.0

    # 전체 회전 각도 계산
    total_angle = sum(angle_changes)
    total_angle_abs = abs(total_angle)

    # 반원형 패턴인지 확인
    if min_total_angle <= total_angle_abs <= max_total_angle:
        return True, total_angle

    return False, total_angle


def find_semicircular_groups(
    line_coords: list[tuple[float, float]],
    max_segment_length: float = MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE,
) -> list[list[int]]:
    """
    LineString의 좌표에서 반원형 패턴을 찾아 그룹으로 반환

    Args:
        line_coords: LineString의 좌표 리스트
        max_segment_length: 반원형 패턴으로 간주할 최대 세그먼트 길이

    Returns:
        반원형 패턴을 이루는 세그먼트 인덱스 그룹 리스트
    """
    if len(line_coords) < 2:
        return []

    # 짧은 세그먼트 인덱스 찾기
    short_indices = []
    for i in range(len(line_coords) - 1):
        segment = LineString([line_coords[i], line_coords[i + 1]])
        if segment.length <= max_segment_length:
            short_indices.append(i)

    if len(short_indices) < MIN_SEGMENTS_FOR_SEMICIRCLE:
        return []

    # 연속된 짧은 세그먼트 그룹 찾기
    groups = []
    current_group = [short_indices[0]]

    for i in range(1, len(short_indices)):
        if short_indices[i] == short_indices[i - 1] + 1:
            current_group.append(short_indices[i])
        else:
            if len(current_group) >= MIN_SEGMENTS_FOR_SEMICIRCLE:
                groups.append(current_group)
            current_group = [short_indices[i]]

    if len(current_group) >= MIN_SEGMENTS_FOR_SEMICIRCLE:
        groups.append(current_group)

    # 각 그룹이 반원형 패턴인지 확인
    semicircular_groups = []
    for group in groups:
        # 그룹의 세그먼트 생성
        segments = [LineString([line_coords[i], line_coords[i + 1]]) for i in group]
        is_semi, _ = is_semicircular_pattern(segments)
        if is_semi:
            semicircular_groups.append(group)

    return semicircular_groups
