# CAIT Certificate Schema

JSON Schemas for CAIT-style records: certificates, tokens, defeaters, transfer/evaluation boundaries, window balances, and arrival records.
Deterministic local validation checks record shape plus lightweight fail-closed semantics.
This is not an AGI detector, model evaluator, deployment authorization system, or safety guarantee.

## Start Here

If you are new to the project, read these files in order:

1. `schemas/cait/schema_index.json`: maps each `record_type` to its schema file and semantic profile.
2. `schemas/cait/semantic_rules.json`: lists portable fail-closed rule IDs and logic.
3. `examples/valid/arrival_record.json`: shows a complete synthetic arrival record accepted by the local validator.

Minimal adoption path:

1. Use `schema_index.json` to choose the schema for each `record_type`.
2. Run JSON Schema Draft 2020-12 structural validation.
3. Implement the rule IDs in `semantic_rules.json` that apply to your record types.
4. Keep local registry thresholds, evidence rules, and evaluation boundaries explicit in your own records.

This repository is based on:

Takahashi, K. (2026). *Certified Autocatalytic Intelligence Theory: Net-Growth Certificate Algebra for Verified Capability Capital*. Zenodo. https://doi.org/10.5281/zenodo.20061296

## What This Project Is

This project provides a small, auditable schema layer for machine-readable CAIT records:

- registry records;
- certificate records;
- domain witnesses;
- token records;
- operator bundle records;
- defeater records;
- evidence budget ledgers;
- assurance cases;
- transfer, evaluation, and controller certificates;
- window balance certificates;
- arrival records.

It also includes a deterministic local validator for basic structural and semantic checks.

The language-neutral interface is the schema directory itself: `schemas/cait/*.schema.json`, `schemas/cait/schema_index.json`, and `schemas/cait/semantic_rules.json`.

## What This Project Is Not

This project is not:

- an AGI detector;
- a frontier model evaluator;
- a deployment authorization system;
- a safety guarantee;
- an autonomous agent system;
- a database, server, dashboard, or workflow engine;
- a complete implementation of the CAIT paper.

The schemas support machine-readable records. They do not certify AGI, ASI, deployment readiness, or real-world safety by themselves.

## Limitations

- This OSS is JSON Schema plus lightweight local semantic validation only.
- JSON Schema validates record shape, not scientific truth.
- The validator performs lightweight local checks only.
- It does not perform scientific truth validation, causal inference, proof checking, replay, queue simulation, AGI/ASI detection, safety guarantees, or deployment approval.
- It is not a frontier model evaluator, risk-governance process, autonomous agent system, or complete CAIT implementation.
- Users must add registry-specific thresholds, evidence rules, evaluation boundaries, and policy semantics for their own setting.
- The included thresholds and examples are synthetic and illustrative.
- A passing validation result means a record is structurally and minimally semantically consistent with this schema package. It does not mean the underlying claim is true.

## Why It Exists

CAIT treats acceleration as certified net reproduction of verified capability capital, not as raw benchmark gain or candidate volume. The schemas in this repository make CAIT-style records easier for engineers, researchers, auditors, and AI agents to inspect, exchange, validate, and reuse.

The fail-closed principle is central: if a positive claim depends on missing evidence, missing scope, unresolved severe defeaters, invalid lifecycle status, invalid transfer/evaluation boundary, or non-positive endogenous net growth, the local validator reports that the record cannot support a positive CAIT-style claim.

## Quick Start

```bash
uv sync
uv run cait-validate examples/valid/arrival_record.json
uv run pytest
```

Validate a specific schema:

```bash
uv run cait-validate examples/valid/minimal_certificate_record.json --schema certificate_record
```

If `--schema` is omitted, the validator infers the schema from the top-level `record_type` field.

## For Non-Python Users

Python is only a reference validator. It is not the only specification. Other implementations can use the language-neutral files directly:

- `schemas/cait/schema_index.json` to map `record_type` values to schema files;
- `schemas/cait/*.schema.json` for Draft 2020-12 structural validation;
- `schemas/cait/semantic_rules.json` for portable fail-closed semantic checks.

Minimal implementation steps in another language:

1. Read the top-level `record_type` key.
2. Load the matching schema file from `schema_index.json`.
3. Validate structure with any JSON Schema Draft 2020-12 implementation.
4. Apply each relevant rule from `semantic_rules.json`.
5. Report the same `rule_id` values where feasible.

The semantic rules manifest contains stable rule IDs, severity, affected record types, primary JSON paths, portable logic, and human-readable descriptions.
The `portable_logic` fields are JSONPath-like pseudocode for implementers. They are intended to make the rule semantics clear across languages, not to require a specific JSONPath library.

## Core Concepts

