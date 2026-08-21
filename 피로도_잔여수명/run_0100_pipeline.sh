#!/bin/bash
# 0100(사라봉) + 0200(고성) 지역 관로 피로도 업데이트 파이프라인
# 새 압력 데이터가 추가된 후 이 스크립트를 실행하여 피로도 CSV 및 DB를 갱신합니다.
#
# 입력:
#   data/raw/export_shp_20250704(0100)/상수관로_사라봉1.shp
#   data/raw/export_shp_20250704(0100)/급수관로_사라봉1.shp
#   data/raw/export_shp_20250704(0200)/상수관로_고성.shp
#   data/raw/export_shp_20250704(0200)/급수관로_고성.shp
#   DB: 61.85.1.119:4306 supply_meter (manage_id=300111, 300027)
#
# 출력:
#   results/tmp/0100_fatigue_merged_zone_fixed.csv
#   results/tmp/0200_fatigue_merged_zone_fixed.csv

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log_step() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$(ts)] STEP $1: $2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}
log_ok() { echo "[$(ts)] ✓ $1"; }

start_time=$(date +%s)

echo "=================================================================="
echo "0100(사라봉) + 0200(고성) 관로 피로도 업데이트 파이프라인"
echo "시작: $(ts)"
echo "=================================================================="

log_step 1 "0100(사라봉) 피로도 계산 — src/tmp/make_0100_fatigue_csv.py"
uv run python src/tmp/make_0100_fatigue_csv.py
log_ok "make_0100_fatigue_csv.py 완료"

log_step 2 "0200(고성) 피로도 계산 — src/tmp/make_0200_fatigue_csv.py"
uv run python src/tmp/make_0200_fatigue_csv.py
log_ok "make_0200_fatigue_csv.py 완료"

end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo ""
echo "=================================================================="
echo "0100/0200 파이프라인 완료 | 소요 시간: ${elapsed}초"
echo ""
echo "생성/갱신된 결과 파일:"
echo "  results/tmp/0100_fatigue_merged_zone_fixed.csv"
echo "  results/tmp/0200_fatigue_merged_zone_fixed.csv"
echo "=================================================================="
