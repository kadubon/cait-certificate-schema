from __future__ import annotations

import json
import re
from pathlib import Path

from cait_schema.validator import validate_instance


def test_first_readme_json_snippet_is_valid() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", readme, flags=re.DOTALL)
    assert match, "README should contain a JSON example."
    instance = json.loads(match.group(1))
    result = validate_instance(instance)
    assert result.valid, result.errors
