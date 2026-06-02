# VBinvest

[한국어](README.md) | [English](README.en.md)

로컬 우선 오픈소스 투자 리서치 대시보드입니다. VBinvest는 사용자가 등록한 종목의 가격·거래량·RSI14·이동평균(5/20/50/120)·뉴스·SEC 공시·OpenDART 공시를 모아 로컬 DB에 보관하고 종목별 리포트를 생성합니다.

## 목차

- [빠른 시작](#빠른-시작)
- [처음 실행 설정](#처음-실행-설정)
- [OpenDART 설정](#opendart-설정)
- [AI API 및 모델](#ai-api-및-모델)
- [데이터와 리포트](#데이터와-리포트)
- [Obsidian 내보내기](#obsidian-내보내기)
- [스크린샷](#스크린샷)
- [선택적 예약 실행](#선택적-예약-실행)
- [백업과 삭제](#백업과-삭제)
- [문제 해결](#문제-해결)
- [개발과 기여](#개발과-기여)
- [라이선스](#라이선스)
- [면책 고지](#면책-고지)

## 빠른 시작

VBinvest는 로컬 우선 설계입니다. 개발 환경에서 소스 빌드를 하려면 Python 3.10+와 Node.js가 필요합니다.
패키지 배포본은 정적 프론트엔드를 포함하므로 런타임에 Node.js가 필요하지 않습니다.
실행 직후 기본 포트 `4173`에서 열리지 않으면 `4174`부터 빈 포트를 자동으로 찾습니다.

### macOS 사용자

```bash
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
chmod +x VBinvest.command
./VBinvest.command
```

`chmod +x`는 macOS 실행 파일 실행 권한을 부여합니다.

### Windows 사용자

```powershell
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
VBinvest.bat
```

PowerShell 진단 실행이 필요할 때는:

```powershell
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
./VBinvest.ps1
```

`VBinvest.bat`와 `VBinvest.ps1`는 공통 런처 `python -m scripts.launcher`를 호출합니다.
문제 발생 시 PowerShell의 `./VBinvest.ps1`이 더 자세한 진단 메시지를 보여줍니다.

## 처음 실행 설정

첫 실행 화면에서 다음 항목을 설정합니다.

| 항목 | 기본값/선택 | 설명 |
| --- | --- | --- |
| 데이터베이스 | `SQLite 내장 DB` (기본값) | `vbinvest` 데이터는 앱 데이터 폴더에 보관됩니다. |
| PostgreSQL Docker | 선택(고급 사용자) | 로컬 PostgreSQL을 컨테이너로 운영할 때 사용합니다. 기본 바인딩은 루프백(127.0.0.1) 권장입니다. |
| PostgreSQL 직접 DSN | 선택(고급 사용자) | 사용자가 관리하는 Postgres 접속 문자열(DSN)로 연결합니다. |
| AI 연동 방식 | `AI API`, `로컬 LLM`, `사용 안 함` | 각 모드에서 비용 및 키 요구사항이 다릅니다. |
| OpenDART | 선택 | 국내 공시가 필요할 때만 `OPENDART_API_KEY`를 저장합니다. |
| Obsidian 저장 경로 | 선택 | 생성되는 Markdown 리포트를 Vault로 저장합니다. |

데이터베이스 모드, API 키, Vault 경로 모두 사용자 책임으로, VBinvest는 중앙 저장소에 데이터를 수집해 보관하지 않습니다.
데이터 소유권은 사용자 소유이며 저장 책임은 사용자에게 있습니다.

## OpenDART 설정

- OpenDART는 중앙에서 무료 제공이 아닌 사용자 본인이 발급한 `OPENDART_API_KEY`로 운영됩니다.
- OpenDART 키 없이 실행해도 앱은 동작하며 SEC 공개 데이터 수집은 키 없이 진행됩니다.
- `OPENDART_API_KEY`는 보통 `.env` 대신 런처 진입 시 보안 저장소로 등록됩니다.

## AI API 및 모델

AI 기능은 다음 두 모드 중에서 선택합니다.

- Cloud provider: OpenAI, OpenRouter, DeepSeek, Qwen/DashScope, Kimi/Moonshot, GLM/Z.AI, custom OpenAI-compatible provider
- Local LLM: Ollama, LM Studio, llama.cpp 같은 OpenAI-compatible endpoint(예: `http://127.0.0.1:11434/v1`)

안전 주의:

- 로컬 모델은 키 없이도 동작할 수 있습니다. (`로컬 모델은 키 없이`)
- Cloud provider는 `AI_API_KEY`가 필요합니다. (`클라우드 AI provider는 API 키가 필요`)
- `Codex/Copilot CLI`는 사용자의 CLI 계정(OAuth)으로 직접 인증되며, 계정 제한/정지 위험이 있을 수 있습니다.
- VBinvest는 키를 `scripts.save_secret`를 통해 보안 저장소에 저장하며, macOS는 Keychain, Windows는 Credential Manager를 사용해 코드/설정 파일에 평문 저장하지 않습니다.

예:

```bash
save_secret "AI_API_KEY"
save_secret "OPENDART_API_KEY"
```

Windows에서는 동일 키가 Windows Credential Manager에 저장됩니다.

`AI_API_KEY`, `OPENDART_API_KEY`는 사용자의 책임으로 발급/과금됩니다.

## 데이터와 리포트

프로그램 시작 시 가능한 범위에서 가격, 지표, 뉴스, SEC 공시, OpenDART 공시를 갱신합니다.
`OpenDART` 키가 없으면 국내 공시 수집만 비활성화되고 나머지 항목은 계속 동작합니다.

- 리포트는 실시간 웹 탐색을 수행하지 않습니다.
- 리포트는 `DB에 저장된 최신 가격`과 지표, 뉴스, 공시를 바탕으로 생성됩니다.
- 필요한 데이터가 누락되면 `source_gap` 항목으로 빈 근거를 표시합니다.

## Obsidian 내보내기

`리포트 발행` 시 Markdown이 Obsidian Vault에도 저장됩니다.
권장:

- 생성 노트 폴더를 일반 수기 노트와 분리
- 주석 마커(`<!-- Vbinvest:generated -->`)로 자동 생성본과 수기본 구분
- 정기 백업: Obsidian Vault 폴더와 VBinvest DB 경로를 함께 백업

## 스크린샷

스크린샷은 추후 갱신 예정입니다.
`TODO: 실제 실행 화면 스크린샷이 준비되는 대로 추가합니다`
GitHub에서 렌더링되는 플레이스홀더만 제공하며 가짜 이미지는 사용하지 않습니다.

## 선택적 예약 실행

앱이 닫혀 있어도 갱신을 반복하려면 OS 예약 실행을 설치할 수 있습니다.

macOS launchd:

```bash
mkdir -p ~/Library/LaunchAgents
cp ops/launchd/vbinvest-daily.plist ~/Library/LaunchAgents/com.vbinvest.daily.plist
cp ops/launchd/vbinvest-weekly.plist ~/Library/LaunchAgents/com.vbinvest.weekly.plist
launchctl load -w ~/Library/LaunchAgents/com.vbinvest.daily.plist
launchctl load -w ~/Library/LaunchAgents/com.vbinvest.weekly.plist
```

Linux cron:

```bash
crontab ops/cron/vbinvest-daily.cron
crontab ops/cron/vbinvest-weekly.cron
```

주간 사전 계산은 기본 비활성화입니다.

삭제:

```bash
launchctl unload -w ~/Library/LaunchAgents/com.vbinvest.daily.plist 2>/dev/null || true
launchctl unload -w ~/Library/LaunchAgents/com.vbinvest.weekly.plist 2>/dev/null || true
crontab -l | sed '/vbinvest-daily.cron/d;/vbinvest-weekly.cron/d' | crontab -
```

## 백업과 삭제

### 백업

- SQLite: 앱 데이터 폴더의 `vbinvest.sqlite3` 또는 DB 파일을 복사해 보관
- PostgreSQL: 기존 운영자의 정책에 따라 `pg_dump` 또는 스냅샷으로 백업
- Obsidian: Vault 내 리포트 폴더를 별도 저장 위치로 정기 백업

### 삭제

- 런처 종료 후 앱 데이터 폴더를 삭제하면 로컬 DB가 같이 삭제됩니다.
- 사용한 예약 실행 항목(launchd/cron)도 같이 제거해야 잔여 자동 실행을 방지할 수 있습니다.

## 문제 해결

- 브라우저가 열리지 않음: 터미널 로그에서 `http://127.0.0.1:<port>`를 직접 열어 주세요.
- 빈 포트를 자동으로 선택하지 못함: 이미 사용 중인 프로세스를 종료하고 다시 실행하세요.
- OpenDART 키 오류: OPENDART API 키 등록 상태 및 네트워크 접속을 확인하세요.
- AI 오류: cloud provider는 API key/base URL/model을 점검하고, local LLM은 서버 실행 상태를 확인하세요.
- Codex/Copilot CLI 오류: 각 CLI의 로그인 상태와 계정 권한을 확인하세요.

## 개발과 기여

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

기능 작업 전 Git hook을 설치합니다.
(`Git hooks`)
- 기여는 Conventional Commits를 지켜주세요.

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

- 브랜치 기본 운영: `develop` 기준으로 기능 브랜치 생성
- 커밋 규칙: Conventional Commits

## 라이선스

라이선스는 저장소의 `LICENSE` 파일을 기준으로 합니다.
`LICENSE`가 없는 배포본은 재배포 전에 라이선스 상태를 먼저 확인하세요.

## 비용과 면책

VBinvest 운영에 필요한 시장 데이터, AI 호출, 공시 수집은 사용자가 설정한 스토리지·서비스에서 과금됩니다.

## 면책 고지

시장 데이터 접근, AI 호출, 공시 수집은 사용자가 선택한 공급자/인프라의 비용입니다.
yfinance, OpenDART, AI provider 호출, 로컬 LLM 하드웨어, 클라우드 AI 비용은 사용자 책임입니다.

VBinvest는 연구·학습용 산출물 생성 도구입니다. 투자 자문, 증권 중개, 자동 매매 엔진이 아니며 투자 판단과 손익은 사용자 본인 책임입니다. 모든 비용은 사용자 비용으로 처리됩니다.
