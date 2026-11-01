"""Guard against accidentally restoring arbitrary code execution in production."""
import ast
from pathlib import Path


def test_runtime_has_no_dynamic_eval_or_exec():
    root = Path(__file__).resolve().parents[1]
    for directory in ("plugins", "database", "helpers"):
        for path in (root / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    assert node.func.id not in {"eval", "exec"}, (
                        f"{path} executes dynamic code: {node.func.id}"
                    )


def test_filter_schema_fields_remain_unchanged():
    from database import filters_mdb
    # Checks the public repository's documented legacy names, not a live DB.
    assert {"CONNECTION", "USERS", "authorised_users", "settings", "BROADCAST"}.issubset(
        filters_mdb.EXCLUDED_COLLECTIONS
    )
