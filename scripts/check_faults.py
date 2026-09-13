"""Finite guard fault manifest. Isolated copies, assertion failures required."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from defusedxml import ElementTree

ROOT = Path(__file__).resolve().parents[1]
FAULTS = [
    ("origin-conservation", "source.py", "sum(shares) == 1", "True", "test_contract_guards"),
    (
        "physical-cost-dedup",
        "source.py",
        'cid not in cost_ids, "duplicate_cost"',
        'True, "duplicate_cost"',
        "test_truncation_and_conflicting_cost",
    ),
    (
        "negative-completeness",
        "source.py",
        'if not c["negative_terms_complete"]:',
        "if False:",
        "test_missing_obligations_never_strengthen",
    ),
    (
        "receiver-qualification",
        "source.py",
        'set(receiver["checks"]) <= checked',
        "True",
        "test_qualification_is_replayed",
    ),
    (
        "loss-accounting",
        "report.py",
        'opening + gross - totals["losses"]',
        "opening + gross",
        "test_lifecycle",
    ),
    (
        "spectral-inequality",
        "reproduction.py",
        "x >= bound * y if lower else x <= bound * y",
        "True",
        "test_bad_model_witnesses",
    ),
]


def main() -> None:
    results = []
    for name, filename, old, new, test in FAULTS:
        with tempfile.TemporaryDirectory(prefix="cait-fault-") as scratch:
            work = Path(scratch)
            shutil.copytree(
                ROOT / "src" / "cait_schema",
                work / "cait_schema",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            shutil.copytree(
                ROOT / "schemas" / "cait", work / "cait_schema" / "schemas" / "cait", dirs_exist_ok=True
            )
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
            file = work / "cait_schema" / "accounting" / filename
            text = file.read_text(encoding="utf-8")
            assert text.count(old) == 1, (name, "mutant target drift")
            file.write_text(text.replace(old, new), encoding="utf-8")
            env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
            env["PYTHONPATH"] = str(work)
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "tests", "-k", test, "--junitxml=result.xml"],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                timeout=90,
            )
            document = ElementTree.parse(work / "result.xml")
            failures = document.findall(".//failure")
            errors = document.findall(".//error")
            killed = result.returncode == 1 and bool(failures) and not errors
            results.append(
                dict(
                    fault=name,
                    status="killed" if killed else "incomplete_or_survived",
                    failures=len(failures),
                )
            )
            assert killed, (name, result.stdout[-3000:], result.stderr[-1000:])
    (ROOT / "fault-results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results))


if __name__ == "__main__":
    main()
