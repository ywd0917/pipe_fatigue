# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

### Claude Code 사용 시 주의사항
- Git 작업은 git-server MCP 도구 사용 (mcp__git-server__*)
- Github issue 와 Pull Request 작업은 `gh`(Github cli) 명령어 사용
- issue 를 만들고 작업을 시작할 때에는 main 밑에 새로 브랜치를 만들고 pr을 만들면서 진행해줘.
- 결과 파일은 항상 `results/` 디렉토리에 저장
- 임시 스크립트는 `src/tmp`에 생성하고, 임시파일의 생성 파일은 `results/tmp`안에 저장
- 모호한 상황에서는 오류와 원인을 출력하고 중단해줘. 그렇지 않으면 오류가 감춰져서 디버깅이 어려줘.
- 개발 표준은 CODING_STANDARDS.md 참조
- 전체 문서 목록은 [docs/INDEX.md](docs/INDEX.md) 참조