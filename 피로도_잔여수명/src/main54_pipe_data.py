"""
연암배수지 관망 정보 데이터 처리 스크립트
- 큰 CSV 파일을 안전하게 읽고 처리
- IST_YMD, FNS_YMD 날짜 필드 처리
- 메모리 효율적인 청크 단위 처리
"""

import pandas as pd
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, cast, Callable

# 한글 폰트 설정 및 유틸리티 함수 import
from common.config import PIPE_DATA_FILES, RESULTS_DIR

# 관망 데이터 처리 유틸리티 함수들 import
from pipe_data import (
    check_file_info,
    analyze_csv_structure,
    read_csv_pipe_lm,
    read_csv_sply_ls,
)


def save_sample_data(
    result: Optional[Dict[str, Any]],
    output_dir: Optional[Path] = None,
    filename: str = "pipe_data_sample.csv",
) -> None:
    """샘플 데이터 저장

    Args:
        result: 처리 결과 딕셔너리 (sample_chunks 포함) 또는 None
            - sample_chunks: DataFrame 리스트 (List[pd.DataFrame])
        output_dir: 출력 디렉토리 경로 (None이면 RESULTS_DIR 사용)
        filename: 저장할 파일명

    Returns:
        None
    """
    if not result or not result.get("sample_chunks"):
        print("저장할 샘플 데이터가 없습니다.")
        return

    try:
        # 출력 디렉토리 설정 (기본값: RESULTS_DIR)
        if output_dir is None:
            output_dir = RESULTS_DIR / "main54_pipe_data"
        output_dir = Path(output_dir)

        # 출력 디렉토리 생성
        output_dir.mkdir(parents=True, exist_ok=True)

        # 샘플 청크들을 하나로 합치기
        combined_sample = pd.concat(result["sample_chunks"], ignore_index=True)

        # CSV로 저장
        sample_output_path = output_dir / filename
        combined_sample.to_csv(sample_output_path, index=False, encoding="utf-8-sig")

        print(f"\n샘플 데이터가 저장되었습니다: {sample_output_path}")
        print(
            f"샘플 데이터 크기: {len(combined_sample):,}행 x {len(combined_sample.columns)}컬럼"
        )

        # 기본 통계 정보
        print("\n샘플 데이터 기본 정보:")
        print(combined_sample.info())

    except Exception as e:
        print(f"샘플 데이터 저장 중 오류 발생: {e}")


def analyze_pipe_types(
    all_chunks: List[pd.DataFrame], file_name: str
) -> Dict[str, int]:
    """모든 청크에서 PIP_TYPE 값들을 분석

    Args:
        all_chunks: 모든 데이터 청크들의 리스트
        file_name: 파일명 (표시용)

    Returns:
        PIP_TYPE별 개수 딕셔너리
    """
    print(f"\n{file_name} PIP_TYPE 분석:")
    print(f"{'='*40}")

    # 모든 PIP_TYPE 값 수집
    all_pipe_types = []
    for chunk in all_chunks:
        if "PIP_TYPE" in chunk.columns:
            pipe_types = chunk["PIP_TYPE"].dropna()
            all_pipe_types.extend(pipe_types.tolist())

    if not all_pipe_types:
        print("PIP_TYPE 컬럼을 찾을 수 없거나 데이터가 없습니다.")
        return {}

    # PIP_TYPE별 개수 계산
    pipe_type_counts = pd.Series(all_pipe_types).value_counts().to_dict()

    # 결과 출력
    print(f"총 {len(pipe_type_counts)}개의 고유한 PIP_TYPE 발견:")
    for pipe_type, count in sorted(
        pipe_type_counts.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / len(all_pipe_types)) * 100
        print(f"  - {pipe_type}: {count:,}개 ({percentage:.1f}%)")

    print(f"\n전체 PIP_TYPE 데이터: {len(all_pipe_types):,}개")

    return pipe_type_counts


