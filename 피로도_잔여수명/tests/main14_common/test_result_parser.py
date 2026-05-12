#!/usr/bin/env python3
"""
test_result_parser.py

main14_common/result_parser.py 모듈에 대한 테스트 코드

Author: assistant
Date: 2025-01-27
"""

import sys
from pathlib import Path

import pytest

# 프로젝트 루트 디렉토리를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.main14_common.result_parser import ResultParser


class TestResultParser:
    """ResultParser 클래스 테스트"""

    def test_parse_matching_stats_korean_text(self):
        """한글 텍스트 파싱 테스트"""
        # Given: 한글 매칭 통계 텍스트
        text = """
        전체 재작업 클러스터: 814개
        매칭된 클러스터: 800개
        매칭률: 98.3%
        클러스터당 평균 파이프: 3.5개
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 올바른 값 추출
        assert stats["total_clusters"] == 814
        assert stats["matched_clusters"] == 800
        assert stats["matching_rate"] == 98.3
        assert stats["avg_pipes_per_cluster"] == 3.5

    def test_parse_matching_stats_english_text(self):
        """영어 텍스트 파싱 테스트"""
        # Given: 영어 매칭 통계 텍스트
        text = """
        Total repair clusters: 500
        Matched clusters: 450
        Matching rate: 90.0%
        Average pipes per cluster: 2.8
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 올바른 값 추출
        assert stats["total_clusters"] == 500
        assert stats["matched_clusters"] == 450
        assert stats["matching_rate"] == 90.0
        assert stats["avg_pipes_per_cluster"] == 2.8

    def test_parse_matching_stats_mixed_format(self):
        """다양한 형식 텍스트 파싱 테스트"""
        # Given: 혼합 형식 텍스트
        text = """
        전체 클러스터 : 1000
        파이프 매칭 성공: 950
        전체 매칭률:95.0
        평균 파이프 수 : 4.2
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 올바른 값 추출
        assert stats["total_clusters"] == 1000
        assert stats["matched_clusters"] == 950
        assert stats["matching_rate"] == 95.0
        assert stats["avg_pipes_per_cluster"] == 4.2

    def test_parse_matching_stats_calculate_missing_rate(self):
        """매칭률 자동 계산 테스트"""
        # Given: 매칭률이 없는 텍스트
        text = """
        전체 재작업 클러스터: 100
        매칭된 클러스터: 75
        클러스터당 평균 파이프: 2.0
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 매칭률 자동 계산
        assert stats["total_clusters"] == 100
        assert stats["matched_clusters"] == 75
        assert stats["matching_rate"] == 75.0  # 자동 계산됨
        assert stats["avg_pipes_per_cluster"] == 2.0

    def test_parse_matching_stats_percentage_vs_decimal(self):
        """퍼센트와 소수 구분 테스트"""
        # Given: 소수로 표현된 매칭률
        text1 = "매칭률: 0.85"
        text2 = "매칭률: 85%"
        text3 = "매칭률: 85.5"

        # When: 파싱 실행
        stats1 = ResultParser.parse_matching_stats(text1)
        stats2 = ResultParser.parse_matching_stats(text2)
        stats3 = ResultParser.parse_matching_stats(text3)

        # Then: 올바른 퍼센트 값으로 변환
        assert stats1["matching_rate"] == 85.0  # 0.85 -> 85%
        assert stats2["matching_rate"] == 85.0  # 85% 그대로
        assert stats3["matching_rate"] == 85.5  # 85.5 그대로

    def test_parse_matching_stats_empty_text(self):
        """빈 텍스트 처리 테스트"""
        # Given: 빈 텍스트
        text = ""

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 기본값 반환
        assert stats["total_clusters"] == 0
        assert stats["matched_clusters"] == 0
        assert stats["matching_rate"] == 0.0
        assert stats["avg_pipes_per_cluster"] == 0.0

    def test_parse_matching_stats_partial_data(self):
        """일부 데이터만 있는 경우 테스트"""
        # Given: 일부 정보만 있는 텍스트
        text = """
        전체 재작업 클러스터: 200
        클러스터당 평균 파이프: 3.0
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 있는 정보만 파싱, 나머지는 기본값
        assert stats["total_clusters"] == 200
        assert stats["matched_clusters"] == 0
        assert stats["matching_rate"] == 0.0
        assert stats["avg_pipes_per_cluster"] == 3.0

    def test_parse_matching_stats_with_noise(self):
        """노이즈가 포함된 텍스트 파싱 테스트"""
        # Given: 다른 정보가 섞인 텍스트
        text = """
        === 분석 시작 ===
        데이터 로딩 중...
        전체 재작업 클러스터: 314개 발견
        처리 시간: 2.5초
        매칭된 클러스터: 300개 (성공)
        오류 발생: 0개
        매칭률: 95.5% 달성
        클러스터당 평균 파이프: 2.7개 계산됨
        === 분석 완료 ===
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 필요한 정보만 추출
        assert stats["total_clusters"] == 314
        assert stats["matched_clusters"] == 300
        assert stats["matching_rate"] == 95.5
        assert stats["avg_pipes_per_cluster"] == 2.7

    def test_parse_matching_stats_case_insensitive(self):
        """대소문자 구분 없이 파싱 테스트"""
        # Given: 대소문자 혼용 텍스트
        text = """
        TOTAL REPAIR CLUSTERS: 100
        matched clusters: 90
        MATCHING RATE: 90.0%
        Average Pipes Per Cluster: 3.0
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 대소문자 무관하게 파싱
        assert stats["total_clusters"] == 100
        assert stats["matched_clusters"] == 90
        assert stats["matching_rate"] == 90.0
        assert stats["avg_pipes_per_cluster"] == 3.0

    @pytest.mark.parametrize(
        "text,expected_total",
        [
            ("전체 재작업 클러스터 100", 100),
            ("전체 재작업 클러스터: 200", 200),
            ("전체재작업클러스터:300", 300),
            ("Total repair clusters 400", 400),
            ("Total repair clusters: 500", 500),
            ("전체 클러스터: 600", 600),
        ],
    )
    def test_parse_total_clusters_variations(self, text, expected_total):
        """전체 클러스터 수 다양한 형식 파싱 테스트"""
        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 올바른 값 추출
        assert stats["total_clusters"] == expected_total

    @pytest.mark.parametrize(
        "text,expected_matched",
        [
            ("매칭된 클러스터: 100", 100),
            ("매칭된 클러스터 200", 200),
            ("Matched clusters: 300", 300),
            ("Matched clusters 400", 400),
            ("파이프 매칭 성공: 500", 500),
        ],
    )
    def test_parse_matched_clusters_variations(self, text, expected_matched):
        """매칭된 클러스터 수 다양한 형식 파싱 테스트"""
        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 올바른 값 추출
        assert stats["matched_clusters"] == expected_matched

    def test_parse_matching_stats_float_clusters(self):
        """클러스터 수가 실수인 경우 처리 테스트"""
        # Given: 실수로 표현된 클러스터 수 (잘못된 데이터)
        text = """
        전체 재작업 클러스터: 100.5
        매칭된 클러스터: 90.7
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 정수로 변환
        assert stats["total_clusters"] == 100  # 소수점 무시
        assert stats["matched_clusters"] == 90  # 소수점 무시

    def test_parse_matching_stats_invalid_data(self):
        """잘못된 데이터 처리 테스트"""
        # Given: 숫자가 아닌 값
        text = """
        전체 재작업 클러스터: 많음
        매칭된 클러스터: 대부분
        매칭률: 높음
        클러스터당 평균 파이프: 보통
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 기본값 반환
        assert stats["total_clusters"] == 0
        assert stats["matched_clusters"] == 0
        assert stats["matching_rate"] == 0.0
        assert stats["avg_pipes_per_cluster"] == 0.0

    def test_parse_matching_stats_multiple_matches(self):
        """여러 개의 매칭이 있는 경우 첫 번째 값 사용 테스트"""
        # Given: 중복된 정보
        text = """
        전체 재작업 클러스터: 100
        전체 재작업 클러스터: 200  # 두 번째는 무시
        매칭된 클러스터: 90
        """

        # When: 파싱 실행
        stats = ResultParser.parse_matching_stats(text)

        # Then: 첫 번째 매칭 사용
        assert stats["total_clusters"] == 100  # 첫 번째 값
