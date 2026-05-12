"""
main18_analyze_duplicate_repairs.py 테스트
복구 작업 중복 위치 분석 스크립트 테스트
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from src.main18_analyze_duplicate_repairs import (
    UNIFIED_CSV_FILE,
    REPAIR_TYPES,
    DISTANCE_THRESHOLD,
    MIN_CLUSTER_SIZE_FOR_ANALYSIS,
    MIN_TIME_INTERVAL_DAYS,
    _find_duplicate_clusters_optimized,
    _find_duplicate_clusters_simple,
    analyze_duplicate_patterns,
    analyze_duplicate_patterns_filtered,
    calculate_haversine_distance,
    create_cluster_interval_histogram,
    create_interval_histogram,
    create_repair_count_pie_chart,
    find_duplicate_clusters,
    generate_report,
    load_recovery_data,
    main,
    parse_numeric_date_column,
    save_results,
)


class TestParseNumericDateColumn:
    """숫자 형식 날짜 파싱 테스트"""

    def test_parse_numeric_format(self):
        """숫자 형식 날짜 정상 파싱"""
        df = pd.DataFrame(
            {"접수일시": [202206230912.0, 202207251313.0, 202208151430.0]}
        )
        dates = parse_numeric_date_column(df, "접수일시")

        assert isinstance(dates, pd.Series)
        assert dates.iloc[0] == pd.Timestamp("2022-06-23 09:12:00")
        assert dates.iloc[1] == pd.Timestamp("2022-07-25 13:13:00")
        assert dates.iloc[2] == pd.Timestamp("2022-08-15 14:30:00")

    def test_parse_with_nan(self):
        """NaN 값 처리"""
        df = pd.DataFrame({"작업시작일시": [202206230912.0, np.nan, 202208151430.0]})
        dates = parse_numeric_date_column(df, "작업시작일시")

        assert dates.iloc[0] == pd.Timestamp("2022-06-23 09:12:00")
        assert pd.isna(dates.iloc[1])
        assert dates.iloc[2] == pd.Timestamp("2022-08-15 14:30:00")

    def test_parse_invalid_year(self):
        """비정상 연도 필터링"""
        df = pd.DataFrame(
            {"작업종료일": [199912312359.0, 202206230912.0, 203101010000.0]}
        )
        dates = parse_numeric_date_column(df, "작업종료일")

        assert pd.isna(dates.iloc[0])  # 1999년
        assert dates.iloc[1] == pd.Timestamp("2022-06-23 09:12:00")  # 정상
        assert pd.isna(dates.iloc[2])  # 2031년

    def test_parse_missing_column(self):
        """존재하지 않는 컬럼 처리"""
        df = pd.DataFrame({"주소": ["대구 북구", "대구 수성구"]})
        dates = parse_numeric_date_column(df, "작업일시")

        assert isinstance(dates, pd.Series)
        assert dates.isna().all()
        assert len(dates) == len(df)


class TestConstants:
    """상수 테스트"""

    def test_distance_threshold(self):
        """거리 임계값 확인"""
        assert DISTANCE_THRESHOLD == 10.0
        assert isinstance(DISTANCE_THRESHOLD, float)

    def test_time_interval_days(self):
        """시간 간격 상수 확인"""
        assert MIN_TIME_INTERVAL_DAYS == 30
        assert MIN_CLUSTER_SIZE_FOR_ANALYSIS == 4

    def test_unified_csv_file(self):
        """통합 CSV 파일 경로 확인"""
        assert (
            UNIFIED_CSV_FILE == "main11e_merge_all_repairs/누수공사_통합_위치추가.csv"
        )
        assert isinstance(UNIFIED_CSV_FILE, str)

    def test_repair_types(self):
        """작업 타입 목록 확인"""
        assert "지상누수" in REPAIR_TYPES
        assert "지하누수" in REPAIR_TYPES
        assert "긴급공사" in REPAIR_TYPES
        assert "관리대장" in REPAIR_TYPES
        assert len(REPAIR_TYPES) == 4


class TestCalculateHaversineDistance:
    """Haversine 거리 계산 테스트"""

    def test_same_point(self):
        """같은 지점의 거리는 0"""
        distance = calculate_haversine_distance(37.5665, 126.9780, 37.5665, 126.9780)
        assert distance == pytest.approx(0, abs=1e-10)

    def test_known_distance(self):
        """알려진 거리 계산 확인 (서울시청 - 남산타워: 약 1.9km)"""
        # 서울시청: 37.5665, 126.9780
        # 남산타워: 37.5512, 126.9882
        distance = calculate_haversine_distance(37.5665, 126.9780, 37.5512, 126.9882)
        assert 1900 < distance < 2000  # 약 1.9km

    def test_antipodal_points(self):
        """정반대편 지점 계산"""
        # 북극과 남극 (최대 거리)
        distance = calculate_haversine_distance(90, 0, -90, 0)
        # 지구 둘레의 절반 (약 20,000km)
        assert 19000000 < distance < 21000000

    def test_equator_distance(self):
        """적도상의 거리 계산"""
        # 적도상 경도 1도 차이 (약 111km)
        distance = calculate_haversine_distance(0, 0, 0, 1)
        assert 110000 < distance < 112000


class TestLoadRecoveryData:
    """데이터 로드 함수 테스트"""

    def test_load_with_missing_files(self, tmp_path):
        """파일이 없을 때 처리"""
        result = load_recovery_data(tmp_path)
        assert result is None

    def test_load_with_valid_files(self, tmp_path):
        """유효한 파일 로드"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 테스트 데이터 생성 - 모든 작업 타입 포함
        data_rows = []
        for i, repair_type in enumerate(REPAIR_TYPES[:3]):  # 3개 타입만 테스트
            for j in range(3):
                data_rows.append(
                    {
                        "위도": 37.5 + (i * 3 + j) * 0.001,
                        "경도": 127.0 + (i * 3 + j) * 0.001,
                        "주소": f"주소{i * 3 + j}",
                        "구군": "강남구",
                        "파일타입": repair_type,
                        "작업종료일": 202301011000.0 + (i * 3 + j) * 10000,
                    }
                )

        # 통합 데이터프레임 생성 및 저장
        df = pd.DataFrame(data_rows)
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        # 데이터 로드
        result = load_recovery_data(tmp_path)

        assert result is not None
        assert len(result) == 9  # 3개 타입 * 3개 레코드
        assert "작업타입" in result.columns
        assert "repair_id" in result.columns
        assert "작업일시" in result.columns

    def test_load_with_invalid_coordinates(self, tmp_path):
        """유효하지 않은 좌표 필터링"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 일부 NaN 좌표 포함
        df = pd.DataFrame(
            {
                "위도": [37.5, np.nan, 37.6, None],
                "경도": [127.0, 127.1, np.nan, 127.2],
                "주소": ["주소1", "주소2", "주소3", "주소4"],
                "파일타입": ["지상누수", "지상누수", "지하누수", "지하누수"],
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        # NaN이 있는 행은 제외되어야 함
        assert result is not None
        assert len(result) == 1  # 첫 번째 행만 유효

    def test_date_parsing(self, tmp_path):
        """날짜 파싱 테스트"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                "파일타입": ["지상누수", "지상누수"],
                "작업종료일": [202301011130.0, 199901011000.0],  # 2023년과 1999년
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        assert result is not None
        # 2000년 이전 날짜는 NaT로 처리
        assert pd.notna(result.iloc[0]["작업일시"])
        assert pd.isna(result.iloc[1]["작업일시"])

    def test_date_priority(self, tmp_path):
        """날짜 우선순위 테스트: 접수일시 > 작업시작일시 > 작업종료일"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
                "파일타입": ["지상누수", "지하누수", "긴급공사"],
                "접수일시": [202301010900.0, np.nan, np.nan],
                "작업시작일시": [202301011000.0, 202301021000.0, np.nan],
                "작업종료일": [202301011100.0, 202301021100.0, 202301031100.0],
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        assert result is not None
        # 첫 번째 행: 접수일시 우선 (09:00)
        assert result.iloc[0]["작업일시"] == pd.Timestamp("2023-01-01 09:00:00")
        # 두 번째 행: 접수일시 없음, 작업시작일시 사용 (10:00)
        assert result.iloc[1]["작업일시"] == pd.Timestamp("2023-01-02 10:00:00")
        # 세 번째 행: 접수일시, 작업시작일시 없음, 작업종료일 사용 (11:00)
        assert result.iloc[2]["작업일시"] == pd.Timestamp("2023-01-03 11:00:00")

    def test_existing_work_datetime_column(self, tmp_path):
        """이미 '작업일시' 컬럼이 있는 경우 처리"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                "파일타입": ["지상누수", "지하누수"],
                "작업일시": pd.date_range("2023-01-01", periods=2),
                "접수일시": [202301020900.0, 202301030900.0],  # 다른 날짜
                "작업종료일": [202301041100.0, 202301051100.0],  # 다른 날짜
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        assert result is not None
        # 기존 '작업일시' 컬럼이 유지되어야 함 (재계산하지 않음)
        assert (
            pd.to_datetime(result.iloc[0]["작업일시"]).date()
            == pd.Timestamp("2023-01-01").date()
        )
        assert (
            pd.to_datetime(result.iloc[1]["작업일시"]).date()
            == pd.Timestamp("2023-01-02").date()
        )


