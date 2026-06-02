from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from scripts.lib.ai_cli_report import (
    AICliAuthError,
    AICliCancelledError,
    AICliInvalidJSONError,
    AICliNotAuthenticatedError,
    AICliNotInstalledError,
    AICliOutputTooLargeError,
    AICliReportResult,
    AICliSchemaError,
    AICliTimeoutError,
    AICliRunError,
    sanitize_report_prompt_payload,
    run_codex_report,
    run_copilot_report,
)


def _write_exec(path: Path, lines: list[str]) -> Path:
    source = "#!/usr/bin/env python3\n" + "\n".join(lines) + "\n"
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def _find_arg(values: list[str], key: str) -> Path:
    for index, arg in enumerate(values):
        if arg == key and index + 1 < len(values):
            return Path(values[index + 1])
    raise AssertionError(f"missing arg: {key}")


def _capture_exec(path: Path, capture: Path, extra_lines: list[str] | None = None) -> Path:
    lines = [
        "import json",
        "import pathlib",
        "import sys",
        f"pathlib.Path(r'{capture.as_posix()}').write_text(json.dumps([sys.argv[0]] + sys.argv[1:], ensure_ascii=False), encoding='utf-8')",
    ]
    if extra_lines:
        lines.extend(extra_lines)
    return _write_exec(path, lines)


def test_baseline_command_uses_separate_argv_and_is_injection_safe(tmp_path: Path) -> None:
    marker = tmp_path / "injected.txt"
    capture = tmp_path / "args.json"
    exec_path = _capture_exec(
        tmp_path / "codex",
        capture,
        [
            "import pathlib",
            "for idx, arg in enumerate(sys.argv):",
            "    if arg == '-o' and idx + 1 < len(sys.argv):",
            "        pathlib.Path(sys.argv[idx + 1]).write_text('{\"opinion\":\"중립\",\"thesis\":\"t\",\"rationale\":[\"r\"],\"bull\":\"b\",\"base\":\"b\",\"bear\":\"b\",\"risks\":[],\"triggers\":[],\"confidence\":0.5}', encoding='utf-8')",
            "    if arg == '--ephemeral' and idx + 1 < len(sys.argv):",
            "        prompt = pathlib.Path(sys.argv[idx + 1]).read_text(encoding='utf-8')",
            "        if '$(touch' in prompt:",
            f"            Path(r'{marker.as_posix()}').write_text('bad')",
        ],
    )

    result = run_codex_report(
        "NVDA;$(touch " + marker.as_posix() + ")",
        {"asset": "NVDA;$(touch " + marker.as_posix() + ")", "sources": [], "disclosures": []},
        executable_path=str(exec_path),
        timeout_seconds=2.0,
        authenticated=True,
    )

    args = json.loads(capture.read_text(encoding="utf-8"))
    assert isinstance(result, AICliReportResult)
    assert isinstance(args, list) and args[0] == str(exec_path)
    assert args.count("-o") == 1
    assert args.count("--output-schema") == 1
    assert args.count("-o") == 1
    assert args.count("--cd") == 1
    assert "--sandbox" in args
    assert not marker.exists()


def test_run_codex_success_reads_valid_json_output_and_schema(tmp_path: Path) -> None:
    capture = tmp_path / "args.json"
    exec_path = _capture_exec(
        tmp_path / "codex",
        capture,
        [
            "for idx, arg in enumerate(sys.argv):",
            "    if arg == '-o' and idx + 1 < len(sys.argv):",
            "        pathlib.Path(sys.argv[idx + 1]).write_text('{\"opinion\":\"중립\",\"thesis\":\"base\",\"rationale\":[\"r\"],\"bull\":\"b\",\"base\":\"b\",\"bear\":\"b\",\"risks\":[],\"triggers\":[],\"confidence\":0.5}', encoding='utf-8')",
        ],
    )

    result = run_codex_report(
        "NVDA",
        {"asset": "NVDA", "sources": ["news"], "disclosures": []},
        executable_path=str(exec_path),
        timeout_seconds=2.0,
        authenticated=True,
    )
    assert result.payload["opinion"] == "중립"
    assert result.command[:2] == [str(exec_path), "exec"]


def test_run_codex_timeout_kills_process_and_cleans(tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "codex",
        [
            "import time",
            "time.sleep(5)",
        ],
    )
    with pytest.raises(AICliTimeoutError):
        run_codex_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(exec_path),
            timeout_seconds=0.2,
            authenticated=True,
        )


def test_run_codex_non_zero_exit_with_non_secret_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "copilot",
        [
            "import sys",
            "sys.stderr.write('auth failed for super-secret-token\\n')",
            "sys.exit(2)",
        ],
    )

    with pytest.raises(AICliRunError) as err:
        run_copilot_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(exec_path),
            timeout_seconds=1.0,
            authenticated=True,
        )
    assert "super-secret-token" not in str(err.value)


