from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts import api


def write_frontend_out(root: Path) -> Path:
    out_dir = root / "out"
    (out_dir / "_next" / "static").mkdir(parents=True)
    (out_dir / "index.html").write_text("<!doctype html><html><body>VBinvest</body></html>", encoding="utf-8")
    (out_dir / "_next" / "static" / "chunk.js").write_text("console.log('VBinvest');", encoding="utf-8")
    return out_dir


def client_with_frontend_out(monkeypatch, out_dir: Path) -> TestClient:
    monkeypatch.setattr(api, "frontend_out_dir", lambda: out_dir, raising=False)
    return TestClient(api.app)


def test_fastapi_serves_built_frontend_index(monkeypatch, tmp_path) -> None:
    out_dir = write_frontend_out(tmp_path)
    client = client_with_frontend_out(monkeypatch, out_dir)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "VBinvest" in response.text


def test_static_frontend_does_not_shadow_health(monkeypatch, tmp_path) -> None:
    out_dir = write_frontend_out(tmp_path)
    client = client_with_frontend_out(monkeypatch, out_dir)

    health_response = client.get("/health")

    assert health_response.status_code == 200
    assert health_response.headers["content-type"].startswith("application/json")
    payload = health_response.json()
    assert payload["status"] == "ok"
    assert payload["version"]
    assert payload["build_version"]
