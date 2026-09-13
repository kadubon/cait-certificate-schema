# Requirement-to-code/test matrix

Preflight: clean HEAD `8ef4bc1ea272751804655a6e056467837ff35670`, source version 0.1.0,
no tags/Releases/open PRs or public PyPI project. Existing baseline: 14 tests passed.
No pre-existing CI, coverage or mutation gate was found. Main has no branch-protection/rulesets.
The user supplied the pending PyPI publisher identity: owner/repository `kadubon/cait-certificate-schema`,
workflow `workflow.yml`, environment `pypi`. Actual OIDC publication remains a separate gate.

| Scope | Existing / added code | Evidence |
| --- | --- | --- |
| Legacy language-neutral wire contracts/CLI | Existing `schemas/cait`, validator and legacy fixtures preserved | Baseline manifest and original tests |
| C1 closed source-bound exact records | Added `numeric`, `schema`, `source` | Bad numerics/keys/units, binding, duplicate, truncation, dependency and scope tests |
| C1 lifecycle/correction/replay | Added `replay`; independent `checker.reference_trace` | Adjacent windows, copied stock, revocation, expiry, correction, pending and failed reuse |
| C2 disjoint origin/credit/cost conservation | Added `report`, resource checks, declared allocation and valuation | Independent rational oracle, cost and share guards, shared limits, unknown-negative tests |
| C2 receiver-qualified reuse | Added recursive evidence closure and logical outcome key | Receiver/protocol/substitution, mandatory checks, second receiver, no duplicate ancestor credit |
| C2 causal/statistical boundaries | Explicit null layers; external influence residuals | Forged-layer and unsupported legacy-import tests; no causal estimator claimed |
| C3 supplied nonnegative models | Added `reproduction` | Exact matrix-power oracle, principal blocks, zero/one, non-symmetric/scaled, incomplete families |
| C3 independent witnesses | Separate weighted row-ratio checker | Forged inequalities, upper whole-basis, missing envelopes, budget exhaustion, weakening |
| C4 checked report and CLI | `checker`, `cli`, additive closed report schema | Forged totals, real command round trips, atomic interruption/source preservation |
| C4 published companions | VEK 1.3.0 wheel and CCR 1.8.0 pinned JSON | Actual positive/negative fixture checks, typed CCR proposal, explicit missing stronger fields |
| C4 delivery | Workflow builds once; installed checks on three OSs; OIDC publishes same bytes | Exact release run and public-index results recorded after publication |

New quality gates enforce **at least 90% statement and 90% branch coverage separately** across
`numeric`, `schema`, `source`, `replay`, `report`, `reproduction` and `checker`. These are new CAIT
policy, not inherited VEK/CPCF thresholds. Full legacy tests remain enabled. Formatting/lint and
strict typing apply to new code; legacy source formatting is retained.

Six selected fault manifests in `scripts/check_faults.py` target origin conservation, physical cost
deduplication, negative completeness, receiver qualification, loss accounting and spectral inequality.
Every selected mutation is executed in an isolated package copy and must cause assertion failures;
errors, interruptions and survivors fail the gate. Results are written to `fault-results.json`.

Unsupported scope remains explicit: authenticated observations, general semantic-equivalence detection,
cross-study amortization, causal identification, externally justified statistical coverage, dynamic matrix
products, nonlinear global reproduction, distributed execution, and simultaneous real service capacity.
These limitations do not turn into positive verdicts in the native computation path.
