"""Generate additive schemas, reference tables and inert examples deterministically."""

from __future__ import annotations

import json
from pathlib import Path

from cait_schema.accounting.checker import check_report
from cait_schema.accounting.examples import NAMES, example
from cait_schema.accounting.report import analyze
from cait_schema.accounting.schema import SCHEMAS

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    schema_dir = ROOT / "schemas" / "accounting"
    fixtures = ROOT / "src" / "cait_schema" / "accounting" / "fixtures"
    docs = ROOT / "docs"
    for path in (schema_dir, fixtures, docs):
        path.mkdir(parents=True, exist_ok=True)
    index = {}
    for name, schema in SCHEMAS.items():
        file = name + ".schema.json"
        value = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://cait-schema.local/schemas/accounting/v1/" + file,
            "title": "CAIT computation v1 " + name,
            **schema,
        }
        (schema_dir / file).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        index[name] = file
    (schema_dir / "schema_index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    lines = [
        "# Generated computation schema reference",
        "",
        "Legacy `schemas/cait` is unchanged.",
        "",
        "| Profile | Schema |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | `schemas/accounting/{file}` |" for name, file in index.items()]
    lines += ["", "## Synthetic examples", "", "| Example | Independent check |", "| --- | --- |"]
    for name in NAMES:
        bundle = example(name)
        report = analyze(bundle)
        (fixtures / (name + ".json")).write_text(
            json.dumps(bundle, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        lines.append(f"| {name} | {check_report(bundle, report)['status']} |")
    (docs / "generated_reference.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
