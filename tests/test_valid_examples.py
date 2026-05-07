from __future__ import annotations

from pathlib import Path

from cait_schema.validator import validate_file


def test_valid_examples_pass() -> None:
    paths = sorted(Path("examples/valid").glob("*.json"))
    assert paths, "No valid examples found."
    for path in paths:
        result = validate_file(path)
        assert result.valid, f"{path} should be valid: {result.errors}"
