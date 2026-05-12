#!/usr/bin/env python
"""
main30_validation_report.py

Phase 12: Automated Validation and Reporting
- 자동화된 분석 검증 및 종합 보고서 생성
- 모든 분석 결과 통합
- 품질 검증 및 일관성 체크
- Executive Summary 생성
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from shapely.geometry import Point

from common.korean_font_utils import setup_korean_font


class ValidationReporter:
    def __init__(self, output_dir: str = "results/spatial_analysis/validation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validation_results: dict[str, Any] = {
            "data_quality": {},
            "analysis_consistency": {},
            "spatial_coverage": {},
            "temporal_coverage": {},
            "statistical_validity": {},
            "metadata": {},
        }

    def validate_all_analyses(self) -> dict[str, Any]:
        """모든 분석 결과 검증"""
        print("\n=== 종합 검증 시작 ===")

        # 1. 데이터 품질 검증
        self._validate_data_quality()

        # 2. 분석 일관성 검증
        self._validate_analysis_consistency()

        # 3. 공간 커버리지 검증
        self._validate_spatial_coverage()

        # 4. 시간 커버리지 검증
        self._validate_temporal_coverage()

        # 5. 통계적 유효성 검증
        self._validate_statistical_validity()

        # 메타데이터 추가
        self.validation_results["metadata"] = {
            "validation_timestamp": datetime.now().isoformat(),
            "total_checks": self._count_total_checks(),
            "passed_checks": self._count_passed_checks(),
            "failed_checks": self._count_failed_checks(),
            "validation_score": self._calculate_validation_score(),
        }

        return self.validation_results

    def _validate_data_quality(self) -> None:
        """데이터 품질 검증"""
        print("  데이터 품질 검증 중...")

        quality_checks = {
            "missing_values": False,
            "coordinate_validity": False,
            "date_consistency": False,
            "value_ranges": False,
            "encoding_issues": False,
        }

        # 원본 데이터 검증
        try:
            # Try multiple possible data locations
            data_paths = [
                "data/repaired-20241230/0520_repair.shp",
                "data/repair/0520_repair.shp",
                "data/0520_repair.shp",
            ]

            gdf_520 = None
            for path in data_paths:
                if Path(path).exists():
                    gdf_520 = gpd.read_file(path, encoding="utf-8")
                    break

            if gdf_520 is None:
                # If no shapefile found, use CSV data
                csv_paths = [
                    Path("data/520_area/repairs_with_location_520_v3.csv"),
                    Path("data/pipe_fatigue/0520_ALL_fixed.csv"),
                ]

                for csv_path in csv_paths:
                    if csv_path.exists():
                        df = pd.read_csv(csv_path, encoding="utf-8")
                        if "x" in df.columns and "y" in df.columns:
                            geometry = [
                                Point(xy) for xy in zip(df.x, df.y, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:5179"
                            )
                            break
                        if "longitude" in df.columns and "latitude" in df.columns:
                            geometry = [
                                Point(xy)
                                for xy in zip(df.longitude, df.latitude, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:4326"
                            )
                            gdf_520 = gdf_520.to_crs("EPSG:5179")
                            break

                if gdf_520 is None:
                    raise FileNotFoundError("No valid data source found")

            # 결측값 체크
            missing_ratio = gdf_520.isnull().sum().sum() / (
                len(gdf_520) * len(gdf_520.columns)
            )
            quality_checks["missing_values"] = missing_ratio < 0.1

            # 좌표 유효성
            coords_valid = all(
                (gdf_520.geometry.is_valid)
                & (gdf_520.geometry.bounds["minx"] > 0)
                & (gdf_520.geometry.bounds["miny"] > 0)
            )
            quality_checks["coordinate_validity"] = coords_valid

            # 날짜 일관성
            if "작업종료일" in gdf_520.columns:
                dates = pd.to_datetime(gdf_520["작업종료일"], errors="coerce")
                date_valid = dates.notna().sum() / len(dates) > 0.9
                quality_checks["date_consistency"] = date_valid

            # 값 범위 체크
            numeric_cols = gdf_520.select_dtypes(include=[np.number]).columns
            outlier_ratio = 0
            for col in numeric_cols:
                Q1 = gdf_520[col].quantile(0.25)
                Q3 = gdf_520[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = (gdf_520[col] < Q1 - 3 * IQR) | (gdf_520[col] > Q3 + 3 * IQR)
                outlier_ratio += outliers.sum() / len(gdf_520)
            quality_checks["value_ranges"] = (
                outlier_ratio / len(numeric_cols) < 0.05 if numeric_cols.any() else True
            )

            quality_checks["encoding_issues"] = True  # 파일이 로드되면 인코딩 OK

        except Exception as e:
            print(f"    데이터 품질 검증 오류: {e}")

        self.validation_results["data_quality"] = quality_checks

    def _validate_analysis_consistency(self) -> None:
        """분석 일관성 검증"""
        print("  분석 일관성 검증 중...")

        consistency_checks = {
            "grid_consistency": False,
            "hotspot_consistency": False,
            "pattern_consistency": False,
            "priority_consistency": False,
        }

        try:
            # 그리드 일관성 체크
            spacetime_path = Path("results/spatial_analysis/spacetime")
            if spacetime_path.exists():
                grid_file = spacetime_path / "spacetime_grid.geojson"
                if grid_file.exists():
                    grid_gdf = gpd.read_file(grid_file)
                    # 60m x 60m 그리드 검증
                    areas = grid_gdf.geometry.area
                    expected_area = 60 * 60
                    area_diff = abs(areas.mean() - expected_area) / expected_area
                    consistency_checks["grid_consistency"] = area_diff < 0.01

            # 핫스팟 일관성
            hotspot_path = Path("results/spatial_analysis/hotspots")
            pattern_path = Path("results/spatial_analysis/patterns")

            if hotspot_path.exists() and pattern_path.exists():
                hotspot_file = hotspot_path / "hotspots_final.csv"
                pattern_file = pattern_path / "emerging_patterns.csv"

                if hotspot_file.exists() and pattern_file.exists():
                    hotspots_df = pd.read_csv(hotspot_file)
                    patterns_df = pd.read_csv(pattern_file)

                    # 핫스팟과 패턴의 셀 ID 일관성
                    common_cells = set(hotspots_df["cell_id"]) & set(
                        patterns_df["cell_id"]
                    )
                    consistency_checks["hotspot_consistency"] = len(common_cells) > 0
                    consistency_checks["pattern_consistency"] = True

            # 우선순위 일관성
            priority_path = Path("results/spatial_analysis/integrated_priority")
            if priority_path.exists():
                priority_file = priority_path / "integrated_priority_rankings.csv"
                if priority_file.exists():
                    priority_df = pd.read_csv(priority_file)
                    # 우선순위 점수가 합리적 범위에 있는지 체크
                    if "integrated_score" in priority_df.columns:
                        scores = priority_df["integrated_score"]
                    elif "priority_score" in priority_df.columns:
                        scores = priority_df["priority_score"]
                    else:
                        scores = pd.Series([0])
                    consistency_checks["priority_consistency"] = (
                        scores >= 0
                    ).all() and (scores <= 100).all()

        except Exception as e:
            print(f"    분석 일관성 검증 오류: {e}")

        self.validation_results["analysis_consistency"] = consistency_checks

    def _validate_spatial_coverage(self) -> None:
        """공간 커버리지 검증"""
        print("  공간 커버리지 검증 중...")

        spatial_checks = {
            "area_coverage": 0.0,
            "cell_coverage": 0.0,
            "hotspot_coverage": 0.0,
            "data_density": 0.0,
        }

        try:
            # 원본 데이터 영역
            # Try multiple possible data locations
            data_paths = [
                "data/repaired-20241230/0520_repair.shp",
                "data/repair/0520_repair.shp",
                "data/0520_repair.shp",
            ]

            gdf_520 = None
            for path in data_paths:
                if Path(path).exists():
                    gdf_520 = gpd.read_file(path, encoding="utf-8")
                    break

            if gdf_520 is None:
                # If no shapefile found, use CSV data
                csv_paths = [
                    Path("data/520_area/repairs_with_location_520_v3.csv"),
                    Path("data/pipe_fatigue/0520_ALL_fixed.csv"),
                ]

                for csv_path in csv_paths:
                    if csv_path.exists():
                        df = pd.read_csv(csv_path, encoding="utf-8")
                        if "x" in df.columns and "y" in df.columns:
                            geometry = [
                                Point(xy) for xy in zip(df.x, df.y, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:5179"
                            )
                            break
                        if "longitude" in df.columns and "latitude" in df.columns:
                            geometry = [
                                Point(xy)
                                for xy in zip(df.longitude, df.latitude, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:4326"
                            )
                            gdf_520 = gdf_520.to_crs("EPSG:5179")
                            break

                if gdf_520 is None:
                    raise FileNotFoundError("No valid data source found")
            total_area = gdf_520.unary_union.convex_hull.area

            # 그리드 커버리지
            grid_file = Path(
                "results/spatial_analysis/spacetime/spacetime_grid.geojson"
            )
            if grid_file.exists():
                grid_gdf = gpd.read_file(grid_file)
                grid_area = grid_gdf.unary_union.area
                spatial_checks["area_coverage"] = min(grid_area / total_area, 1.0)
                spatial_checks["cell_coverage"] = len(grid_gdf) / (
                    total_area / (60 * 60)
                )

            # 핫스팟 커버리지
            hotspot_file = Path("results/spatial_analysis/hotspots/hotspots_final.csv")
            if hotspot_file.exists():
                hotspots_df = pd.read_csv(hotspot_file)
                if grid_gdf is not None:
                    spatial_checks["hotspot_coverage"] = len(hotspots_df) / len(
                        grid_gdf
                    )

            # 데이터 밀도
            spatial_checks["data_density"] = len(gdf_520) / (
                total_area / 10000
            )  # per ha

        except Exception as e:
            print(f"    공간 커버리지 검증 오류: {e}")

        self.validation_results["spatial_coverage"] = spatial_checks

    def _validate_temporal_coverage(self) -> None:
        """시간 커버리지 검증"""
        print("  시간 커버리지 검증 중...")

        temporal_checks = {
            "date_range": "",
            "temporal_completeness": 0.0,
            "seasonal_coverage": False,
            "trend_validity": False,
        }

        try:
            # 원본 데이터 시간 범위
            # Try multiple possible data locations
            data_paths = [
                "data/repaired-20241230/0520_repair.shp",
                "data/repair/0520_repair.shp",
                "data/0520_repair.shp",
            ]

            gdf_520 = None
            for path in data_paths:
                if Path(path).exists():
                    gdf_520 = gpd.read_file(path, encoding="utf-8")
                    break

            if gdf_520 is None:
                # If no shapefile found, use CSV data
                csv_paths = [
                    Path("data/520_area/repairs_with_location_520_v3.csv"),
                    Path("data/pipe_fatigue/0520_ALL_fixed.csv"),
                ]

                for csv_path in csv_paths:
                    if csv_path.exists():
                        df = pd.read_csv(csv_path, encoding="utf-8")
                        if "x" in df.columns and "y" in df.columns:
                            geometry = [
                                Point(xy) for xy in zip(df.x, df.y, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:5179"
                            )
                            break
                        if "longitude" in df.columns and "latitude" in df.columns:
                            geometry = [
                                Point(xy)
                                for xy in zip(df.longitude, df.latitude, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:4326"
                            )
                            gdf_520 = gdf_520.to_crs("EPSG:5179")
                            break

                if gdf_520 is None:
                    raise FileNotFoundError("No valid data source found")

            if "작업종료일" in gdf_520.columns:
                dates = pd.to_datetime(gdf_520["작업종료일"], errors="coerce")
                valid_dates = dates.dropna()

                if len(valid_dates) > 0:
                    date_range = (
                        f"{valid_dates.min().date()} ~ {valid_dates.max().date()}"
                    )
                    temporal_checks["date_range"] = date_range

                    # 시간적 완전성
                    total_days = (valid_dates.max() - valid_dates.min()).days
                    unique_days = valid_dates.dt.date.nunique()
                    temporal_checks["temporal_completeness"] = unique_days / max(
                        total_days, 1
                    )

                    # 계절 커버리지
                    months = valid_dates.dt.month.unique()
                    temporal_checks["seasonal_coverage"] = len(months) >= 12

                    # 트렌드 유효성
                    if len(valid_dates) > 30:
                        temporal_checks["trend_validity"] = True

        except Exception as e:
            print(f"    시간 커버리지 검증 오류: {e}")

        self.validation_results["temporal_coverage"] = temporal_checks

    def _validate_statistical_validity(self) -> None:
        """통계적 유효성 검증"""
        print("  통계적 유효성 검증 중...")

        statistical_checks = {
            "sample_size_adequate": False,
            "normality_test": {},
            "correlation_validity": False,
            "confidence_intervals": False,
        }

        try:
            # 샘플 크기 적절성
            # Try multiple possible data locations
            data_paths = [
                "data/repaired-20241230/0520_repair.shp",
                "data/repair/0520_repair.shp",
                "data/0520_repair.shp",
            ]

            gdf_520 = None
            for path in data_paths:
                if Path(path).exists():
                    gdf_520 = gpd.read_file(path, encoding="utf-8")
                    break

            if gdf_520 is None:
                # If no shapefile found, use CSV data
                csv_paths = [
                    Path("data/520_area/repairs_with_location_520_v3.csv"),
                    Path("data/pipe_fatigue/0520_ALL_fixed.csv"),
                ]

                for csv_path in csv_paths:
                    if csv_path.exists():
                        df = pd.read_csv(csv_path, encoding="utf-8")
                        if "x" in df.columns and "y" in df.columns:
                            geometry = [
                                Point(xy) for xy in zip(df.x, df.y, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:5179"
                            )
                            break
                        if "longitude" in df.columns and "latitude" in df.columns:
                            geometry = [
                                Point(xy)
                                for xy in zip(df.longitude, df.latitude, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:4326"
                            )
                            gdf_520 = gdf_520.to_crs("EPSG:5179")
                            break

                if gdf_520 is None:
                    raise FileNotFoundError("No valid data source found")
            statistical_checks["sample_size_adequate"] = len(gdf_520) >= 30

            # 정규성 검정 (주요 변수)
            if "CNT_JNT" in gdf_520.columns:
                cnt_values = gdf_520["CNT_JNT"].dropna()
                if len(cnt_values) > 3:
                    _, p_value = stats.normaltest(cnt_values)
                    statistical_checks["normality_test"]["CNT_JNT"] = {
                        "p_value": float(p_value),
                        "is_normal": p_value > 0.05,
                    }

            # 상관관계 유효성
            kfactors_file = Path(
                "results/spatial_analysis/kfactors_dataset/kfactors_spacetime_dataset.csv"
            )
            if kfactors_file.exists():
                kfactors_df = pd.read_csv(kfactors_file)
                k_cols = [c for c in kfactors_df.columns if c.startswith("mean_K_")]
                if len(k_cols) >= 2:
                    corr_matrix = kfactors_df[k_cols].corr()
                    # 적어도 하나의 유의미한 상관관계가 있는지
                    significant_corr = (corr_matrix.abs() > 0.3).sum().sum() > len(
                        k_cols
                    )
                    statistical_checks["correlation_validity"] = significant_corr

            # 신뢰구간 체크
            prediction_file = Path(
                "results/spatial_analysis/predictions/kfactors_prediction_results.json"
            )
            if prediction_file.exists():
                with open(prediction_file) as f:
                    pred_results = json.load(f)
                    if "confidence_intervals" in pred_results.get(
                        "metric_predictions", {}
                    ):
                        statistical_checks["confidence_intervals"] = True

        except Exception as e:
            print(f"    통계적 유효성 검증 오류: {e}")

        self.validation_results["statistical_validity"] = statistical_checks

    def _count_total_checks(self) -> int:
        """전체 체크 항목 수 계산"""
        total = 0
        for category in self.validation_results:
            if category != "metadata" and isinstance(
                self.validation_results[category], dict
            ):
                total += len(self.validation_results[category])
        return total

    def _count_passed_checks(self) -> int:
        """통과한 체크 항목 수 계산"""
        passed = 0
        for category in self.validation_results:
            if category != "metadata" and isinstance(
                self.validation_results[category], dict
            ):
                for check, value in self.validation_results[category].items():
                    if (isinstance(value, bool) and value) or (
                        isinstance(value, int | float) and value > 0.5
                    ):
                        passed += 1
        return passed

    def _count_failed_checks(self) -> int:
        """실패한 체크 항목 수 계산"""
        total = self._count_total_checks()
        passed = self._count_passed_checks()
        return total - passed

    def _calculate_validation_score(self) -> float:
        """검증 점수 계산 (0-100)"""
        total = self._count_total_checks()
        if total == 0:
            return 0.0
        passed = self._count_passed_checks()
        return round((passed / total) * 100, 2)

    def generate_executive_summary(self) -> str:
        """Executive Summary 생성"""
        print("\n=== Executive Summary 생성 중 ===")

        summary = []
        summary.append("# 520 지역 재작업 공간분석 종합 보고서\n")
        summary.append(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 1. 핵심 발견사항
        summary.append("## 1. 핵심 발견사항\n")
        key_findings = self._extract_key_findings()
        for finding in key_findings:
            summary.append(f"- {finding}\n")

        # 2. 분석 커버리지
        summary.append("\n## 2. 분석 커버리지\n")
        coverage = self._extract_coverage_summary()
        for item in coverage:
            summary.append(f"- {item}\n")

        # 3. 우선순위 권장사항
        summary.append("\n## 3. 우선순위 권장사항\n")
        recommendations = self._extract_recommendations()
        for i, rec in enumerate(recommendations, 1):
            summary.append(f"{i}. {rec}\n")

        # 4. 검증 결과
        summary.append("\n## 4. 검증 결과\n")
        if "metadata" in self.validation_results:
            meta = self.validation_results["metadata"]
            summary.append(f"- 전체 검증 항목: {meta.get('total_checks', 0)}개\n")
            summary.append(f"- 통과 항목: {meta.get('passed_checks', 0)}개\n")
            summary.append(f"- 실패 항목: {meta.get('failed_checks', 0)}개\n")
            summary.append(f"- **검증 점수: {meta.get('validation_score', 0)}점**\n")

        # 5. 데이터 품질
        summary.append("\n## 5. 데이터 품질 평가\n")
        quality_summary = self._extract_quality_summary()
        for item in quality_summary:
            summary.append(f"- {item}\n")

        # 6. 다음 단계
        summary.append("\n## 6. 다음 단계\n")
        next_steps = self._extract_next_steps()
        for step in next_steps:
            summary.append(f"- {step}\n")

        return "".join(summary)

    def _extract_key_findings(self) -> list[str]:
        """핵심 발견사항 추출"""
        findings = []

        # 핫스팟 분석 결과
        hotspot_file = Path("results/spatial_analysis/hotspots/hotspots_final.csv")
        if hotspot_file.exists():
            hotspots_df = pd.read_csv(hotspot_file)
            high_confidence = hotspots_df[hotspots_df["confidence"] >= 0.99]
            if len(high_confidence) > 0:
                findings.append(
                    f"**{len(high_confidence)}개 고신뢰도(99%) 핫스팟 지역 발견**"
                )

        # K-factors 예측 결과
        pred_file = Path(
            "results/spatial_analysis/predictions/kfactors_prediction_results.json"
        )
        if pred_file.exists():
            with open(pred_file) as f:
                pred_data = json.load(f)
                warnings = pred_data.get("early_warnings", [])
                if warnings:
                    findings.append(f"**{len(warnings)}개 조기 경보 발생**")

        # 패턴 분석 결과
        pattern_file = Path("results/spatial_analysis/patterns/emerging_patterns.csv")
        if pattern_file.exists():
            patterns_df = pd.read_csv(pattern_file)
            intensifying = patterns_df[patterns_df["pattern_type"] == "Intensifying"]
            if len(intensifying) > 0:
                findings.append(
                    f"**{len(intensifying)}개 지역에서 위험도 강화 패턴 감지**"
                )

        # 우선순위 결과
        priority_file = Path(
            "results/spatial_analysis/integrated_priority/decision_matrix.csv"
        )
        if priority_file.exists():
            priority_df = pd.read_csv(priority_file)
            critical = priority_df[priority_df["risk_category"] == "Critical"]
            if len(critical) > 0:
                findings.append(f"**{len(critical)}개 지역 즉시 조치 필요**")

        if not findings:
            findings.append("분석 결과 특이사항 없음")

        return findings

    def _extract_coverage_summary(self) -> list[str]:
        """커버리지 요약 추출"""
        coverage = []

        if "spatial_coverage" in self.validation_results:
            spatial = self.validation_results["spatial_coverage"]
            area_cov = spatial.get("area_coverage", 0) * 100
            coverage.append(f"공간 커버리지: {area_cov:.1f}%")

        if "temporal_coverage" in self.validation_results:
            temporal = self.validation_results["temporal_coverage"]
            date_range = temporal.get("date_range", "N/A")
            coverage.append(f"시간 범위: {date_range}")
            if temporal.get("seasonal_coverage"):
                coverage.append("계절별 데이터: 완전 커버")

        # 데이터 규모
        try:
            # Try multiple possible data locations
            data_paths = [
                "data/repaired-20241230/0520_repair.shp",
                "data/repair/0520_repair.shp",
                "data/0520_repair.shp",
            ]

            gdf_520 = None
            for path in data_paths:
                if Path(path).exists():
                    gdf_520 = gpd.read_file(path, encoding="utf-8")
                    break

            if gdf_520 is None:
                # If no shapefile found, use CSV data
                csv_paths = [
                    Path("data/520_area/repairs_with_location_520_v3.csv"),
                    Path("data/pipe_fatigue/0520_ALL_fixed.csv"),
                ]

                for csv_path in csv_paths:
                    if csv_path.exists():
                        df = pd.read_csv(csv_path, encoding="utf-8")
                        if "x" in df.columns and "y" in df.columns:
                            geometry = [
                                Point(xy) for xy in zip(df.x, df.y, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:5179"
                            )
                            break
                        if "longitude" in df.columns and "latitude" in df.columns:
                            geometry = [
                                Point(xy)
                                for xy in zip(df.longitude, df.latitude, strict=False)
                            ]
                            gdf_520 = gpd.GeoDataFrame(
                                df, geometry=geometry, crs="EPSG:4326"
                            )
                            gdf_520 = gdf_520.to_crs("EPSG:5179")
                            break

                if gdf_520 is None:
                    raise FileNotFoundError("No valid data source found")
            coverage.append(f"분석 대상: {len(gdf_520):,}개 재작업 지점")
        except:
            pass

        return coverage

    def _extract_recommendations(self) -> list[str]:
        """권장사항 추출"""
        recommendations = []

        # 우선순위 기반 권장사항
        priority_file = Path(
            "results/spatial_analysis/integrated_priority/integrated_priority_rankings.csv"
        )
        if priority_file.exists():
            priority_df = pd.read_csv(priority_file)
            top_priorities = priority_df.head(5)
            for _, row in top_priorities.iterrows():
                cell_id = row["cell_id"]
                if "integrated_score" in priority_df.columns:
                    score = row["integrated_score"]
                elif "priority_score" in priority_df.columns:
                    score = row["priority_score"]
                else:
                    score = 0.0
                recommendations.append(
                    f"셀 {cell_id} (점수: {score:.1f}) - 우선 점검 권장"
                )

        if not recommendations:
            recommendations.append("정기 점검 일정 유지")

        return recommendations

    def _extract_quality_summary(self) -> list[str]:
        """데이터 품질 요약 추출"""
        quality = []

        if "data_quality" in self.validation_results:
            dq = self.validation_results["data_quality"]
            quality.append(f"결측값: {'✓' if dq.get('missing_values') else '✗'}")
            quality.append(
                f"좌표 유효성: {'✓' if dq.get('coordinate_validity') else '✗'}"
            )
            quality.append(f"날짜 일관성: {'✓' if dq.get('date_consistency') else '✗'}")
            quality.append(f"값 범위: {'✓' if dq.get('value_ranges') else '✗'}")

        return quality

    def _extract_next_steps(self) -> list[str]:
        """다음 단계 추출"""
        next_steps = []

        # 검증 점수 기반
        if "metadata" in self.validation_results:
            score = self.validation_results["metadata"].get("validation_score", 0)
            if score < 50:
                next_steps.append("데이터 품질 개선 필요")
            elif score < 80:
                next_steps.append("일부 분석 재검토 권장")
            else:
                next_steps.append("현재 분석 결과 활용 가능")

        # 실패한 체크 기반
        failed = self.validation_results.get("metadata", {}).get("failed_checks", 0)
        if failed > 5:
            next_steps.append(f"{failed}개 검증 실패 항목 검토 필요")

        # 조기 경보 기반
        pred_file = Path(
            "results/spatial_analysis/predictions/kfactors_prediction_results.json"
        )
        if pred_file.exists():
            with open(pred_file) as f:
                pred_data = json.load(f)
                if pred_data.get("early_warnings"):
                    next_steps.append("조기 경보 지역 집중 모니터링")

        return next_steps

    def create_validation_dashboard(self) -> None:
        """검증 대시보드 생성"""
        print("\n=== 검증 대시보드 생성 중 ===")
        setup_korean_font()

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle("520 지역 분석 검증 대시보드", fontsize=16, fontweight="bold")

        # 1. 데이터 품질
        ax = axes[0, 0]
        self._plot_data_quality(ax)

        # 2. 분석 일관성
        ax = axes[0, 1]
        self._plot_analysis_consistency(ax)

        # 3. 공간 커버리지
        ax = axes[0, 2]
        self._plot_spatial_coverage(ax)

        # 4. 시간 커버리지
        ax = axes[1, 0]
        self._plot_temporal_coverage(ax)

        # 5. 통계적 유효성
        ax = axes[1, 1]
        self._plot_statistical_validity(ax)

        # 6. 종합 점수
        ax = axes[1, 2]
        self._plot_overall_score(ax)

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "validation_dashboard.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def _plot_data_quality(self, ax: plt.Axes) -> None:
        """데이터 품질 플롯"""
        if "data_quality" in self.validation_results:
            dq = self.validation_results["data_quality"]
            labels = list(dq.keys())
            values = [1 if v else 0 for v in dq.values()]

            colors = ["green" if v else "red" for v in values]
            ax.bar(labels, values, color=colors, alpha=0.7)

            ax.set_title("데이터 품질", fontweight="bold")
            ax.set_ylim(0, 1.2)
            ax.set_ylabel("통과 여부")
            ax.set_xticklabels(labels, rotation=45, ha="right")

            # 통과율 표시
            pass_rate = sum(values) / len(values) * 100 if values else 0
            ax.text(
                0.5,
                0.95,
                f"통과율: {pass_rate:.0f}%",
                transform=ax.transAxes,
                ha="center",
                fontsize=10,
                fontweight="bold",
            )

    def _plot_analysis_consistency(self, ax: plt.Axes) -> None:
        """분석 일관성 플롯"""
        if "analysis_consistency" in self.validation_results:
            ac = self.validation_results["analysis_consistency"]

            # 파이 차트
            passed = sum(1 for v in ac.values() if v)
            failed = len(ac) - passed

            if passed + failed > 0:
                sizes = [passed, failed]
                labels = ["통과", "실패"]
                colors = ["#90EE90", "#FFB6C1"]
                explode = (0.1, 0)

                ax.pie(
                    sizes,
                    explode=explode,
                    labels=labels,
                    colors=colors,
                    autopct="%1.0f%%",
                    shadow=True,
                    startangle=90,
                )
                ax.set_title("분석 일관성", fontweight="bold")

    def _plot_spatial_coverage(self, ax: plt.Axes) -> None:
        """공간 커버리지 플롯"""
        if "spatial_coverage" in self.validation_results:
            sc = self.validation_results["spatial_coverage"]

            metrics = []
            values = []
            for key, val in sc.items():
                if isinstance(val, int | float):
                    metrics.append(key)
                    values.append(val * 100 if val <= 1 else val)

            if metrics:
                bars = ax.barh(metrics, values, color="skyblue", alpha=0.7)
                ax.set_title("공간 커버리지", fontweight="bold")
                ax.set_xlabel("커버리지 (%)")

                # 값 표시
                for bar, val in zip(bars, values, strict=False):
                    ax.text(
                        bar.get_width() + 1,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:.1f}%",
                        va="center",
                    )

    def _plot_temporal_coverage(self, ax: plt.Axes) -> None:
        """시간 커버리지 플롯"""
        if "temporal_coverage" in self.validation_results:
            tc = self.validation_results["temporal_coverage"]

            # 텍스트 정보 표시
            info_text = []
            if tc.get("date_range"):
                info_text.append(f"기간: {tc['date_range']}")
            if "temporal_completeness" in tc:
                info_text.append(f"완전성: {tc['temporal_completeness']*100:.1f}%")
            if "seasonal_coverage" in tc:
                info_text.append(
                    f"계절 커버: {'✓' if tc['seasonal_coverage'] else '✗'}"
                )
            if "trend_validity" in tc:
                info_text.append(f"트렌드 유효: {'✓' if tc['trend_validity'] else '✗'}")

            ax.text(
                0.5,
                0.5,
                "\n".join(info_text),
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=11,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.5),
            )
            ax.set_title("시간 커버리지", fontweight="bold")
            ax.axis("off")

    def _plot_statistical_validity(self, ax: plt.Axes) -> None:
        """통계적 유효성 플롯"""
        if "statistical_validity" in self.validation_results:
            sv = self.validation_results["statistical_validity"]

            # 체크리스트 스타일 표시
            checks = []
            if "sample_size_adequate" in sv:
                checks.append(("샘플 크기", "✓" if sv["sample_size_adequate"] else "✗"))
            if "correlation_validity" in sv:
                checks.append(("상관관계", "✓" if sv["correlation_validity"] else "✗"))
            if "confidence_intervals" in sv:
                checks.append(("신뢰구간", "✓" if sv["confidence_intervals"] else "✗"))

            np.arange(len(checks))
            labels = [c[0] for c in checks]
            colors = ["green" if c[1] == "✓" else "red" for c in checks]
            markers = [c[1] for c in checks]

            for i, (label, marker, color) in enumerate(
                zip(labels, markers, colors, strict=False)
            ):
                ax.text(0.3, i, label, va="center", fontsize=10)
                ax.text(
                    0.7,
                    i,
                    marker,
                    va="center",
                    fontsize=14,
                    color=color,
                    fontweight="bold",
                )

            ax.set_title("통계적 유효성", fontweight="bold")
            ax.set_ylim(-0.5, len(checks) - 0.5)
            ax.set_xlim(0, 1)
            ax.axis("off")

    def _plot_overall_score(self, ax: plt.Axes) -> None:
        """종합 점수 플롯"""
        if "metadata" in self.validation_results:
            score = self.validation_results["metadata"].get("validation_score", 0)

            # 게이지 차트 스타일
            theta = np.linspace(0, np.pi, 100)
            r = 1

            # 배경
            ax.plot(np.cos(theta), np.sin(theta), "lightgray", linewidth=20, alpha=0.3)

            # 점수
            score_theta = np.pi * (1 - score / 100)
            ax.plot(
                [0, r * np.cos(score_theta)],
                [0, r * np.sin(score_theta)],
                "red",
                linewidth=3,
            )

            # 점수 표시
            ax.text(
                0,
                -0.3,
                f"{score:.0f}점",
                ha="center",
                fontsize=24,
                fontweight="bold",
                color="navy",
            )

            # 등급
            if score >= 90:
                grade = "우수"
                color = "green"
            elif score >= 70:
                grade = "양호"
                color = "blue"
            elif score >= 50:
                grade = "보통"
                color = "orange"
            else:
                grade = "개선필요"
                color = "red"

            ax.text(
                0,
                -0.5,
                grade,
                ha="center",
                fontsize=16,
                fontweight="bold",
                color=color,
            )

            ax.set_title("종합 검증 점수", fontweight="bold")
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-0.7, 1.2)
            ax.axis("off")

    def save_results(self) -> None:
        """결과 저장"""
        print("\n=== 검증 결과 저장 중 ===")

        # JSON 결과 - numpy bool 처리
        def convert_types(obj):
            """Convert numpy types to Python types for JSON serialization"""
            if isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_types(v) for v in obj]
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        with open(
            self.output_dir / "validation_results.json", "w", encoding="utf-8"
        ) as f:
            json.dump(
                convert_types(self.validation_results), f, ensure_ascii=False, indent=2
            )

        # Executive Summary
        summary = self.generate_executive_summary()
        with open(self.output_dir / "executive_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)

        # 상세 보고서
        detailed_report = self._generate_detailed_report()
        with open(
            self.output_dir / "detailed_validation_report.md", "w", encoding="utf-8"
        ) as f:
            f.write(detailed_report)

        print(f"  Executive Summary 저장: {self.output_dir}/executive_summary.md")
        print(f"  상세 보고서 저장: {self.output_dir}/detailed_validation_report.md")
        print(f"  검증 결과 JSON 저장: {self.output_dir}/validation_results.json")

    def _generate_detailed_report(self) -> str:
        """상세 보고서 생성"""
        report = []
        report.append("# 520 지역 분석 상세 검증 보고서\n")
        report.append(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 각 카테고리별 상세 결과
        categories = [
            ("데이터 품질", "data_quality"),
            ("분석 일관성", "analysis_consistency"),
            ("공간 커버리지", "spatial_coverage"),
            ("시간 커버리지", "temporal_coverage"),
            ("통계적 유효성", "statistical_validity"),
        ]

        for title, key in categories:
            report.append(f"\n## {title}\n")
            if key in self.validation_results:
                results = self.validation_results[key]
                for check, value in results.items():
                    if isinstance(value, bool):
                        status = "✓ 통과" if value else "✗ 실패"
                        report.append(f"- **{check}**: {status}\n")
                    elif isinstance(value, int | float):
                        report.append(f"- **{check}**: {value:.2f}\n")
                    elif isinstance(value, str):
                        report.append(f"- **{check}**: {value}\n")
                    elif isinstance(value, dict):
                        report.append(f"- **{check}**: \n")
                        for sub_key, sub_val in value.items():
                            report.append(f"  - {sub_key}: {sub_val}\n")

        # 메타데이터
        if "metadata" in self.validation_results:
            report.append("\n## 검증 메타데이터\n")
            meta = self.validation_results["metadata"]
            for key, value in meta.items():
                report.append(f"- **{key}**: {value}\n")

        return "".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 12: 자동화된 검증 및 종합 보고서 생성"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/spatial_analysis/validation",
        help="출력 디렉토리",
    )
    parser.add_argument(
        "--create-dashboard",
        action="store_true",
        default=True,
        help="검증 대시보드 생성",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Automated Validation and Reporting (Phase 12)")
    print("=" * 60)

    try:
        # 검증 실행
        reporter = ValidationReporter(output_dir=args.output_dir)

        # 모든 분석 검증
        validation_results = reporter.validate_all_analyses()

        # 대시보드 생성
        if args.create_dashboard:
            reporter.create_validation_dashboard()

        # 결과 저장
        reporter.save_results()

        # 요약 출력
        if "metadata" in validation_results:
            meta = validation_results["metadata"]
            print("\n=== 검증 요약 ===")
            print(f"  전체 체크: {meta.get('total_checks', 0)}개")
            print(f"  통과: {meta.get('passed_checks', 0)}개")
            print(f"  실패: {meta.get('failed_checks', 0)}개")
            print(f"  검증 점수: {meta.get('validation_score', 0)}점")

        print("\n" + "=" * 60)
        print(f"검증 완료! 결과: {args.output_dir}")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
