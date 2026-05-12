#!/bin/bash

# GIS 데이터 시각화 - 모든 shapefile 이미지 생성 스크립트
# 
# 이 스크립트는 main2_draw_zone.py를 사용하여 
# 1) 4개의 Zone (LRGZ, MDLZ, SCDZ, SMLZ) 이미지
# 2) 기타 모든 shapefile의 FTR_IDN별 시각화 이미지를 생성합니다.

echo "=========================================="
echo "GIS 데이터 시각화 - 전체 이미지 생성"
echo "=========================================="
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Python 스크립트 경로
PYTHON_SCRIPT="src/main2_draw_zone.py"

# 결과 디렉토리 생성
mkdir -p results

# Zone 타입 배열
declare -a zones=("lrgz" "mdlz" "scdz" "smlz")
declare -a zone_names=("대블록(LRGZ)" "중블록(MDLZ)" "2차구역(SCDZ)" "소블록(SMLZ)")

# 시작 시간 기록
start_time=$(date +%s)

# 각 Zone별로 이미지 생성
for i in "${!zones[@]}"; do
    zone="${zones[$i]}"
    zone_name="${zone_names[$i]}"
    output_file="results/zone_${zone}.png"
    
    echo "[$((i+1))/4] ${zone_name} 생성 중..."
    echo "출력 파일: ${output_file}"
    
    # Python 스크립트 실행
    python "$PYTHON_SCRIPT" \
        --zone "$zone" \
        --output "$output_file" \
        --no-interactive
    
    # 실행 결과 확인
    if [ $? -eq 0 ]; then
        echo "✓ ${zone_name} 생성 완료"
    else
        echo "✗ ${zone_name} 생성 실패 (경고: 계속 진행)"
    fi
    
    echo ""
done

# 전체 Zone 표시 이미지도 생성
echo "[5/5] 전체 Zone 영역 생성 중..."
output_file="results/zone_all.png"
echo "출력 파일: ${output_file}"

python "$PYTHON_SCRIPT" \
    --output "$output_file" \
    --title "전체 Zone 영역" \
    --no-interactive

if [ $? -eq 0 ]; then
    echo "✓ 전체 Zone 영역 생성 완료"
else
    echo "✗ 전체 Zone 영역 생성 실패"
    exit 1
fi

echo ""
echo "=========================================="
echo "기타 Shapefile 시각화 시작"
echo "=========================================="
echo ""

# 모든 export 디렉토리 찾기
EXPORT_DIRS=($(find data/raw -type d -name "export_shp_*" | sort))
echo "발견된 export 디렉토리: ${#EXPORT_DIRS[@]}개"
for dir in "${EXPORT_DIRS[@]}"; do
    echo "  - $dir"
done
echo ""

# Zone 파일 목록 (이미 처리했으므로 제외)
ZONE_FILES=("WEA_LRGZ_AS.shp" "WEA_MDLZ_AS.shp" "WEA_SCDZ_AS.shp" "WEA_SMLZ_AS.shp")

# 각 export 디렉토리별로 처리
for export_dir in "${EXPORT_DIRS[@]}"; do
    echo ""
    echo "=== $(basename "$export_dir") 처리 중 ==="
    
    # 모든 shapefile 찾기 (Zone 파일 제외)
    OTHER_SHAPEFILES=()
    while IFS= read -r shp_file; do
        basename_shp=$(basename "$shp_file")
        # Zone 파일이 아닌 경우만 추가
        if [[ ! " ${ZONE_FILES[@]} " =~ " ${basename_shp} " ]]; then
            OTHER_SHAPEFILES+=("$shp_file")
        fi
    done < <(find "$export_dir" -name "*.shp" | sort)
    
    # 기타 shapefile 개수
    total_other=${#OTHER_SHAPEFILES[@]}
    echo "Zone 외 shapefile 개수: $total_other"
    
    # 각 shapefile에 대해 FTR_IDN별 시각화
    count=0
    for shp_path in "${OTHER_SHAPEFILES[@]}"; do
        count=$((count + 1))
        shp_name=$(basename "$shp_path" .shp)
        # V_WTL_ 접두사 제거
        clean_name=${shp_name#V_WTL_}
        # WTL_ 접두사도 제거 (WTL_FIRE_PS, WTL_VALV_PS 등)
        clean_name=${clean_name#WTL_}
        output_file="results/${clean_name}.png"
        
        echo ""
        echo "[$count/$total_other] $shp_name 시각화 중..."
        
        # Python 스크립트 실행 (파일명만 전달하면 모든 export 디렉토리에서 처리됨)
        python "$PYTHON_SCRIPT" \
            --file "$shp_name.shp" \
            --output "$output_file" \
            --no-interactive
        
        # 실행 결과 확인
        if [ $? -eq 0 ]; then
            echo "✓ $shp_name 시각화 완료"
        else
            echo "✗ $shp_name 시각화 실패 (경고: 계속 진행)"
        fi
    done
    
    # 첫 번째 디렉토리만 처리하면 나머지는 이미 처리됨
    # (--file 옵션이 파일명만 받으면 모든 디렉토리를 처리하므로)
    break
done

# 종료 시간 및 소요 시간 계산
end_time=$(date +%s)
elapsed_time=$((end_time - start_time))

echo ""
echo "=========================================="
echo "모든 이미지 생성 완료!"
echo "소요 시간: ${elapsed_time}초"
echo ""
echo "생성된 Zone 파일:"
ls -la results/zone_*.png 2>/dev/null | awk '{print "  - " $9 " (" $5 " bytes)"}'
echo ""
echo "생성된 기타 시각화 파일:"
# zone_로 시작하지 않는 png 파일들 표시
ls -la results/*.png 2>/dev/null | grep -v "zone_" | awk '{print "  - " $9 " (" $5 " bytes)"}'
echo "=========================================="