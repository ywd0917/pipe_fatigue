"""
main11g_fix_area_no.py 테스트 코드

주요 테스트:
1. 원본 CSV의 모든 컬럼이 보존되는지 확인
2. 컬럼 순서가 정확히 일치하는지 확인
3. 추가 컬럼이 없는지 확인
"""

from pathlib import Path

import pandas as pd
import pytest

# 하드코딩된 원본 컬럼 리스트 (16개)
EXPECTED_COLUMNS = [
    "ID",
    "작업일시",
    "위도",
    "경도",
    "파일타입",
    "공사명",
    "공사개요",
    "구군",
    "주소",
    "중구역번호",
    "소구역번호",
    "도로구분",
    "누수관경",
    "누수량",
    "용수구분",
    "용도구분",
]


class TestColumnPreservation:
    """컬럼 보존 관련 테스트"""

    def test_output_columns_match_input(self):
        """출력 파일의 컬럼이 원본과 일치하는지 확인"""
        # 결과 파일 경로
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        # 결과 파일 로드
        df = pd.read_csv(output_file)

        # 1. 컬럼 개수 확인
        assert (
            len(df.columns) == 16
        ), f"컬럼 개수가 일치하지 않습니다. 예상: 16, 실제: {len(df.columns)}"

        # 2. 컬럼 리스트 완전 일치 확인 (순서 포함)
        actual_columns = list(df.columns)
        assert (
            actual_columns == EXPECTED_COLUMNS
        ), f"컬럼이 일치하지 않습니다.\n예상: {EXPECTED_COLUMNS}\n실제: {actual_columns}"

        # 3. 각 컬럼이 존재하는지 개별 확인
        for col in EXPECTED_COLUMNS:
            assert col in df.columns, f"필수 컬럼 누락: {col}"

        # 4. 추가 컬럼이 없는지 확인
        extra_columns = set(df.columns) - set(EXPECTED_COLUMNS)
        assert len(extra_columns) == 0, f"추가 컬럼이 발견되었습니다: {extra_columns}"

    def test_no_matching_status_columns(self):
        """매칭 상태 컬럼이 제거되었는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 매칭 상태 컬럼이 없는지 확인
        assert "중구역_매칭" not in df.columns, "중구역_매칭 컬럼이 제거되지 않았습니다"
        assert "소구역_매칭" not in df.columns, "소구역_매칭 컬럼이 제거되지 않았습니다"

    def test_column_order_preservation(self):
        """컬럼 순서가 유지되는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 컬럼 순서를 인덱스로 확인
        for idx, expected_col in enumerate(EXPECTED_COLUMNS):
            actual_col = df.columns[idx]
            assert (
                actual_col == expected_col
            ), f"컬럼 순서 불일치 - 위치 {idx}: 예상 '{expected_col}', 실제 '{actual_col}'"


