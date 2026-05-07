from __future__ import annotations

from cait_schema.cli import main


def test_cli_valid_file_exits_zero(capsys) -> None:
    exit_code = main(["examples/valid/arrival_record.json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "structural: pass" in output
    assert "semantic: pass" in output


def test_cli_invalid_file_reports_rule_id(capsys) -> None:
    exit_code = main(["examples/invalid/arrival_residual_risk_above_threshold.json"])
    output = capsys.readouterr().out
    assert exit_code != 0
    assert "rule_id: passing_arrival_respects_residual_risk_threshold" in output