class TestFindDuplicateClusters:
    """중복 클러스터 찾기 테스트"""

    def test_no_duplicates(self):
        """중복이 없는 경우"""
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6, 37.7],
                "경도": [127.0, 127.1, 127.2],
            }
        )
        clusters = find_duplicate_clusters(df)
        assert len(clusters) == 0

    def test_all_duplicates(self):
        """모두 중복인 경우"""
        df = pd.DataFrame(
            {
                "위도": [37.5] * 5,
                "경도": [127.0] * 5,
            }
        )
        clusters = find_duplicate_clusters(df)
        assert len(clusters) == 1
        assert len(clusters[0]) == 5

    def test_multiple_clusters(self):
        """여러 클러스터가 있는 경우"""
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.5, 37.6, 37.6, 37.7],
                "경도": [127.0, 127.0, 127.1, 127.1, 127.2],
            }
        )
        clusters = find_duplicate_clusters(df)
        assert len(clusters) == 2  # 2개 클러스터

    def test_threshold_boundary(self):
        """임계값 경계 테스트"""
        # 10m 간격으로 배치 (임계값 = 10m)
        df = pd.DataFrame(
            {
                "위도": [37.5, 37.50005],  # 약 5-6m 거리 (10m 이내)
                "경도": [127.0, 127.0],
            }
        )
        clusters = find_duplicate_clusters(df)
        assert len(clusters) == 1  # 임계값 이내

    def test_simple_vs_optimized(self):
        """단순 버전과 최적화 버전 비교"""
        df = pd.DataFrame(
            {
                "위도": [37.5 + i * 0.0001 for i in range(10)],
                "경도": [127.0] * 10,
            }
        )

        # 작은 데이터셋 - 단순 버전
        clusters_simple = _find_duplicate_clusters_simple(df)

        # 큰 데이터셋 - 최적화 버전
        clusters_optimized = _find_duplicate_clusters_optimized(df)

        # 두 결과가 유사해야 함
        assert len(clusters_simple) == len(clusters_optimized)