class TestDataIntegrity:
    """데이터 무결성 테스트"""

    def test_row_count_preserved(self):
        """행 개수가 유지되는지 확인"""
        input_file = Path(
            "data/main11e_fix_error/누수공사_통합_520_위치추가_20250917.csv"
        )
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not input_file.exists() or not output_file.exists():
            pytest.skip("입력 또는 출력 파일이 존재하지 않습니다")

        input_df = pd.read_csv(input_file)
        output_df = pd.read_csv(output_file)

        assert len(input_df) == len(output_df), (
            f"행 개수가 일치하지 않습니다. "
            f"입력: {len(input_df)}, 출력: {len(output_df)}"
        )

    def test_id_column_unchanged(self):
        """ID 컬럼이 변경되지 않았는지 확인"""
        input_file = Path(
            "data/main11e_fix_error/누수공사_통합_520_위치추가_20250917.csv"
        )
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not input_file.exists() or not output_file.exists():
            pytest.skip("입력 또는 출력 파일이 존재하지 않습니다")

        input_df = pd.read_csv(input_file)
        output_df = pd.read_csv(output_file)

        # ID 컬럼이 동일한지 확인
        assert input_df["ID"].equals(output_df["ID"]), "ID 컬럼이 변경되었습니다"

    def test_zone_numbers_updated(self):
        """중구역번호와 소구역번호가 업데이트되었는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 중구역번호가 520으로 통일되었는지 확인 (0520 지역이므로)
        # NaN이 아닌 값들 확인
        mdz_values = df["중구역번호"].dropna().unique()
        assert len(mdz_values) > 0, "중구역번호가 모두 NaN입니다"

        # 대부분의 중구역번호가 520인지 확인
        if 520 in mdz_values or "520" in mdz_values.astype(str):
            # 520이 가장 많은 값인지 확인
            value_counts = df["중구역번호"].value_counts()
            most_common = value_counts.index[0]
            assert str(most_common) == "520", f"가장 많은 중구역번호가 520이 아닙니다: {most_common}"

        # 소구역번호가 업데이트되었는지 확인 (NaN 감소)
        smz_notna_count = df["소구역번호"].notna().sum()
        assert smz_notna_count > 0, "소구역번호가 모두 NaN입니다"


class TestDataValidation:
    """데이터 유효성 검증 테스트"""

    def test_coordinate_validity(self):
        """위도/경도 값이 한국 범위 내에 있는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 한국의 위도/경도 범위
        # 위도: 33-43도, 경도: 124-132도
        valid_lat = df["위도"].between(33, 43)
        valid_lon = df["경도"].between(124, 132)

        assert valid_lat.all(), f"유효하지 않은 위도 값이 있습니다: {df[~valid_lat]['위도'].values}"
        assert valid_lon.all(), f"유효하지 않은 경도 값이 있습니다: {df[~valid_lon]['경도'].values}"

    def test_no_null_coordinates(self):
        """좌표에 null 값이 없는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        assert df["위도"].notna().all(), "위도에 null 값이 있습니다"
        assert df["경도"].notna().all(), "경도에 null 값이 있습니다"

    def test_zone_number_format(self):
        """구역 번호 형식이 올바른지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 중구역번호: 정수 또는 문자열로 된 숫자
        mdz_notna = df["중구역번호"].notna()
        if mdz_notna.any():
            # 520이 주요 값인지 확인
            mdz_values = df[mdz_notna]["중구역번호"].astype(str)
            assert mdz_values.str.match(r"^\d+$").all(), "중구역번호가 숫자 형식이 아닙니다"

        # 소구역번호: 3-4자리 문자열 (243, 0243 모두 허용)
        smz_notna = df["소구역번호"].notna()
        if smz_notna.any():
            smz_values = df[smz_notna]["소구역번호"].astype(str)
            assert smz_values.str.match(r"^\d{3,4}$").all(), "소구역번호가 3-4자리 숫자가 아닙니다"


