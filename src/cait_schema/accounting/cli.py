"""Read-only computations with explicit atomic output creation."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .checker import check_report
from .examples import NAMES, example
from .interchange import companion, export_ccr, integration
from .numeric import AnalysisError, parse, require
from .replay import replay
from .report import analyze, window
from .reproduction import reproduction
from .source import prepare


def atomic_output(path: Path, text: str, sources: list[Path]) -> None:
    require(
        path.resolve() not in {p.resolve() for p in sources} and not path.exists(),
        "output_exists",
        "Output must be a new path, distinct from source evidence",
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".cait-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link creation fails atomically if another writer creates the destination.
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cait-analyze")
    parser.add_argument(
        "command",
        choices=[
            "validate-bundle",
            "replay",
            "window",
            "reproduction",
            "check-report",
            "export-ccr",
            "example",
        ],
    )
    parser.add_argument("input", nargs="?")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--created-at", help="Explicit proposal creation timestamp")
    args = parser.parse_args(argv)
    result: dict[str, Any]
    sources: list[Path] = []
    try:
        if args.command == "example":
            require(args.input in NAMES, "example", "Choose: " + ", ".join(NAMES))
            bundle = example(args.input)
            report = analyze(bundle)
            result = dict(bundle=bundle, report=report, check=check_report(bundle, report))
            if args.input == "interchange":
                result["interchange"] = integration(
                    bundle,
                    report,
                    companion("vek-report-positive.json"),
                    companion("ccr-task.json"),
                    created_at="2026-09-13T00:00:00Z",
                )
        else:
            require(args.input is not None, "input", "Input path required")
            sources = [Path(args.input)]
            bundle = parse(sources[0].read_text(encoding="utf-8"))
            if args.command == "reproduction":
                result = reproduction(bundle)
            elif args.command == "window":
                result = analyze(bundle)
            elif args.command == "check-report":
                require(args.report is not None, "input", "--report required")
                sources.append(args.report)
                result = check_report(bundle, parse(args.report.read_text(encoding="utf-8")))
            elif args.command == "export-ccr":
                require(args.created_at is not None, "timestamp", "--created-at required")
                result = export_ccr(bundle, window(bundle), created_at=args.created_at)
            else:
                prepared = prepare(bundle)
                result = (
                    dict(
                        status="unknown" if prepared.missing else "validated",
                        missing=list(prepared.missing),
                        authority=None,
                    )
                    if args.command == "validate-bundle"
                    else dict(traces=[replay(prepared, s) for s in prepared.contract["scenarios"]])
                )
        text = json.dumps(result, sort_keys=True, indent=2) + "\n"
        if args.out:
            atomic_output(args.out, text, sources)
        else:
            print(text, end="")
    except (AnalysisError, OSError, ValueError) as exc:
        result = dict(
            status=getattr(exc, "status", "invalid"), code=getattr(exc, "code", "input"), detail=str(exc)
        )
        print(json.dumps(result))
    return {"invalid": 2, "inconsistent": 3, "exhausted": 4, "unknown": 0}.get(result.get("status", ""), 0)


if __name__ == "__main__":
    raise SystemExit(main())
