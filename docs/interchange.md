# Version-bound interoperability

CAIT owns derived reports. It does not write companion ledgers, allocate external resources,
issue leases, approve execution or settle rewards. Adapters are optional local JSON functions;
neither VEK nor CCR is a runtime dependency. No companion repository was modified.

## VEK 1.3.0

The actual public-PyPI wheel is pinned by SHA-256
`4182b48369823b06ea35b9c234ddcea824bf53fe6ece5f068200edf11ddd23ca`, corresponding to
release commit `b07998135cb9dccde1e67db3c6ed77fdec847e09`. Its capacity-report schema
and generated positive/negative fixtures are copied byte-for-byte with license and source
hashes in `src/cait_schema/accounting/fixtures/companions/manifest.json`.

`import_vek` validates the pinned schema, exact producer version, explicit expected scope/source
digest, finite horizon, rational slot duration, unique work IDs, work conservation and resource
dimensions. It retains checkpoint revision, contract identity, work unit, offered/completed/due/
unfinished quantities, repair, pending followups, resource use and the separately labeled forecast.
The positive fixture is admitted; the actual negative fixture contains a fabricated average-derived
guarantee and is rejected. This is a semantic regression against released fixtures, not a generic
JSON round trip. An accepted VEK packet does not establish measured throughput or independent errors.

The report lacks its full original reducer journal, so imported counters are explicitly VEK-supplied,
not independently reconstructed CAIT measurements. Observed/guaranteed rate remains null. Cross-scope
valuation and simultaneous capacity are unknown. The integration example binds all source digests
but does not merge incompatible clocks or resources by implication.

## CCR 1.8.0

Pinned commit `1591e88e3b05f9b5fb06b2d0c749aad8bc0909be` supplies the actual
`ccr.task.v0.1` schema and `examples/minimal/task.json`, plus the phase-observation schema,
Apache-2.0 license and NOTICE. Full source paths and SHA-256 values are in the same manifest.

The task importer retains task/input/dependency identity. That published task subset does not
establish run/arm/holdout identity, unique physical cost events, journal completeness or qualified
receiver outcomes; these stay missing. The phase-observation schema is reference material only,
not an implemented source-accounting importer. No legacy aggregate is promoted to replayed evidence.

`export_ccr` independently checks the native CAIT report before producing a CAIT-owned
`cait_ccr_accounting_sidecar_v1` and schema-valid CCR task proposal. It carries exact per-coordinate
balances, source/report digests, costs, origin shares, lifecycle residuals and verifier-work obligations
in explicit `x_` extension fields. The proposal is open, unleased, read-only, network-disabled and
candidate-only. Custom verifier-registry admission is required; no registry binding is invented.
Its timestamp must be supplied explicitly. It contains no command to run or private source material.
An input reference never grants a different mission access to its underlying bytes.

`integration` binds the native checked report, actual VEK fixture and actual CCR source task to a
derived envelope and export. Statistical coverage, causal attribution, joint capacity, arrival and
execution authority remain unestablished. It never emits a passing legacy `arrival_record`.
