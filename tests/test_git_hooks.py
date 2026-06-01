from __future__ import annotations

from pathlib import Path

from scripts.git_hooks.check_commit_msg import validate_commit_message
from scripts.git_hooks.check_paths import find_forbidden_paths
from scripts.git_hooks.check_pre_push import EXPECTED_ORIGIN_URL, validate_branch_name, validate_origin_url
from scripts.git_hooks.install_hooks import install_hooks


def test_commit_msg_rejects_malformed_message() -> None:
    result = validate_commit_message("bad message\n")

    assert not result.ok
    assert "Conventional Commit" in result.message


def test_commit_msg_accepts_conventional_message() -> None:
    result = validate_commit_message("chore: initialize git flow\n")

    assert result.ok


def test_path_guard_rejects_local_data_and_secrets() -> None:
    legacy_period = "".join(["w", "e", "e", "k", "l", "y"])
    legacy_market_period = "".join(["d", "a", "i", "l", "y"])
    findings = find_forbidden_paths(
        [
            ".env",
            "data/vbinvest.sqlite3",
            "reports/NVDA/2026-06-01.md",
            "vault/VBinvest",
            ".omo/start-work/ledger.jsonl",
            "evidence/task-1-red.txt",
            ".agents/skills/vbinvest-data-ingestion/SKILL.md",
            ".apm/instructions/vbinvest.instructions.md",
            "HERMES.md",
            f"scripts/{legacy_period}_pipeline.py",
            f"scripts/{legacy_market_period}_market_ingest.py",
        ],
    )

    assert findings == [
        ".env: local env files must not be committed",
        "data/vbinvest.sqlite3: local database files must not be committed",
        "reports/NVDA/2026-06-01.md: generated reports must not be committed",
        "vault/VBinvest: vault links or exports must not be committed",
        ".omo/start-work/ledger.jsonl: local orchestration state must not be committed",
        "evidence/task-1-red.txt: local QA evidence must not be committed",
        ".agents/skills/vbinvest-data-ingestion/SKILL.md: local agent/operator context must not be committed",
        ".apm/instructions/vbinvest.instructions.md: local agent/operator context must not be committed",
        "HERMES.md: local agent/operator context must not be committed",
        f"scripts/{legacy_period}_pipeline.py: scheduled recurring research pipeline must not be committed",
        f"scripts/{legacy_market_period}_market_ingest.py: scheduled market ingest surface must not be committed",
    ]


def test_path_guard_allows_examples_and_source_files() -> None:
    findings = find_forbidden_paths([".env.example", "scripts/api.py", "README.md"])

    assert findings == []


def test_origin_validation_accepts_public_repo_url() -> None:
    result = validate_origin_url(EXPECTED_ORIGIN_URL)

    assert result.ok


def test_origin_validation_rejects_other_remote() -> None:
    result = validate_origin_url("https://github.com/example/other.git")

    assert not result.ok
    assert EXPECTED_ORIGIN_URL in result.message


def test_branch_validation_accepts_git_flow_branches() -> None:
    accepted = ["main", "develop", "feature/local-launcher", "release/v0.1.0", "hotfix/auth-fix"]

    assert [validate_branch_name(branch).ok for branch in accepted] == [True, True, True, True, True]


def test_branch_validation_rejects_unplanned_branch() -> None:
    result = validate_branch_name("random-work")

    assert not result.ok
    assert "Git Flow" in result.message


def test_hook_installer_is_tracked_script() -> None:
    assert Path("scripts/git_hooks/install_hooks.py").exists()


def test_hook_installer_writes_python_wrappers(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()

    install_hooks(tmp_path)

    commit_msg_hook = (tmp_path / ".git" / "hooks" / "commit-msg").read_text(encoding="utf-8")
    assert "python scripts/git_hooks/check_commit_msg.py" in commit_msg_hook