- `registry_record`: declares the coordinate dictionary, lifecycle table, evidence modes, external-input boundary, evaluator boundary, service graph, transfer boundary, and acceptance rule.
- `certificate_record`: carries a lower/upper interval, evidence mode, lifecycle status, dependency support, defeaters, freshness, and provenance links.
- `domain_witness`: records whether certificate composition predicates are satisfied, including compatible scope, accepted dependencies, valid budget, fresh evidence, no open blocking defeater, and disjoint support.
- `token_record`: represents a content-addressed capability artifact with lifecycle status, evidence links, lineage, transfer/evaluation boundary links, and resource charges.
- `defeater_record`: records a possible blocker or downgrader, including severity, affected scope, and resolution status.
- `arrival_record`: reports whether a target profile satisfies the registered CAIT-style arrival decision rule.
- `endogenous_net_growth_interval`: lower/upper interval for net endogenous growth after losses and resource/risk charges.
- `external_injection_share`: share of reported production attributable to logged external injection.
- `unresolved_attribution_share`: share of reported production that remains unresolved.
- `transfer_coverage`: fraction of target coordinates covered by accepted transfer evidence.
- `queue_margin`: lower service capacity minus arrival demand.
- `safety_control_status`: whether service and safety-control constraints pass, fail, or remain conditional.

## Minimal Example

```json
{
  "record_type": "arrival_record",
  "arrival_id": "arr_demo_001",
  "target_profile_id": "synthetic_target_profile",
  "final_decision": "pass",
  "mandatory_subcertificates_status": "accepted",
  "mandatory_subcertificate_ids": [
    "cert_window_balance_demo",
    "cert_transfer_demo",
    "cert_evaluation_demo",
    "cert_controller_demo"
  ],
  "endogenous_net_growth_interval": {
    "lower": 1.25,
    "upper": 2.0,
    "unit": "capability_tokens_per_window",
    "confidence": 0.95
  },
  "queue_margin": {
    "lower": 0.4,
    "upper": 1.1,
    "unit": "verified_tokens_per_day"
  },
  "external_injection_share": 0.1,
  "unresolved_attribution_share": 0.0,
  "transfer_coverage": 1.0,
  "acceptance_thresholds": {
    "max_external_injection_share": 0.2,
    "max_unresolved_attribution_share": 0.05,
    "min_transfer_coverage": 0.9,
    "max_residual_risk_upper": 0.1
  },
  "target_coordinate_statuses": [
    {
      "coordinate": "synthetic_code_repair",
      "status": "accepted",
      "within_boundary": true
    }
  ],
  "target_defeaters": [],
  "safety_control_status": "pass",
  "transfer_status": "pass",
  "evaluation_status": "pass",
  "window_balance_status": "pass",
  "operational_metrics": {
    "external_injection_share": 0.1,
    "unresolved_attribution_share": 0.0,
    "transfer_coverage": 1.0,
    "audit_freshness": "pass",
    "residual_risk": {
      "lower": 0.0,
      "upper": 0.05,
      "unit": "risk_score"
    }
  }
}
```

All examples in this repository are synthetic and illustrative.

## Schema List

Schemas are in `schemas/cait/`.

- `schema_index.json`
- `semantic_rules.json`
- `cait.schema.json`
- `common.schema.json`
- `registry_record.schema.json`
- `certificate_record.schema.json`
- `domain_witness.schema.json`
- `token_record.schema.json`
- `operator_bundle_record.schema.json`
- `defeater_record.schema.json`
- `evidence_budget_ledger.schema.json`
- `assurance_case.schema.json`
- `transfer_certificate.schema.json`
- `evaluation_certificate.schema.json`
- `controller_certificate.schema.json`
- `window_balance_certificate.schema.json`
- `arrival_record.schema.json`

## Validation Semantics

JSON Schema validates record structure. The Python validator adds lightweight semantic checks:

- every interval must satisfy `lower <= upper`;
- passing arrival records require `endogenous_net_growth_interval.lower > 0`;
- passing arrival records require `queue_margin.lower > 0`;
- passing arrival records cannot contain unresolved high or blocking target defeaters;
- passing arrival records must have accepted mandatory subcertificates;
- passing arrival records must list at least one mandatory subcertificate ID;
- passing arrival records must have pass status for safety-control, transfer, evaluation, and window-balance subcertificates;
- passing arrival records must keep `external_injection_share` at or below the registered threshold;
- passing arrival records must keep `unresolved_attribution_share` at or below the registered threshold;
- passing arrival records must meet or exceed the registered `transfer_coverage` threshold;
- passing arrival records must have `operational_metrics.audit_freshness = "pass"`;
- passing arrival records must keep `operational_metrics.residual_risk.upper` at or below the registered threshold;
- top-level attribution/coverage shares must match the corresponding `operational_metrics` values;
- lifecycle statuses other than `accepted` cannot claim `positive_capital_effect = "full"`;
- evidence mode strengthening must include an explicit witness;
- a positive claim that requires a domain witness fails if the witness is missing or invalid;
- target coordinates outside the transfer/evaluation boundary must be `abstained_or_uncertified`.

These checks are intentionally limited. They are meant to catch obvious schema-level misuse, not to establish scientific truth.

## Local-Only Behavior

The validator reads local files and local schemas. It does not send data anywhere, call external services, download runtime resources, or collect telemetry.

## Citation

If you use this repository, cite the related manuscript:

Takahashi, K. (2026). *Certified Autocatalytic Intelligence Theory: Net-Growth Certificate Algebra for Verified Capability Capital*. Zenodo. https://doi.org/10.5281/zenodo.20061296

## License

Apache License 2.0. See `LICENSE`.