def process_pipe_data(
    file_path: str,
    reader_func: Callable[..., pd.DataFrame],
    output_dir: Optional[Path] = None,
    file_name: str = "",
) -> Optional[Dict[str, Any]]:
    """관망 데이터 전체 처리

    Args:
        file_path: 처리할 CSV 파일 경로
        reader_func: 파일 타입별 CSV 읽기 함수
        output_dir: 결과 파일을 저장할 디렉토리
        file_name: 파일 이름 (표시용)

    Returns:
        처리 결과 딕셔너리 또는 None (실패시)
        - file_info: 파일 정보 (경로, 크기 등)
        - structure_info: CSV 구조 정보 (컬럼, 타입, 날짜 필드 등)
        - date_fields: 식별된 날짜 필드 리스트
        - all_chunks: 전체 데이터 청크들
        - total_rows: 전체 행 수
        - pipe_type_counts: PIP_TYPE별 개수
    """
    if output_dir is None:
        output_dir = RESULTS_DIR / "main54_pipe_data"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    display_name = file_name if file_name else os.path.basename(file_path)
    print(f"\n{'='*60}")
    print(f"{display_name} 데이터 처리 시작")
    print(f"{'='*60}")

    # 출력 디렉토리 생성
    output_dir.mkdir(exist_ok=True)

    # 1. 파일 정보 확인
    file_info = check_file_info(file_path)

    # 2. CSV 구조 분석
    structure_info = analyze_csv_structure(file_path, nrows=5)

    if not structure_info:
        print("CSV 구조 분석에 실패했습니다.")
        return None

    # 4. 날짜 필드 식별
    date_fields: List[str] = cast(List[str], structure_info.get("date_fields", []))

    # IST_YMD, FNS_YMD 필드 명시적 추가
    columns: List[str] = cast(List[str], structure_info["columns"])
    for col in columns:
        if "IST_YMD" in col or "FNS_YMD" in col:
            if col not in date_fields:
                date_fields.append(col)

    print(f"\n식별된 날짜 필드: {date_fields}")

    # BEG_YMD 필드 추가 안내
    if "IST_YMD" in date_fields or "FNS_YMD" in date_fields:
        print("IST_YMD와 FNS_YMD 중 더 최신 데이터를 BEG_YMD로 추가합니다.")

    # PIP_TYPE 필드 추가 안내
    print("파일 타입별 PIP_TYPE 필드를 추가합니다.")

    # 5. 청크 단위 전체 데이터 처리
    print("\n청크 단위 전체 데이터 처리:")
    chunk_count = 0
    all_chunks: List[pd.DataFrame] = []
    total_rows = 0

    try:
        for chunk in reader_func(file_path, chunksize=1000, date_columns=date_fields):
            chunk_count += 1
            chunk_df = cast(pd.DataFrame, chunk)
            all_chunks.append(chunk_df)
            total_rows += len(chunk_df)

        print(f"전체 처리 완료: {chunk_count}개 청크, 총 {total_rows:,}행")

    except Exception as e:
        print(f"청크 처리 중 오류 발생: {e}")
        all_chunks = []
        total_rows = 0

    # 6. PIP_TYPE 분석
    pipe_type_counts = {}
    if all_chunks:
        pipe_type_counts = analyze_pipe_types(all_chunks, display_name)

    # 7. 결과 요약
    result = {
        "file_info": file_info,
        "structure_info": structure_info,
        "date_fields": date_fields,
        "all_chunks": all_chunks,
        "total_rows": total_rows,
        "pipe_type_counts": pipe_type_counts,
    }

    # 8. 요약 정보 출력
    print(f"\n{'='*40}")
    print("처리 결과 요약")
    print(f"{'='*40}")
    print(f"파일 크기: {file_info['size_mb']:.2f} MB")
    print(f"총 컬럼 수: {len(structure_info['columns'])}")
    print(f"날짜 필드 수: {len(date_fields)}")
    print(f"전체 청크 수: {len(all_chunks)}")
    print(f"전체 행 수: {total_rows:,}행")
    print(f"고유 PIP_TYPE 수: {len(pipe_type_counts)}개")

    if date_fields:
        print("\n날짜 필드 상세:")
        for field in date_fields:
            print(f"  - {field}")

    return result


