"""ftr_visualizer.py 모듈 테스트."""

import pytest

from src.ftr_visualizer import (
    generate_distinct_colors,
)


class TestGenerateDistinctColors:
    """generate_distinct_colors 함수 테스트"""

    def test_generate_distinct_colors_basic(self):
        """기본 색상 생성 테스트"""
        # When: 5개 색상 생성
        colors = generate_distinct_colors(5)

        # Then: 5개의 서로 다른 색상 생성
        assert len(colors) == 5
        assert len(set(colors)) == 5  # 중복 없음

        # 모든 색상이 hex 형식
        for color in colors:
            assert color.startswith("#")
            assert len(color) == 7

    def test_generate_distinct_colors_many(self):
        """많은 색상 생성 테스트"""
        # When: 20개 색상 생성
        colors = generate_distinct_colors(20)

        # Then: 20개의 서로 다른 색상 생성
        assert len(colors) == 20
        assert len(set(colors)) == 20  # 중복 없음

    def test_generate_distinct_colors_zero(self):
        """0개 색상 요청 테스트"""
        # When: 0개 색상 생성
        colors = generate_distinct_colors(0)

        # Then: 빈 리스트 반환
        assert colors == []

    def test_generate_distinct_colors_one(self):
        """1개 색상 요청 테스트"""
        # When: 1개 색상 생성
        colors = generate_distinct_colors(1)

        # Then: 1개 색상 반환
        assert len(colors) == 1
        assert colors[0].startswith("#")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
