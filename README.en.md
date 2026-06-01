# VBinvest

[한국어](README.md) | [English](README.en.md)

VBinvest is a local-first, open-source investing research dashboard. It refreshes market data when the local program starts, shows charts and indicators, and generates AI-assisted research reports with credentials owned by the user.

VBinvest is not a hosted SaaS by default. Users run it locally, store data locally, and pay any market data, OpenDART, AI API, or local model cost through their own accounts or hardware.

## Quick Start

Local program mode is the primary path.

```bash
git clone https://github.com/SOL4R1S/VBInvest.git
cd VBInvest
./VBinvest.command
```

On Windows:

```powershell
VBinvest.bat
```

The launcher starts the local backend on `127.0.0.1`, chooses free ports, opens the web UI, and shows the first-run setup wizard.

## First-Run Choices

- Database: `SQLite built-in DB (recommended)`, `PostgreSQL Docker automatic start`, or `PostgreSQL direct connection`
- Obsidian: choose a vault path for generated Markdown reports
- OpenDART: optional `OPENDART_API_KEY` for Korean disclosures
- AI: AI API integration, local LLM endpoint, Codex CLI, Copilot CLI, or disabled

On macOS, launcher-provided `AI_API_KEY` and `OPENDART_API_KEY` values are saved to Keychain service `VBinvest` through `save_secret "AI_API_KEY"` and `save_secret "OPENDART_API_KEY"` instead of being persisted in local config files. On Windows, the same accounts are stored in Windows Credential Manager.

## Cost And Risk Policy

- VBinvest does not provide centralized free market data or AI credits.
- yfinance, OpenDART, AI providers, local LLM hardware, and cloud model calls are the user's responsibility.
- Codex/Copilot CLI modes are advanced options and may be subject to account limits or provider policy restrictions.

## Development

Developers need Python and Node.js. End users of packaged local releases should not need Node.js at runtime.

```bash
./.venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm test -- --run && npm run build
```

Install Git hooks before feature work:

```bash
./.venv/bin/python scripts/git_hooks/install_hooks.py
```

## Disclaimer

VBinvest creates research and learning artifacts only. It is not investment advice, a brokerage service, or a trading system.
