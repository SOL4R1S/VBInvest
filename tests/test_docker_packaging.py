from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "postgres" / "docker-compose.yml"
ENV_EXAMPLE_PATH = ROOT / "postgres" / ".env.example"
MAKEFILE_PATH = ROOT / "Makefile"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_target_block(makefile_text: str, target: str) -> str:
    lines = makefile_text.splitlines()
    target_pattern = re.compile(rf"^{re.escape(target)}:\s*$")
    start = None
    for index, line in enumerate(lines):
        if target_pattern.match(line):
            start = index + 1
            break
    assert start is not None, f"missing make target: {target}"

    block: list[str] = []
    for line in lines[start:]:
        if not line.strip():
            continue
        if line and not line.startswith("\t"):
            break
        block.append(line)
    return "\n".join(block)


def test_docker_compose_loops_back_and_uses_named_data_volume() -> None:
    text = read_text(COMPOSE_PATH)
    ports = re.findall(r"^[ \t]*-\s*\"([^\"]+)\"\s*$", text, flags=re.MULTILINE)

    assert "127.0.0.1:5432:5432" in ports
    assert "0.0.0.0:5432:5432" not in text
    assert "vbinvest-postgres-data:/var/lib/postgresql/data" in text
    assert "./init:/docker-entrypoint-initdb.d:ro" in text


def test_docker_packaging_configuration_uses_placeholders_and_no_secrets() -> None:
    compose = read_text(COMPOSE_PATH)
    env_example = read_text(ENV_EXAMPLE_PATH)

    assert "env_file:" in compose
    assert "- .env" in compose
    assert "POSTGRES_PASSWORD=<generate-local-password>" in env_example
    assert "POSTGRES_PASSWORD=secret" not in compose
    assert "POSTGRES_PASSWORD=secret" not in env_example
    assert "/Volumes/" not in compose
    assert "/Volumes/" not in read_text(MAKEFILE_PATH)


def test_makefile_has_packaging_smoke_targets_and_docker_guard() -> None:
    text = read_text(MAKEFILE_PATH)
    for target in ("launcher-smoke", "package-smoke", "docker-postgres-smoke"):
        assert re.search(rf"(?m)^{re.escape(target)}:\s*$", text), f"Makefile is missing target: {target}"

    docker_block = extract_target_block(text, "docker-postgres-smoke")
    assert "command -v docker >/dev/null 2>&1" in docker_block
    assert "SKIP (docker unavailable)" in docker_block
    assert "docker compose config --quiet" in docker_block
    assert re.search(r"docker compose config(?!\s+--quiet)", docker_block) is None, (
        "docker-postgres-smoke must use --quiet for config validation"
    )
