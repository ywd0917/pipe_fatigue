#!/usr/bin/env python3
"""
데이터 품질 체크 스크립트
520 지역 데이터의 품질을 검증합니다.
"""

import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from src.common.config import DATA_DIR

warnings.filterwarnings("ignore")


class DataQualityChecker:
    """데이터 품질 검사 클래스"""

    def __init__(self, data_path: str | None = None):
        """
        초기화

        Args:
            data_path: 데이터 파일 경로
        """
        self.data_path = (
            data_path or DATA_DIR / "520_area" / "repairs_with_location_520_v3.csv"
        )
        self.df = None
        self.quality_report = {}

    def load_data(self) -> bool:
        """데이터 로드"""
        try:
            self.df = pd.read_csv(self.data_path, encoding="utf-8-sig")
            print(f"✓ 데이터 로드 성공: {len(self.df)} 레코드")
            return True
        except Exception as e:
            print(f"✗ 데이터 로드 실패: {e}")
            return False

    def check_coordinates(self) -> dict[str, any]:
        """좌표 유효성 검사"""
        print("\n=== 좌표 유효성 검사 ===")

        results = {
            "valid": True,
            "total": len(self.df),
            "invalid_count": 0,
            "invalid_records": [],
        }

        # 한국 좌표 범위 (WGS84)
        LAT_MIN, LAT_MAX = 33.0, 43.0
        LON_MIN, LON_MAX = 124.0, 132.0

        # 좌표 컬럼 찾기 (영문 또는 한글)
        lat_col = None
        lon_col = None

        if "latitude" in self.df.columns and "longitude" in self.df.columns:
            lat_col, lon_col = "latitude", "longitude"
        elif "위도" in self.df.columns and "경도" in self.df.columns:
            lat_col, lon_col = "위도", "경도"

        if lat_col and lon_col:
            invalid_mask = (
                (self.df[lat_col] < LAT_MIN)
                | (self.df[lat_col] > LAT_MAX)
                | (self.df[lon_col] < LON_MIN)
                | (self.df[lon_col] > LON_MAX)
                | self.df[lat_col].isna()
                | self.df[lon_col].isna()
            )

            results["invalid_count"] = invalid_mask.sum()
            results["invalid_records"] = self.df[invalid_mask].index.tolist()
            results["valid"] = results["invalid_count"] == 0

            if results["valid"]:
                print(
                    f"✓ 모든 좌표가 유효 범위 내에 있음 (lat: {LAT_MIN}-{LAT_MAX}°, lon: {LON_MIN}-{LON_MAX}°)"
                )
            else:
                print(
                    f"✗ {results['invalid_count']}개 레코드의 좌표가 유효 범위를 벗어남"
                )
                print(f"  문제 레코드 인덱스: {results['invalid_records'][:5]}...")
        else:
            print("✗ 좌표 컬럼을 찾을 수 없음")
            results["valid"] = False

        self.quality_report["coordinates"] = results
        return results

    def check_dates(self) -> dict[str, any]:
        """날짜 유효성 검사"""
        print("\n=== 날짜 유효성 검사 ===")

        results = {
            "valid": True,
            "total": len(self.df),
            "invalid_count": 0,
            "invalid_records": [],
            "date_range": None,
        }

        # 날짜 컬럼 찾기
        date_column = None
        for col in ["작업종료일", "작업일자", "date", "Date"]:
            if col in self.df.columns:
                date_column = col
                break

        if date_column:
            # 날짜 파싱
            if date_column == "작업종료일":
                # YYYYMMDDHHMM 형식
                dates = pd.to_datetime(
                    self.df[date_column].astype(str).str[:8],
                    format="%Y%m%d",
                    errors="coerce",
                )
            else:
                dates = pd.to_datetime(self.df[date_column], errors="coerce")

            # 유효 날짜 범위 (2000년 이후)
            MIN_DATE = pd.Timestamp("2000-01-01")
            MAX_DATE = pd.Timestamp.now()

            invalid_mask = dates.isna() | (dates < MIN_DATE) | (dates > MAX_DATE)
            results["invalid_count"] = invalid_mask.sum()
            results["invalid_records"] = self.df[invalid_mask].index.tolist()
            results["valid"] = results["invalid_count"] == 0
            results["date_range"] = (dates.min(), dates.max())

            if results["valid"]:
                print("✓ 모든 날짜가 유효 범위 내에 있음 (2000-현재)")
                print(f"  날짜 범위: {dates.min()} ~ {dates.max()}")
            else:
                print(f"✗ {results['invalid_count']}개 레코드의 날짜가 유효하지 않음")
        else:
            print("✗ 날짜 컬럼을 찾을 수 없음")
            results["valid"] = False

        self.quality_report["dates"] = results
        return results

    def check_duplicates(self) -> dict[str, any]:
        """중복 항목 검사"""
        print("\n=== 중복 항목 검사 ===")

        results = {
            "valid": True,
            "total": len(self.df),
            "duplicate_count": 0,
            "duplicate_records": [],
        }

        # 중복 검사 키 컬럼
        key_columns = []

        # 좌표 컬럼 찾기
        if "latitude" in self.df.columns and "longitude" in self.df.columns:
            key_columns.extend(["latitude", "longitude"])
        elif "위도" in self.df.columns and "경도" in self.df.columns:
            key_columns.extend(["위도", "경도"])

        for col in ["작업종료일", "작업일자", "date", "Date"]:
            if col in self.df.columns:
                key_columns.append(col)
                break

        if key_columns:
            duplicates = self.df.duplicated(subset=key_columns, keep="first")
            results["duplicate_count"] = duplicates.sum()
            results["duplicate_records"] = self.df[duplicates].index.tolist()
            results["valid"] = results["duplicate_count"] == 0

            if results["valid"]:
                print("✓ 중복 항목 없음 (위치 & 날짜 기준)")
            else:
                print(f"✗ {results['duplicate_count']}개 중복 항목 발견")
                print(f"  중복 레코드 인덱스: {results['duplicate_records'][:5]}...")
        else:
            print("⚠️ 중복 검사를 위한 키 컬럼이 부족함")

        self.quality_report["duplicates"] = results
        return results

    def check_encoding(self) -> dict[str, any]:
        """인코딩 검사"""
        print("\n=== 인코딩 검사 ===")

        results = {"valid": True, "address_columns": [], "encoding_issues": []}

        # 주소 관련 컬럼 찾기
        address_cols = ["주소", "상세주소", "address", "Address", "소재지"]
        found_cols = [col for col in address_cols if col in self.df.columns]

        results["address_columns"] = found_cols

        if found_cols:
            for col in found_cols:
                # 한글 포함 여부 확인
                korean_pattern = r"[가-힣]"
                has_korean = (
                    self.df[col]
                    .astype(str)
                    .str.contains(korean_pattern, na=False)
                    .any()
                )

                if has_korean:
                    print(f"✓ {col}: 한글 인코딩 정상")
                else:
                    print(f"⚠️ {col}: 한글이 없거나 인코딩 문제 가능성")
                    results["encoding_issues"].append(col)

            results["valid"] = len(results["encoding_issues"]) == 0
        else:
            print("⚠️ 주소 관련 컬럼을 찾을 수 없음")

        self.quality_report["encoding"] = results
        return results

    def check_repair_types(self) -> dict[str, any]:
        """재작업 타입 일관성 검사"""
        print("\n=== 재작업 타입 일관성 검사 ===")

        results = {
            "valid": True,
            "repair_column": None,
            "unique_types": [],
            "type_counts": {},
        }

        # 재작업 타입 컬럼 찾기
        repair_cols = ["repair_type", "작업유형", "누수원인소분류", "type", "Type"]

        for col in repair_cols:
            if col in self.df.columns:
                results["repair_column"] = col
                unique_types = self.df[col].unique()
                results["unique_types"] = [str(t) for t in unique_types if pd.notna(t)]
                results["type_counts"] = self.df[col].value_counts().to_dict()

                print(f"✓ 재작업 타입 컬럼: {col}")
                print(f"  고유 타입 수: {len(results['unique_types'])}")
                print("  타입별 분포:")
                for typ, count in results["type_counts"].items():
                    print(f"    - {typ}: {count}건")
                break

        if not results["repair_column"]:
            print("⚠️ 재작업 타입 컬럼을 찾을 수 없음")
            results["valid"] = False

        self.quality_report["repair_types"] = results
        return results

    def generate_summary(self) -> None:
        """품질 검사 요약"""
        print("\n" + "=" * 60)
        print("데이터 품질 검사 요약")
        print("=" * 60)

        all_valid = True

        for check_name, results in self.quality_report.items():
            if results.get("valid"):
                status = "✓ PASS"
            else:
                status = "✗ FAIL"
                all_valid = False

            print(f"{check_name.upper()}: {status}")

        print("\n" + "=" * 60)
        if all_valid:
            print("✓ 모든 데이터 품질 검사 통과")
        else:
            print("⚠️ 일부 데이터 품질 문제 발견")
        print("=" * 60)

    def save_report(self, output_path: str | None = None) -> None:
        """품질 검사 보고서 저장"""
        if not output_path:
            output_path = DATA_DIR.parent / "results" / "data_quality_report.txt"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("520 지역 데이터 품질 검사 보고서\n")
            f.write(f"생성 일시: {datetime.now()}\n")
            f.write(f"데이터 파일: {self.data_path}\n")
            f.write("=" * 60 + "\n\n")

            for check_name, results in self.quality_report.items():
                f.write(f"[{check_name.upper()}]\n")
                f.write(f"상태: {'PASS' if results.get('valid') else 'FAIL'}\n")

                if check_name == "coordinates":
                    f.write(f"무효 좌표: {results.get('invalid_count', 0)}개\n")
                elif check_name == "dates":
                    if results.get("date_range"):
                        f.write(
                            f"날짜 범위: {results['date_range'][0]} ~ {results['date_range'][1]}\n"
                        )
                    f.write(f"무효 날짜: {results.get('invalid_count', 0)}개\n")
                elif check_name == "duplicates":
                    f.write(f"중복 항목: {results.get('duplicate_count', 0)}개\n")
                elif check_name == "encoding":
                    f.write(
                        f"주소 컬럼: {', '.join(results.get('address_columns', []))}\n"
                    )
                elif check_name == "repair_types":
                    if results.get("unique_types"):
                        f.write(f"고유 타입: {len(results['unique_types'])}개\n")

                f.write("\n")

        print(f"\n보고서 저장: {output_path}")

    def run(self) -> bool:
        """전체 품질 검사 실행"""
        print("\n" + "=" * 60)
        print("520 지역 데이터 품질 검사")
        print("=" * 60)

        # 데이터 로드
        if not self.load_data():
            return False

        # 각 검사 수행
        self.check_coordinates()
        self.check_dates()
        self.check_duplicates()
        self.check_encoding()
        self.check_repair_types()

        # 요약 및 저장
        self.generate_summary()
        self.save_report()

        return True


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="520 지역 데이터 품질 검사")
    parser.add_argument("--data-path", type=str, help="데이터 파일 경로")
    parser.add_argument("--output", type=str, help="보고서 출력 경로")

    args = parser.parse_args()

    checker = DataQualityChecker(data_path=args.data_path)
    success = checker.run()

    if args.output:
        checker.save_report(args.output)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
