#!/usr/bin/env python3
"""프로젝트 의존성 분석 스크립트"""

import subprocess
from pathlib import Path


def run_pydeps_analysis():
    """pydeps를 사용하여 의존성 분석 실행"""

    # 출력 디렉토리 생성
    output_dir = Path("docs/dependencies")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 의존성 분석 시작...")

    # 분석 목록
    analyses = [
        {
            "name": "내부 의존성",
            "output": "deps_internal.svg",
            "cmd": ["pydeps", "src", "--max-bacon", "2", "--cluster", "--only", "src"],
        },
        {
            "name": "전체 의존성",
            "output": "deps_all.svg",
            "cmd": ["pydeps", "src", "--max-bacon", "2", "--cluster"],
        },
        {
            "name": "Common 모듈",
            "output": "deps_common.svg",
            "cmd": ["pydeps", "src/common", "--max-bacon", "1"],
        },
        {
            "name": "Analysis 모듈",
            "output": "deps_analysis.svg",
            "cmd": ["pydeps", "src/analysis", "--max-bacon", "1"],
        },
    ]

    # 각 분석 실행
    for analysis in analyses:
        print(f"\n📊 {analysis['name']} 분석 중...")
        output_path = output_dir / analysis["output"]
        cmd = analysis["cmd"] + ["-o", str(output_path)]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"   ✅ 완료: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 실패: {e}")

    # 텍스트 리포트 생성
    print("\n📄 텍스트 리포트 생성 중...")

    # 의존성 구조
    deps_file = output_dir / "dependency_structure.txt"
    try:
        result = subprocess.run(
            ["pydeps", "src", "--show-deps", "--only", "src", "--no-output"],
            capture_output=True,
            text=True,
            check=True
        )
        deps_file.write_text(result.stdout)
        print(f"   ✅ 의존성 구조: {deps_file}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ 실패: {e}")

    # 순환 의존성 확인
    print("\n🔄 순환 의존성 확인 중...")
    try:
        result = subprocess.run(
            ["pydeps", "src", "--show-cycles"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            print(f"   ⚠️  순환 의존성 발견:\n{result.stdout}")
        else:
            print("   ✅ 순환 의존성 없음")
    except subprocess.CalledProcessError:
        print("   ✅ 순환 의존성 없음")

    print("\n✨ 의존성 분석 완료!")
    print(f"   결과는 {output_dir} 디렉토리에서 확인할 수 있습니다.")


if __name__ == "__main__":
    run_pydeps_analysis()