class TestAnalyzeDuplicatePatterns:
    """중복 패턴 분석 테스트"""

    def test_empty_clusters(self):
        """빈 클러스터"""
        df = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
                "작업타입": ["지상누수"],
                "구군": ["강남구"],
            }
        )
        stats = analyze_duplicate_patterns(df, {})

        assert stats["total_repairs"] == 1
        assert stats["duplicate_clusters"] == 0
        assert stats["duplicate_repairs"] == 0

    def test_type_transitions(self):
        """작업 타입 전환 패턴"""
        df = pd.DataFrame(
            {
                "위도": [37.5] * 4,
                "경도": [127.0] * 4,
                "작업타입": ["지상누수", "지하누수", "기타공사", "지상누수"],
                "작업일시": pd.date_range("2023-01-01", periods=4),
                "repair_id": range(4),
            }
        )
        clusters = {0: [0, 1, 2, 3]}

        stats = analyze_duplicate_patterns(df, clusters)

        assert "지상누수 → 지하누수" in stats["type_transitions"]
        assert "지하누수 → 기타공사" in stats["type_transitions"]

    def test_time_intervals(self):
        """시간 간격 계산"""
        dates = pd.date_range("2023-01-01", periods=3, freq="30D")
        df = pd.DataFrame(
            {
                "위도": [37.5] * 3,
                "경도": [127.0] * 3,
                "작업타입": ["지상누수"] * 3,
                "작업일시": dates,
                "repair_id": range(3),
            }
        )
        clusters = {0: [0, 1, 2]}

        stats = analyze_duplicate_patterns(df, clusters)

        assert len(stats["time_intervals"]) == 2
        assert all(interval == 30 for interval in stats["time_intervals"])

    def test_district_stats(self):
        """구군별 통계"""
        df = pd.DataFrame(
            {
                "위도": [37.5] * 6,
                "경도": [127.0] * 6,
                "작업타입": ["지상누수"] * 6,
                "구군": ["강남구", "강남구", "서초구", "서초구", "서초구", "송파구"],
                "작업일시": pd.date_range("2023-01-01", periods=6),
                "repair_id": range(6),
            }
        )
        clusters = {0: [0, 1], 1: [2, 3, 4]}

        stats = analyze_duplicate_patterns(df, clusters)

        assert stats["district_stats"]["강남구"]["total"] == 2
        assert stats["district_stats"]["강남구"]["duplicates"] == 2
        assert stats["district_stats"]["서초구"]["total"] == 3
        assert stats["district_stats"]["서초구"]["duplicates"] == 3

    def test_filtered_patterns(self):
        """필터링된 패턴 분석"""
        df = pd.DataFrame(
            {
                "위도": [37.5] * 10,
                "경도": [127.0] * 10,
                "작업타입": ["지상누수"] * 10,
                "작업일시": pd.date_range("2023-01-01", periods=10),
                "repair_id": range(10),
            }
        )
        clusters = {
            0: [0, 1],  # 2개
            1: [2, 3, 4],  # 3개
            2: [5, 6, 7, 8],  # 4개
            3: [9],  # 1개 (실제로는 클러스터가 아님)
        }

        # 4개 이상만 필터링
        stats = analyze_duplicate_patterns_filtered(df, clusters, min_size=4)

        assert stats["duplicate_clusters"] == 1  # 4개 클러스터만
        assert stats["duplicate_repairs"] == 4


