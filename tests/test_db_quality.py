import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vbinvestdb_has_no_duplicate_method_names():
    source_path = ROOT / "scripts" / "lib" / "db.py"
    module = ast.parse(source_path.read_text())
    duplicates: list[tuple[str, int, int]] = []

    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == "VBinvestDB":
            seen: dict[str, int] = {}
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    first_line = seen.get(item.name)
                    if first_line is None:
                        seen[item.name] = item.lineno
                    else:
                        duplicates.append((item.name, first_line, item.lineno))

    assert duplicates == []
