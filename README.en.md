# VBinvest

[한국어](README.md) | [English](README.en.md)

VBinvest is a local-first open-source research dashboard. It stores price/volume/RSI14/MA 5/20/50/120/history, news, SEC filings, and OpenDART disclosures for tracked symbols in local storage and generates per-symbol reports.
VBinvest is not a hosted SaaS. You run it locally on your own machine, and data/API/AI costs are handled through your own keys and environment.

## Table of Contents

- [Quick Start](#quick-start)
- [First-Run Choices](#first-run-choices)
- [OpenDART setup](#opendart-setup)
- [AI API and models](#ai-api-and-models)
- [Data and reports](#data-and-reports)
- [Feature status and tested environment](#feature-status-and-tested-environment)
- [Obsidian export](#obsidian-export)
- [Screenshots](#screenshots)
- [Optional Scheduled Runs](#optional-scheduled-runs)
- [Backup and uninstall](#backup-and-uninstall)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Git Flow and releases](#git-flow-and-releases)
- [License](#license)
- [Disclaimer](#disclaimer)

## Quick Start

VBinvest is local-first. Developer environment setup for source builds requires Python 3.10+ and Node.js.
Packaged releases include static frontend assets, so Node.js runtime is not required.

The launcher chooses free ports automatically from `4173` upward, so if the default port is busy it will try another available port.
Node.js runtime is not required for packaged releases.

### macOS Users

```bash
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
chmod +x VBinvest.command
./VBinvest.command
```

`chmod +x VBinvest.command` marks the launcher as executable.
`VBinvest.command` runs the server in the background by default and closes the Terminal window used to launch it.
Logs are written to `~/Library/Logs/VBinvest/launcher.log`.
To keep the Terminal window open, run `VBINVEST_KEEP_TERMINAL=1 ./VBinvest.command`; for foreground debugging, run `VBINVEST_FOREGROUND=1 ./VBinvest.command`.
You can close the app with the in-app `Shutdown` button; closing the browser tab also sends a best-effort local shutdown request.

### Windows Users

Use the batch launcher:

```powershell
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
VBinvest.bat
```

Or use the PowerShell launcher for clearer diagnostics:

```powershell
./VBinvest.ps1
```

Both `VBinvest.bat` and `VBinvest.ps1` run `python -m scripts.launcher`.

## First-Run Choices

You can choose startup mode from the first-run screen.

- **Database**
  - `SQLite` (default): data stored in local app data directory.
  - `PostgreSQL Docker` (advanced users): use Docker-hosted PostgreSQL bound to loopback.
  - `Direct PostgreSQL DSN` / `Direct DSN` (advanced users): connect to your own PostgreSQL DSN.
- **AI mode**: `AI API`, `Local LLM`, `Disable`.
- **OpenDART**: optional.
- **Obsidian path**: where generated notes are exported.

VBinvest does not centralize or monetize user storage. Data remains in the user-selected storage, so **data ownership** and backup responsibility stays with you.
- You own your data

## OpenDART setup

- OpenDART integration is optional and requires a user-paid, user-owned `OPENDART_API_KEY`.
- If you do not set `OPENDART_API_KEY`, only Korean disclosure crawling is disabled; other features still run.
- SEC filings are public records and can be collected without an OpenDART key.
- On macOS, launcher secrets are stored via Keychain; on Windows, via Windows Credential Manager.

## AI API and models

VBinvest supports cloud and local providers through OpenAI-compatible endpoints:

- Cloud: OpenAI, OpenRouter, DeepSeek, Qwen/DashScope, Kimi/Moonshot, GLM/Z.AI, custom compatible provider
- Local: Ollama, LM Studio, llama.cpp via `http://127.0.0.1:<port>/v1`

Notes:

- local models can run without a key.
- cloud AI providers require an API key.
- Codex/Copilot CLI are launched under your own CLI account and OAuth state; VBinvest does not store or read those access tokens.
- A warning should be shown in UI for account restriction/suspension risk when using Codex/Copilot.

Security snippets used by the launcher include:

```bash
save_secret "AI_API_KEY"
save_secret "OPENDART_API_KEY"
```

On Windows these keys are stored using Credential Manager.

## Data and reports

When the program starts, it updates price, indicators, news, SEC filings, and OpenDART filings within the configured capabilities.

- Report generation does not perform live web browsing.
- It uses the latest DB-backed prices and metrics saved to local DB.
- Missing required inputs are tracked as `source_gap`.
- `Generate Report` creates a Markdown note in Obsidian and a DB record.

## Feature status and tested environment

Current major features include:

- Local-first launch: macOS/Windows launchers, automatic free-port selection, macOS background launch, in-app shutdown button
- First-run setup: SQLite/PostgreSQL, Obsidian Vault, OpenDART, AI API/Local LLM settings
- Market data: startup backfill and incremental refresh for tracked symbols, yfinance-backed price collection, five-year initial backfill, recent 1260 trading-day dashboard query
- Indicators/charts: RSI14, MA5/20/50/120, candle/line mode toggle, separate indicator panel, moving-average color legend, wheel zoom, and drag pan
- Symbol management: watchlist groups, ticker validation, name/ticker autocomplete search, startup ticker catalog refresh
- Reports: on-demand report generation, DB-backed prices/indicators/news/disclosures, Obsidian Markdown export
- UX: market refresh progress, elapsed time, and estimated remaining time

### Local LLM test notes

The following result is from one user environment. Local model behavior can vary by model size, context length, Ollama version, and memory pressure.

| Item | Result |
| --- | --- |
| Test machine | Mac mini M4, 24GB RAM |
| Runtime | Ollama local OpenAI-compatible endpoint |
| Verified working | `gemma4:e4b-it-q4_K_M` |
| Verified failing | `qwen3.5:2b`, `hf.co/NidAll/supergemma4-e4b-abilterated-Q4_K_M-GGUF:Q4_K_M` |
| Result | With `gemma4:e4b-it-q4_K_M`, on-demand report generation and Obsidian Markdown export completed successfully. The failing models may fail because of local response-format, context, or compatibility issues; switching to another model is recommended. |

## Obsidian export

Generated reports are exported as Markdown to the configured Obsidian folder.
Generated notes can include marker `<!-- Vbinvest:generated -->` to separate authored notes.

Recommended setup:

- Use a separate folder for generated notes.
- Keep generated notes identifiable with your own marker or folder naming.
- Contributions are welcome.
- Back up both your Obsidian export folder and DB backups together.

## Screenshots

Real screenshots are not included yet.
GitHub shows guidance text only; no fake screenshots are bundled.

## Optional Scheduled Runs

You can install optional scheduled runs for background sync when the app is not open.

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

Scheduled precompute remains disabled by default. Reports are generated on demand from the ticker screen when you press the report button.

Uninstall scheduler:

```bash
launchctl unload -w ~/Library/LaunchAgents/com.vbinvest.daily.plist 2>/dev/null || true
launchctl unload -w ~/Library/LaunchAgents/com.vbinvest.weekly.plist 2>/dev/null || true
crontab -l | sed '/vbinvest-daily.cron/d;/vbinvest-weekly.cron/d' | crontab -
```

## Backup and uninstall

### Backup

- SQLite: copy `vbinvest.sqlite3` from app data directory.
- PostgreSQL: use `pg_dump` for backup or your PostgreSQL snapshot process.
- Obsidian: back up the generated report folder as part of your knowledge base.

### Uninstall

- Close the app with launcher shutdown or UI exit.
- Remove app data directory after backup if you want a clean uninstall.
- Remove launchd/cron items listed above before deleting dependencies.

## Troubleshooting

- Browser did not open: open `http://127.0.0.1:<port>` from the printed output.
- Port is not available: stop competing processes and restart.
- OpenDART not configured: confirm key and entitlement.
- AI mode fails: check cloud key/base URL/model or local LLM server status.
- Codex/Copilot CLI fails: check CLI install/login status and account restrictions.

## Contributing

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

Install Git hooks before contributions:

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

- This project uses its own `scripts/git_hooks/*` checks. The Python pre-commit package is not required.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for the detailed contribution workflow.
- Fork and create feature branches from `develop`.
- Use Conventional Commits.
- Submissions are expected to include tests/docs updates for behavior-impacting changes.

## Git Flow and releases

VBinvest public work follows Git Flow.
Publishing / Release follows this policy.

- `develop` is the integration branch. Normal work is pushed to `origin/develop`.
- `main` is the stable release branch. Never force-push `main` or `develop`.
- Use `feature/<short-name>` for feature work, `release/vX.Y.Z` for stabilization, and `hotfix/<short-name>` for urgent fixes.
- Before pushing, local git hooks, secret scan, backend/frontend tests, and launcher/package smoke checks must pass.

Create releases with SemVer release tags:

```bash
git checkout develop
git pull origin develop
git tag v0.1.0
git push origin v0.1.0
```

After a release tag is pushed, GitHub Actions builds a macOS/Windows launcher-ready release artifact and writes the Git-SHA-backed `build_version` to `build_version.txt`. Until packaged binaries exist, each release artifact contains the source-run package and launcher files.

## License

The repository `LICENSE` file defines redistribution terms.
If a release copy does not include `LICENSE`, verify the license status before redistributing it.

## Disclaimer

VBinvest does not include centralized market data or AI credits as a default bundled service.
User-paid data and AI costs are your responsibility.
yfinance, OpenDART, cloud model calls, local LLM compute, and any related API costs are paid by the user.

VBinvest generates research/learning material, not investment advice, brokerage, or automated trading execution.
All investment decisions, trading outcomes, and risks are your own responsibility.
