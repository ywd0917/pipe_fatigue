"""
Rain Flow Counting 계산 스크립트 with K_repair (최신 1년 데이터)
- main55_calc_fatigure.py를 기반으로 K_repair 계수 추가
- 출력 경로: results/main56_calc_fatigure/
- 출력 파일명: _by_age 제거
"""

import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 모듈 import
from rainflow_processing import (
    analyze_date_range_rainflow,
    process_pipe_data_with_age,
    calculate_rainflow_by_age,
)
from fatigue_calculations import (
    add_K_material_to_dataframe,
    calculate_fatigue_damage_dataframe,
)
from pipe_prop import read_pipe_properties
from traffic_loader import print_unmapped_roads_summary
from repair_loader_k import (
    load_k_repair_mapping,
    apply_k_repair_to_dataframe,
    print_k_repair_statistics,
)

# 공통 설정 import
from common.config import (
    PRESSURE_DATA_FILES,
    PIPE_PROP_PATH,
    PIPE_DATA_FILES,
    PROJECT_ROOT,
)


def get_rainflow_summary(analysis_result: Dict[str, Any]) -> Dict[str, float]:
    """
    Rain Flow Counting 분석 결과에서 주요 값들을 추출
    """
    if not analysis_result["success"]:
        return {
            "high_total_cycles": 0.0,
            "low_total_cycles": 0.0,
            "high_full_cycles": 0.0,
            "low_full_cycles": 0.0,
            "high_half_cycles": 0.0,
            "low_half_cycles": 0.0,
            "high_mean_range": 0.0,
            "low_mean_range": 0.0,
            "high_max_range": 0.0,
            "low_max_range": 0.0,
        }

    results = analysis_result["results"]

    return {
        "high_total_cycles": results["high_pass"]["analysis"].get("total_cycles", 0.0),
        "low_total_cycles": results["low_pass"]["analysis"].get("total_cycles", 0.0),
        "high_full_cycles": results["high_pass"]["analysis"].get("full_cycles", 0.0),
        "low_full_cycles": results["low_pass"]["analysis"].get("full_cycles", 0.0),
        "high_half_cycles": results["high_pass"]["analysis"].get("half_cycles", 0.0),
        "low_half_cycles": results["low_pass"]["analysis"].get("half_cycles", 0.0),
        "high_mean_range": results["high_pass"]["analysis"].get("mean_range", 0.0),
        "low_mean_range": results["low_pass"]["analysis"].get("mean_range", 0.0),
        "high_max_range": results["high_pass"]["analysis"].get("max_range", 0.0),
        "low_max_range": results["low_pass"]["analysis"].get("max_range", 0.0),
    }


