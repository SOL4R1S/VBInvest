"""Tests for scripts.routers.frontend — health, system, and static serving."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from scripts import api
from scripts.api import app


def test_health_endpoint():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_system_info(monkeypatch):
    monkeypatch.setattr(api, "db", lambda: None)
    client = TestClient(app)
    resp = client.get("/api/system/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "platform" in body


def test_frontend_serves_index(monkeypatch, tmp_path):
    index = tmp_path / "index.html"
    index.write_text("<html><body>VBinvest</body></html>")
    monkeypatch.setattr(api, "frontend_out_dir", lambda: tmp_path)
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "VBinvest" in resp.text


def test_frontend_serves_asset(monkeypatch, tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "main.js").write_text("console.log(1)")
    monkeypatch.setattr(api, "frontend_out_dir", lambda: tmp_path)
    client = TestClient(app)
    resp = client.get("/assets/main.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text


def test_frontend_spa_fallback(monkeypatch, tmp_path):
    index = tmp_path / "index.html"
    index.write_text("<html>SPA</html>")
    monkeypatch.setattr(api, "frontend_out_dir", lambda: tmp_path)
    client = TestClient(app)
    resp = client.get("/some/deep/route")
    assert resp.status_code == 200
    assert "SPA" in resp.text


def test_frontend_404_when_no_build(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "frontend_out_dir", lambda: tmp_path / "nonexistent")
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 404
