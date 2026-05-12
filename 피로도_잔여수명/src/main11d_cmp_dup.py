"""
중복 작업 분석 스크립트
results/*_위치추가.csv 파일들에서 작업일시(날짜)와 위치가 동일한 중복 작업을 찾음
위치는 EPSG:5179 좌표계로 변환하여 비교
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from pyproj import Transformer


# 처리할 파일명 목록 지정
# ※ 여기서 분석할 CSV 파일명을 직접 지정하세요
TARGET_FILES = [
    "지상누수_위치추가.csv",
    "지하누수_위치추가.csv",
    # "기타공사_위치추가.csv",
    "긴급공사_위치추가.csv",
    "관리대장_위치추가.csv",
]


def load_files():
    """
    results 디렉토리에서 파일 로드 및 필수 컬럼 검증

    Returns:
        dict: 파일명을 키로 하는 DataFrame 딕셔너리

    Raises:
        ValueError: 필수 컬럼이 없는 경우
    """
    results_dir = Path("results")
    if not results_dir.exists():
        raise FileNotFoundError(f"{results_dir} 디렉토리를 찾을 수 없습니다.")

    # 파일 검색
    files = []
    for file_name in TARGET_FILES:
        file_path = results_dir / file_name
        if file_path.exists():
            files.append(file_path)
        else:
            print(f"⚠️  파일을 찾을 수 없음: {file_name}")

    if not files:
        raise FileNotFoundError(
            f"처리할 파일이 없습니다. 필요한 파일: {', '.join(TARGET_FILES)}"
        )

    file_data = {}
    missing_columns = {}

    for file_path in sorted(files):
        # CSV 파일 읽기 (여러 인코딩 시도)
        df = None
        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except Exception:
                continue

        if df is None:
            print(f"⚠️  {file_path.name} 읽기 실패: 지원되지 않는 인코딩")
            continue

        # 필수 컬럼 확인
        required_columns = ["작업일시", "위도", "경도"]
        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            missing_columns[file_path.name] = missing
        else:
            file_data[file_path.name] = df

    # 필수 컬럼이 없는 파일이 있으면 오류 발생
    if missing_columns:
        error_msg = "\n❌ 필수 컬럼이 없는 파일 발견:\n"
        error_msg += "=" * 50 + "\n"
        for file_name, cols in missing_columns.items():
            error_msg += f"\n파일: {file_name}\n"
            error_msg += f"  누락된 컬럼: {', '.join(cols)}\n"
        error_msg += "\n" + "=" * 50
        error_msg += "\n\n모든 파일에 '작업일시', '위도', '경도' 컬럼이 필요합니다."

        print(error_msg)
        raise ValueError(f"필수 컬럼 누락: {len(missing_columns)}개 파일에서 오류")

    return file_data


def convert_to_epsg5179(df):
    """
    WGS84 위도/경도를 EPSG:5179 좌표로 변환

    Args:
        df: DataFrame with 위도, 경도 columns

    Returns:
        DataFrame with added x_5179, y_5179 columns
    """
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)

    # 위도/경도가 모두 있는 행만 변환
    valid_mask = (df["위도"].notna()) & (df["경도"].notna())
    valid_coords = df[valid_mask]

    if len(valid_coords) > 0:
        # 벡터화된 변환
        x_coords, y_coords = transformer.transform(
            valid_coords["경도"].values, valid_coords["위도"].values
        )
        df.loc[valid_mask, "x_5179"] = x_coords
        df.loc[valid_mask, "y_5179"] = y_coords
    else:
        df["x_5179"] = np.nan
        df["y_5179"] = np.nan

    return df


def calculate_distances_within_groups(df):
    """
    중복 그룹 내에서 첫 번째 위치로부터의 거리 계산

    Args:
        df: 중복된 레코드들의 DataFrame

    Returns:
        거리가 추가된 DataFrame
    """
    df["그룹내거리_m"] = 0.0

    # 각 그룹별로 처리
    group_cols = ["작업일자", "x_rounded", "y_rounded"]

    for group_key, group in df.groupby(group_cols):
        if len(group) > 1:
            # 그룹의 첫 번째 위치
            first_x = group.iloc[0]["x_5179"]
            first_y = group.iloc[0]["y_5179"]

            # 각 위치까지의 거리 계산
            distances = np.sqrt(
                (group["x_5179"] - first_x) ** 2 + (group["y_5179"] - first_y) ** 2
            )
            df.loc[group.index, "그룹내거리_m"] = distances

    return df


def find_duplicates(df, file_name, tolerance=1.0, verbose=False):
    """
    작업일시(날짜)와 EPSG:5179 좌표로 중복 확인

    Args:
        df: 입력 DataFrame
        file_name: 파일명
        tolerance: 좌표 허용 오차 (미터)
        verbose: 상세 정보 출력 여부

    Returns:
        중복된 레코드들의 DataFrame
    """
    df = df.copy()

    # 작업일시에서 날짜만 추출
    df["작업일자"] = pd.to_datetime(df["작업일시"], errors="coerce").dt.date

    # WGS84 → EPSG:5179 변환
    df = convert_to_epsg5179(df)

    # 유효한 데이터만 필터링
    df_valid = df[
        (df["x_5179"].notna()) & (df["y_5179"].notna()) & (df["작업일자"].notna())
    ].copy()

    if len(df_valid) == 0:
        return pd.DataFrame()

    if verbose:
        print(f"  - 유효한 데이터: {len(df_valid)}/{len(df)}행")

    # 좌표 반올림 (tolerance 적용)
    df_valid["x_rounded"] = np.round(df_valid["x_5179"] / tolerance) * tolerance
    df_valid["y_rounded"] = np.round(df_valid["y_5179"] / tolerance) * tolerance

    # 중복 확인
    duplicates = df_valid[
        df_valid.duplicated(["작업일자", "x_rounded", "y_rounded"], keep=False)
    ].copy()

    if len(duplicates) == 0:
        return pd.DataFrame()

    # 메타 정보 추가
    duplicates["원본행번호"] = duplicates.index + 2  # Excel 행번호 (헤더 제외)
    duplicates["파일명"] = file_name

    # 주소/위치 컬럼 통합
    if "주소" in duplicates.columns:
        duplicates["주소또는위치"] = duplicates["주소"]
    elif "위치" in duplicates.columns:
        duplicates["주소또는위치"] = duplicates["위치"]
    else:
        duplicates["주소또는위치"] = ""

    # 중복 그룹별로 거리 계산
    duplicates = calculate_distances_within_groups(duplicates)

    # 정렬
    duplicates = duplicates.sort_values(["작업일자", "x_5179", "y_5179"])

    return duplicates


def find_cross_file_duplicates(file_data_dict, tolerance=1.0, verbose=False):
    """
    여러 파일 간의 중복 확인 (EPSG:5179 기준)

    Args:
        file_data_dict: 파일명을 키로 하는 DataFrame 딕셔너리
        tolerance: 좌표 허용 오차 (미터)
        verbose: 상세 정보 출력 여부

    Returns:
        파일 간 중복된 레코드들의 DataFrame
    """
    all_records = []

    for file_name, df in file_data_dict.items():
        df_copy = df.copy()
        df_copy["source_file"] = file_name
        df_copy["작업일자"] = pd.to_datetime(df["작업일시"], errors="coerce").dt.date

        # 좌표 변환
        df_copy = convert_to_epsg5179(df_copy)

        # 유효한 데이터만
        df_valid = df_copy[
            (df_copy["x_5179"].notna())
            & (df_copy["y_5179"].notna())
            & (df_copy["작업일자"].notna())
        ].copy()

        if len(df_valid) > 0:
            # 좌표 반올림
            df_valid["x_rounded"] = np.round(df_valid["x_5179"] / tolerance) * tolerance
            df_valid["y_rounded"] = np.round(df_valid["y_5179"] / tolerance) * tolerance

            # 원본 인덱스 저장
            df_valid["원본행번호"] = df_valid.index + 2

            # 주소/위치 통합
            if "주소" in df_valid.columns:
                df_valid["주소또는위치"] = df_valid["주소"]
            elif "위치" in df_valid.columns:
                df_valid["주소또는위치"] = df_valid["위치"]
            else:
                df_valid["주소또는위치"] = ""

            all_records.append(df_valid)

    if not all_records:
        return pd.DataFrame()

    # 모든 파일 합치기
    combined = pd.concat(all_records, ignore_index=True)

    # 중복 찾기 (같은 파일 내 중복은 제외)
    dup_groups = combined.groupby(["작업일자", "x_rounded", "y_rounded"])
    cross_duplicates = []

    for group_key, group in dup_groups:
        # 서로 다른 파일에서 온 레코드가 있는 경우만
        if group["source_file"].nunique() > 1:
            cross_duplicates.append(group)

    if cross_duplicates:
        result = pd.concat(cross_duplicates, ignore_index=True)
        result = calculate_distances_within_groups(result)
        result = result.sort_values(["작업일자", "source_file", "x_5179", "y_5179"])
        return result

    return pd.DataFrame()


def print_results(file_duplicates, cross_duplicates, tolerance):
    """
    중복 분석 결과를 콘솔에 출력

    Args:
        file_duplicates: 파일별 중복 딕셔너리
        cross_duplicates: 파일 간 중복 DataFrame
        tolerance: 사용된 허용 오차
    """
    print("\n" + "=" * 80)
    print("중복 분석 결과 (EPSG:5179 좌표계 기준)")
    print("=" * 80)

    # 파일별 중복
    print("\n=== 파일별 중복 현황 ===\n")

    if not file_duplicates:
        print("파일 내 중복 없음")
    else:
        for file_name, duplicates in file_duplicates.items():
            print(f"\n{file_name}:")
            print(f"  - 중복 발견: {len(duplicates)}행")

            # 그룹별 상세 정보
            group_cols = ["작업일자", "x_rounded", "y_rounded"]
            groups = duplicates.groupby(group_cols)
            print(f"  - 중복 그룹: {len(groups)}개")
            print(f"  - 허용 오차: {tolerance}m")

            # 상위 5개 그룹만 표시
            print("\n  상세 중복 (최대 5개 그룹):")
            for i, ((date, x, y), group) in enumerate(groups):
                if i >= 5:
                    remaining = len(groups) - 5
                    print(f"\n  ... 외 {remaining}개 그룹 더 있음")
                    break

                print(
                    f"\n  [그룹 {i+1}] {date} | EPSG:5179({x:.1f}, {y:.1f}) ± {tolerance}m"
                )
                print(f"    총 {len(group)}건 중복:")

                for _, row in group.iterrows():
                    dist = row["그룹내거리_m"]
                    addr = row["주소또는위치"]
                    row_num = row["원본행번호"]
                    if dist == 0:
                        print(f"    - 행 {row_num}: {addr} (기준점)")
                    else:
                        print(f"    - 행 {row_num}: {addr} ({dist:.1f}m 떨어짐)")

    # 파일 간 중복
    print("\n\n=== 파일 간 중복 ===\n")

    if len(cross_duplicates) == 0:
        print("파일 간 중복 없음")
    else:
        print(f"총 {len(cross_duplicates)}개 레코드가 여러 파일에 중복됨")

        # 그룹별 표시
        group_cols = ["작업일자", "x_rounded", "y_rounded"]
        groups = cross_duplicates.groupby(group_cols)
        print(f"중복 그룹: {len(groups)}개\n")

        for i, ((date, x, y), group) in enumerate(groups):
            if i >= 5:
                remaining = len(groups) - 5
                print(f"\n... 외 {remaining}개 그룹 더 있음")
                break

            print(f"\n[그룹 {i+1}] {date} | EPSG:5179({x:.1f}, {y:.1f}) ± {tolerance}m")

            for _, row in group.iterrows():
                file = row["source_file"]
                addr = row["주소또는위치"]
                dist = row["그룹내거리_m"]
                row_num = row["원본행번호"]

                if dist == 0:
                    print(f"  [{file}] 행 {row_num}: {addr}")
                else:
                    print(f"  [{file}] 행 {row_num}: {addr} ({dist:.1f}m)")


def save_results(file_duplicates, cross_duplicates, output_dir, tolerance):
    """
    중복 분석 결과를 파일로 저장

    Args:
        file_duplicates: 파일별 중복 딕셔너리
        cross_duplicates: 파일 간 중복 DataFrame
        output_dir: 출력 디렉토리
        tolerance: 사용된 허용 오차
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 상세 CSV 파일
    all_duplicates = []

    # 파일별 중복 추가
    for file_name, duplicates in file_duplicates.items():
        if len(duplicates) > 0:
            dup_copy = duplicates.copy()
            dup_copy["중복유형"] = "파일내"
            all_duplicates.append(dup_copy)

    # 파일 간 중복 추가
    if len(cross_duplicates) > 0:
        cross_copy = cross_duplicates.copy()
        cross_copy["중복유형"] = "파일간"
        cross_copy["파일명"] = cross_copy["source_file"]
        all_duplicates.append(cross_copy)

    if all_duplicates:
        # 필요한 컬럼만 선택
        result_df = pd.concat(all_duplicates, ignore_index=True)

        columns_to_save = [
            "중복유형",
            "파일명",
            "원본행번호",
            "작업일자",
            "위도",
            "경도",
            "x_5179",
            "y_5179",
            "그룹내거리_m",
            "주소또는위치",
        ]

        # 존재하는 컬럼만 선택
        columns_to_save = [col for col in columns_to_save if col in result_df.columns]
        result_df = result_df[columns_to_save]

        # CSV 저장
        csv_path = output_path / "중복분석_상세.csv"
        result_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n상세 결과 저장: {csv_path}")

    # 2. 요약 텍스트 파일
    summary_path = output_path / "중복분석_요약.txt"

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("중복 분석 요약\n")
        f.write("=" * 50 + "\n")
        f.write(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"좌표계: EPSG:5179\n")
        f.write(f"허용 오차: {tolerance}m\n")
        f.write("\n")

        f.write("파일별 통계:\n")
        if file_duplicates:
            for file_name, duplicates in file_duplicates.items():
                group_count = duplicates.groupby(
                    ["작업일자", "x_rounded", "y_rounded"]
                ).ngroups
                f.write(
                    f"- {file_name}: {len(duplicates)}개 중복 ({group_count}그룹)\n"
                )
        else:
            f.write("- 파일 내 중복 없음\n")

        f.write("\n")
        f.write(f"파일 간 중복: {len(cross_duplicates)}개\n")

        if len(cross_duplicates) > 0:
            group_count = cross_duplicates.groupby(
                ["작업일자", "x_rounded", "y_rounded"]
            ).ngroups
            f.write(f"  - 중복 그룹: {group_count}개\n")

            # 파일 조합별 통계
            file_pairs = {}
            for (date, x, y), group in cross_duplicates.groupby(
                ["작업일자", "x_rounded", "y_rounded"]
            ):
                files = sorted(group["source_file"].unique())
                if len(files) >= 2:
                    pair = f"{files[0]} ↔ {files[1]}"
                    if len(files) > 2:
                        pair += f" 외 {len(files)-2}개"
                    file_pairs[pair] = file_pairs.get(pair, 0) + 1

            if file_pairs:
                f.write("\n파일 조합별 중복:\n")
                for pair, count in file_pairs.items():
                    f.write(f"  - {pair}: {count}개 그룹\n")

    print(f"요약 결과 저장: {summary_path}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description="위치추가 CSV 파일들의 중복 작업 분석 (EPSG:5179 기준)"
    )
    parser.add_argument(
        "--output-dir", default="results", help="출력 디렉토리 (기본: results)"
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="EPSG:5179 좌표 허용 오차 미터 단위 (기본: 1.0m)",
    )
    parser.add_argument("--verbose", action="store_true", help="상세 정보 출력")

    args = parser.parse_args()

    print("=" * 80)
    print("중복 분석 시작 (EPSG:5179 좌표계 기준)")
    print("=" * 80)

    try:
        # 1. 파일 로드 및 검증
        print("\n1. 파일 로드 및 필수 컬럼 확인...")
        file_data = load_files()

        print(f"   ✓ {len(file_data)}개 파일 로드 완료")
        for file_name in file_data.keys():
            print(f"     - {file_name}")

        # 2. 각 파일별 중복 확인
        print("\n2. 파일별 중복 확인...")
        all_duplicates = {}

        for file_name, df in file_data.items():
            if args.verbose:
                print(f"\n   처리 중: {file_name}")

            duplicates = find_duplicates(df, file_name, args.tolerance, args.verbose)

            if len(duplicates) > 0:
                all_duplicates[file_name] = duplicates
                group_count = duplicates.groupby(
                    ["작업일자", "x_rounded", "y_rounded"]
                ).ngroups
                print(
                    f"   - {file_name}: {len(duplicates)}개 중복 발견 ({group_count}개 그룹)"
                )
            else:
                print(f"   - {file_name}: 중복 없음")

        # 3. 파일 간 중복 확인
        print("\n3. 파일 간 중복 확인...")
        cross_duplicates = find_cross_file_duplicates(
            file_data, args.tolerance, args.verbose
        )

        if len(cross_duplicates) > 0:
            group_count = cross_duplicates.groupby(
                ["작업일자", "x_rounded", "y_rounded"]
            ).ngroups
            print(
                f"   - 파일 간 중복: {len(cross_duplicates)}개 발견 ({group_count}개 그룹)"
            )
        else:
            print(f"   - 파일 간 중복: 없음")

        # 4. 결과 출력
        print_results(all_duplicates, cross_duplicates, args.tolerance)

        # 5. 결과 저장
        print("\n4. 결과 저장...")
        save_results(all_duplicates, cross_duplicates, args.output_dir, args.tolerance)

        print("\n" + "=" * 80)
        print("중복 분석 완료")
        print("=" * 80)

    except ValueError as e:
        print(f"\n오류 발생: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n파일 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n예상치 못한 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
