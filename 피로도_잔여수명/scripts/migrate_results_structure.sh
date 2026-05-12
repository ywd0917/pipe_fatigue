#!/bin/bash

# main51-55 결과 파일을 새 폴더 구조로 이동
# 실행 전에 백업 권장: cp -r results results.backup

set -e  # 에러 발생 시 중단

echo "=== main51-55 결과 파일 구조 재정리 ==="
echo ""

# main51
echo "📁 main51_find_freq 처리 중..."
mkdir -p results/main51_find_freq
if ls results/frequency_spectrum_*.png 1> /dev/null 2>&1; then
    mv results/frequency_spectrum_*.png results/main51_find_freq/
    echo "  ✓ frequency_spectrum_*.png 이동 완료"
else
    echo "  ⚠ frequency_spectrum_*.png 없음 (이미 이동 또는 미생성)"
fi
if [ -f results/component_separation_analysis.png ]; then
    mv results/component_separation_analysis.png results/main51_find_freq/
    echo "  ✓ component_separation_analysis.png 이동 완료"
else
    echo "  ⚠ component_separation_analysis.png 없음"
fi

# main52
echo ""
echo "📁 main52_pass_filter 처리 중..."
mkdir -p results/main52_pass_filter
if ls results/valley_based_filter_*.png 1> /dev/null 2>&1; then
    mv results/valley_based_filter_*.png results/main52_pass_filter/
    echo "  ✓ valley_based_filter_*.png 이동 완료"
else
    echo "  ⚠ valley_based_filter_*.png 없음 (이미 이동 또는 미생성)"
fi

# main53
echo ""
echo "📁 main53_rainflow 처리 중..."
mkdir -p results/main53_rainflow
moved=0
if ls results/rainflow_*.png 1> /dev/null 2>&1; then
    mv results/rainflow_*.png results/main53_rainflow/
    echo "  ✓ rainflow_*.png 이동 완료"
    ((moved++))
fi
if ls results/cumulative_*.png 1> /dev/null 2>&1; then
    mv results/cumulative_*.png results/main53_rainflow/
    echo "  ✓ cumulative_*.png 이동 완료"
    ((moved++))
fi
if [ -f results/fatigue_comparison.csv ]; then
    mv results/fatigue_comparison.csv results/main53_rainflow/
    echo "  ✓ fatigue_comparison.csv 이동 완료"
    ((moved++))
fi
if [ $moved -eq 0 ]; then
    echo "  ⚠ main53 파일 없음 (이미 이동 또는 미생성)"
fi

# main54
echo ""
echo "📁 main54_pipe_data 처리 중..."
mkdir -p results/main54_pipe_data
if [ -f results/pipe_data_sample.csv ]; then
    mv results/pipe_data_sample.csv results/main54_pipe_data/
    echo "  ✓ pipe_data_sample.csv 이동 완료"
else
    echo "  ⚠ pipe_data_sample.csv 없음 (이미 이동 또는 미생성)"
fi

# main55
echo ""
echo "📁 main55_calc_fatigure 처리 중..."
mkdir -p results/main55_calc_fatigure
moved=0
if [ -f results/fatigue_pipe_lm_by_age.csv ]; then
    mv results/fatigue_pipe_lm_by_age.csv results/main55_calc_fatigure/
    echo "  ✓ fatigue_pipe_lm_by_age.csv 이동 완료"
    ((moved++))
fi
if [ -f results/fatigue_sply_ls_by_age.csv ]; then
    mv results/fatigue_sply_ls_by_age.csv results/main55_calc_fatigure/
    echo "  ✓ fatigue_sply_ls_by_age.csv 이동 완료"
    ((moved++))
fi
if [ $moved -eq 0 ]; then
    echo "  ⚠ main55 파일 없음 (이미 이동 또는 미생성)"
fi

echo ""
echo "=== 이동 완료 ==="
echo ""
echo "📂 새 폴더 구조:"
ls -la results/main5*/ 2>/dev/null || echo "  (생성된 폴더 없음)"
