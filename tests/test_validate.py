"""Tests for scripts.lib.validate — HTML dashboard validation."""

from scripts.lib.validate import REQUIRED, validate_html


def _minimal_html(*, extra: str = "", forbidden: str = "") -> str:
    tokens = "\n".join(f"<!-- {t} -->" for t in REQUIRED)
    return f"<html><body>{tokens}{extra}{forbidden}</body></html>"


def test_valid_html(tmp_path):
    html = tmp_path / "dashboard.html"
    html.write_text(_minimal_html(), encoding="utf-8")
    result = validate_html(html)
    assert result.ok is True
    assert result.errors == []


def test_missing_file(tmp_path):
    result = validate_html(tmp_path / "nonexistent.html")
    assert result.ok is False
    assert any("missing" in e for e in result.errors)


def test_missing_required_token(tmp_path):
    html = tmp_path / "dashboard.html"
    html.write_text("<html><body>incomplete</body></html>", encoding="utf-8")
    result = validate_html(html)
    assert result.ok is False
    assert any("missing required token" in e for e in result.errors)


def test_forbidden_token(tmp_path):
    html = tmp_path / "dashboard.html"
    html.write_text(_minimal_html(forbidden="<!-- 긍정 관찰 -->"), encoding="utf-8")
    result = validate_html(html)
    assert result.ok is False
    assert any("forbidden token" in e for e in result.errors)


def test_naive_zoom_token(tmp_path):
    html = tmp_path / "dashboard.html"
    html.write_text(_minimal_html(extra="applyZoomViewBox"), encoding="utf-8")
    result = validate_html(html)
    assert result.ok is False
    assert any("applyZoomViewBox" in e for e in result.errors)


def test_html_not_ending_with_closing_tag(tmp_path):
    html = tmp_path / "dashboard.html"
    html.write_text(_minimal_html() + "\n<!-- trailing -->", encoding="utf-8")
    result = validate_html(html)
    assert result.ok is False
    assert any("does not end with </html>" in e for e in result.errors)
