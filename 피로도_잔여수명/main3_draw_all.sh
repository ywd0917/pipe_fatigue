#!/bin/bash

# Soil (지질) 데이터 시각화 - 모든 이미지 생성 스크립트
# 
# 이 스크립트는 main3_draw_soil.py를 사용하여
# 1) 통합 지질도 이미지
# 2) 각 레이어별 개별 이미지
# 3) 특정 필드별 그룹화 이미지를 생성합니다.

echo "=========================================="
echo "Soil (지질) 데이터 시각화 - 전체 이미지 생성"
echo "=========================================="
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Python 스크립트 경로
PYTHON_SCRIPT="src/main3_draw_soil.py"

# 결과 디렉토리 생성
mkdir -p results

# 시작 시간 기록
start_time=$(date +%s)

# 카운터 초기화
total_tasks=13
current_task=0

# 1. 전체 통합 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] 전체 통합 지질도 생성 중..."
output_file="results/soil_integrated.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --output "$output_file" \
    --title "지질도 통합 시각화" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ 전체 통합 지질도 생성 완료"
else
    echo "✗ 전체 통합 지질도 생성 실패"
fi
echo ""

# 2. Litho age별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Litho age별 시각화 생성 중..."
output_file="results/soil_Litho_age.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Litho \
    --group-by age \
    --output "$output_file" \
    --title "암상 분포도 - 지질시대별" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Litho age별 시각화 생성 완료"
else
    echo "✗ Litho age별 시각화 생성 실패"
fi
echo ""

# 3. Litho lithoidx별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Litho lithoidx별 시각화 생성 중..."
output_file="results/soil_Litho_lithoidx.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Litho \
    --group-by lithoidx \
    --output "$output_file" \
    --title "암상 분포도 - 암석 종류별" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Litho lithoidx별 시각화 생성 완료"
else
    echo "✗ Litho lithoidx별 시각화 생성 실패"
fi
echo ""

# 4. Boundary TYPE별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Boundary TYPE별 시각화 생성 중..."
output_file="results/soil_Boundary_TYPE.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Boudary \
    --group-by TYPE \
    --output "$output_file" \
    --title "지질 경계선 - 유형별" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Boundary TYPE별 시각화 생성 완료"
else
    echo "✗ Boundary TYPE별 시각화 생성 실패"
fi
echo ""

# 5. Fault TYPE별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Fault TYPE별 시각화 생성 중..."
output_file="results/soil_Fault_TYPE.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Fault \
    --group-by TYPE \
    --output "$output_file" \
    --title "단층선 - 유형별" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Fault TYPE별 시각화 생성 완료"
else
    echo "✗ Fault TYPE별 시각화 생성 실패"
fi
echo ""

# 6. Frame MAPNAME별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Frame MAPNAME별 시각화 생성 중..."
output_file="results/soil_Frame_MAPNAME.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Frame \
    --group-by MAPNAME \
    --output "$output_file" \
    --title "도엽 경계 - 지역별" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Frame MAPNAME별 시각화 생성 완료"
else
    echo "✗ Frame MAPNAME별 시각화 생성 실패"
fi
echo ""

# 7-10. 각 레이어별 개별 시각화
declare -a layers=("frame" "litho" "boundary" "fault")
declare -a layer_names=("도엽 경계" "암상 분포" "지질 경계" "단층선")

for i in "${!layers[@]}"; do
    current_task=$((current_task + 1))
    layer="${layers[$i]}"
    layer_name="${layer_names[$i]}"
    output_file="results/soil_layer_${layer}.png"
    
    echo "[$current_task/$total_tasks] ${layer_name} 레이어만 시각화 생성 중..."
    echo "출력 파일: ${output_file}"
    
    python "$PYTHON_SCRIPT" \
        --layer "$layer" \
        --output "$output_file" \
        --title "${layer_name} 레이어" \
        --no-interactive
    
    if [ $? -eq 0 ]; then
        echo "✓ ${layer_name} 레이어 시각화 생성 완료"
    else
        echo "✗ ${layer_name} 레이어 시각화 생성 실패"
    fi
    echo ""
done

# 11. Litho + Fault 조합
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Litho + Fault 조합 시각화 생성 중..."
output_file="results/soil_litho_fault.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --layer litho fault \
    --output "$output_file" \
    --title "암상 분포 및 단층선" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Litho + Fault 조합 시각화 생성 완료"
else
    echo "✗ Litho + Fault 조합 시각화 생성 실패"
fi
echo ""

# 12. Frame 없이 Litho age별 시각화
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Frame 배경 없이 Litho age별 시각화 생성 중..."
output_file="results/soil_Litho_age_noframe.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --file Litho \
    --group-by age \
    --no-frame \
    --output "$output_file" \
    --title "암상 분포도 - 지질시대별 (Frame 없음)" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Frame 없이 Litho age별 시각화 생성 완료"
else
    echo "✗ Frame 없이 Litho age별 시각화 생성 실패"
fi
echo ""

# 13. Boundary + Fault 조합 (선 레이어만)
current_task=$((current_task + 1))
echo "[$current_task/$total_tasks] Boundary + Fault 조합 시각화 생성 중..."
output_file="results/soil_boundary_fault.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --layer boundary fault \
    --output "$output_file" \
    --title "지질 경계선 및 단층선" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ Boundary + Fault 조합 시각화 생성 완료"
else
    echo "✗ Boundary + Fault 조합 시각화 생성 실패"
fi

# 종료 시간 및 소요 시간 계산
end_time=$(date +%s)
elapsed_time=$((end_time - start_time))

echo ""
echo "=========================================="
echo "모든 이미지 생성 완료!"
echo "소요 시간: ${elapsed_time}초"
echo ""
echo "생성된 통합 시각화 파일:"
ls -la results/soil_integrated.png 2>/dev/null | awk '{print "  - " $9 " (" $5 " bytes)"}'
echo ""
echo "생성된 개별 파일 시각화:"
ls -la results/soil_*_*.png 2>/dev/null | grep -v "integrated" | grep -v "layer" | awk '{print "  - " $9 " (" $5 " bytes)"}'
echo ""
echo "생성된 레이어별 시각화:"
ls -la results/soil_layer_*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 " bytes)"}'
echo "=========================================="