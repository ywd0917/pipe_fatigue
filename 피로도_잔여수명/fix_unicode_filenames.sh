#!/bin/bash

# Unicode 파일명 정규화 스크립트
# NFD(자소분리) → NFC(자소결합) 변환

echo "=== Unicode 파일명 정규화 시작 ==="
echo "처리 대상: data 폴더와 모든 서브폴더"
echo

# 데이터 디렉토리 설정
DATA_DIR="./data"

if [ ! -d "$DATA_DIR" ]; then
    echo "오류: data 디렉토리를 찾을 수 없습니다."
    exit 1
fi

# 변경 카운터
changed_count=0

# 한글이 포함된 모든 파일 찾기 (재귀적)
find "$DATA_DIR" -type f -name "*" | while IFS= read -r filepath; do
    # 파일명만 추출
    dirname=$(dirname "$filepath")
    filename=$(basename "$filepath")
    
    # Python을 사용해서 Unicode 정규화
    normalized_name=$(python3 -c "
import unicodedata
import sys
filename = sys.argv[1]
normalized = unicodedata.normalize('NFC', filename)
if filename != normalized:
    print(normalized)
else:
    print('')
" "$filename")
    
    # 파일명이 변경되었으면 이동
    if [ -n "$normalized_name" ] && [ "$filename" != "$normalized_name" ]; then
        old_path="$filepath"
        new_path="$dirname/$normalized_name"
        
        echo "변경: $filename → $normalized_name"
        
        # 파일 이동
        if mv "$old_path" "$new_path" 2>/dev/null; then
            echo "  ✓ 성공: $old_path"
            changed_count=$((changed_count + 1))
        else
            echo "  ✗ 실패: $old_path"
        fi
    fi
done

echo
echo "=== 정규화 완료 ==="
echo "변경된 파일 수: $changed_count"
echo