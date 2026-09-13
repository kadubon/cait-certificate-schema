"""Offline installed distribution verification, independent of the checkout."""

from __future__ import annotations

import contextlib
import io
import json
import socket
from importlib import metadata, resources
from unittest.mock import patch

from cait_schema import __version__, validate_instance

from .checker import check_report
from .examples import NAMES
from .interchange import companion, integration
from .numeric import AnalysisError, parse
from .report import analyze


def run() -> dict[str, object]:
    with (
        patch.object(socket.socket, "connect", side_effect=RuntimeError("offline execution")),
        patch.object(socket, "create_connection", side_effect=RuntimeError("offline execution")),
    ):
        assert metadata.version("cait-certificate-schema") == __version__ == "0.2.0"
        legacy = resources.files("cait_schema").joinpath("legacy_examples")
        count = 0
        for path in legacy.iterdir():
            if path.name.endswith(".json"):
                assert validate_instance(json.loads(path.read_text(encoding="utf-8"))).valid
                count += 1
        checks = {}
        for name in NAMES:
            path = resources.files("cait_schema.accounting").joinpath("fixtures", name + ".json")
            bundle = parse(path.read_text(encoding="utf-8"))
            report = analyze(bundle)
            status = check_report(bundle, report)["status"]
            assert status == ("inconsistent" if name == "inconsistent" else "checked")
            checks[name] = status
            if name == "interchange":
                result = integration(
                    bundle,
                    report,
                    companion("vek-report-positive.json"),
                    companion("ccr-task.json"),
                    created_at="2026-09-13T00:00:00Z",
                )
                assert result["joint_capacity"] is None
        from .cli import main

        with contextlib.redirect_stdout(io.StringIO()):
            assert main(["example", "interchange"]) == 0
        try:
            from .interchange import import_vek

            negative = companion("vek-report-negative.json")
            import_vek(negative, scope=negative["scope"], source_digest=negative["source_digest"])
        except AnalysisError:
            pass
        else:
            raise AssertionError("Invalid companion fixture accepted")
    return dict(
        version=__version__, legacy_examples=count, scenarios=checks, offline=True, interchange="checked"
    )


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
