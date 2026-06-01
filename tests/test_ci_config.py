from pathlib import Path

from scripts.secret_scan import scan_text


ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_runs_backend_frontend_e2e_and_secret_scan():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "pytest -q" in workflow
    assert "npm run lint" in workflow
    assert "npm run typecheck" in workflow
    assert "npm test -- --run" in workflow
    assert "npm run build" in workflow
    assert "npx playwright test" in workflow
    assert "scripts/secret_scan.py" in workflow


def test_makefile_exposes_single_local_test_gate():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "test:" in makefile
    assert "backend-test" in makefile
    assert "frontend-test" in makefile
    assert "e2e-test" in makefile
    assert "secret-scan" in makefile


def test_secret_scan_rejects_real_password_fixture():
    findings = scan_text("POSTGRES_PASSWORD=real-password-12345", "fixture.env")

    assert findings == ["fixture.env: POSTGRES_PASSWORD must use a <placeholder> value"]