def main() -> None:
    """메인 실행 함수

    Returns:
        None
    """
    print("연암배수지 관망 정보 데이터 처리 프로그램")
    print("목적: 큰 CSV 파일의 안전한 읽기 및 처리")

    # 처리할 파일들 설정
    files_to_process = []

    # PIPE_DATA_FILES에서 파일 정보 구성
    for file_path, file_name in PIPE_DATA_FILES:
        if file_name == "PIPE_LM":
            files_to_process.append(
                {
                    "path": file_path,
                    "name": "PIPE_LM (관망 정보)",
                    "filename": "pipe_lm_sample.csv",
                    "reader": read_csv_pipe_lm,
                }
            )
        elif file_name == "SPLY_LS":
            files_to_process.append(
                {
                    "path": file_path,
                    "name": "SPLY_LS (급수관 정보)",
                    "filename": "sply_ls_sample.csv",
                    "reader": read_csv_sply_ls,
                }
            )

    all_results = []

    for file_info in files_to_process:
        file_path = cast(Path, file_info["path"])
        file_name = cast(str, file_info["name"])
        sample_filename = cast(str, file_info["filename"])
        reader_func = cast(Callable[..., pd.DataFrame], file_info["reader"])

        if not os.path.exists(str(file_path)):
            print(f"파일을 찾을 수 없습니다: {file_path}")
            continue

        try:
            # 데이터 처리 실행 (파일별 전용 함수 전달)
            result = process_pipe_data(str(file_path), reader_func, file_name=file_name)

            if result:
                # 전체 데이터 저장 (파일별로 다른 이름으로 저장)
                # save_sample_data 함수는 'sample_chunks' 키를 찾으므로 호환성을 위해 키 이름 변경
                result_for_save = result.copy()
                result_for_save["sample_chunks"] = result["all_chunks"]
                save_sample_data(result_for_save, filename=sample_filename)
                all_results.append(
                    {"file_name": file_name, "file_path": file_path, "result": result}
                )

                print(f"\n{file_name} 처리 완료!")
            else:
                print(f"{file_name} 데이터 처리에 실패했습니다.")

        except Exception as e:
            print(f"{file_name} 처리 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()

    # 전체 결과 요약
    if all_results:
        print(f"\n{'='*80}")
        print("전체 처리 결과 요약")
        print(f"{'='*80}")

        for i, file_result in enumerate(all_results, 1):
            result = cast(Optional[Dict[str, Any]], file_result["result"])
            if result is None:
                print(f"\n{i}. {file_result['file_name']}: 처리 실패")
                continue
            print(f"\n{i}. {file_result['file_name']}:")
            print(f"   파일 크기: {result['file_info']['size_mb']:.2f} MB")
            print(f"   총 컬럼 수: {len(result['structure_info']['columns'])}")
            print(f"   날짜 필드 수: {len(result['date_fields'])}")
            print(f"   전체 청크 수: {len(result['all_chunks'])}")
            print(f"   전체 행 수: {result['total_rows']:,}행")
            print(f"   고유 PIP_TYPE 수: {len(result.get('pipe_type_counts', {}))}개")

            # PIP_TYPE 요약 출력
            pipe_type_counts = result.get("pipe_type_counts", {})
            if pipe_type_counts:
                print("   PIP_TYPE 분포:")
                for pipe_type, count in sorted(
                    pipe_type_counts.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    percentage = (count / sum(pipe_type_counts.values())) * 100
                    print(f"     - {pipe_type}: {count:,}개 ({percentage:.1f}%)")
                if len(pipe_type_counts) > 5:
                    print(f"     ... 외 {len(pipe_type_counts) - 5}개 타입")

        print(f"\n{'='*60}")
        print("모든 파일 처리 완료!")
        print(f"{'='*60}")
        print("다음 단계:")
        print("1. 각 파일의 샘플 데이터 확인")
        print("2. 필요한 컬럼 선택")
        print("3. 전체 데이터 처리 계획 수립")
        print("4. 피로도 분석에 필요한 데이터 추출")
        print("5. 두 파일 간의 관계 분석")
    else:
        print("처리된 파일이 없습니다.")


if __name__ == "__main__":
    main()