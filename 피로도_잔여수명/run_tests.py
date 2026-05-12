#!/usr/bin/env python3
"""
테스트 실행 스크립트
다양한 테스트 옵션을 제공하는 편리한 스크립트
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list[str], description: str) -> tuple[bool, float]:
    """명령어 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"실행 명령어: {' '.join(cmd)}")
    print()

    start_time = time.time()
    try:
        subprocess.run(cmd, check=True, capture_output=False)
        elapsed = time.time() - start_time
        print(f"\n✅ {description} 완료 ({elapsed:.1f}초)")
        return True, elapsed
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"\n❌ {description} 실패 (종료 코드: {e.returncode}, {elapsed:.1f}초)")
        return False, elapsed
    except FileNotFoundError:
        print(f"\n❌ 명령어를 찾을 수 없습니다: {cmd[0]}")
        print("필요한 패키지를 설치하세요: pip install -e .[dev]")
        return False, 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="피로 손상 분석 프로젝트 테스트 실행")

    # 테스트 타입 옵션
    parser.add_argument("--unit", action="store_true",
                       help="단위 테스트만 실행")
    parser.add_argument("--integration", action="store_true",
                       help="통합 테스트만 실행")
    parser.add_argument("--slow", action="store_true",
                       help="느린 테스트 포함")
    parser.add_argument("--visualization", action="store_true",
                       help="시각화 테스트만 실행")
    parser.add_argument("--performance", action="store_true",
                       help="성능 테스트만 실행")

    # 특정 모듈 테스트
    parser.add_argument("--module", choices=["main1"],
                       help="특정 모듈만 테스트")

    # 출력 옵션
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="상세한 출력")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="간단한 출력")
    parser.add_argument("--no-cov", action="store_true",
                       help="커버리지 측정 비활성화")

    # 코드 품질 검사 옵션
    parser.add_argument("--check", action="store_true",
                       help="코드 품질 검사 실행 (black, ruff, mypy)")
    parser.add_argument("--format", action="store_true",
                       help="black으로 코드 포맷팅")
    parser.add_argument("--lint", action="store_true",
                       help="ruff로 코드 스타일 검사")
    parser.add_argument("--type-check", action="store_true",
                       help="mypy로 타입 검사")

    # 전체 테스트 옵션
    parser.add_argument("--all", action="store_true",
                       help="모든 테스트 실행 (ruff, black, mypy, pytest)")

    # 기타 옵션
    parser.add_argument("--install-deps", action="store_true",
                       help="테스트 의존성 설치")
    parser.add_argument("--clean", action="store_true",
                       help="테스트 결과 파일 정리")
    parser.add_argument("--continue-on-error", action="store_true",
                       help="테스트 실패 시에도 계속 진행")

    args = parser.parse_args()

    # 의존성 설치
    if args.install_deps and not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                                            "테스트 의존성 설치"):
        return 1

    # --all 옵션 처리
    if args.all:
        print("\n🔧 모든 테스트 실행 (4종)\n")
        print("실행 순서: 1) pytest → 2) ruff → 3) black → 4) mypy\n")

        results = []
        total_start = time.time()
        continue_on_error = args.continue_on_error

        # 1. pytest 테스트 (먼저 코드가 작동하는지 확인)
        pytest_cmd = [sys.executable, "-m", "pytest", "tests/"]
        if not args.no_cov:
            pytest_cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing", "--cov-fail-under=65"])
        success, elapsed = run_command(pytest_cmd, "pytest 단위 테스트")
        results.append(("pytest", success, elapsed))
        if not success and not continue_on_error:
            return 1

        # 2. ruff 검사
        success, elapsed = run_command([sys.executable, "-m", "ruff", "check", "src/", "tests/"],
                                     "ruff 코드 스타일 검사")
        results.append(("ruff", success, elapsed))
        if not success and not continue_on_error:
            return 1

        # 3. black 포맷팅 검사
        success, elapsed = run_command([sys.executable, "-m", "black", "--check", "src/", "tests/"],
                                     "black 코드 포맷팅 검사")
        results.append(("black", success, elapsed))
        if not success and not continue_on_error:
            return 1

        # 4. mypy 타입 검사
        success, elapsed = run_command([sys.executable, "-m", "mypy", "src/"],
                                     "mypy 타입 검사")
        results.append(("mypy", success, elapsed))

        # 결과 요약
        total_elapsed = time.time() - total_start
        print(f"\n{'='*60}")
        print("📊 테스트 결과 요약")
        print(f"{'='*60}")

        for name, success, elapsed in results:
            status = "✅ 통과" if success else "❌ 실패"
            print(f"{name:10s}: {status} ({elapsed:.1f}초)")

        print(f"{'='*60}")
        all_passed = all(r[1] for r in results)
        final_status = "✅ 모든 테스트 통과!" if all_passed else "❌ 일부 테스트 실패"
        print(f"최종 결과: {final_status}")
        print(f"총 소요 시간: {total_elapsed:.1f}초")

        if all_passed:
            print("\n🎉 축하합니다! 모든 테스트를 통과했습니다.")

        return 0 if all_passed else 1

    # 코드 품질 검사
    if args.lint and not run_command([sys.executable, "-m", "ruff", "check", "src/", "tests/"],
                                      "ruff 코드 스타일 검사"):
        return 1

    if args.format and not run_command([sys.executable, "-m", "black", "src/", "tests/"],
                                       "black 코드 포맷팅"):
        return 1

    if args.type_check and not run_command([sys.executable, "-m", "mypy", "src/"],
                                           "mypy 타입 검사"):
        return 1

    if args.check:
        # 종합적인 코드 품질 검사
        print("\n📋 종합 코드 품질 검사 시작\n")
        print("순서: 1) black 포맷팅 → 2) ruff 스타일 검사 → 3) mypy 타입 검사\n")

        success = True

        # 1. black 포맷팅 (실제로 파일 수정)
        if not run_command([sys.executable, "-m", "black", "src/", "tests/"],
                          "black 코드 포맷팅"):
            success = False

        # 2. ruff 스타일 검사
        if not run_command([sys.executable, "-m", "ruff", "check", "src/", "tests/"],
                          "ruff 코드 스타일 검사"):
            success = False

        # 3. mypy 타입 검사
        if not run_command([sys.executable, "-m", "mypy", "src/"],
                          "mypy 타입 검사"):
            success = False

        if not success:
            print("\n❌ 코드 품질 검사 실패")
            return 1

        print("\n✅ 모든 코드 품질 검사 통과")
        return 0

    # 코드 품질 검사만 실행하고 종료
    if args.lint or args.format or args.type_check or args.check:
        return 0

    # 정리
    if args.clean:
        import shutil
        paths_to_clean = [
            "htmlcov",
            ".coverage",
            ".pytest_cache",
            "test_results"
        ]

        for path in paths_to_clean:
            if Path(path).exists():
                if Path(path).is_dir():
                    shutil.rmtree(path)
                    print(f"디렉토리 삭제: {path}")
                else:
                    Path(path).unlink()
                    print(f"파일 삭제: {path}")

        print("✅ 정리 완료")
        return 0

    # pytest 명령어 구성
    cmd = [sys.executable, "-m", "pytest"]

    # 출력 레벨 설정
    if args.verbose:
        cmd.append("-v")
    elif args.quiet:
        cmd.append("-q")

    # 커버리지 설정
    if not args.no_cov:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing", "--cov-fail-under=0"])

    # 마커 기반 필터링
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.visualization:
        markers.append("visualization")
    if args.performance:
        markers.append("performance")

    if not args.slow:
        markers.append("not slow")

    if markers:
        cmd.extend(["-m", " and ".join(markers)])

    # 특정 모듈 테스트
    if args.module:
        module_map = {
            "main1": "tests/test_main1_read_gis_files.py"
        }
        cmd.append(module_map[args.module])
    else:
        cmd.append("tests/")

    # 테스트 실행
    success = run_command(cmd, "단위 테스트 실행")

    if success and not args.no_cov:
        print("\n📊 커버리지 리포트가 htmlcov/index.html에 생성되었습니다.")
        print("브라우저에서 열어보려면: open htmlcov/index.html")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
