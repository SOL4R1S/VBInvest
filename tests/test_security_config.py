from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_postgres_env_example_uses_placeholder_password():
    text = (ROOT / "postgres" / ".env.example").read_text(encoding="utf-8")

    assert "POSTGRES_PASSWORD=<generate-local-password>" in text
    assert "statusbar" not in text


def test_tracked_docs_do_not_contain_sample_password_value():
    checked_paths = [
        ROOT / "README.md",
        ROOT / "postgres" / ".env.example",
        ROOT / "frontend" / ".env.example",
    ]

    leaked = []
    for path in checked_paths:
        if path.is_dir():
            files = path.rglob("*.md")
        else:
            files = [path]
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            if "statusbar!662" in text:
                leaked.append(str(file_path.relative_to(ROOT)))

    assert leaked == []


def test_gitignore_keeps_local_env_and_virtualenv_untracked():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env" in text
    assert "*.env" in text
    assert ".venv/" in text
    assert "__pycache__/" in text
