# VBinvest

[한국어](README.md) | [English](README.en.md)

VBinvest는 로컬 우선(local-first) 오픈소스 투자 리서치 대시보드입니다. 프로그램을 켤 때 사용자가 등록한 종목의 시장 데이터를 갱신하고, 차트와 지표를 보여주며, 사용자가 직접 준비한 데이터/API/AI 자격 증명으로 AI 보조 리서치 리포트를 생성합니다.

VBinvest는 기본적으로 호스팅 SaaS가 아닙니다. 사용자는 프로그램을 로컬에서 실행하고, 데이터도 로컬에 저장하며, yfinance, OpenDART, AI API, 로컬 모델 하드웨어 비용은 각자 본인의 계정과 환경에서 부담합니다.

## 빠른 시작

로컬 프로그램 실행 방식이 기본 경로입니다.

```bash
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
./VBinvest.command
```

Windows에서는 다음 파일을 실행합니다.

```powershell
VBinvest.bat
```

런처는 `127.0.0.1`에서 로컬 백엔드와 웹 UI를 띄우고, 빈 포트를 자동으로 선택한 뒤 브라우저를 열어 초기 설정 화면으로 이동합니다.

## 초기 설정

- 데이터베이스: `SQLite 내장 DB (권장)`, `PostgreSQL Docker 자동 실행`, `PostgreSQL 직접 연결`
- Obsidian: 생성된 Markdown 리포트를 저장할 Vault 경로 선택
- OpenDART: 국내 공시 조회가 필요하면 선택적으로 `OPENDART_API_KEY` 설정
- AI: `AI API 연동`, local LLM endpoint, Codex CLI, Copilot CLI, 또는 비활성화

macOS에서는 런처로 전달된 `AI_API_KEY`, `OPENDART_API_KEY` 값을 로컬 설정 파일에 저장하지 않고 Keychain 서비스 `VBinvest`에 저장합니다. 이 동작은 `save_secret "AI_API_KEY"`와 `save_secret "OPENDART_API_KEY"`를 통해 수행됩니다. Windows에서는 같은 계정명이 Windows Credential Manager에 저장됩니다.

## 비용과 위험 정책

- VBinvest는 중앙 서버에서 무료 시장 데이터나 AI 크레딧을 제공하지 않습니다.
- yfinance, OpenDART, AI provider, local LLM 하드웨어, 클라우드 모델 호출 비용은 사용자 책임입니다.
- Codex/Copilot CLI 모드는 고급 옵션이며, 계정 제한이나 provider 정책의 영향을 받을 수 있습니다.

## 개발

개발자는 Python과 Node.js가 필요합니다. 패키징된 로컬 릴리스를 사용하는 일반 사용자는 런타임에 Node.js가 필요하지 않게 만드는 것을 목표로 합니다.

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

기능 작업 전 Git hook을 설치합니다.

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

## 면책 고지

VBinvest는 리서치와 학습용 산출물을 생성하는 도구입니다. 투자 자문, 증권 중개 서비스, 자동 매매 시스템이 아닙니다.
