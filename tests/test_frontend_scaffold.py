from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_scaffold_exists():
    frontend = ROOT / "frontend"
    assert frontend.is_dir()
    assert (frontend / "package.json").is_file()
    assert (frontend / "app" / "page.tsx").is_file()
    assert (frontend / "app" / "layout.tsx").is_file()
    assert (frontend / "tests" / "dashboard.test.ts").is_file()


def test_frontend_does_not_expose_public_test_token_route():
    frontend = ROOT / "frontend"

    assert not (frontend / "app" / "api" / "test-token" / "route.ts").exists()
    # Legacy lib/api.ts was removed; verify no src/lib module exposes the route.
    src_lib = frontend / "src" / "lib"
    if src_lib.is_dir():
        for ts_file in src_lib.glob("*.ts"):
            assert "api/test-token" not in ts_file.read_text(), f"{ts_file.name} references api/test-token"
