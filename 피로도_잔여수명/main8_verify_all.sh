#!/bin/bash

# 파이프-도로 중첩 검증 - 모든 샘플 이미지 생성 스크립트
# 
# 이 스크립트는 main8_verify_overlap_samples.py를 사용하여
# 1) 모든 지역 코드에 대한 검증 이미지
# 2) pipe와 sply 유형 모두 처리
# 3) 다양한 샘플 크기로 테스트를 수행합니다.

echo "=========================================="
echo "파이프-도로 중첩 검증 - 전체 샘플 생성"
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

# traffic 디렉토리에서 지역 코드 추출
echo "지역 코드 탐색 중..."
TRAFFIC_DIR="results/traffic"

if [ ! -d "$TRAFFIC_DIR" ]; then
    echo "오류: traffic 디렉토리를 찾을 수 없습니다: $TRAFFIC_DIR"
    exit 1
fi

# CSV 파일에서 지역 코드 추출
declare -a REGION_CODES=()
for csv_file in "$TRAFFIC_DIR"/*_traffic.csv; do
    if [ -f "$csv_file" ]; then
        basename_csv=$(basename "$csv_file")
        # 파일명에서 지역 코드 추출 (예: 0520_pipe_traffic.csv -> 0520)
        region_code=$(echo "$basename_csv" | cut -d'_' -f1)
        # 중복 제거
        if [[ ! " ${REGION_CODES[@]} " =~ " ${region_code} " ]]; then
            REGION_CODES+=("$region_code")
        fi
    fi
done

# 지역 코드 정렬 (더 안전한 방법)
readarray -t REGION_CODES < <(printf '%s\n' "${REGION_CODES[@]}" | sort -u)

echo "발견된 지역 코드: ${#REGION_CODES[@]}개"
for code in "${REGION_CODES[@]}"; do
    echo "  - $code"
done
echo ""

# 파이프 유형 배열
declare -a PIPE_TYPES=("pipe" "sply")
declare -a PIPE_NAMES=("배수관" "급수관")

# 샘플 크기 배열
declare -a SAMPLE_SIZES=(8 12 16 20)

# 전체 작업 수 계산 (기본 실행 테스트 2개 추가)
total_tasks=$((${#REGION_CODES[@]} * ${#PIPE_TYPES[@]} * ${#SAMPLE_SIZES[@]} + 2))
current_task=0

echo "총 작업 수: $total_tasks"
echo "=========================================="
echo ""

# 각 지역 코드별로 처리
for region_code in "${REGION_CODES[@]}"; do
    echo "=== 지역 코드: $region_code 처리 중 ==="
    
    # 각 파이프 유형별로 처리
    for i in "${!PIPE_TYPES[@]}"; do
        pipe_type="${PIPE_TYPES[$i]}"
        pipe_name="${PIPE_NAMES[$i]}"
        
        # 각 샘플 크기별로 처리
        for sample_size in "${SAMPLE_SIZES[@]}"; do
            current_task=$((current_task + 1))
            
            echo ""
            echo "[$current_task/$total_tasks] $region_code - $pipe_name - 샘플 $sample_size개 생성 중..."
            
            # Python 스크립트 실행
            python "$PYTHON_SCRIPT" \
                "$region_code" \
                --pipe-type "$pipe_type" \
                --sample-size "$sample_size" \
                --output-dir "results/overlap_verification"
            
            # 실행 결과 확인
            if [ $? -eq 0 ]; then
                echo "✓ $region_code - $pipe_name - 샘플 $sample_size개 생성 완료"
                # 생성된 파일 확인 (실제 파일명은 샘플 크기를 포함하지 않음)
                generated_file="results/overlap_verification/verification_${region_code}_${pipe_type}_samples.png"
                if [ -f "$generated_file" ]; then
                    file_size=$(ls -lh "$generated_file" | awk '{print $5}')
                    echo "  파일: $generated_file ($file_size)"
                fi
            else
                echo "✗ $region_code - $pipe_name - 샘플 $sample_size개 생성 실패"
            fi
        done
    done
    
    echo ""
done

# 기본 실행 테스트 (지역 코드 없이)
echo "=========================================="
echo "기본 실행 테스트 (지역 코드 자동 선택)"
echo "=========================================="

current_task=$((current_task + 1))
echo ""
echo "[$current_task/$total_tasks] 기본 실행 - 배수관 검증 중..."

python "$PYTHON_SCRIPT"

if [ $? -eq 0 ]; then
    echo "✓ 기본 실행 - 배수관 검증 완료"
else
    echo "✗ 기본 실행 - 배수관 검증 실패"
fi

current_task=$((current_task + 1))
echo ""
echo "[$current_task/$total_tasks] 기본 실행 - 급수관 검증 중..."

python "$PYTHON_SCRIPT" --pipe-type sply

if [ $? -eq 0 ]; then
    echo "✓ 기본 실행 - 급수관 검증 완료"
else
    echo "✗ 기본 실행 - 급수관 검증 실패"
fi

# 종료 시간 및 소요 시간 계산
end_time=$(date +%s)
elapsed_time=$((end_time - start_time))

echo ""
echo "=========================================="
echo "모든 검증 이미지 생성 완료!"
echo "소요 시간: ${elapsed_time}초"
echo ""
echo "생성된 검증 이미지 파일:"
ls -la results/overlap_verification/verification_*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 " bytes)"}'

# 총 파일 수와 크기
total_files=$(ls results/overlap_verification/verification_*.png 2>/dev/null | wc -l)
total_size=$(du -sh results/overlap_verification 2>/dev/null | cut -f1)

echo ""
echo "총 파일 수: $total_files개"
echo "총 디렉토리 크기: $total_size"
echo "=========================================="