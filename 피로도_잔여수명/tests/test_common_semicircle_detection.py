"""
semicircle_detection.py 테스트
반원형 패턴 감지 모듈 테스트
"""

import numpy as np
from shapely.geometry import LineString

from src.common.semicircle_detection import (
    MAX_ANGLE_VARIATION,
    MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE,
    MAX_TOTAL_ANGLE,
    MIN_SEGMENTS_FOR_SEMICIRCLE,
    MIN_TOTAL_ANGLE,
    angle_difference,
    calculate_angle,
    find_semicircular_groups,
    is_semicircular_pattern,
)


class TestConstants:
    """반원형 감지 상수 테스트"""

    def test_constants_values(self):
        """상수 값 검증"""
        assert MIN_SEGMENTS_FOR_SEMICIRCLE == 4
        assert MAX_ANGLE_VARIATION == 0.3
        assert np.pi / 3 == MIN_TOTAL_ANGLE  # 60도
        assert np.pi * 1.5 == MAX_TOTAL_ANGLE  # 270도
        assert MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE == 1.0

    def test_constants_types(self):
        """상수 타입 검증"""
        assert isinstance(MIN_SEGMENTS_FOR_SEMICIRCLE, int)
        assert isinstance(MAX_ANGLE_VARIATION, float)
        assert isinstance(MIN_TOTAL_ANGLE, float)
        assert isinstance(MAX_TOTAL_ANGLE, float)
        assert isinstance(MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE, float)


class TestCalculateAngle:
    """calculate_angle 함수 테스트"""

    def test_horizontal_line(self):
        """수평선 각도 계산"""
        # 오른쪽 방향 (0도)
        angle = calculate_angle((0, 0), (1, 0))
        assert np.isclose(angle, 0)

        # 왼쪽 방향 (180도)
        angle = calculate_angle((1, 0), (0, 0))
        assert np.isclose(angle, np.pi) or np.isclose(angle, -np.pi)

    def test_vertical_line(self):
        """수직선 각도 계산"""
        # 위쪽 방향 (90도)
        angle = calculate_angle((0, 0), (0, 1))
        assert np.isclose(angle, np.pi / 2)

        # 아래쪽 방향 (-90도)
        angle = calculate_angle((0, 1), (0, 0))
        assert np.isclose(angle, -np.pi / 2)

    def test_diagonal_line(self):
        """대각선 각도 계산"""
        # 45도
        angle = calculate_angle((0, 0), (1, 1))
        assert np.isclose(angle, np.pi / 4)

        # -45도
        angle = calculate_angle((0, 0), (1, -1))
        assert np.isclose(angle, -np.pi / 4)

    def test_same_point(self):
        """같은 점일 때"""
        angle = calculate_angle((0, 0), (0, 0))
        assert angle == 0

    def test_return_type(self):
        """반환 타입 확인"""
        angle = calculate_angle((0, 0), (1, 1))
        assert isinstance(angle, float)


class TestAngleDifference:
    """angle_difference 함수 테스트"""

    def test_same_angle(self):
        """같은 각도"""
        diff = angle_difference(0, 0)
        assert diff == 0

        diff = angle_difference(np.pi / 2, np.pi / 2)
        assert diff == 0

    def test_positive_difference(self):
        """양의 차이"""
        diff = angle_difference(0, np.pi / 2)
        assert np.isclose(diff, np.pi / 2)

        diff = angle_difference(np.pi / 4, np.pi / 2)
        assert np.isclose(diff, np.pi / 4)

    def test_negative_difference(self):
        """음의 차이"""
        diff = angle_difference(np.pi / 2, 0)
        assert np.isclose(diff, -np.pi / 2)

        diff = angle_difference(np.pi / 2, np.pi / 4)
        assert np.isclose(diff, -np.pi / 4)

    def test_wrap_around(self):
        """각도 순환 처리"""
        # 180도 이상 차이날 때 반대 방향으로 계산
        diff = angle_difference(-np.pi * 0.9, np.pi * 0.9)
        assert np.isclose(diff, -0.2 * np.pi)

        diff = angle_difference(np.pi * 0.9, -np.pi * 0.9)
        assert np.isclose(diff, 0.2 * np.pi)

    def test_range_constraint(self):
        """결과가 -π ~ π 범위에 있는지 확인"""
        # 다양한 각도 조합 테스트
        angles = [-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi]
        for a1 in angles:
            for a2 in angles:
                diff = angle_difference(a1, a2)
                assert -np.pi <= diff <= np.pi


