#!/usr/bin/env python3
"""
K-factors/D_final 공간 그리드 데이터 생성
520 지역 파이프의 K-factors와 D_final을 60m × 60m 그리드에 매핑
"""

import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import (
    DATA_DIR,
    FATIGUE_PIPE_LM_CSV,
    FATIGUE_SPLY_LS_CSV,
    RESULTS_DIR,
)
from src.common.shapefile_loader import ShapefileLoader

warnings.filterwarnings("ignore")

# 상수 정의
GRID_SIZE = 60  # 60m × 60m 그리드 (main21과 동일)
OUTPUT_DIR = RESULTS_DIR / "spatial_analysis"

# K-factors 컬럼 정의 (D_final 포함하여 통합 관리)
KFACTORS_COLUMNS = [
    "K_age",  # 파이프 연령 계수
    "K_soil",  # 토양 조건 계수
    "K_traffic",  # 교통 하중 계수
    "hoop_stress",  # 원주 응력
    "K_stress",  # 응력 계수
    "K_total",  # 총 위험도 계수
    "STD_DIP",  # 관경
    "0520_D_final",  # 피로 손상 (D_final)
]


class KFactorsDfinalGridGenerator:
    """K-factors/D_final 공간 그리드 생성기"""

    def __init__(self, grid_size: int = GRID_SIZE, limit: int = 1000):
        """
        초기화

        Args:
            grid_size: 그리드 크기 (미터)
            limit: 처리할 최대 파이프 수 (0=무제한)
        """
        self.grid_size = grid_size
        self.limit = limit
        self.pipe_data = None
        self.grid_gdf = None
        self.kfactors_grid = None

    def load_pipe_data(self) -> None:
        """파이프 데이터 및 K-factors/D_final 로드"""
        print("\n=== K-factors/D_final 데이터 로드 중 ===")

        # 1. ShapefileLoader를 사용하여 V_WTL 파일 로드
        loader = ShapefileLoader(DATA_DIR / "raw", verbose=True)

        print("V_WTL Shapefile 로드 중...")
        # 520 지역 파이프 데이터 로드
        gdf_pipe_lm = loader.load_pipe_shapefile("0520", "PIPE_LM")
        gdf_sply_ls = loader.load_pipe_shapefile("0520", "SPLY_LS")

        if gdf_pipe_lm is None or gdf_sply_ls is None:
            print("경고: V_WTL 파이프 shapefile을 로드할 수 없습니다.")
            print("더미 데이터로 진행합니다.")
            self._generate_dummy_data_simple()
            return

        # CRS가 이미 ShapefileLoader에 의해 설정됨 (EPSG:5179)
        # WGS84로 변환이 필요하면 나중에 처리

        # 데이터 크기 제한 (테스트용)
        if self.limit > 0:
            if len(gdf_pipe_lm) > self.limit:
                print(f"PIPE_LM 데이터 제한: {len(gdf_pipe_lm)}개 → {self.limit}개")
                gdf_pipe_lm = gdf_pipe_lm.iloc[: self.limit]
            if len(gdf_sply_ls) > self.limit:
                print(f"SPLY_LS 데이터 제한: {len(gdf_sply_ls)}개 → {self.limit}개")
                gdf_sply_ls = gdf_sply_ls.iloc[: self.limit]

        print(
            f"로드 완료 - PIPE_LM: {len(gdf_pipe_lm)}개, SPLY_LS: {len(gdf_sply_ls)}개"
        )

        # 2. K-factors/D_final CSV 데이터 로드
        pipe_lm_csv = FATIGUE_PIPE_LM_CSV
        sply_ls_csv = FATIGUE_SPLY_LS_CSV

        if not pipe_lm_csv.exists() or not sply_ls_csv.exists():
            print("경고: K-factors/D_final CSV 파일이 없습니다.")
            # 더미 데이터 생성 (테스트용)
            self._generate_dummy_kfactors(gdf_pipe_lm, gdf_sply_ls)
            return

        df_pipe_lm = pd.read_csv(pipe_lm_csv)
        df_sply_ls = pd.read_csv(sply_ls_csv)

        print(
            f"K-factors 데이터: PIPE_LM {len(df_pipe_lm)}개, SPLY_LS {len(df_sply_ls)}개"
        )

        # 3. FTR_IDN 기준으로 데이터 병합
        # V_WTL 파일은 FTR_IDN을 직접 가지고 있음
        pipe_lm_merged = self._merge_pipe_data(gdf_pipe_lm, df_pipe_lm, "PIPE_LM")
        sply_ls_merged = self._merge_pipe_data(gdf_sply_ls, df_sply_ls, "SPLY_LS")

        # 4. 통합 데이터셋 생성 (GeoDataFrame로 병합)
        # pipe_lm_merged와 sply_ls_merged가 모두 GeoDataFrame인지 확인
        if isinstance(pipe_lm_merged, gpd.GeoDataFrame) and isinstance(
            sply_ls_merged, gpd.GeoDataFrame
        ):
            self.pipe_data = pd.concat(
                [pipe_lm_merged, sply_ls_merged], ignore_index=True
            )
            # GeoDataFrame로 변환 (CRS 유지 - EPSG:5179)
            self.pipe_data = gpd.GeoDataFrame(self.pipe_data, crs=pipe_lm_merged.crs)
        else:
            print("경고: 병합된 데이터가 GeoDataFrame가 아닙니다.")
            return

        # EPSG:5179(TM) 유지 - 미터 단위로 작업하기 위해
        # WGS84로 변환하지 않음

        print(f"통합 파이프 데이터: {len(self.pipe_data)}개 세그먼트")

    def _merge_pipe_data(
        self, gdf_pipe: gpd.GeoDataFrame, df_kfactors: pd.DataFrame, pipe_type: str
    ) -> gpd.GeoDataFrame:
        """
        파이프 geometry와 K-factors/D_final 데이터 병합

        Args:
            gdf_pipe: V_WTL 파이프 geometry GeoDataFrame
            df_kfactors: K-factors/D_final DataFrame
            pipe_type: 파이프 타입 (PIPE_LM or SPLY_LS)

        Returns:
            병합된 GeoDataFrame
        """
        # V_WTL 파일은 FTR_IDN을 직접 가지고 있음
        # FTR_IDN이 없으면 ORIG_FTR을 사용 (호환성을 위해)
        id_column = "FTR_IDN" if "FTR_IDN" in gdf_pipe.columns else "ORIG_FTR"

        # V_WTL 파일은 이미 각 파이프별로 한 개의 레코드를 가지고 있을 가능성이 높음
        # 먼저 고유 ID 개수 확인
        unique_ids = gdf_pipe[id_column].unique()
        print(
            f"  {pipe_type}: {len(unique_ids)}개 고유 파이프, {len(gdf_pipe)}개 레코드"
        )

        # 만약 각 ID가 하나의 레코드만 가지고 있다면 그룹화 불필요
        if len(unique_ids) == len(gdf_pipe):
            # 그룹화 불필요 - 바로 사용
            gdf_grouped = gdf_pipe[[id_column, "geometry"]].copy()
            gdf_grouped = gdf_grouped.rename(columns={id_column: "FTR_IDN"})
            gdf_grouped["CNT_JNT"] = 0  # V_WTL 파일에는 CNT_JNT 없음
            gdf_grouped["pipe_type"] = pipe_type
        else:
            # 그룹화 필요 - pandas groupby 사용하여 최적화
            print(
                f"  그룹화 중... (평균 {len(gdf_pipe)/len(unique_ids):.1f}개 세그먼트/파이프)"
            )

            # 중심점 계산을 위해 x, y 좌표 추출
            gdf_pipe["centroid_x"] = gdf_pipe.geometry.centroid.x
            gdf_pipe["centroid_y"] = gdf_pipe.geometry.centroid.y

            # groupby로 평균 위치 계산
            grouped = (
                gdf_pipe.groupby(id_column)
                .agg({"centroid_x": "mean", "centroid_y": "mean"})
                .reset_index()
            )

            # GeoDataFrame 생성
            grouped["geometry"] = grouped.apply(
                lambda row: Point(row["centroid_x"], row["centroid_y"]), axis=1
            )
            grouped["FTR_IDN"] = grouped[id_column]
            grouped["CNT_JNT"] = 0
            grouped["pipe_type"] = pipe_type

            gdf_grouped = gpd.GeoDataFrame(
                grouped[["FTR_IDN", "geometry", "CNT_JNT", "pipe_type"]],
                crs=gdf_pipe.crs,
            )

        # K-factors/D_final 데이터 병합
        if "FTR_IDN" in df_kfactors.columns:
            # 필요한 컬럼만 선택
            cols_to_merge = ["FTR_IDN"] + [
                col for col in KFACTORS_COLUMNS if col in df_kfactors.columns
            ]
            df_kfactors_subset = df_kfactors[cols_to_merge]

            # 병합
            gdf_merged = gdf_grouped.merge(df_kfactors_subset, on="FTR_IDN", how="left")
        else:
            gdf_merged = gdf_grouped

        return gdf_merged

    def _generate_dummy_kfactors(
        self, gdf_pipe_lm: gpd.GeoDataFrame, gdf_sply_ls: gpd.GeoDataFrame
    ) -> None:
        """
        더미 K-factors/D_final 데이터 생성 (실제 데이터가 없을 때)

        Args:
            gdf_pipe_lm: V_WTL_PIPE_LM GeoDataFrame
            gdf_sply_ls: V_WTL_SPLY_LS GeoDataFrame
        """
        print("\n더미 K-factors/D_final 데이터 생성 중...")

        np.random.seed(42)

        # V_WTL 파일 구조에 맞춰 처리
        id_column_lm = "FTR_IDN" if "FTR_IDN" in gdf_pipe_lm.columns else "ORIG_FTR"
        id_column_ls = "FTR_IDN" if "FTR_IDN" in gdf_sply_ls.columns else "ORIG_FTR"

        # PIPE_LM 더미 데이터
        pipe_lm_data = []
        for ftr_id in gdf_pipe_lm[id_column_lm].unique():
            segments = gdf_pipe_lm[gdf_pipe_lm[id_column_lm] == ftr_id]
            centroids = segments.geometry.centroid
            avg_point = Point(centroids.x.mean(), centroids.y.mean())

            pipe_lm_data.append(
                {
                    "FTR_IDN": ftr_id,
                    "geometry": avg_point,
                    "CNT_JNT": 0,  # V_WTL 파일에는 CNT_JNT 없음
                    "pipe_type": "PIPE_LM",
                    "K_age": np.random.uniform(0.8, 1.5),
                    "K_soil": np.random.uniform(0.9, 1.3),
                    "K_traffic": np.random.uniform(0.7, 1.4),
                    "hoop_stress": np.random.uniform(50, 150),
                    "K_stress": np.random.uniform(0.8, 1.2),
                    "K_total": np.random.uniform(0.5, 2.0),
                    "STD_DIP": np.random.choice([100, 150, 200, 250, 300]),
                    "0520_D_final": np.random.uniform(0.001, 0.1),
                }
            )

        # SPLY_LS 더미 데이터
        sply_ls_data = []
        for ftr_id in gdf_sply_ls[id_column_ls].unique():
            segments = gdf_sply_ls[gdf_sply_ls[id_column_ls] == ftr_id]
            centroids = segments.geometry.centroid
            avg_point = Point(centroids.x.mean(), centroids.y.mean())

            sply_ls_data.append(
                {
                    "FTR_IDN": ftr_id,
                    "geometry": avg_point,
                    "CNT_JNT": 0,  # V_WTL 파일에는 CNT_JNT 없음
                    "pipe_type": "SPLY_LS",
                    "K_age": np.random.uniform(0.8, 1.5),
                    "K_soil": np.random.uniform(0.9, 1.3),
                    "K_traffic": np.random.uniform(0.7, 1.4),
                    "hoop_stress": np.random.uniform(50, 150),
                    "K_stress": np.random.uniform(0.8, 1.2),
                    "K_total": np.random.uniform(0.5, 2.0),
                    "STD_DIP": np.random.choice([100, 150, 200, 250, 300]),
                    "0520_D_final": np.random.uniform(0.001, 0.1),
                }
            )

        # GeoDataFrame 생성
        self.pipe_data = gpd.GeoDataFrame(
            pipe_lm_data + sply_ls_data, crs=gdf_pipe_lm.crs  # EPSG:5179 유지
        )

        print(f"더미 데이터 생성 완료: {len(self.pipe_data)}개 파이프")

    def _generate_dummy_data_simple(self) -> None:
        """간단한 더미 데이터 생성 (에러 시 사용)"""
        print("\n간단한 더미 K-factors/D_final 데이터 생성 중...")

        np.random.seed(42)
        n_points = 100  # 테스트용 간단한 데이터

        # 520 지역 좌표 범위 (EPSG:5179 미터 단위)
        x = np.random.uniform(344000, 348000, n_points)
        y = np.random.uniform(366000, 369000, n_points)

        data = []
        for i in range(n_points):
            data.append(
                {
                    "FTR_IDN": f"PIPE_{i:04d}",
                    "geometry": Point(x[i], y[i]),
                    "CNT_JNT": np.random.randint(1, 10),
                    "pipe_type": np.random.choice(["PIPE_LM", "SPLY_LS"]),
                    "K_age": np.random.uniform(0.8, 1.5),
                    "K_soil": np.random.uniform(0.9, 1.3),
                    "K_traffic": np.random.uniform(0.7, 1.4),
                    "hoop_stress": np.random.uniform(50, 150),
                    "K_stress": np.random.uniform(0.8, 1.2),
                    "K_total": np.random.uniform(0.5, 2.0),
                    "STD_DIP": np.random.choice([100, 150, 200, 250, 300]),
                    "0520_D_final": np.random.uniform(0.001, 0.1),
                }
            )

        self.pipe_data = gpd.GeoDataFrame(data, crs="EPSG:5179")
        print(f"간단한 더미 데이터 생성 완료: {len(self.pipe_data)}개 파이프")

    def create_spatial_grid(self) -> None:
        """60m × 60m 공간 그리드 생성"""
        print(f"\n=== {self.grid_size}m × {self.grid_size}m 그리드 생성 중 ===")

        if self.pipe_data is None or len(self.pipe_data) == 0:
            print("경고: 파이프 데이터가 없습니다.")
            return

        # 바운딩 박스 계산
        bounds = self.pipe_data.total_bounds  # minx, miny, maxx, maxy

        # 그리드 범위 설정 (여유 추가)
        buffer = self.grid_size
        minx = bounds[0] - buffer
        miny = bounds[1] - buffer
        maxx = bounds[2] + buffer
        maxy = bounds[3] + buffer

        # EPSG:5179는 미터 단위이므로 바로 사용 가능
        x_coords = np.arange(minx, maxx, self.grid_size)
        y_coords = np.arange(miny, maxy, self.grid_size)

        print(f"  영역: ({minx:.0f}, {miny:.0f}) ~ ({maxx:.0f}, {maxy:.0f})")
        print(
            f"  그리드 크기: {len(x_coords)-1} × {len(y_coords)-1} = {(len(x_coords)-1)*(len(y_coords)-1)}개 예상"
        )

        # 너무 많은 그리드 생성 방지
        if (len(x_coords) - 1) * (len(y_coords) - 1) > 100000:
            print("경고: 그리드가 너무 많습니다. 그리드 크기를 늘려주세요.")
            return

        # 벡터화된 방식으로 그리드 생성
        from itertools import product

        grid_cells = []

        for i, j in product(range(len(x_coords) - 1), range(len(y_coords) - 1)):
            x = x_coords[i]
            y = y_coords[j]
            cell = Polygon(
                [
                    (x, y),
                    (x_coords[i + 1], y),
                    (x_coords[i + 1], y_coords[j + 1]),
                    (x, y_coords[j + 1]),
                ]
            )

            grid_cells.append(
                {"geometry": cell, "grid_x": x, "grid_y": y, "cell_id": f"{i}_{j}"}
            )

        # GeoDataFrame 생성 (EPSG:5179 유지)
        self.grid_gdf = gpd.GeoDataFrame(grid_cells, crs=self.pipe_data.crs)
        print(f"생성된 그리드 셀: {len(self.grid_gdf)}개")

    def aggregate_kfactors_to_grid(self) -> None:
        """K-factors/D_final을 그리드 셀별로 집계"""
        print("\n=== K-factors/D_final 그리드 집계 중 ===")

        if self.grid_gdf is None or self.pipe_data is None:
            print("경고: 그리드 또는 파이프 데이터가 없습니다.")
            return

        # 공간 조인 (각 파이프가 어느 그리드에 속하는지)
        pipes_in_grid = gpd.sjoin(
            self.pipe_data, self.grid_gdf, how="inner", predicate="within"
        )

        # 그리드별 집계
        aggregations = {
            "CNT_JNT": ["mean", "max", "sum"],
            "pipe_type": "count",  # 파이프 개수
        }

        # K-factors/D_final 집계 추가
        for col in KFACTORS_COLUMNS:
            if col in pipes_in_grid.columns:
                aggregations[col] = ["mean", "max", "min", "std"]

        # 그룹화 및 집계
        grid_stats = pipes_in_grid.groupby("cell_id").agg(aggregations)

        # 컬럼명 평탄화
        grid_stats.columns = [
            "_".join(col).strip() for col in grid_stats.columns.values
        ]
        grid_stats = grid_stats.reset_index()

        # 파이프 개수 컬럼명 변경
        grid_stats.rename(columns={"pipe_type_count": "pipe_count"}, inplace=True)

        # 그리드 GeoDataFrame와 병합
        self.kfactors_grid = self.grid_gdf.merge(grid_stats, on="cell_id", how="left")

        # NaN 값을 0으로 채우기
        numeric_cols = self.kfactors_grid.select_dtypes(include=[np.number]).columns
        self.kfactors_grid[numeric_cols] = self.kfactors_grid[numeric_cols].fillna(0)

        # K-factors/D_final 통합 점수 계산
        self._calculate_composite_score()

        print(f"K-factors/D_final 집계 완료: {len(self.kfactors_grid)}개 그리드 셀")
        print(f"파이프가 있는 셀: {(self.kfactors_grid['pipe_count'] > 0).sum()}개")

    def _calculate_composite_score(self) -> None:
        """K-factors/D_final 통합 점수 계산"""
        print("\n=== K-factors/D_final 통합 점수 계산 중 ===")

        # 통합 점수 = K_total × D_final (평균값 기준)
        if (
            "K_total_mean" in self.kfactors_grid.columns
            and "0520_D_final_mean" in self.kfactors_grid.columns
        ):
            self.kfactors_grid["kfactors_dfinal_score"] = (
                self.kfactors_grid["K_total_mean"]
                * self.kfactors_grid["0520_D_final_mean"]
            )
        else:
            # 더미 점수 (데이터가 없을 때)
            self.kfactors_grid["kfactors_dfinal_score"] = np.random.uniform(
                0, 0.1, len(self.kfactors_grid)
            )

        # 위험도 카테고리 분류
        score = self.kfactors_grid["kfactors_dfinal_score"]

        # 파이프가 있는 셀만 필터링하여 quantile 계산
        score_with_pipes = score[self.kfactors_grid["pipe_count"] > 0]

        if len(score_with_pipes) > 0:
            # qcut 사용하여 동일한 개수로 분할 (중복 허용)
            try:
                self.kfactors_grid["risk_category"] = pd.qcut(
                    score,
                    q=4,
                    labels=["Low", "Medium", "High", "Critical"],
                    duplicates="drop",  # 중복된 bin edge 제거
                )
            except ValueError:
                # qcut 실패 시 간단한 분류
                print("  경고: qcut 실패, 대체 분류 방법 사용")
                self.kfactors_grid["risk_category"] = pd.cut(
                    score,
                    bins=[-np.inf, 0.001, 0.01, 0.05, np.inf],
                    labels=["Low", "Medium", "High", "Critical"],
                )
        else:
            # 파이프가 없으면 모두 Low로 설정
            self.kfactors_grid["risk_category"] = "Low"

        print("통합 점수 계산 완료")

    def save_results(self) -> None:
        """결과 저장"""
        print("\n=== 결과 저장 중 ===")

        output_dir = OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # CSV 저장
        csv_path = output_dir / "0520_kfactors_dfinal_grid.csv"

        # geometry 컬럼 제외하고 저장
        df_to_save = self.kfactors_grid.drop(columns=["geometry"])
        df_to_save.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"CSV 저장: {csv_path}")

        # GeoJSON 저장 (GIS 통합용)
        geojson_path = output_dir / "0520_kfactors_dfinal_grid.geojson"
        self.kfactors_grid.to_file(geojson_path, driver="GeoJSON")
        print(f"GeoJSON 저장: {geojson_path}")

        # 요약 통계 저장
        summary_path = output_dir / "0520_kfactors_dfinal_summary.txt"
        self._save_summary(summary_path)
        print(f"요약 저장: {summary_path}")

    def _save_summary(self, path: Path) -> None:
        """요약 통계 저장"""
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("K-factors/D_final 공간 그리드 집계 요약\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"생성 일시: {pd.Timestamp.now()}\n")
            f.write(f"그리드 크기: {self.grid_size}m × {self.grid_size}m\n")
            f.write(f"전체 그리드 셀: {len(self.kfactors_grid)}개\n")
            f.write(
                f"파이프가 있는 셀: {(self.kfactors_grid['pipe_count'] > 0).sum()}개\n\n"
            )

            # K-factors/D_final 통계
            if "kfactors_dfinal_score" in self.kfactors_grid.columns:
                score = self.kfactors_grid[self.kfactors_grid["pipe_count"] > 0][
                    "kfactors_dfinal_score"
                ]

                f.write("-" * 70 + "\n")
                f.write("K-factors/D_final 통합 점수 통계\n")
                f.write("-" * 70 + "\n")
                f.write(f"최소값: {score.min():.6f}\n")
                f.write(f"25%: {score.quantile(0.25):.6f}\n")
                f.write(f"중앙값: {score.median():.6f}\n")
                f.write(f"평균: {score.mean():.6f}\n")
                f.write(f"75%: {score.quantile(0.75):.6f}\n")
                f.write(f"최대값: {score.max():.6f}\n")
                f.write(f"표준편차: {score.std():.6f}\n\n")

            # 위험도 카테고리별 분포
            if "risk_category" in self.kfactors_grid.columns:
                risk_dist = self.kfactors_grid[self.kfactors_grid["pipe_count"] > 0][
                    "risk_category"
                ].value_counts()

                f.write("-" * 70 + "\n")
                f.write("위험도 카테고리 분포\n")
                f.write("-" * 70 + "\n")
                for category in ["Low", "Medium", "High", "Critical"]:
                    if category in risk_dist.index:
                        count = risk_dist[category]
                        pct = count / risk_dist.sum() * 100
                        f.write(f"{category}: {count}개 ({pct:.1f}%)\n")

            # 개별 K-factors 통계
            f.write("\n" + "-" * 70 + "\n")
            f.write("개별 K-factors 평균값 통계\n")
            f.write("-" * 70 + "\n")

            for col in KFACTORS_COLUMNS:
                mean_col = f"{col}_mean"
                if mean_col in self.kfactors_grid.columns:
                    values = self.kfactors_grid[self.kfactors_grid["pipe_count"] > 0][
                        mean_col
                    ]
                    f.write(f"{col}:\n")
                    f.write(f"  평균: {values.mean():.6f}\n")
                    f.write(f"  표준편차: {values.std():.6f}\n")
                    f.write(f"  범위: {values.min():.6f} ~ {values.max():.6f}\n\n")

            f.write("=" * 70 + "\n")
            f.write("분석 완료\n")
            f.write("=" * 70 + "\n")

    def run(self) -> None:
        """전체 처리 실행"""
        print("\n" + "=" * 70)
        print("K-factors/D_final 공간 그리드 데이터 생성")
        print("=" * 70)

        # 1. 데이터 로드
        self.load_pipe_data()

        if self.pipe_data is None or len(self.pipe_data) == 0:
            print("\n오류: 파이프 데이터를 로드할 수 없습니다.")
            return

        # 2. 그리드 생성
        self.create_spatial_grid()

        # 3. K-factors/D_final 집계
        self.aggregate_kfactors_to_grid()

        # 4. 결과 저장
        self.save_results()

        print("\n" + "=" * 70)
        print("처리 완료!")
        print("=" * 70)


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="K-factors/D_final 공간 그리드 데이터 생성 - 520 지역 파이프 위험도 분석"
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=GRID_SIZE,
        help=f"그리드 크기 (미터, 기본값: {GRID_SIZE})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(OUTPUT_DIR),
        help=f"출력 디렉토리 (기본값: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="처리할 최대 파이프 수 (기본값: 1000, 0=무제한)",
    )

    args = parser.parse_args()

    # argparse가 --help 처리 후 종료하므로 여기서부터는 실행 코드
    generator = KFactorsDfinalGridGenerator(grid_size=args.grid_size, limit=args.limit)
    generator.run()


if __name__ == "__main__":
    main()
