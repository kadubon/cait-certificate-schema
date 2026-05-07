from __future__ import annotations

import argparse
import sys

from cait_schema.validator import validate_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cait-validate",
        description="Validate a local CAIT-style JSON record against local JSON Schemas and lightweight semantic checks.",
    )
    parser.add_argument("json_file", help="Path to a JSON record.")
    parser.add_argument("--schema", help="Schema name, for example 'arrival_record'. If omitted, record_type is used.")
    args = parser.parse_args(argv)

    try:
        result = validate_file(args.json_file, schema_name=args.schema)
    except Exception as exc:  # noqa: BLE001 - CLI should return clear local errors.
        print(f"file: {args.json_file}")
        print(f"schema: {args.schema or '<inferred>'}")
        print("structural: fail")
        print("semantic: fail")
        print(f"error: {exc}")
        return 2

    print(f"file: {result.file_path}")
    print(f"schema: {result.schema_name}")
    print(f"structural: {'pass' if result.structural_valid else 'fail'}")
    print(f"semantic: {'pass' if result.semantic_valid else 'fail'}")
    if result.issues:
        print("errors:")
        for issue in result.issues:
            print(f"  - rule_id: {issue.rule_id}")
            print(f"    severity: {issue.severity}")
            print(f"    record_types: {', '.join(issue.record_types)}")
            print(f"    path: {issue.path}")
            print(f"    message: {issue.message}")
    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