def test_run_codex_invalid_json_output_raises(tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "codex",
        [
            "import pathlib",
            "import sys",
            "for idx, arg in enumerate(sys.argv):",
            "    if arg == '-o' and idx + 1 < len(sys.argv):",
            "        pathlib.Path(sys.argv[idx + 1]).write_text('{invalid-json', encoding='utf-8')",
        ],
    )
    with pytest.raises(AICliInvalidJSONError):
        run_codex_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(exec_path),
            timeout_seconds=2.0,
            authenticated=True,
        )


def test_run_codex_schema_mismatch_raises(tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "codex",
        [
            "import json",
            "import pathlib",
            "import sys",
            "for idx, arg in enumerate(sys.argv):",
            "    if arg == '-o' and idx + 1 < len(sys.argv):",
            "        pathlib.Path(sys.argv[idx + 1]).write_text(json.dumps({'opinion':'중립'}), encoding='utf-8')",
        ],
    )
    with pytest.raises(AICliSchemaError):
        run_codex_report(
            "NVDA",
            {"asset": "NVDA", "opinion": "중립"},
            executable_path=str(exec_path),
            timeout_seconds=2.0,
            schema={
                "type": "object",
                "required": ["opinion", "thesis"],
                "properties": {
                    "opinion": {"type": "string"},
                    "thesis": {"type": "string"},
                },
            },
            authenticated=True,
        )


def test_run_copilot_unauthenticated_state_blocked(tmp_path: Path) -> None:
    with pytest.raises(AICliNotAuthenticatedError):
        run_copilot_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(tmp_path / "copilot"),
            timeout_seconds=1.0,
            authenticated=False,
        )


def test_copilot_missing_binary_blocked(tmp_path: Path) -> None:
    with pytest.raises(AICliNotInstalledError):
        run_copilot_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(tmp_path / "missing-copilot"),
            timeout_seconds=1.0,
            authenticated=True,
        )


def test_run_codex_cancellation_stops_process(tmp_path: Path) -> None:
    _capture_exec(
        tmp_path / "codex",
        tmp_path / "args.json",
        [
            "import time",
            "time.sleep(8)",
        ],
    )
    canceled = threading.Event()
    seen: dict[str, Exception] = {}

    def _run() -> None:
        try:
            run_codex_report(
                "NVDA",
                {"asset": "NVDA"},
                executable_path=str(tmp_path / "codex"),
                timeout_seconds=10.0,
                authenticated=True,
                cancellation_event=canceled,
            )
        except AICliCancelledError as exc:
            seen["error"] = exc

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    time.sleep(0.2)
    canceled.set()
    thread.join(timeout=3.0)

    assert isinstance(seen.get("error"), AICliCancelledError)
    assert not thread.is_alive()


def test_run_codex_cleanup_removes_temp_workspace(tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "codex",
        [
            "import json",
            "import pathlib",
            "import sys",
            "for idx, arg in enumerate(sys.argv):",
            "    if arg == '-o' and idx + 1 < len(sys.argv):",
            "        pathlib.Path(sys.argv[idx + 1]).write_text(json.dumps({'opinion':'중립','thesis':'t','rationale':['r'],'bull':'b','base':'b','bear':'b','risks':[], 'triggers':[], 'confidence':0.5}), encoding='utf-8')",
        ],
    )
    result = run_codex_report(
        "NVDA",
        {"asset": "NVDA", "opinion": "중립"},
        executable_path=str(exec_path),
        timeout_seconds=2.0,
        authenticated=True,
    )
    assert not result.workspace.exists()
    assert not result.output_file.exists()
    assert not result.prompt_file.exists()


def test_sanitize_payload_drops_secret_like_fields() -> None:
    payload = sanitize_report_prompt_payload(
        "NVDA",
        {
            "asset": "NVDA",
            "latest": {"close": 12.34},
            "api_key": "super-secret-token",
            "secret_note": "keep-out",
            "nested": {"token": "do-not-include", "value": 1},
            "sources": ["a", "b"],
            "disclosures": ["x"],
        },
    )
    assert "api_key" not in json.dumps(payload)
    assert "secret" not in json.dumps(payload)
    assert "token" not in json.dumps(payload)
    assert payload["asset"] == "NVDA"
    assert payload["sources"] == ["a", "b"]


def test_output_size_guard_triggers(tmp_path: Path) -> None:
    exec_path = _write_exec(
        tmp_path / "codex",
        [
            "import os",
            "import sys",
            "import time",
            "for _ in range(100000):",
            "    print('x' * 1024)",
            "    os.fsync(1)",
            "    ",
        ],
    )
    with pytest.raises(AICliOutputTooLargeError):
        run_codex_report(
            "NVDA",
            {"asset": "NVDA"},
            executable_path=str(exec_path),
            timeout_seconds=2.0,
            max_output_bytes=32,
            authenticated=True,
        )