class TestGenerateReport:
    """보고서 생성 테스트"""

    def test_basic_report(self):
        """기본 보고서 생성"""
        stats = {
            "total_repairs": 100,
            "duplicate_clusters": 10,
            "duplicate_repairs": 30,
            "type_transitions": {},
            "time_intervals": [],
            "district_stats": {},
            "cluster_details": [],
            "first_construction_date": pd.Timestamp("2023-01-01"),
            "last_construction_date": pd.Timestamp("2023-12-31"),
        }

        report = generate_report(stats)

        assert "총 복구 작업 건수: 100건" in report
        assert "중복 위치 그룹 수: 10개" in report
        assert "중복 비율: 30.00%" in report
        assert "2023-01-01" in report
        assert "2023-12-31" in report

    def test_report_with_intervals(self):
        """시간 간격이 있는 보고서"""
        stats = {
            "total_repairs": 100,
            "duplicate_clusters": 10,
            "duplicate_repairs": 30,
            "type_transitions": {"지상누수 → 지하누수": 5},
            "time_intervals": [10, 20, 30, 90, 180, 365, 730],
            "district_stats": {"강남구": {"total": 50, "duplicates": 20}},
            "cluster_details": [],
            "first_construction_date": None,
            "last_construction_date": None,
        }

        report = generate_report(stats, " (테스트)")

        assert "테스트" in report
        assert "평균 간격:" in report
        assert "30일 이내:" in report
        assert "강남구:" in report


class TestVisualizationFunctions:
    """시각화 함수 테스트"""

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("src.main18_analyze_duplicate_repairs.setup_korean_font")
    def test_create_repair_count_pie_chart(
        self, mock_font, mock_close, mock_savefig, tmp_path
    ):
        """파이 차트 생성 테스트"""
        stats = {
            "total_repairs": 100,
            "duplicate_repairs": 30,
            "duplicate_clusters": 10,
            "cluster_details": [
                {"repairs": [1, 2]},
                {"repairs": [3, 4, 5]},
                {"repairs": [6, 7, 8, 9]},
            ],
        }

        create_repair_count_pie_chart(stats, tmp_path)

        mock_font.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("src.main18_analyze_duplicate_repairs.setup_korean_font")
    def test_create_interval_histogram(
        self, mock_font, mock_close, mock_savefig, tmp_path
    ):
        """히스토그램 생성 테스트"""
        intervals = [10, 20, 30, 40, 50, 100, 200, 300, 400]

        create_interval_histogram(intervals, tmp_path)

        mock_font.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("src.main18_analyze_duplicate_repairs.setup_korean_font")
    def test_create_cluster_interval_histogram(
        self, mock_font, mock_close, mock_savefig, tmp_path
    ):
        """클러스터 간격 히스토그램 테스트"""
        cluster_avg_intervals = [15.5, 30.2, 45.7, 60.0, 90.5]

        create_cluster_interval_histogram(cluster_avg_intervals, tmp_path)

        mock_font.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    def test_empty_data_handling(self, tmp_path):
        """빈 데이터 처리"""
        stats = {
            "total_repairs": 0,
            "duplicate_repairs": 0,
            "duplicate_clusters": 0,
            "cluster_details": [],
        }

        # 빈 데이터로 차트 생성 시 에러 없이 처리되어야 함
        create_repair_count_pie_chart(stats, tmp_path)
        create_interval_histogram([], tmp_path)


