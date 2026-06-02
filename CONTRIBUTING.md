# Contributing / 기여 가이드

## 한국어

VBinvest는 로컬 우선 오픈소스 프로젝트입니다. 일반 사용자는 이 문서를 읽을 필요가 없고, `VBinvest.command` 또는 `VBinvest.bat`로 실행하면 됩니다.

기여자는 작업 전에 프로젝트 전용 Git hook을 설치하세요.

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

이 저장소에서 별도 pre-commit 패키지는 필수 설치 항목이 아닙니다. 현재 검증은 프로젝트 자체 스크립트로 실행됩니다.

- `scripts/git_hooks/check_paths.py`: `.env`, 로컬 DB, Obsidian vault/export, QA evidence 같은 로컬 산출물 커밋 차단
- `scripts/git_hooks/check_commit_msg.py`: Conventional Commits 형식 검사
- `scripts/git_hooks/check_pre_push.py`: `origin`, branch policy, secret scan 검사

커밋/푸시 전 권장 확인:

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
./.venv/bin/python scripts/secret_scan.py
./.venv/bin/python scripts/git_hooks/check_pre_push.py
```

브랜치는 `develop`에서 `feature/<short-name>` 형태로 만들고, 커밋 메시지는 `feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`, `refactor:` 중 하나로 시작하세요.

## English

VBinvest is a local-first open-source project. Regular users do not need this document; they can run `VBinvest.command` or `VBinvest.bat`.

Contributors should install the project-local Git hooks before working:

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

The Python pre-commit package is not required. This repository currently uses its own project-local hook scripts.

- `scripts/git_hooks/check_paths.py`: blocks local `.env`, database files, Obsidian vault/export files, and QA evidence
- `scripts/git_hooks/check_commit_msg.py`: validates Conventional Commits
- `scripts/git_hooks/check_pre_push.py`: checks `origin`, branch policy, and secret scan

Recommended checks before committing or pushing:

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
./.venv/bin/python scripts/secret_scan.py
./.venv/bin/python scripts/git_hooks/check_pre_push.py
```

Create feature branches from `develop` using `feature/<short-name>`. Commit messages should start with one of `feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`, or `refactor:`.
