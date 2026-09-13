from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from cait_schema.accounting.cli import atomic_output, main
from cait_schema.accounting.examples import NAMES, example
from cait_schema.accounting.interchange import (
    companion,
    export_ccr,
    import_ccr_task,
    import_vek,
    integration,
    legacy_partition,
)
from cait_schema.accounting.numeric import AnalysisError, canonical, digest
from cait_schema.accounting.report import window


@pytest.mark.parametrize("name", ["vek-report-positive.json", "vek-report-negative.json"])
def test_actual_vek_fixture(name):
    r = companion(name)
    if name == "vek-report-negative.json":
        with pytest.raises(AnalysisError):
            import_vek(r, scope=r["scope"], source_digest=r["source_digest"])
        return
    imported = import_vek(r, scope=r["scope"], source_digest=r["source_digest"])
    assert imported["completed"] == r["local_accounting"]["completed"]
    assert imported["measured_rate"] is None
    assert imported["forecast"] == r["forecast"]
    assert imported["authority"] is None


def test_real_interchange_path():
    b = example("interchange")
    r = window(b)
    integrated = integration(
        b,
        r,
        companion("vek-report-positive.json"),
        companion("ccr-task.json"),
        created_at="2026-09-13T00:00:00Z",
    )
    assert integrated["native"]["proposal"]["status"] == "open"
    assert integrated["ccr_source"]["accounting"] is None
    assert integrated["joint_capacity"] is None
    assert integrated["native"]["proposal"]["lease"]["leased_by"] is None
    assert integrated["bindings"]["bundle"] == digest(b)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(producer_version="9.0.0"),
        lambda r: r.update(horizon=0),
        lambda r: r["work"].append(deepcopy(r["work"][0])),
        lambda r: r["local_accounting"].update(completed=99),
        lambda r: r.update(slot_seconds="0"),
        lambda r: r["local_accounting"].update(consumed=[]),
        lambda r: r.update(observed_service={"fake": True}),
    ],
)
def test_vek_rejects_promotions(change):
    r = companion("vek-report-positive.json")
    change(r)
    with pytest.raises(AnalysisError):
        import_vek(r, scope=r["scope"], source_digest=r["source_digest"])


def test_interchange_fail_closed():
    with pytest.raises(AnalysisError):
        companion("../../private")
    with pytest.raises(AnalysisError):
        import_ccr_task({})
    b = example()
    r = window(b)
    r["bounds"][0]["lower"] = "100"
    with pytest.raises(AnalysisError):
        export_ccr(b, r, created_at="2026-09-13T00:00:00Z")
    old = json.loads(Path("examples/valid/window_balance_certificate.json").read_text())
    assert legacy_partition(old)["status"] == "unsupported"
    with pytest.raises(AnalysisError):
        legacy_partition({**old, "window_status": "invalid"})


@pytest.mark.parametrize("command", ["validate-bundle", "replay", "window", "check-report", "export-ccr"])
def test_cli_real_operations(tmp_path, capsys, command):
    path = tmp_path / "bundle.json"
    report = tmp_path / "report.json"
    b = example()
    path.write_text(canonical(b))
    report.write_text(canonical(window(b)))
    args = [command, str(path)]
    if command == "check-report":
        args += ["--report", str(report)]
    if command == "export-ccr":
        args += ["--created-at", "2026-09-13T00:00:00Z"]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)
    assert path.read_text() == canonical(b)


def test_cli_matrix_and_examples(tmp_path, capsys):
    b = example()
    path = tmp_path / "model.json"
    path.write_text(b["models"][0]["content"])
    assert main(["reproduction", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["classification"] == "supercritical"
    for name in NAMES:
        output = tmp_path / (name + ".json")
        assert main(["example", name, "--out", str(output)]) == 0
        assert output.exists()
    assert main(["example", "unknown"]) == 2
    assert main(["window"]) == 2
    assert main(["window", str(tmp_path / "missing")]) == 2


def test_output_failure_preserves_sources(tmp_path, monkeypatch):
    src = tmp_path / "source.json"
    src.write_text("source")
    with pytest.raises(AnalysisError):
        atomic_output(src, "replacement", [src])
    assert src.read_text() == "source"

    def fail(*args):
        raise OSError("interrupted")

    monkeypatch.setattr("cait_schema.accounting.cli.os.link", fail)
    with pytest.raises(OSError):
        atomic_output(tmp_path / "result.json", "result", [src])
    assert not list(tmp_path.glob(".cait-*"))
    assert not (tmp_path / "result.json").exists()


def test_cli_failure_codes(tmp_path, capsys):
    b = example("inconsistent")
    path = tmp_path / "bundle.json"
    path.write_text(canonical(b))
    assert main(["window", str(path)]) == 3
    b = example()
    b["contract"]["operation_budget"] = 1
    # Changing registration directly is invalid, not an implied new contract.
    path.write_text(canonical(b))
    assert main(["window", str(path)]) == 2
    path.write_text(canonical(example()))
    assert main(["check-report", str(path)]) == 2
    assert main(["export-ccr", str(path)]) == 2