class TestSaveResults:
    """결과 저장 테스트"""

    def test_save_all_results(self, tmp_path):
        """모든 결과 파일 저장"""
        df = pd.DataFrame(
            {
                "위도": [37.5] * 5,
                "경도": [127.0] * 5,
                "작업타입": ["지상누수"] * 5,
                "구군": ["강남구"] * 5,
                "주소": ["서울시 강남구"] * 5,
                "작업일시": pd.date_range("2023-01-01", periods=5),
                "repair_id": range(5),
            }
        )

        stats = {
            "total_repairs": 5,
            "duplicate_clusters": 1,
            "duplicate_repairs": 5,
            "type_transitions": {"지상누수 → 지상누수": 4},
            "time_intervals": [1, 1, 1, 1],
            "district_stats": {"강남구": {"total": 5, "duplicates": 5}},
            "cluster_details": [
                {
                    "cluster_id": 0,
                    "size": 5,
                    "repairs": [
                        {
                            "repair_id": i,
                            "type": "지상누수",
                            "date": pd.Timestamp("2023-01-01"),
                            "address": "서울시 강남구",
                            "lat": 37.5,
                            "lon": 127.0,
                        }
                        for i in range(5)
                    ],
                    "types": ["지상누수"] * 5,
                    "districts": ["강남구"],
                    "date_range": "2023-01-01 ~ 2023-01-05",
                    "time_intervals": [1, 1, 1, 1],
                    "avg_interval": 1.0,
                }
            ],
            "first_construction_date": pd.Timestamp("2023-01-01"),
            "last_construction_date": pd.Timestamp("2023-01-05"),
        }

        with (
            patch("src.main18_analyze_duplicate_repairs.create_repair_count_pie_chart"),
            patch("src.main18_analyze_duplicate_repairs.create_interval_histogram"),
            patch(
                "src.main18_analyze_duplicate_repairs.create_cluster_interval_histogram"
            ),
        ):
            save_results(df, stats, tmp_path)

        # 파일들이 생성되었는지 확인
        assert (tmp_path / "duplicate_repairs_analysis.csv").exists()
        assert (tmp_path / "duplicate_statistics.txt").exists()
        assert (tmp_path / "duplicate_summary.csv").exists()
        assert (tmp_path / "duplicate_cluster_intervals.csv").exists()
        assert (tmp_path / "duplicate_interval_distribution.csv").exists()

    def test_save_empty_results(self, tmp_path):
        """빈 결과 저장"""
        df = pd.DataFrame()
        stats = {
            "total_repairs": 1,  # Division by zero 방지
            "duplicate_clusters": 0,
            "duplicate_repairs": 0,
            "type_transitions": {},
            "time_intervals": [],
            "district_stats": {},
            "cluster_details": [],
            "first_construction_date": None,
            "last_construction_date": None,
        }

        with patch(
            "src.main18_analyze_duplicate_repairs.create_repair_count_pie_chart"
        ):
            save_results(df, stats, tmp_path)

        # 최소한 일부 파일은 생성되어야 함
        assert (tmp_path / "duplicate_statistics.txt").exists()
        assert (tmp_path / "duplicate_summary.csv").exists()


