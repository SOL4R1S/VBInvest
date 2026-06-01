# VBinvest

[한국어](README.md) | [English](README.en.md)

VBinvest는 로컬 우선(local-first) 오픈소스 투자 리서치 대시보드입니다. 프로그램을 켤 때 사용자가 등록한 종목의 시장 데이터를 갱신하고, 차트와 지표를 보여주며, 사용자가 직접 준비한 데이터/API/AI 자격 증명으로 AI 보조 리서치 리포트를 생성합니다.

VBinvest는 기본적으로 호스팅 SaaS가 아닙니다. 사용자는 프로그램을 로컬에서 실행하고, 데이터도 로컬에 저장하며, yfinance, OpenDART, AI API, 로컬 모델 하드웨어 비용은 각자 본인의 계정과 환경에서 부담합니다.

## 빠른 시작

로컬 프로그램 실행 방식이 기본 경로입니다.

```bash
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
chmod +x VBinvest.command
./VBinvest.command
```

macOS에서는 `VBinvest.command`가 백엔드와 웹 UI를 함께 실행합니다. Windows에서는 다음 파일을 실행합니다.

```powershell
VBinvest.bat
```

런처는 `127.0.0.1`에서 로컬 백엔드와 웹 UI를 띄우고, 빈 포트를 자동으로 선택한 뒤 브라우저를 열어 초기 설정 화면으로 이동합니다.

## 초기 설정

- 데이터베이스: `SQLite 내장 DB (권장)`, `PostgreSQL Docker 자동 실행`, `PostgreSQL 직접 연결`
- Obsidian: 생성된 Markdown 리포트를 저장할 Vault 경로 선택
- OpenDART: 국내 공시 조회가 필요하면 선택적으로 `OPENDART_API_KEY` 설정
- AI: `AI API 연동`, Ollama 같은 local LLM endpoint, OpenAI-compatible cloud provider, Codex CLI, Copilot CLI, 또는 비활성화

macOS에서는 런처로 전달된 `AI_API_KEY`, `OPENDART_API_KEY` 값을 로컬 설정 파일에 저장하지 않고 Keychain 서비스 `VBinvest`에 저장합니다. 이 동작은 `save_secret "AI_API_KEY"`와 `save_secret "OPENDART_API_KEY"`를 통해 수행됩니다. Windows에서는 같은 계정명이 Windows Credential Manager에 저장됩니다.

로컬 모델은 키 없이 사용할 수 있습니다. 예를 들어 Ollama 또는 `127.0.0.1`/`localhost`의 OpenAI-compatible endpoint는 API 키가 없어도 허용됩니다. 클라우드 AI provider는 API 키가 필요하며, 키가 없으면 프로그램은 리포트 생성을 안전하게 막고 설정 오류만 표시합니다. Codex/Copilot CLI 모드는 OAuth 기반으로 쓸 수 있는 고급 옵션이지만, provider 정책이나 계정 제한 가능성이 있으므로 기본 권장 경로는 아닙니다.

## 데이터 갱신과 리포트

프로그램 시작 시 등록된 종목의 가격, 지표, 뉴스, SEC 공시, OpenDART 공시를 가능한 범위에서 갱신합니다. OpenDART 키가 없으면 국내 공시 수집만 비활성화되고, 가격/지표/뉴스/SEC 갱신은 계속 진행됩니다.

`리포트 발행` 버튼은 실시간 웹 탐색을 수행하지 않습니다. 대신 DB에 저장된 최신 가격, RSI, 이동평균, 거래량, 뉴스, SEC/OpenDART 공시를 사용합니다. 필요한 소스가 부족하면 리포트에는 `source_gap`이 남아 사용자가 어떤 근거가 비어 있는지 확인할 수 있습니다.

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
