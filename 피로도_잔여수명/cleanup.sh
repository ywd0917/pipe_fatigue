#!/bin/bash

# 불필요한 파일 삭제 스크립트
# 프로젝트 루트에서 실행할 것

set -e

echo "=========================================="
echo "불필요한 파일 정리 시작"
echo "=========================================="
echo ""

# 삭제할 항목들
CACHE_DIRS=(".mypy_cache" ".ruff_cache" ".pytest_cache" "htmlcov")
PATTERN_FILES=("*.bak" "*.log" "*.egg-info")
DS_STORE=".DS_Store"

# 삭제된 항목 카운터
deleted_count=0

# 1. 캐시 디렉토리 삭제
echo "📦 Python 캐시 디렉토리 삭제..."
for dir in "${CACHE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ 삭제: $dir/"
        du -sh "$dir" 2>/dev/null || true
        rm -rf "$dir"
        ((deleted_count++))
    fi
done
echo ""

# 2. .DS_Store 파일 삭제 (모든 하위 디렉토리 포함)
echo "🍎 macOS .DS_Store 파일 삭제..."
found_ds_store=$(find . -name ".DS_Store" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$found_ds_store" -gt 0 ]; then
    find . -name ".DS_Store" -type f -print -delete
    echo "  ✓ 삭제: ${found_ds_store}개의 .DS_Store 파일"
    deleted_count=$((deleted_count + found_ds_store))
else
    echo "  - .DS_Store 파일 없음"
fi
echo ""

# 3. 백업 파일 삭제 (*.bak)
echo "📄 백업 파일 (*.bak) 삭제..."
found_bak=$(find . -name "*.bak" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$found_bak" -gt 0 ]; then
    find . -name "*.bak" -type f -print -delete
    echo "  ✓ 삭제: ${found_bak}개의 .bak 파일"
    deleted_count=$((deleted_count + found_bak))
else
    echo "  - .bak 파일 없음"
fi
echo ""

# 4. 로그 파일 삭제 (*.log, 루트만)
echo "📋 로그 파일 (*.log) 삭제..."
found_log=$(find . -maxdepth 1 -name "*.log" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$found_log" -gt 0 ]; then
    find . -maxdepth 1 -name "*.log" -type f -print -delete
    echo "  ✓ 삭제: ${found_log}개의 .log 파일"
    deleted_count=$((deleted_count + found_log))
else
    echo "  - .log 파일 없음"
fi
echo ""

# 5. __pycache__ 디렉토리 삭제 (.venv 제외)
echo "🐍 __pycache__ 디렉토리 삭제..."
found_pycache=$(find . -name "__pycache__" -type d -not -path "./.venv/*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$found_pycache" -gt 0 ]; then
    find . -name "__pycache__" -type d -not -path "./.venv/*" -print -exec rm -rf {} + 2>/dev/null || true
    echo "  ✓ 삭제: ${found_pycache}개의 __pycache__ 디렉토리"
    deleted_count=$((deleted_count + found_pycache))
else
    echo "  - __pycache__ 디렉토리 없음"
fi
echo ""

# 6. egg-info 디렉토리 삭제
echo "🥚 egg-info 디렉토리 삭제..."
found_egg=$(find . -maxdepth 1 -name "*.egg-info" -type d 2>/dev/null | wc -l | tr -d ' ')
if [ "$found_egg" -gt 0 ]; then
    for egg_dir in *.egg-info; do
        if [ -d "$egg_dir" ]; then
            echo "  ✓ 삭제: $egg_dir/"
            rm -rf "$egg_dir"
            ((deleted_count++))
        fi
    done
else
    echo "  - egg-info 디렉토리 없음"
fi
echo ""

# 완료 메시지
echo "=========================================="
echo "✅ 정리 완료!"
echo "총 삭제된 항목: ${deleted_count}개"
echo "=========================================="
