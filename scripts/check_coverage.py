"""Enforce separate new-core statement and branch floors, never combined coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CORE = {"numeric.py", "source.py", "replay.py", "report.py", "reproduction.py", "checker.py", "schema.py"}


def main() -> None:
    data = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.json").read_text())
    summaries = [
        v["summary"] for k, v in data["files"].items() if k.replace("\\", "/").split("/")[-1] in CORE
    ]
    assert len(summaries) == len(CORE), "Every new core module must be measured"
    statement = sum(s["covered_lines"] for s in summaries) / sum(s["num_statements"] for s in summaries)
    branch = sum(s["covered_branches"] for s in summaries) / sum(s["num_branches"] for s in summaries)
    print(
        json.dumps(
            {"statement_percent": 100 * statement, "branch_percent": 100 * branch, "core": sorted(CORE)}
        )
    )
    assert statement >= 0.90 and branch >= 0.90, "New core requires >=90% statements AND >=90% branches"


if __name__ == "__main__":
    main()