def process_all_pipe_data_with_rainflow_and_repair(
    pipe_properties: pd.DataFrame,
    repair_data: Dict[str, pd.DataFrame],
) -> None:
    """
    모든 파이프 데이터 파일을 처리하고 Rain Flow Counting, K 계수들, K_repair, 피로도 계산
    """
    print(f"\n{'='*80}")
    print("모든 파이프 데이터 처리 및 Rain Flow Counting with K_repair 계산")
    print(f"{'='*80}")

    # 출력 디렉토리 설정
    output_dir = PROJECT_ROOT / "results" / "main56_calc_fatigure"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 압력 데이터 소스 (DB 조회용 지역 코드)
    pressure_data_files = ["0243", "0461", "0470", "0480", "0490", "0520"]

    # 파이프 데이터 파일 목록
    pipe_data_files = PIPE_DATA_FILES

    total_processed = 0
    successful_files = 0

    for file_path, file_type in pipe_data_files:
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"\n파일을 찾을 수 없습니다: {file_path}")
            continue

        try:
            print(f"\n처리 중: {file_type} ({file_path.name})")

            # 1. 파이프 데이터 읽기 및 나이 계산
            pipe_df = process_pipe_data_with_age(
                str(file_path), file_type, output_dir=str(output_dir)
            )

            if pipe_df.empty:
                print(f"데이터가 비어있습니다: {file_path}")
                continue

            # 2. 나이별 Rain Flow Counting 계산
            result_df = calculate_rainflow_by_age(
                pipe_df, file_type, pressure_data_files, use_db=True
            )

            # 3. 재료계수(K_material), K 계수들, 피로한계 추가
            result_df = add_K_material_to_dataframe(
                result_df, pipe_properties, file_type
            )

            # 4. K_repair 적용
            result_df = apply_k_repair_to_dataframe(result_df, file_type, repair_data)
            print_k_repair_statistics(result_df, file_type)

            # 5. 각 지역별 피로도 계산
            regions = ["0243", "0461", "0470", "0480", "0490", "0520"]
            for region in regions:
                if f"{region}_high_total_cycles" in result_df.columns:
                    result_df = calculate_fatigue_damage_dataframe(
                        result_df, region, data_type="pressure", use_k_total=True
                    )

                    if f"{region}_D_final" in result_df.columns:
                        result_df[f"{region}_remaining_life_years"] = result_df.apply(
                            lambda row: (
                                (1 - row[f"{region}_D_final"])
                                / row[f"{region}_D_final"]
                                if row[f"{region}_D_final"] < 1
                                and row[f"{region}_D_final"] > 0
                                else 0
                            ),
                            axis=1,
                        )

                    if f"{region}_high_fatigue_intermediate" in result_df.columns:
                        result_df[f"{region}_high_fatigue_damage"] = result_df[
                            f"{region}_high_fatigue_intermediate"
                        ]
                        del result_df[f"{region}_high_fatigue_intermediate"]

                    if f"{region}_low_fatigue_intermediate" in result_df.columns:
                        result_df[f"{region}_low_fatigue_damage"] = result_df[
                            f"{region}_low_fatigue_intermediate"
                        ]
                        del result_df[f"{region}_low_fatigue_intermediate"]

            # 6. 컬럼 순서 재정렬
            duplicate_cols = [col for col in result_df.columns if col.endswith('.1')]
            if duplicate_cols:
                result_df = result_df.drop(columns=duplicate_cols)
            
            base_columns = [
                col
                for col in result_df.columns
                if not col.startswith(("0243", "0461", "0470", "0480", "0490", "0520"))
            ]

            k_columns = [
                "K_diameter", "K_age", "K_soil", "K_traffic", "K_vibration",
                "hoop_stress", "K_stress", "K_repair", "K_total",
            ]
            k_columns_present = [col for col in k_columns if col in base_columns]
            other_base_columns = [col for col in base_columns if col not in k_columns]

            region_columns = []
            for region in ["0243", "0461", "0470", "0480", "0490", "0520"]:
                region_cols = [col for col in result_df.columns if col.startswith(region)]
                ordered_cols = [
                    f"{region}_low_total_cycles",
                    f"{region}_high_total_cycles",
                    f"{region}_low_fatigue_damage",
                    f"{region}_high_fatigue_damage",
                    f"{region}_D_base",
                    f"{region}_D_final_org",
                    f"{region}_D_final",
                    f"{region}_remaining_life_years",
                ]
                region_columns.extend(
                    [col for col in ordered_cols if col in region_cols]
                )

            final_columns = other_base_columns + k_columns_present + region_columns
            result_df = result_df[final_columns]

            result_df = result_df.drop(columns=['K_total_without_repair'], errors='ignore')

            # 7. 결과 저장
            if file_type == "PIPE_LM":
                output_filename = "fatigue_pipe_lm.csv"
            elif file_type == "SPLY_LS":
                output_filename = "fatigue_sply_ls.csv"
            else:
                output_filename = f"fatigue_{file_path.stem}.csv"

            output_path = output_dir / output_filename
            result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

            total_processed += 1
            successful_files += 1

            print(f"✓ 결과 저장 완료: {output_path}")
            print(f"  - 총 레코드 수: {len(result_df):,}")
            print(f"  - 총 컬럼 수: {len(result_df.columns)}")

            if "K_repair" in result_df.columns:
                k_repair_applied = (result_df["K_repair"] > 0).sum()
                print(f"  - K_repair 적용된 레코드: {k_repair_applied:,} / {len(result_df):,}")

        except Exception as e:
            print(f"오류 발생 ({file_path}): {e!s}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print("파이프 데이터 처리 완료")
    print(f"{'='*80}")
    print(f"총 처리 파일 수: {total_processed}")
    print(f"성공적으로 처리된 파일 수: {successful_files}")
    print(f"실패한 파일 수: {total_processed - successful_files}")


def main(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    process_pipes: bool = True,
    process_rainflow: bool = True,
) -> None:
    print(
        "통합 데이터 분석 프로그램 with K_repair (나이 기반 Rain Flow Counting, K 계수들 및 피로도 포함)"
    )
    print("=" * 80)
    
    try:
        repair_data = {}
        if process_pipes:
            print("\nK_repair 데이터 로드 중...")
            repair_data = load_k_repair_mapping()

        pipe_properties = None
        if process_pipes:
            pipe_properties = read_pipe_properties(str(PIPE_PROP_PATH))
            if pipe_properties.empty:
                print("파이프 속성 데이터를 로드할 수 없어 프로그램을 종료합니다.")
                return

        if process_pipes:
            print("\n[1단계] 파이프 데이터 처리, Rain Flow Counting, K 계수들, K_repair 및 피로도 계산")
            if pipe_properties is not None:
                process_all_pipe_data_with_rainflow_and_repair(pipe_properties, repair_data)
    
    except FileNotFoundError as e:
        missing_file = Path(str(e))
        print(f"\n오류: 필수 입력 파일을 찾을 수 없습니다")
        print(f"누락된 파일: {missing_file}")
        sys.exit(1)

    if process_rainflow:
        print("\n[2단계] 기본 Rain Flow Counting 분석")

        if start_date is None:
            start_date = datetime(2023, 1, 1)
        if end_date is None:
            end_date = datetime(2023, 12, 31, 23, 59, 59)

        print(f"분석 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

        data_files = []
        for file_path in PRESSURE_DATA_FILES:
            file_name = file_path.name
            if "0470" in file_name or "0520" in file_name:
                data_files.append(file_path)

        all_results = []

        for file_path in data_files:
            if Path(file_path).exists():
                result = analyze_date_range_rainflow(str(file_path), start_date, end_date)
                all_results.append(result)

                if result["success"]:
                    summary = get_rainflow_summary(result)
                    print(f"\n{'-'*50}")
                    print(f"주요 Rain Flow Counting 값 - {result['file_name']}")
                    print(f"{'-'*50}")
                    print(f"고주파 총 사이클: {summary['high_total_cycles']:.1f}")
                    print(f"저주파 총 사이클: {summary['low_total_cycles']:.1f}")
            else:
                print(f"파일을 찾을 수 없습니다: {file_path}")
                all_results.append({"file_path": file_path, "file_name": Path(file_path).name, "error": "File not found", "success": False})

        if all_results:
            successful_count = sum(1 for r in all_results if r["success"])
            total_count = len(all_results)
            print(f"\n{'='*80}")
            print("기본 Rain Flow Counting 분석 완료")
            print(f"총 파일 수: {total_count}, 성공: {successful_count}")

    print(f"\n{'='*80}")
    print("전체 프로그램 실행 완료")
    print(f"{'='*80}")

    results_dir = Path("results/main56_calc_fatigure")
    if results_dir.exists():
        print("\n생성된 결과 파일:")
        result_files = list(results_dir.glob("*.csv"))
        for i, file_path in enumerate(sorted(result_files), 1):
            file_size = file_path.stat().st_size / 1024
            print(f"  {i:2d}. {file_path.name} ({file_size:.1f} KB)")

    if process_pipes:
        print_unmapped_roads_summary()


if __name__ == "__main__":
    main()