class TestMainFunction:
    """메인 함수 테스트"""

    @patch("sys.argv", ["main18_analyze_duplicate_repairs.py"])
    @patch("src.main18_analyze_duplicate_repairs.save_results")
    @patch("src.main18_analyze_duplicate_repairs.analyze_duplicate_patterns")
    @patch("src.main18_analyze_duplicate_repairs.find_duplicate_clusters")
    @patch("src.main18_analyze_duplicate_repairs.load_recovery_data")
    def test_main_no_data(self, mock_load, mock_find, mock_analyze, mock_save):
        """데이터가 없을 때"""
        mock_load.return_value = None

        main()

        mock_load.assert_called_once()
        mock_find.assert_not_called()
        mock_analyze.assert_not_called()
        mock_save.assert_not_called()

    @patch("sys.argv", ["main18_analyze_duplicate_repairs.py"])
    @patch("src.main18_analyze_duplicate_repairs.save_results")
    @patch("src.main18_analyze_duplicate_repairs.analyze_duplicate_patterns_filtered")
    @patch("src.main18_analyze_duplicate_repairs.analyze_duplicate_patterns")
    @patch("src.main18_analyze_duplicate_repairs.find_duplicate_clusters")
    @patch("src.main18_analyze_duplicate_repairs.load_recovery_data")
    def test_main_no_duplicates(
        self, mock_load, mock_find, mock_analyze, mock_filtered, mock_save
    ):
        """중복이 없을 때"""
        mock_load.return_value = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
            }
        )
        mock_find.return_value = {}

        main()

        mock_load.assert_called_once()
        mock_find.assert_called_once()
        mock_analyze.assert_not_called()
        mock_save.assert_not_called()

    @patch("sys.argv", ["main18_analyze_duplicate_repairs.py"])
    @patch("src.main18_analyze_duplicate_repairs.save_results")
    @patch("src.main18_analyze_duplicate_repairs.analyze_duplicate_patterns_filtered")
    @patch("src.main18_analyze_duplicate_repairs.analyze_duplicate_patterns")
    @patch("src.main18_analyze_duplicate_repairs.find_duplicate_clusters")
    @patch("src.main18_analyze_duplicate_repairs.load_recovery_data")
    def test_main_with_duplicates(
        self, mock_load, mock_find, mock_analyze, mock_filtered, mock_save
    ):
        """중복이 있을 때"""
        mock_df = pd.DataFrame(
            {
                "위도": [37.5] * 5,
                "경도": [127.0] * 5,
                "작업타입": ["지상누수"] * 5,
                "작업일시": pd.date_range("2023-01-01", periods=5),
                "repair_id": range(5),
            }
        )
        mock_load.return_value = mock_df
        mock_find.return_value = {0: [0, 1, 2, 3, 4]}

        mock_stats = {
            "total_repairs": 5,
            "duplicate_clusters": 1,
            "duplicate_repairs": 5,
            "type_transitions": {},
            "time_intervals": [],
            "district_stats": {},
            "cluster_details": [],
            "first_construction_date": None,
            "last_construction_date": None,
        }
        mock_analyze.return_value = mock_stats
        mock_filtered.return_value = mock_stats

        main()

        mock_load.assert_called_once()
        mock_find.assert_called_once()
        mock_analyze.assert_called_once()
        mock_filtered.assert_called_once()
        mock_save.assert_called_once()


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_single_point_cluster(self):
        """단일 점은 클러스터가 아님"""
        df = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
            }
        )
        clusters = find_duplicate_clusters(df)
        assert len(clusters) == 0

    def test_large_dataset_optimization(self):
        """대용량 데이터셋 최적화 테스트"""
        # 5000개 이상의 데이터
        np.random.seed(42)
        df = pd.DataFrame(
            {
                "위도": np.random.uniform(37.4, 37.6, 5001),
                "경도": np.random.uniform(126.9, 127.1, 5001),
            }
        )

        # cKDTree 최적화 버전이 사용되는지 확인
        with patch(
            "src.main18_analyze_duplicate_repairs.find_duplicate_clusters_ckdtree"
        ) as mock_opt:
            mock_opt.return_value = {}
            find_duplicate_clusters(df)
            mock_opt.assert_called_once()

    def test_invalid_date_handling(self, tmp_path):
        """유효하지 않은 날짜 처리"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5, 37.6],
                "경도": [127.0, 127.1],
                "파일타입": ["지상누수", "지하누수"],
                "작업종료일": ["invalid", 202301011130.0],
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        assert result is not None
        # 유효하지 않은 날짜는 NaT로 처리
        assert pd.isna(result.iloc[0]["작업일시"])
        assert pd.notna(result.iloc[1]["작업일시"])

    def test_unicode_handling(self, tmp_path):
        """유니코드 문자 처리"""
        # 통합 CSV 파일 경로 생성
        output_dir = tmp_path / "main11e_merge_all_repairs"
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.DataFrame(
            {
                "위도": [37.5],
                "경도": [127.0],
                "파일타입": ["지상누수"],
                "주소": ["서울특별시 강남구 테헤란로 123번길"],
                "구군": ["강남구"],
            }
        )
        df.to_csv(
            output_dir / "누수공사_통합_위치추가.csv", index=False, encoding="utf-8-sig"
        )

        result = load_recovery_data(tmp_path)

        assert result is not None
        assert "테헤란로" in result.iloc[0]["주소"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
