# Security

This project contains JSON Schemas, synthetic examples, and local validation tooling for CAIT-style records.

It is not a service, agent framework, evaluator, deployment authorizer, or monitoring system. By default it has:

- no network calls;
- no telemetry;
- no runtime downloads;
- no cloud-service dependency;
- no background automation.

Do not place sensitive operational records, credentials, private logs, model secrets, incident reports, API keys, tokens, cookies, or proprietary evaluation data in public examples or public issues.

If you report a security issue in the tooling, include a minimal synthetic reproduction. Do not include sensitive data.

The opt-in accounting parser uses closed local schemas, bounded exact rationals and immutable
source-byte digests. It rejects duplicate keys, remote/executable schema inputs and ambiguous
cost/credit records. Hashes do not authenticate operators; no signature-verification or causal
estimation profile is claimed. Derived output requires a new path and cannot overwrite source
evidence. Independent reconstruction does not authorize execution or prove source truth.
See `docs/accounting.md` for finite limits and `docs/interchange.md` for pinned adapter boundaries.
