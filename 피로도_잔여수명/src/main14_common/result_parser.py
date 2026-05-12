"""
분석 결과 파싱 유틸리티
main14 시리즈 스크립트의 출력을 파싱하는 함수들
"""

import re
from typing import Any


class ResultParser:
    """분석 결과 파싱 유틸리티 클래스"""

    @staticmethod
    def parse_matching_stats(text: str) -> dict[str, Any]:
        """매칭 통계 파싱

        Args:
            text: 파싱할 텍스트

        Returns:
            매칭 통계 딕셔너리
            {
                'total_clusters': int,
                'matched_clusters': int,
                'matching_rate': float,
                'avg_pipes_per_cluster': float
            }
        """
        stats = {
            "total_clusters": 0,
            "matched_clusters": 0,
            "matching_rate": 0.0,
            "avg_pipes_per_cluster": 0.0,
        }

        # 전체 클러스터 수
        patterns = [
            r"전체\s*재작업\s*클러스터[:\s]*(\d+)",
            r"Total\s*repair\s*clusters?[:\s]*(\d+)",
            r"전체\s*클러스터[:\s]*(\d+)",
            r"클러스터\s*수[:\s]*(\d+)",  # "클러스터 수: 981" 패턴 추가
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                stats["total_clusters"] = int(match.group(1))
                break

        # 매칭된 클러스터 수
        patterns = [
            r"매칭된\s*클러스터[:\s]*(\d+)",
            r"Matched\s*clusters?[:\s]*(\d+)",
            r"파이프\s*매칭\s*성공[:\s]*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                stats["matched_clusters"] = int(match.group(1))
                break

        # 매칭률
        patterns = [
            r"매칭률[:\s]*([\d.]+)%?",
            r"Matching\s*rate[:\s]*([\d.]+)%?",
            r"전체\s*매칭률[:\s]*([\d.]+)%?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rate = float(match.group(1))
                # 퍼센트가 아닌 경우 100을 곱함
                if rate <= 1.0 and "%" not in match.group(0):
                    rate *= 100
                stats["matching_rate"] = rate
                break

        # 클러스터당 평균 파이프 수
        patterns = [
            r"클러스터당\s*평균\s*파이프[:\s]*([\d.]+)",
            r"클러스터당\s*평균[:\s]*([\d.]+)",
            r"Average\s*pipes?\s*per\s*cluster[:\s]*([\d.]+)",
            r"평균\s*파이프\s*수[:\s]*([\d.]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                stats["avg_pipes_per_cluster"] = float(match.group(1))
                break

        # 매칭률이 없으면 계산
        if stats["matching_rate"] == 0.0 and stats["total_clusters"] > 0:
            stats["matching_rate"] = (
                stats["matched_clusters"] / stats["total_clusters"]
            ) * 100

        return stats
