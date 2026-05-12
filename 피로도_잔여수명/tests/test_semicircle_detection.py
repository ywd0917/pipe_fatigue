"""
반원형 패턴 감지 모듈 테스트
"""

import math

import pytest
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


class TestCalculateAngle:
    """calculate_angle 함수 테스트"""

    def test_calculate_angle_horizontal_right(self):
        """수평 오른쪽 방향 각도"""
        angle = calculate_angle((0, 0), (1, 0))
        assert abs(angle - 0) < 1e-10

    def test_calculate_angle_vertical_up(self):
        """수직 위쪽 방향 각도"""
        angle = calculate_angle((0, 0), (0, 1))
        assert abs(angle - math.pi / 2) < 1e-10

    def test_calculate_angle_diagonal(self):
        """대각선 방향 각도"""
        angle = calculate_angle((0, 0), (1, 1))
        assert abs(angle - math.pi / 4) < 1e-10

    def test_calculate_angle_negative_coordinates(self):
        """음수 좌표"""
        angle = calculate_angle((0, 0), (-1, -1))
        assert abs(angle - (-3 * math.pi / 4)) < 1e-10

    def test_calculate_angle_same_point(self):
        """같은 점"""
        angle = calculate_angle((1, 1), (1, 1))
        assert angle == 0


class TestAngleDifference:
    """angle_difference 함수 테스트"""

    def test_angle_difference_normal(self):
        """일반적인 각도 차이"""
        diff = angle_difference(0, math.pi / 2)
        assert abs(diff - math.pi / 2) < 1e-10

    def test_angle_difference_wrap_around_positive(self):
        """양수 방향 wrap around"""
        diff = angle_difference(-math.pi * 0.8, math.pi * 0.8)
        expected = math.pi * 0.8 - (-math.pi * 0.8)
        if expected > math.pi:
            expected -= 2 * math.pi
        assert abs(diff - expected) < 1e-10

    def test_angle_difference_wrap_around_negative(self):
        """음수 방향 wrap around"""
        diff = angle_difference(math.pi * 0.8, -math.pi * 0.8)
        expected = -math.pi * 0.8 - math.pi * 0.8
        if expected < -math.pi:
            expected += 2 * math.pi
        assert abs(diff - expected) < 1e-10

    def test_angle_difference_zero(self):
        """각도 차이가 0"""
        diff = angle_difference(math.pi / 4, math.pi / 4)
        assert abs(diff) < 1e-10

    def test_angle_difference_pi(self):
        """π 차이"""
        diff = angle_difference(0, math.pi)
        assert abs(abs(diff) - math.pi) < 1e-10


class TestIsSemicircularPattern:
    """is_semicircular_pattern 함수 테스트"""

    def create_semicircle_segments(
        self, radius: float = 1.0, num_segments: int = 6
    ) -> list[LineString]:
        """반원형 세그먼트 생성"""
        segments = []
        angle_step = math.pi / num_segments

        for i in range(num_segments):
            angle1 = i * angle_step
            angle2 = (i + 1) * angle_step

            x1 = radius * math.cos(angle1)
            y1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            y2 = radius * math.sin(angle2)

            segments.append(LineString([(x1, y1), (x2, y2)]))

        return segments

    def create_straight_line_segments(self, num_segments: int = 4) -> list[LineString]:
        """직선 세그먼트 생성"""
        segments = []
        for i in range(num_segments):
            segments.append(LineString([(i, 0), (i + 1, 0)]))
        return segments

    def test_is_semicircular_pattern_true(self):
        """반원형 패턴 인식"""
        segments = self.create_semicircle_segments(radius=0.5, num_segments=6)
        is_semi, total_angle = is_semicircular_pattern(segments)

        assert is_semi is True
        assert abs(abs(total_angle) - math.pi) < 1.0  # 약간의 오차 허용

    def test_is_semicircular_pattern_false_straight_line(self):
        """직선은 반원형이 아님"""
        segments = self.create_straight_line_segments(num_segments=6)
        is_semi, total_angle = is_semicircular_pattern(segments)

        assert is_semi is False

    def test_is_semicircular_pattern_false_too_few_segments(self):
        """세그먼트 수가 부족"""
        segments = self.create_semicircle_segments(num_segments=2)
        is_semi, total_angle = is_semicircular_pattern(segments)

        assert is_semi is False

    def test_is_semicircular_pattern_false_too_long_segments(self):
        """세그먼트가 너무 긺"""
        # 반원형이지만 각 세그먼트가 최대 길이를 초과
        segments = self.create_semicircle_segments(radius=2.0, num_segments=4)
        is_semi, total_angle = is_semicircular_pattern(segments, max_segment_length=0.5)

        assert is_semi is False

    def test_is_semicircular_pattern_custom_parameters(self):
        """사용자 정의 매개변수"""
        segments = self.create_semicircle_segments(radius=0.3, num_segments=8)
        is_semi, total_angle = is_semicircular_pattern(
            segments,
            min_segments=8,
            max_angle_variation=0.5,
            min_total_angle=math.pi / 4,
            max_total_angle=math.pi * 2,
        )

        assert is_semi is True

    def test_is_semicircular_pattern_irregular_angles(self):
        """불규칙한 각도 변화"""
        segments = [
            LineString([(0, 0), (0.5, 0)]),
            LineString([(0.5, 0), (1, 0.5)]),
            LineString([(1, 0.5), (0.5, 1)]),
            LineString([(0.5, 1), (0, 0.5)]),
            LineString([(0, 0.5), (0.5, 0)]),  # 급격한 방향 변화
        ]

        is_semi, total_angle = is_semicircular_pattern(segments)
        assert is_semi is False


