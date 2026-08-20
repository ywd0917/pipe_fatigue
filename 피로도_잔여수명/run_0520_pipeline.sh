#!/bin/bash
# 0520 지역 관로 피로도 업데이트 파이프라인
# 새 압력 데이터가 추가된 후 이 스크립트를 실행하여 피로도 CSV를 갱신합니다.
#
# 입력:
#   DB: 59.25.253.40:4334 supply_meter
#     - 0243 소구역 (manage_id=235)
#     - 0461 소구역 (manage_id=39232)
#     - 0470 소구역 (manage_id=39235)
#     - 0480 소구역 (manage_id=39233)
#     - 0490 소구역 (manage_id=39234)
#     - 0520 중구역 (manage_id=39227)
#
# 출력:
#   results/main56_calc_fatigure/fatigue_pipe_lm.csv
#   results/main56_calc_fatigure/fatigue_sply_ls.csv
#   results/main57_merge_fatigue/ (병합 CSV)

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
log_ok()   { echo "[$(ts)] ✓ $1"; }

start_time=$(date +%s)

echo "=================================================================="
echo "0520 지역 관로 피로도 업데이트 파이프라인"
echo "시작: $(ts)"
echo "=================================================================="

log_step 1 "피로도 계산 (K_repair 포함) — main56_calc_fatigure.py"
uv run python src/main56_calc_fatigure.py
log_ok "main56_calc_fatigure.py 완료"

log_step 2 "PIPE_LM + SPLY_LS 병합 — main57_merge_fatigue.py"
uv run python src/main57_merge_fatigue.py
log_ok "main57_merge_fatigue.py 완료"

end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo ""
echo "=================================================================="
echo "0520 파이프라인 완료 | 소요 시간: ${elapsed}초"
echo ""
echo "생성/갱신된 결과 파일:"
echo "  results/main56_calc_fatigure/fatigue_pipe_lm.csv"
echo "  results/main56_calc_fatigure/fatigue_sply_ls.csv"
echo "  results/main57_merge_fatigue/ (병합 CSV)"
echo "=================================================================="
