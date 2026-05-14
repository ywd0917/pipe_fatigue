#!/bin/bash
# 관로 피로도 업데이트 파이프라인
# 새 압력 데이터가 추가된 후 이 스크립트를 실행하여 피로도 CSV를 갱신합니다.
#
# 실행 순서:
#   1. main56_calc_fatigure.py  - K_repair 반영 피로도 계산
#   2. main57_merge_fatigue.py  - PIPE_LM + SPLY_LS 병합
#   3. src/tmp/make_0100_fatigue_csv.py - 0100(사라봉) 지역 피로도 계산

set -euo pipefail

# ── 경로 설정 ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ── 타임스탬프 함수 ────────────────────────────────────────────────────────
ts() { date '+%Y-%m-%d %H:%M:%S'; }

log_step() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$(ts)] STEP $1: $2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

log_ok()   { echo "[$(ts)] ✓ $1"; }
log_fail() { echo "[$(ts)] ✗ $1" >&2; }

# ── 시작 ──────────────────────────────────────────────────────────────────
start_time=$(date +%s)

echo "=================================================================="
echo "관로 피로도 업데이트 파이프라인"
echo "시작: $(ts)"
echo "작업 디렉토리: $SCRIPT_DIR"
echo "=================================================================="

# ── STEP 1: 피로도 계산 (K_repair 포함) ─────────────────────────────────
log_step 1 "피로도 계산 (K_repair 포함) — main56_calc_fatigure.py"
uv run python src/main56_calc_fatigure.py
log_ok "main56_calc_fatigure.py 완료"

# ── STEP 2: PIPE_LM + SPLY_LS 병합 ──────────────────────────────────────
log_step 2 "피로도 CSV 병합 — main57_merge_fatigue.py"
uv run python src/main57_merge_fatigue.py
log_ok "main57_merge_fatigue.py 완료"

# ── STEP 3: 0100(사라봉) 지역 피로도 ────────────────────────────────────
log_step 3 "0100(사라봉) 피로도 계산 — src/tmp/make_0100_fatigue_csv.py"
uv run python src/tmp/make_0100_fatigue_csv.py
log_ok "make_0100_fatigue_csv.py 완료"

# ── 완료 요약 ─────────────────────────────────────────────────────────────
end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo ""
echo "=================================================================="
echo "파이프라인 완료"
echo "종료: $(ts)"
echo "소요 시간: ${elapsed}초"
echo ""
echo "생성/갱신된 결과 파일:"
echo "  results/main56_calc_fatigure/fatigue_pipe_lm.csv"
echo "  results/main56_calc_fatigure/fatigue_sply_ls.csv"
echo "  results/main57_merge_fatigue/ (병합 CSV)"
echo "  results/tmp/0100_fatigue_merged_zone_fixed.csv"
echo "=================================================================="