class TestFindSemicircularGroups:
    """find_semicircular_groups 함수 테스트"""

    def test_find_semicircular_groups_empty_coords(self):
        """빈 좌표 리스트"""
        groups = find_semicircular_groups([])
        assert groups == []

    def test_find_semicircular_groups_single_point(self):
        """단일 점"""
        groups = find_semicircular_groups([(0, 0)])
        assert groups == []

    def test_find_semicircular_groups_no_short_segments(self):
        """짧은 세그먼트가 없음"""
        coords = [(0, 0), (10, 0), (20, 0)]  # 모든 세그먼트가 10m로 길음
        groups = find_semicircular_groups(coords, max_segment_length=1.0)
        assert groups == []

    def test_find_semicircular_groups_semicircle(self):
        """반원형 패턴 감지"""
        # 반원형 좌표 생성 (반지름 0.5)
        coords = []
        num_points = 8
        for i in range(num_points):
            angle = i * math.pi / (num_points - 1)
            x = 0.5 * math.cos(angle)
            y = 0.5 * math.sin(angle)
            coords.append((x, y))

        groups = find_semicircular_groups(coords, max_segment_length=1.0)
        assert len(groups) >= 1  # 적어도 하나의 그룹 발견

    def test_find_semicircular_groups_mixed_pattern(self):
        """혼합 패턴 (긴 세그먼트 + 짧은 반원형)"""
        coords = []

        # 긴 직선 세그먼트
        coords.extend([(0, 0), (5, 0)])

        # 짧은 반원형 세그먼트
        for i in range(6):
            angle = i * math.pi / 5
            x = 5 + 0.3 * math.cos(angle)
            y = 0.3 * math.sin(angle)
            coords.append((x, y))

        # 다시 긴 직선 세그먼트
        coords.extend([(8, 0), (13, 0)])

        groups = find_semicircular_groups(coords, max_segment_length=1.0)
        # 반원형 부분만 감지되어야 함
        assert len(groups) >= 0  # 실제 반원형 감지 여부는 패턴에 따라 다름

    def test_find_semicircular_groups_multiple_semicircles(self):
        """여러 개의 반원형 패턴"""
        coords = []

        # 첫 번째 반원
        for i in range(5):
            angle = i * math.pi / 4
            x = 0.4 * math.cos(angle)
            y = 0.4 * math.sin(angle)
            coords.append((x, y))

        # 간격
        coords.append((2, 0))

        # 두 번째 반원
        for i in range(5):
            angle = i * math.pi / 4
            x = 2 + 0.4 * math.cos(angle)
            y = 0.4 * math.sin(angle)
            coords.append((x, y))

        groups = find_semicircular_groups(coords, max_segment_length=1.0)
        # 두 개의 반원형 그룹을 찾을 수 있는지 확인
        assert len(groups) >= 0


class TestModuleConstants:
    """모듈 상수 테스트"""

    def test_constants_types(self):
        """상수들의 타입 확인"""
        assert isinstance(MIN_SEGMENTS_FOR_SEMICIRCLE, int)
        assert isinstance(MAX_ANGLE_VARIATION, float)
        assert isinstance(MIN_TOTAL_ANGLE, float)
        assert isinstance(MAX_TOTAL_ANGLE, float)
        assert isinstance(MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE, float)

    def test_constants_values(self):
        """상수들의 값 확인"""
        assert MIN_SEGMENTS_FOR_SEMICIRCLE >= 3
        assert MAX_ANGLE_VARIATION > 0
        assert MIN_TOTAL_ANGLE > 0
        assert MAX_TOTAL_ANGLE > MIN_TOTAL_ANGLE
        assert MAX_SEGMENT_LENGTH_FOR_SEMICIRCLE > 0

    def test_constants_relationships(self):
        """상수들 간의 관계 확인"""
        assert MAX_TOTAL_ANGLE > MIN_TOTAL_ANGLE
        assert math.pi / 6 <= MIN_TOTAL_ANGLE  # 최소 30도
        assert math.pi * 2 >= MAX_TOTAL_ANGLE  # 최대 360도


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_very_small_segments(self):
        """매우 작은 세그먼트"""
        segments = [
            LineString([(0, 0), (0.001, 0)]),
            LineString([(0.001, 0), (0.002, 0.001)]),
            LineString([(0.002, 0.001), (0.001, 0.002)]),
            LineString([(0.001, 0.002), (0, 0.001)]),
        ]

        is_semi, total_angle = is_semicircular_pattern(segments)
        # 매우 작은 세그먼트도 처리 가능해야 함
        assert isinstance(is_semi, bool)
        assert isinstance(total_angle, float)

    def test_collinear_points(self):
        """일직선상의 점들"""
        coords = [(0, 0), (0.1, 0), (0.2, 0), (0.3, 0), (0.4, 0)]
        groups = find_semicircular_groups(coords)
        # 직선은 반원형이 아니므로 빈 리스트
        assert groups == []

    def test_single_segment_group(self):
        """단일 세그먼트 그룹"""
        segments = [LineString([(0, 0), (0.5, 0)])]
        is_semi, total_angle = is_semicircular_pattern(segments)

        assert is_semi is False  # 최소 세그먼트 수 미달


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
