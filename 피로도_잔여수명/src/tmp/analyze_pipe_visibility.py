#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
파이프 가시성 분석 스크립트
35개 고위험 파이프 세그먼트의 실제 geometry 존재 여부 및 길이 분석
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.config import RAW_DATA_DIR, RESULTS_DIR
from src.common.shapefile_loader import ShapefileLoader
import logging

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("analyze_pipe_visibility")


def load_high_risk_pipes() -> pd.DataFrame:
    """고위험 파이프 데이터 로드"""
    csv_path = RESULTS_DIR / "main58b_analyze_overlap" / "overlap_pipes.csv"
    if not csv_path.exists():
        logger.error(f"파일을 찾을 수 없음: {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    logger.info(f"고위험 파이프 로드: {len(df)}개 레코드")
    return df


def analyze_pipe_geometries(high_risk_df: pd.DataFrame) -> Dict:
    """파이프 geometry 분석"""
    loader = ShapefileLoader(RAW_DATA_DIR, verbose=False)
    regions = ['0243', '0461', '0470', '0480', '0490', '0520']

    # Region 컬럼을 문자열로 변환
    high_risk_df['Region'] = high_risk_df['Region'].astype(str).str.zfill(4)

    results = {
        'found': [],
        'not_found': [],
        'short_pipes': [],  # < 10m
        'pipe_lengths': {},
        'region_stats': {}
    }

    # 각 지역별로 분석
    for region_code in regions:
        logger.info(f"\n=== 지역 {region_code} 분석 ===")

        # 해당 지역의 고위험 파이프
        region_pipes = high_risk_df[high_risk_df['Region'] == region_code]
        unique_ftrs = region_pipes['FTR_IDN'].unique()
        logger.info(f"  고위험 파이프: {len(region_pipes)}개 레코드, {len(unique_ftrs)}개 고유 FTR_IDN")

        # Shapefiles 로드
        pipe_lm = loader.load_pipe_shapefile(region_code, "PIPE_LM")
        sply_ls = loader.load_pipe_shapefile(region_code, "SPLY_LS")

        found_count = 0
        not_found_count = 0

        for ftr_idn in unique_ftrs:
            pipe_info = region_pipes[region_pipes['FTR_IDN'] == ftr_idn].iloc[0]
            pipe_type = pipe_info['Type']

            # 해당 타입의 shapefile에서 검색
            if pipe_type == 'PIPE_LM' and pipe_lm is not None:
                pipe_geom = pipe_lm[pipe_lm['FTR_IDN'] == ftr_idn]
            elif pipe_type == 'SPLY_LS' and sply_ls is not None:
                pipe_geom = sply_ls[sply_ls['FTR_IDN'] == ftr_idn]
            else:
                pipe_geom = pd.DataFrame()

            if not pipe_geom.empty:
                found_count += 1
                results['found'].append((ftr_idn, region_code, pipe_type))

                # 파이프 길이 계산 (미터 단위)
                for _, row in pipe_geom.iterrows():
                    if row.geometry and row.geometry.geom_type == 'LineString':
                        # EPSG:5174 (Korean TM) 좌표계에서 길이 계산
                        length = row.geometry.length
                        results['pipe_lengths'][(ftr_idn, region_code)] = length

                        # 짧은 파이프 체크
                        if length < 10:
                            results['short_pipes'].append({
                                'FTR_IDN': ftr_idn,
                                'Region': region_code,
                                'Type': pipe_type,
                                'Length': length,
                                'D_final': pipe_info['D_final_org']
                            })
                            logger.warning(f"    짧은 파이프: FTR_IDN={ftr_idn}, 길이={length:.2f}m")

                        # 좌표 범위 확인
                        coords = list(row.geometry.coords)
                        if coords:
                            x_coords = [c[0] for c in coords]
                            y_coords = [c[1] for c in coords]
                            logger.debug(f"    FTR_IDN={ftr_idn}: 길이={length:.2f}m, "
                                       f"X범위=[{min(x_coords):.0f}, {max(x_coords):.0f}], "
                                       f"Y범위=[{min(y_coords):.0f}, {max(y_coords):.0f}]")
            else:
                not_found_count += 1
                results['not_found'].append((ftr_idn, region_code, pipe_type))
                logger.error(f"    FTR_IDN={ftr_idn} ({pipe_type})를 shapefile에서 찾을 수 없음")

        results['region_stats'][region_code] = {
            'total': len(unique_ftrs),
            'found': found_count,
            'not_found': not_found_count
        }

        logger.info(f"  결과: {found_count}개 찾음, {not_found_count}개 못 찾음")

    return results


def generate_report(results: Dict) -> None:
    """분석 보고서 생성"""
    report_path = RESULTS_DIR / "main58b_analyze_overlap" / "pipe_visibility_report.txt"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("파이프 가시성 분석 보고서\n")
        f.write("=" * 60 + "\n\n")

        # 전체 요약
        total_found = len(results['found'])
        total_not_found = len(results['not_found'])
        total = total_found + total_not_found

        f.write("## 전체 요약\n")
        f.write(f"- 총 분석 대상: {total}개 파이프-지역 조합\n")
        if total > 0:
            f.write(f"- Shapefile에서 찾음: {total_found}개 ({total_found/total*100:.1f}%)\n")
            f.write(f"- Shapefile에서 못 찾음: {total_not_found}개 ({total_not_found/total*100:.1f}%)\n")
        else:
            f.write("- 분석할 파이프가 없습니다.\n")
        f.write(f"- 짧은 파이프 (<10m): {len(results['short_pipes'])}개\n\n")

        # 지역별 통계
        f.write("## 지역별 통계\n")
        f.write("지역 | 총 파이프 | 찾음 | 못 찾음\n")
        f.write("-----|-----------|------|--------\n")
        for region, stats in sorted(results['region_stats'].items()):
            f.write(f"{region} | {stats['total']:9} | {stats['found']:4} | {stats['not_found']:7}\n")
        f.write("\n")

        # 파이프 길이 분포
        if results['pipe_lengths']:
            lengths = list(results['pipe_lengths'].values())
            f.write("## 파이프 길이 분포\n")
            f.write(f"- 최소 길이: {min(lengths):.2f}m\n")
            f.write(f"- 최대 길이: {max(lengths):.2f}m\n")
            f.write(f"- 평균 길이: {np.mean(lengths):.2f}m\n")
            f.write(f"- 중간값: {np.median(lengths):.2f}m\n\n")

            # 길이 구간별 분포
            f.write("### 길이 구간별 분포\n")
            bins = [0, 10, 50, 100, 500, 1000, float('inf')]
            labels = ['< 10m', '10-50m', '50-100m', '100-500m', '500-1000m', '> 1000m']

            for i in range(len(bins)-1):
                count = sum(1 for l in lengths if bins[i] <= l < bins[i+1])
                f.write(f"- {labels[i]}: {count}개 ({count/len(lengths)*100:.1f}%)\n")
            f.write("\n")

        # 짧은 파이프 상세
        if results['short_pipes']:
            f.write("## 짧은 파이프 상세 (<10m)\n")
            f.write("FTR_IDN | 지역 | 타입 | 길이(m) | D_final\n")
            f.write("--------|------|------|---------|--------\n")
            for pipe in sorted(results['short_pipes'], key=lambda x: x['Length']):
                f.write(f"{pipe['FTR_IDN']:7} | {pipe['Region']} | {pipe['Type']:8} | "
                       f"{pipe['Length']:7.2f} | {pipe['D_final']:.4f}\n")
            f.write("\n")

        # 찾지 못한 파이프
        if results['not_found']:
            f.write("## Shapefile에서 찾지 못한 파이프\n")
            f.write("FTR_IDN | 지역 | 타입\n")
            f.write("--------|------|------\n")
            for ftr_idn, region, pipe_type in sorted(results['not_found']):
                f.write(f"{ftr_idn:7} | {region} | {pipe_type}\n")
            f.write("\n")

        # 권장사항
        f.write("## 권장사항\n")
        if results['short_pipes']:
            f.write(f"1. {len(results['short_pipes'])}개의 짧은 파이프 (<10m)는 지도에서 잘 보이지 않을 수 있음\n")
            f.write("   → 마커나 심볼로 추가 표시 권장\n")
        if results['not_found']:
            f.write(f"2. {len(results['not_found'])}개의 파이프를 shapefile에서 찾을 수 없음\n")
            f.write("   → 데이터 정합성 확인 필요\n")
        f.write("3. 파이프 길이가 매우 다양함 (최소-최대 차이가 큼)\n")
        f.write("   → 적응형 시각화 전략 필요\n")

    logger.info(f"\n보고서 저장: {report_path}")


def main():
    """메인 실행 함수"""
    logger.info("파이프 가시성 분석 시작")

    # 1. 고위험 파이프 데이터 로드
    high_risk_df = load_high_risk_pipes()
    if high_risk_df.empty:
        logger.error("고위험 파이프 데이터가 없습니다.")
        return

    # 2. 파이프 geometry 분석
    results = analyze_pipe_geometries(high_risk_df)

    # 3. 보고서 생성
    generate_report(results)

    logger.info("파이프 가시성 분석 완료")


if __name__ == "__main__":
    main()