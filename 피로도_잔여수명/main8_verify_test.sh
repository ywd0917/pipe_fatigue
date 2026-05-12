#!/bin/bash

# 파이프-도로 중첩 검증 - 특정 케이스 테스트 스크립트
# 
# 이 스크립트는 main8_verify_overlap_samples.py를 사용하여
# 지정된 4가지 케이스를 실행합니다:
# - 0520 × PIPE_LM
# - 0520 × SPLY_LS
# - 0903 × PIPE_LM  
# - 0903 × SPLY_LS

echo "=========================================="
echo "파이프-도로 중첩 검증 - 4가지 케이스 테스트"
echo "=========================================="
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Python 스크립트 경로
PYTHON_SCRIPT="src/main8_verify_overlap_samples.py"

# 결과 디렉토리 생성
mkdir -p results/overlap_verification

# 시작 시간 기록
start_time=$(date +%s)

# 테스트 케이스 정의
declare -a REGION_CODES=("0520" "0520" "0903" "0903")
declare -a PIPE_TYPES=("pipe" "sply" "pipe" "sply")
declare -a PIPE_NAMES=("PIPE_LM" "SPLY_LS" "PIPE_LM" "SPLY_LS")

# 샘플 크기
SAMPLE_SIZE=16

echo "테스트 설정:"
echo "  - 샘플 크기: $SAMPLE_SIZE"
echo "  - 테스트 케이스:"
echo "    1) 0520 × PIPE_LM"
echo "    2) 0520 × SPLY_LS"
echo "    3) 0903 × PIPE_LM"
echo "    4) 0903 × SPLY_LS"
echo ""
echo "=========================================="

# 성공/실패 카운터
success_count=0
fail_count=0

# 4가지 케이스 실행
for i in ${!REGION_CODES[@]}; do
    region_code="${REGION_CODES[$i]}"
    pipe_type="${PIPE_TYPES[$i]}"
    pipe_name="${PIPE_NAMES[$i]}"
    
    echo ""
    echo "=== 케이스 $((i+1))/4: $region_code × $pipe_name ==="
    
    # 현재 시간을 이용한 고유 파일명 생성
    timestamp=$(date +%Y%m%d_%H%M%S)
    output_file="results/overlap_verification/case_$((i+1))_${timestamp}_${region_code}_${pipe_type}.png"
    
    echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "출력 파일: $output_file"
    echo ""
    
    # Python 스크립트 실행
    python "$PYTHON_SCRIPT" \
        "$region_code" \
        --pipe-type "$pipe_type" \
        --sample-size "$SAMPLE_SIZE" \
        --output-dir "results/overlap_verification" 2>&1 | tee /tmp/verify_test_$((i+1)).log
    
    # 실행 결과 확인
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo ""
        echo "✓ 케이스 $((i+1)) 완료: $region_code × $pipe_name"
        success_count=$((success_count + 1))
        
        # 로그에서 통계 정보 추출
        echo "통계 정보:"
        grep -E "(매칭|샘플 선택)" /tmp/verify_test_$((i+1)).log | sed 's/^/  /'
        
        # 생성된 파일 정보
        generated_file=$(ls -t results/overlap_verification/verification_${region_code}_${pipe_type}_samples.png 2>/dev/null | head -1)
        if [ -f "$generated_file" ]; then
            file_size=$(ls -lh "$generated_file" 2>/dev/null | awk '{print $5}')
            echo "  파일: $(basename "$generated_file") ($file_size)"
        fi
    else
        echo ""
        echo "✗ 케이스 $((i+1)) 실패: $region_code × $pipe_name"
        fail_count=$((fail_count + 1))
    fi
    
    echo "종료 시간: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "----------------------------------------"
done

# 종료 시간 및 소요 시간 계산
end_time=$(date +%s)
elapsed_time=$((end_time - start_time))

# 임시 로그 파일 정리
rm -f /tmp/verify_test_*.log

echo ""
echo "=========================================="
echo "모든 테스트 완료!"
echo "=========================================="
echo ""
echo "실행 결과:"
echo "  - 성공: $success_count/4"
echo "  - 실패: $fail_count/4"
echo "  - 총 소요 시간: ${elapsed_time}초"
echo ""
echo "생성된 파일들:"
ls -la results/overlap_verification/*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 " bytes)"}'

# 총 파일 수와 크기
total_files=$(ls results/overlap_verification/*.png 2>/dev/null | wc -l)
total_size=$(du -sh results/overlap_verification 2>/dev/null | cut -f1)

echo ""
echo "총 파일 수: $total_files개"
echo "총 디렉토리 크기: $total_size"
echo "=========================================="