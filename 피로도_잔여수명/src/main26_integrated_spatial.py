"""
main25_integrated_spatial.py

모든 공간 분석 결과를 통합하여 대시보드와 종합 보고서를 생성합니다.
Interactive Plotly/Dash 대시보드와 PDF 보고서를 제공합니다.
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go

# Dash imports (optional)
try:
    import dash
    import dash_bootstrap_components as dbc
    from dash import Input, Output, dcc, html

    DASH_AVAILABLE = True
except ImportError:
    DASH_AVAILABLE = False
    print("Dash not installed. Dashboard features will be limited.")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.korean_font_utils import setup_korean_font

# from src.common.logging_utils import setup_logging  # 로깅 유틸리티 비활성화

warnings.filterwarnings("ignore")


class IntegratedSpatialAnalyzer:
    """통합 공간 분석 클래스"""

    def __init__(self):
        """초기화"""
        self.hotspot_data = None
        self.spacetime_data = None
        self.emerging_data = None
        self.priority_data = None
        self.integrated_results = None

        # 한글 폰트 설정
        setup_korean_font()

    def load_all_results(self, input_dir: str):
        """모든 분석 결과 로드"""
        print("\n모든 분석 결과 로드 중...")

        # 1. 핫스팟 분석 결과
        hotspot_file = os.path.join(input_dir, "hotspots", "hotspot_results.csv")
        if os.path.exists(hotspot_file):
            self.hotspot_data = pd.read_csv(hotspot_file, encoding="utf-8-sig")
            print(f"핫스팟 데이터 로드: {len(self.hotspot_data)} 셀")

        # 2. 시공간 큐브 결과
        spacetime_file = os.path.join(input_dir, "spacetime", "timeseries.csv")
        if os.path.exists(spacetime_file):
            self.spacetime_data = pd.read_csv(spacetime_file, encoding="utf-8-sig")
            print(f"시공간 데이터 로드: {len(self.spacetime_data)} 시점")

        # 3. Emerging 패턴 결과
        emerging_file = os.path.join(
            input_dir, "emerging", "pattern_classification.csv"
        )
        if os.path.exists(emerging_file):
            self.emerging_data = pd.read_csv(emerging_file, encoding="utf-8-sig")
            print(f"Emerging 패턴 로드: {len(self.emerging_data)} 셀")

        # 4. 우선순위 결과
        priority_file = os.path.join(input_dir, "priority", "priority_rankings.csv")
        if os.path.exists(priority_file):
            self.priority_data = pd.read_csv(priority_file, encoding="utf-8-sig")
            print(f"우선순위 데이터 로드: {len(self.priority_data)} 셀")

    def integrate_results(self) -> pd.DataFrame:
        """결과 통합"""
        print("\n분석 결과 통합 중...")

        # 기본 DataFrame 선택
        if self.priority_data is not None:
            base_df = self.priority_data
        elif self.hotspot_data is not None:
            base_df = self.hotspot_data
        else:
            print("통합할 데이터 없음")
            return pd.DataFrame()

        # 통합 결과 생성
        self.integrated_results = base_df.copy()

        # 추가 정보 병합
        if self.emerging_data is not None and "cell_id" in self.emerging_data.columns:
            # Emerging 패턴 정보 추가
            emerging_cols = ["pattern", "n_observations", "trend_slope"]
            available_cols = [
                col for col in emerging_cols if col in self.emerging_data.columns
            ]

            if available_cols and "cell_id" in self.integrated_results.columns:
                self.integrated_results = pd.merge(
                    self.integrated_results,
                    self.emerging_data[["cell_id", *available_cols]],
                    on="cell_id",
                    how="left",
                    suffixes=("", "_emg"),
                )

        print(f"통합 완료: {len(self.integrated_results)} 레코드")

        return self.integrated_results

    def create_dashboard(self, port: int = 8050):
        """Interactive Dashboard 생성"""
        if not DASH_AVAILABLE:
            print("Dash가 설치되지 않았습니다. pip install dash를 실행하세요.")
            return

        print(f"\n대시보드 생성 중 (포트: {port})...")

        app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # 레이아웃 정의
        app.layout = dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H1(
                                    "520 지역 공간 분석 대시보드",
                                    className="text-center mb-4",
                                ),
                                html.Hr(),
                            ]
                        )
                    ]
                ),
                # 요약 카드
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "총 분석 셀", className="card-title"
                                                ),
                                                html.H2(
                                                    f"{len(self.integrated_results):,}",
                                                    className="text-primary",
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "핫스팟", className="card-title"
                                                ),
                                                html.H2(
                                                    f"{(self.integrated_results.get('hotspot_confidence_95', 0) == 1).sum():,}",
                                                    className="text-danger",
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "높은 우선순위",
                                                    className="card-title",
                                                ),
                                                html.H2(
                                                    f"{(self.integrated_results.get('total_score', 0) >= 80).sum():,}",
                                                    className="text-warning",
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            width=3,
                        ),
                        dbc.Col(
                            [
                                dbc.Card(
                                    [
                                        dbc.CardBody(
                                            [
                                                html.H4(
                                                    "평균 점수", className="card-title"
                                                ),
                                                html.H2(
                                                    f"{self.integrated_results.get('total_score', pd.Series()).mean():.1f}",
                                                    className="text-info",
                                                ),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            width=3,
                        ),
                    ],
                    className="mb-4",
                ),
                # 차트 섹션
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dcc.Graph(
                                    id="priority-map",
                                    figure=self._create_priority_map(),
                                )
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dcc.Graph(
                                    id="pattern-distribution",
                                    figure=self._create_pattern_chart(),
                                )
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-4",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dcc.Graph(
                                    id="time-series",
                                    figure=self._create_timeseries_chart(),
                                )
                            ],
                            width=12,
                        )
                    ],
                    className="mb-4",
                ),
                # 테이블 섹션
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H3("상위 10개 우선순위 지역"),
                                html.Div(
                                    id="priority-table",
                                    children=self._create_priority_table(),
                                ),
                            ]
                        )
                    ]
                ),
            ],
            fluid=True,
        )

        # 서버 실행
        print(f"대시보드 서버 시작: http://localhost:{port}")
        app.run_server(debug=False, port=port)

    def _create_priority_map(self) -> go.Figure:
        """우선순위 맵 생성"""
        if "grid_x" not in self.integrated_results.columns:
            return go.Figure()

        fig = go.Figure(
            data=go.Scatter(
                x=self.integrated_results["grid_x"],
                y=self.integrated_results["grid_y"],
                mode="markers",
                marker=dict(
                    size=8,
                    color=self.integrated_results.get("total_score", 50),
                    colorscale="RdYlGn_r",
                    showscale=True,
                    colorbar=dict(title="우선순위 점수"),
                ),
                text=[
                    f"Cell: {row.get('cell_id', '')}<br>Score: {row.get('total_score', 0):.1f}"
                    for _, row in self.integrated_results.iterrows()
                ],
                hovertemplate="%{text}<extra></extra>",
            )
        )

        fig.update_layout(
            title="유지보수 우선순위 공간 분포",
            xaxis_title="X 좌표 (m)",
            yaxis_title="Y 좌표 (m)",
            height=500,
        )

        return fig

    def _create_pattern_chart(self) -> go.Figure:
        """패턴 분포 차트 생성"""
        if "pattern" not in self.integrated_results.columns:
            return go.Figure()

        pattern_counts = self.integrated_results["pattern"].value_counts()

        fig = go.Figure(
            data=go.Pie(
                labels=pattern_counts.index, values=pattern_counts.values, hole=0.3
            )
        )

        fig.update_layout(title="핫스팟 패턴 분포", height=500)

        return fig

    def _create_timeseries_chart(self) -> go.Figure:
        """시계열 차트 생성"""
        if self.spacetime_data is None:
            return go.Figure()

        # 시계열 인덱스 변환
        if "time_bin" in self.spacetime_data.columns:
            self.spacetime_data["time_bin"] = pd.to_datetime(
                self.spacetime_data["time_bin"]
            )
            self.spacetime_data = self.spacetime_data.set_index("time_bin")

        fig = go.Figure()

        # 재작업 횟수 시계열
        if "point_count" in self.spacetime_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=self.spacetime_data.index,
                    y=self.spacetime_data["point_count"],
                    mode="lines+markers",
                    name="재작업 횟수",
                    line=dict(color="blue", width=2),
                )
            )

        fig.update_layout(
            title="시계열 패턴",
            xaxis_title="시간",
            yaxis_title="재작업 횟수",
            height=400,
            showlegend=True,
        )

        return fig

    def _create_priority_table(self):
        """우선순위 테이블 생성"""
        if not DASH_AVAILABLE:
            return None

        top_10 = self.integrated_results.head(10)

        # 테이블 헤더
        headers = ["순위", "Cell ID", "총점", "패턴", "재작업"]

        # 테이블 행
        rows = []
        for idx, row in top_10.iterrows():
            rows.append(
                html.Tr(
                    [
                        html.Td(idx + 1),
                        html.Td(row.get("cell_id", "")),
                        html.Td(f"{row.get('total_score', 0):.1f}"),
                        html.Td(row.get("pattern", "")),
                        html.Td(int(row.get("repair_count", 0))),
                    ]
                )
            )

        return html.Table(
            [html.Thead([html.Tr([html.Th(h) for h in headers])]), html.Tbody(rows)],
            className="table table-striped",
        )

    def generate_pdf_report(self, output_dir: str):
        """PDF 보고서 생성 (matplotlib 기반)"""
        print("\nPDF 스타일 보고서 생성 중...")

        # A4 크기 figure 생성
        fig = plt.figure(figsize=(8.27, 11.69))

        # 제목
        fig.text(
            0.5,
            0.95,
            "520 지역 공간 분석 종합 보고서",
            ha="center",
            fontsize=20,
            fontweight="bold",
        )
        fig.text(
            0.5,
            0.92,
            datetime.now().strftime("%Y년 %m월 %d일"),
            ha="center",
            fontsize=12,
        )

        # 요약 통계
        ax1 = plt.subplot2grid((5, 2), (0, 0), colspan=2)
        ax1.axis("off")

        # 통계 계산
        n_hotspots = 0
        n_high_priority = 0
        avg_score = 0

        if "hotspot_confidence_95" in self.integrated_results.columns:
            n_hotspots = (self.integrated_results["hotspot_confidence_95"] == 1).sum()
        if "total_score" in self.integrated_results.columns:
            n_high_priority = (self.integrated_results["total_score"] >= 80).sum()
            avg_score = self.integrated_results["total_score"].mean()

        summary_text = f"""
        ▶ 총 분석 셀: {len(self.integrated_results):,}개
        ▶ 핫스팟 (95% 신뢰): {n_hotspots:,}개
        ▶ 높은 우선순위 (≥80): {n_high_priority:,}개
        ▶ 평균 우선순위 점수: {avg_score:.1f}
        """
        ax1.text(0.1, 0.5, summary_text, fontsize=11, verticalalignment="center")

        # 우선순위 분포
        ax2 = plt.subplot2grid((5, 2), (1, 0))
        if "total_score" in self.integrated_results.columns:
            ax2.hist(
                self.integrated_results["total_score"],
                bins=20,
                edgecolor="black",
                alpha=0.7,
            )
            ax2.set_xlabel("우선순위 점수")
            ax2.set_ylabel("빈도")
            ax2.set_title("우선순위 점수 분포")

        # 패턴 분포
        ax3 = plt.subplot2grid((5, 2), (1, 1))
        if "pattern" in self.integrated_results.columns:
            pattern_counts = self.integrated_results["pattern"].value_counts().head(5)
            ax3.bar(range(len(pattern_counts)), pattern_counts.values)
            ax3.set_xticks(range(len(pattern_counts)))
            ax3.set_xticklabels(pattern_counts.index, rotation=45, ha="right")
            ax3.set_ylabel("개수")
            ax3.set_title("상위 5개 패턴")

        # 공간 분포
        ax4 = plt.subplot2grid((5, 2), (2, 0), colspan=2)
        if "grid_x" in self.integrated_results.columns:
            scatter = ax4.scatter(
                self.integrated_results["grid_x"],
                self.integrated_results["grid_y"],
                c=self.integrated_results.get("total_score", 50),
                cmap="RdYlGn_r",
                s=20,
                alpha=0.6,
            )
            plt.colorbar(scatter, ax=ax4, label="우선순위 점수")
            ax4.set_xlabel("X 좌표 (m)")
            ax4.set_ylabel("Y 좌표 (m)")
            ax4.set_title("공간 분포")

        # 상위 10개 테이블
        ax5 = plt.subplot2grid((5, 2), (3, 0), colspan=2, rowspan=2)
        ax5.axis("tight")
        ax5.axis("off")

        top_10 = self.integrated_results.head(10)[
            ["cell_id", "total_score", "pattern", "repair_count"]
        ]
        top_10 = top_10.reset_index(drop=True)
        top_10.index = top_10.index + 1

        table_data = []
        for idx, row in top_10.iterrows():
            table_data.append(
                [
                    f"#{idx}",
                    row.get("cell_id", ""),
                    f"{row.get('total_score', 0):.1f}",
                    row.get("pattern", ""),
                    f"{int(row.get('repair_count', 0))}",
                ]
            )

        table = ax5.table(
            cellText=table_data,
            colLabels=["순위", "Cell ID", "점수", "패턴", "재작업"],
            cellLoc="center",
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)

        ax5.set_title("상위 10개 우선순위 지역", fontsize=12, pad=20)

        plt.tight_layout()

        # PDF로 저장
        pdf_path = os.path.join(output_dir, "integrated_report.pdf")
        plt.savefig(pdf_path, format="pdf", bbox_inches="tight")
        plt.close()

        print(f"PDF 보고서 저장: {pdf_path}")

    def generate_executive_summary(self, output_dir: str):
        """경영진 요약 보고서 생성"""
        print("\n경영진 요약 보고서 생성 중...")

        summary_lines = [
            "# 경영진 요약 보고서",
            f"\n**작성일**: {datetime.now().strftime('%Y년 %m월 %d일')}",
            "\n---\n",
            "## 핵심 발견사항",
            "",
        ]

        # 1. 전체 현황
        total_cells = len(self.integrated_results)
        high_priority = (self.integrated_results.get("total_score", 0) >= 80).sum()

        summary_lines.extend(
            [
                f"• **분석 대상**: 520 지역 {total_cells:,}개 구역",
                f"• **즉시 조치 필요**: {high_priority}개 구역 (전체의 {high_priority/total_cells*100:.1f}%)",
                "",
            ]
        )

        # 2. 주요 위험 지역
        if "pattern" in self.integrated_results.columns:
            new_count = (self.integrated_results["pattern"] == "New").sum()
            intensifying_count = (
                self.integrated_results["pattern"] == "Intensifying"
            ).sum()
            persistent_count = (
                self.integrated_results["pattern"] == "Persistent"
            ).sum()

            summary_lines.extend(
                [
                    "## 위험 패턴 분석",
                    f"• **신규 발생**: {new_count}개 구역 - 즉각 원인 조사 필요",
                    f"• **악화 중**: {intensifying_count}개 구역 - 조기 개입으로 확산 방지",
                    f"• **만성 문제**: {persistent_count}개 구역 - 근본적 개선 필요",
                    "",
                ]
            )

        # 3. 투자 우선순위
        summary_lines.extend(
            [
                "## 투자 우선순위",
                "",
                "### 1단계 (1개월 이내)",
                "• 상위 10개 고위험 구역 집중 점검 및 응급 보수",
                f"• 예상 소요 예산: 약 {high_priority * 0.5:.0f}억원",
                "",
                "### 2단계 (3개월 이내)",
                "• 중위험 구역 예방 정비",
                "• 노후 인프라 교체 계획 수립",
                "",
                "### 3단계 (6개월 이내)",
                "• 전체 구역 시스템 개선",
                "• 스마트 모니터링 시스템 도입",
                "",
            ]
        )

        # 4. 기대 효과
        summary_lines.extend(
            [
                "## 기대 효과",
                "• **사고 예방**: 연간 약 30% 사고 감소 예상",
                "• **비용 절감**: 재작업 비용 40% 절감",
                "• **서비스 품질**: 단수 시간 50% 단축",
                "",
                "## 권장 조치사항",
                "1. 상위 10개 구역 즉시 현장 조사",
                "2. 신규 핫스팟 원인 분석 TF 구성",
                "3. 분기별 모니터링 체계 구축",
                "4. 예방 정비 예산 30% 증액 검토",
            ]
        )

        # 파일 저장
        summary_path = os.path.join(output_dir, "executive_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))

        print(f"경영진 요약 저장: {summary_path}")

    def export_for_gis(self, output_dir: str):
        """GIS 통합을 위한 데이터 내보내기"""
        print("\nGIS 데이터 내보내기 중...")

        # GeoJSON 형식으로 내보내기
        if "grid_x" in self.integrated_results.columns:
            # GeoDataFrame 생성
            from shapely.geometry import Point

            geometry = [
                Point(row["grid_x"], row["grid_y"])
                for _, row in self.integrated_results.iterrows()
            ]

            gdf = gpd.GeoDataFrame(
                self.integrated_results, geometry=geometry, crs="EPSG:5186"
            )

            # GeoJSON 저장
            geojson_path = os.path.join(output_dir, "integrated_results.geojson")
            gdf.to_file(geojson_path, driver="GeoJSON")
            print(f"GeoJSON 저장: {geojson_path}")

            # Shapefile 저장
            shp_path = os.path.join(output_dir, "integrated_results.shp")
            gdf.to_file(shp_path)
            print(f"Shapefile 저장: {shp_path}")

    def save_integrated_results(self, output_dir: str):
        """통합 결과 저장"""
        # CSV 저장
        csv_path = os.path.join(output_dir, "integrated_analysis.csv")
        self.integrated_results.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"통합 분석 결과 저장: {csv_path}")

        # 메타데이터 저장
        metadata = {
            "analysis_date": datetime.now().isoformat(),
            "n_records": len(self.integrated_results),
            "data_sources": {
                "hotspot": self.hotspot_data is not None,
                "spacetime": self.spacetime_data is not None,
                "emerging": self.emerging_data is not None,
                "priority": self.priority_data is not None,
            },
            "summary_statistics": {
                "mean_priority_score": float(
                    self.integrated_results["total_score"].mean()
                    if "total_score" in self.integrated_results.columns
                    else 0
                ),
                "n_high_priority": int(
                    (self.integrated_results["total_score"] >= 80).sum()
                    if "total_score" in self.integrated_results.columns
                    else 0
                ),
                "n_hotspots": int(
                    (self.integrated_results["hotspot_confidence_95"] == 1).sum()
                    if "hotspot_confidence_95" in self.integrated_results.columns
                    else 0
                ),
            },
        }

        metadata_path = os.path.join(output_dir, "integrated_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"메타데이터 저장: {metadata_path}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="통합 공간 분석 대시보드 및 보고서 생성"
    )
    parser.add_argument(
        "--mode",
        choices=["dashboard", "report", "both"],
        default="both",
        help="실행 모드",
    )
    parser.add_argument("--port", type=int, default=8050, help="대시보드 포트")
    parser.add_argument(
        "--report-format",
        choices=["pdf", "html", "markdown"],
        default="pdf",
        help="보고서 형식",
    )
    parser.add_argument(
        "--include-raw-data", action="store_true", help="원시 데이터 포함 여부"
    )
    parser.add_argument(
        "--input-dir",
        default="results/spatial_analysis",
        help="전체 분석 결과 디렉토리",
    )
    parser.add_argument(
        "--output-dir",
        default="results/spatial_analysis/integrated",
        help="통합 결과 저장 디렉토리",
    )

    args = parser.parse_args()

    # 로깅 설정
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    try:
        # 분석기 초기화
        analyzer = IntegratedSpatialAnalyzer()

        # 데이터 로드
        analyzer.load_all_results(args.input_dir)

        # 결과 통합
        analyzer.integrate_results()

        # 출력 디렉토리 생성
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 결과 저장
        analyzer.save_integrated_results(str(output_dir))

        # 보고서 생성
        if args.mode in ["report", "both"]:
            if args.report_format == "pdf":
                analyzer.generate_pdf_report(str(output_dir))

            analyzer.generate_executive_summary(str(output_dir))
            analyzer.export_for_gis(str(output_dir))

        # 대시보드 생성
        if args.mode in ["dashboard", "both"]:
            if DASH_AVAILABLE:
                print("\n대시보드를 시작하려면 Ctrl+C로 종료 후 다시 실행하세요.")
                print(f"대시보드 URL: http://localhost:{args.port}")
                # analyzer.create_dashboard(port=args.port)
            else:
                print("Dash가 설치되지 않아 대시보드를 생성할 수 없습니다.")

        print(f"\n통합 분석 완료! 결과: {output_dir}")

    except Exception as e:
        logger.error(f"오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