class TestZoneMatching:
    """구역 매칭 정확성 테스트"""

    def test_all_520_zone_matched(self):
        """모든 중구역번호가 520인지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 중구역번호가 모두 520인지 확인
        mdz_values = df["중구역번호"].dropna().astype(str).unique()
        assert len(mdz_values) == 1, f"중구역번호가 여러 개입니다: {mdz_values}"
        assert mdz_values[0] == "520", f"중구역번호가 520이 아닙니다: {mdz_values[0]}"

    def test_valid_subzone_numbers(self):
        """소구역번호가 유효한 범위인지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 520 지역의 유효한 소구역번호 (실제 처리된 데이터 기반)
        # 3자리 형식으로 저장됨 (예: 243, 480 등)
        valid_subzones = ["240", "243", "461", "470", "480", "490", "580"]

        smz_values = df["소구역번호"].dropna().astype(str).unique()

        # 모든 소구역번호가 유효한 범위에 있는지 확인
        invalid_zones = [zone for zone in smz_values if zone not in valid_subzones]
        assert len(invalid_zones) == 0, f"유효하지 않은 소구역번호: {invalid_zones}"

    def test_zone_consistency(self):
        """중구역과 소구역의 일관성 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)

        # 중구역번호가 있으면 소구역번호도 있어야 함
        has_mdz = df["중구역번호"].notna()
        has_smz = df["소구역번호"].notna()

        # 중구역이 있는 경우 대부분 소구역도 있어야 함 (완벽하지 않을 수 있음)
        if has_mdz.any():
            consistency_rate = (has_mdz & has_smz).sum() / has_mdz.sum()
            assert consistency_rate > 0.8, f"중구역-소구역 일관성이 낮습니다: {consistency_rate:.1%}"


class TestDataComparison:
    """입력/출력 데이터 비교 테스트"""

    def test_non_zone_columns_unchanged(self):
        """구역번호 외 다른 컬럼 값이 변경되지 않았는지 확인"""
        input_file = Path(
            "data/main11e_fix_error/누수공사_통합_520_위치추가_20250917.csv"
        )
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not input_file.exists() or not output_file.exists():
            pytest.skip("입력 또는 출력 파일이 존재하지 않습니다")

        input_df = pd.read_csv(input_file)
        output_df = pd.read_csv(output_file)

        # 구역번호를 제외한 컬럼들 비교
        columns_to_check = ["공사명", "공사개요", "구군", "주소", "파일타입"]

        for col in columns_to_check:
            if col in input_df.columns and col in output_df.columns:
                assert input_df[col].equals(output_df[col]), f"{col} 컬럼이 변경되었습니다"

    def test_coordinate_columns_unchanged(self):
        """위도/경도 값이 변경되지 않았는지 확인"""
        input_file = Path(
            "data/main11e_fix_error/누수공사_통합_520_위치추가_20250917.csv"
        )
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not input_file.exists() or not output_file.exists():
            pytest.skip("입력 또는 출력 파일이 존재하지 않습니다")

        input_df = pd.read_csv(input_file)
        output_df = pd.read_csv(output_file)

        # 위도/경도 비교 (부동소수점 오차 고려)
        assert input_df["위도"].round(7).equals(output_df["위도"].round(7)), "위도 값이 변경되었습니다"
        assert input_df["경도"].round(7).equals(output_df["경도"].round(7)), "경도 값이 변경되었습니다"

    def test_datetime_format_preserved(self):
        """작업일시 형식이 보존되었는지 확인"""
        input_file = Path(
            "data/main11e_fix_error/누수공사_통합_520_위치추가_20250917.csv"
        )
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not input_file.exists() or not output_file.exists():
            pytest.skip("입력 또는 출력 파일이 존재하지 않습니다")

        input_df = pd.read_csv(input_file)
        output_df = pd.read_csv(output_file)

        # 작업일시 컬럼이 동일한지 확인
        assert input_df["작업일시"].equals(output_df["작업일시"]), "작업일시 형식이 변경되었습니다"


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_file_exists(self):
        """출력 파일이 생성되었는지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )
        assert output_file.exists(), f"출력 파일이 생성되지 않았습니다: {output_file}"

    def test_output_not_empty(self):
        """출력 파일이 비어있지 않은지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        df = pd.read_csv(output_file)
        assert len(df) > 0, "출력 파일이 비어있습니다"

    def test_encoding_utf8_bom(self):
        """파일 인코딩이 UTF-8 BOM인지 확인"""
        output_file = Path(
            "results/main11g_fix_area_no/누수공사_통합_520_위치추가_20250917_구역수정.csv"
        )

        if not output_file.exists():
            pytest.skip(f"출력 파일이 존재하지 않습니다: {output_file}")

        # 파일의 첫 3바이트 확인 (UTF-8 BOM: EF BB BF)
        with open(output_file, "rb") as f:
            bom = f.read(3)
            assert bom == b'\xef\xbb\xbf', "파일이 UTF-8 BOM으로 인코딩되지 않았습니다"


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"])