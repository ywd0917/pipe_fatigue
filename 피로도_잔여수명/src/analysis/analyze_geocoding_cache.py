#!/usr/bin/env python
"""캐시 파일 분석"""

import json
from pathlib import Path

cache_file = Path("results/geocoding_cache_kakao.json")

if cache_file.exists():
    with cache_file.open(encoding="utf-8") as f:
        data = json.load(f)

    print("=== Kakao Geocoding 캐시 분석 ===\n")
    print(f"캐시 파일: {cache_file}")
    print(
        f"파일 크기: {cache_file.stat().st_size:,} bytes ({cache_file.stat().st_size/1024/1024:.2f} MB)"
    )
    print(f"총 캐시 항목: {len(data)}개\n")

    # 상태별 통계
    stats = {"success": 0, "not_found": 0, "error": 0}
    for key, value in data.items():
        status = value.get("status", "unknown")
        if status in stats:
            stats[status] += 1

    print("상태별 통계:")
    print(
        f"  - 성공 (좌표 찾음): {stats['success']}개 ({stats['success']/len(data)*100:.1f}%)"
    )
    print(
        f"  - 실패 (주소 못찾음): {stats['not_found']}개 ({stats['not_found']/len(data)*100:.1f}%)"
    )
    print(f"  - 오류: {stats['error']}개")

    print("\n샘플 데이터 (처음 5개):")
    for i, (key, value) in enumerate(list(data.items())[:5]):
        addr = value.get("original_address", "N/A")
        status = value.get("status")
        if status == "success":
            lat = value.get("latitude")
            lon = value.get("longitude")
            print(f"{i+1}. {addr} → 성공 ({lat:.6f}, {lon:.6f})")
        else:
            print(f"{i+1}. {addr} → {status}")

    # 캐시 키 분석
    print("\n캐시 키 형식 (정규화된 주소):")
    sample_key = next(iter(data.keys()))
    sample_original = data[sample_key].get("original_address", "N/A")
    print(f"  원본: {sample_original}")
    print(f"  키: {sample_key}")
    print("  (소문자, 공백제거)")
else:
    print(f"캐시 파일이 없습니다: {cache_file}")
