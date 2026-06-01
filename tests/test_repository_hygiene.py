from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def test_local_orchestration_and_qa_artifacts_are_not_tracked() -> None:
    files = tracked_files()

    assert not any(path.startswith("docs/") for path in files)
    assert not any(path.startswith(".omo/") for path in files)
    assert not any(path.startswith("evidence/") for path in files)
    assert not any(path.startswith(".agents/") for path in files)
    assert not any(path.startswith(".apm/") for path in files)
    assert "AGENTS.md" not in files
    assert "HERMES.md" not in files
    assert "SOURCE_OF_TRUTH.md" not in files


def test_legacy_hosted_plans_are_not_tracked_in_open_source_pr() -> None:
    files = tracked_files()
    hosted_config = "".join(["v", "e", "r", "c", "e", "l"]) + ".json"

    assert not any(path.startswith("plans/") for path in files)
    assert hosted_config not in files


def test_scheduled_recurring_research_pipeline_is_not_tracked() -> None:
    files = tracked_files()
    legacy_period = "".join(["w", "e", "e", "k", "l", "y"])

    assert f"scripts/{legacy_period}_pipeline.py" not in files
    assert f"scripts/{legacy_period}_research_analysis.py" not in files
    assert f"frontend/app/api/cron/{legacy_period}-research/route.ts" not in files
    assert f"tests/test_{legacy_period}_pipeline.py" not in files
    assert f"tests/test_{legacy_period}_research.py" not in files


def test_scheduled_market_ingest_surface_is_not_tracked() -> None:
    files = tracked_files()
    legacy_period = "".join(["d", "a", "i", "l", "y"])

    assert f"scripts/{legacy_period}_market_ingest.py" not in files
    assert f"scripts/lib/{legacy_period}_scheduler.py" not in files
    assert f"frontend/app/api/cron/{legacy_period}-ingest/route.ts" not in files
    assert f"tests/test_{legacy_period}_market_ingest.py" not in files
    assert f"tests/test_{legacy_period}_cron.py" not in files


def test_no_legacy_vibe_investing_references_are_tracked() -> None:
    forbidden_terms = [
        "-".join(["vibe", "investing"]),
        "-".join(["semiconductor", "vibe"]),
        "".join(["gameworker", "kim"]),
    ]
    offenders: list[str] = []
    for path in sorted(tracked_files()):
        full_path = ROOT / path
        if not full_path.is_file():
            continue
        try:
            text = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(term in text for term in forbidden_terms):
            offenders.append(path)

    assert offenders == []
