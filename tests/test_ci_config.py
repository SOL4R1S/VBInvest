from __future__ import annotations

import re
from pathlib import Path

from scripts.secret_scan import scan_text


ROOT = Path(__file__).resolve().parents[1]


def read_workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_ci_workflow_triggers_quality_checks_for_git_flow_push_and_pull_request() -> None:
    workflow = read_workflow("ci.yml")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "branches: [develop, main, release/**]" in workflow
    for required in [
        "python -m pytest -q",
        "npm run lint",
        "npm run typecheck",
        "npm test -- --run",
        "npm run build",
        "npx playwright test",
        "scripts/secret_scan.py",
    ]:
        assert required in workflow


def test_backend_pytest_steps_pin_repo_root_on_pythonpath() -> None:
    for workflow_name in ["ci.yml", "release.yml"]:
        workflow = read_workflow(workflow_name)

        assert "PYTHONPATH: ${{ github.workspace }}" in workflow
        assert "python -m pytest -q" in workflow


def test_ci_workflow_runs_git_hook_parity_and_launcher_package_smoke() -> None:
    workflow = read_workflow("ci.yml")

    assert "scripts/git_hooks/check_paths.py" in workflow
    assert "scripts/git_hooks/check_commit_msg.py" in workflow
    assert "scripts/git_hooks/check_pre_push.py" in workflow or (
        "validate_branch_name" in workflow and "validate_origin_url" in workflow
    )
    assert "make launcher-smoke" in workflow
    assert "make package-smoke" in workflow


def test_release_workflow_publishes_v_tag_launcher_artifacts_with_build_metadata() -> None:
    workflow = read_workflow("release.yml")

    assert "tags:" in workflow
    assert "v*" in workflow
    assert "actions/upload-artifact" in workflow
    assert "softprops/action-gh-release" in workflow
    for required in [
        "VBinvest.command",
        "VBinvest.bat",
        "VBinvest.ps1",
        "README.md",
        "README.en.md",
        "VERSION",
        "build_version.txt",
    ]:
        assert required in workflow
    assert "VBINVEST_BUILD_VERSION" in workflow or "load_version_metadata" in workflow or "build_version" in workflow


def test_readmes_document_git_flow_publish_and_release_process() -> None:
    korean = (ROOT / "README.md").read_text(encoding="utf-8")
    english = (ROOT / "README.en.md").read_text(encoding="utf-8")

    for required in ["Publishing / Release", "origin/develop", "force-push", "secret scan"]:
        assert required in korean
        assert required in english
    assert "릴리스 태그" in korean
    assert "artifact" in korean
    assert "release tag" in english
    assert "release artifact" in english


def test_makefile_exposes_single_local_test_gate() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "test:" in makefile
    assert "backend-test" in makefile
    assert "frontend-test" in makefile
    assert "e2e-test" in makefile
    assert "secret-scan" in makefile


def test_secret_scan_rejects_real_password_fixture() -> None:
    findings = scan_text("POSTGRES_PASSWORD=real-password-12345", "fixture.env")

    assert findings == ["fixture.env: POSTGRES_PASSWORD must use a <placeholder> value"]


def test_ci_workflow_declares_release_branch_glob_only_once_for_branches_array() -> None:
    workflow = read_workflow("ci.yml")

    assert re.search(r"branches:\s*\[develop,\s*main,\s*release/\*\*\]", workflow)