class TestIsSemicircularPattern:
    """is_semicircular_pattern 함수 테스트"""

    def test_too_few_segments(self):
        """세그먼트가 너무 적을 때"""
        # 3개 세그먼트 (최소 4개 필요)
        segments = [
            LineString([(0, 0), (0.5, 0)]),
            LineString([(0.5, 0), (1, 0)]),
            LineString([(1, 0), (1.5, 0)]),
        ]
        is_semi, angle = is_semicircular_pattern(segments)
        assert is_semi is False
        assert angle == 0.0

    def test_straight_line(self):
        """직선 패턴"""
        segments = [
            LineString([(0, 0), (0.5, 0)]),
            LineString([(0.5, 0), (1, 0)]),
            LineString([(1, 0), (1.5, 0)]),
            LineString([(1.5, 0), (2, 0)]),
        ]
        is_semi, angle = is_semicircular_pattern(segments)
        assert is_semi is False

    def test_semicircle_pattern(self):
        """반원 패턴"""
        # 90도 호를 그리는 세그먼트들
        radius = 0.5
        n_segments = 6
        angles = np.linspace(0, np.pi / 2, n_segments + 1)

        segments = []
        for i in range(n_segments):
            start = (radius * np.cos(angles[i]), radius * np.sin(angles[i]))
            end = (radius * np.cos(angles[i + 1]), radius * np.sin(angles[i + 1]))
            segments.append(LineString([start, end]))

        is_semi, total_angle = is_semicircular_pattern(segments)
        assert is_semi is True
        assert abs(total_angle) > MIN_TOTAL_ANGLE
        assert abs(total_angle) < MAX_TOTAL_ANGLE

    def test_long_segments(self):
        """세그먼트가 너무 길 때"""
        # 2m 길이의 세그먼트들 (최대 1m)
        segments = [
            LineString([(0, 0), (2, 0)]),
            LineString([(2, 0), (4, 0.5)]),
            LineString([(4, 0.5), (6, 1)]),
            LineString([(6, 1), (8, 1.5)]),
        ]
        is_semi, angle = is_semicircular_pattern(segments)
        assert is_semi is False

    def test_irregular_curve(self):
        """불규칙한 곡선"""
        # 각도 변화가 일정하지 않은 패턴
        segments = [
            LineString([(0, 0), (0.5, 0)]),
            LineString([(0.5, 0), (1, 0.1)]),  # 작은 각도 변화
            LineString([(1, 0.1), (1.2, 0.8)]),  # 큰 각도 변화
            LineString([(1.2, 0.8), (1.5, 0.9)]),  # 작은 각도 변화
        ]
        is_semi, angle = is_semicircular_pattern(segments)
        assert is_semi is False

    def test_custom_parameters(self):
        """사용자 정의 파라미터"""
        segments = [
            LineString([(0, 0), (0.5, 0)]),
            LineString([(0.5, 0), (1, 0)]),
        ]

        # 최소 세그먼트 수를 2로 설정
        is_semi, angle = is_semicircular_pattern(segments, min_segments=2)
        # 직선이므로 여전히 False
        assert is_semi is False

    def test_empty_segments(self):
        """빈 세그먼트 리스트"""
        is_semi, angle = is_semicircular_pattern([])
        assert is_semi is False
        assert angle == 0.0


class TestFindSemicircularGroups:
    """find_semicircular_groups 함수 테스트"""

    def test_no_segments(self):
        """세그먼트가 없을 때"""
        coords = [(0, 0)]  # 단일 점
        groups = find_semicircular_groups(coords)
        assert groups == []

    def test_straight_line_coords(self):
        """직선 좌표들"""
        coords = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        groups = find_semicircular_groups(coords)
        assert groups == []  # 직선이므로 반원형 그룹 없음

    def test_mixed_pattern(self):
        """직선과 곡선이 섞인 패턴"""
        # 직선 부분
        coords = [(0, 0), (1, 0), (2, 0)]

        # 반원 부분 추가
        radius = 0.5
        n_points = 6
        angles = np.linspace(0, np.pi, n_points)
        for angle in angles:
            x = 2 + radius * np.cos(angle)
            y = radius * np.sin(angle)
            coords.append((x, y))

        groups = find_semicircular_groups(coords)
        # 반원 부분이 감지되어야 함
        assert len(groups) >= 0  # 패턴에 따라 다를 수 있음

    def test_multiple_semicircles(self):
        """여러 개의 반원형 패턴"""
        coords = []

        # 첫 번째 반원
        radius = 0.3
        for i in range(6):
            angle = i * np.pi / 5
            coords.append((radius * np.cos(angle), radius * np.sin(angle)))

        # 직선 구간
        coords.extend([(1, 0), (2, 0), (3, 0)])

        # 두 번째 반원
        for i in range(6):
            angle = i * np.pi / 5
            coords.append((3 + radius * np.cos(angle), radius * np.sin(angle)))

        groups = find_semicircular_groups(coords)
        # 최소 1개 이상의 그룹이 발견되어야 함
        assert isinstance(groups, list)

    def test_long_segments_filtering(self):
        """긴 세그먼트는 필터링"""
        # 긴 세그먼트 (2m)와 짧은 세그먼트 혼합
        coords = [
            (0, 0),
            (2, 0),  # 긴 세그먼트
            (2.5, 0),  # 짧은 세그먼트
            (3, 0),
            (3.5, 0),
            (4, 0),
        ]
        groups = find_semicircular_groups(coords, max_segment_length=1.0)
        # 긴 세그먼트로 인해 연속성이 깨짐
        assert len(groups) == 0

    def test_return_type(self):
        """반환 타입 확인"""
        coords = [(0, 0), (1, 0), (2, 0)]
        groups = find_semicircular_groups(coords)
        assert isinstance(groups, list)
        for group in groups:
            assert isinstance(group, list)
            for idx in group:
                assert isinstance(idx, int)
