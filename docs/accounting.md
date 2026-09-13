# Evidence-bound finite accounting

## Registration and source identity

`cait_computation_contract_v1` fixes scope, episode, study (including training/holdout),
arms, checkpoint, half-open integer-clock window `[start,end)`, recorded cutoff, coordinates,
units, receiver/context/task/evaluator/protocol checks, initial endowments, joint scenarios,
stream ranges, mandatory event/cost IDs, negative-term completeness, resource limits,
cost allocations and optional versioned valuation. Register these premises before evaluation.
Changing one creates a different premise, not stronger evidence about the old claim.

Every event is an immutable UTF-8 JSON string plus SHA-256 of those exact bytes. The event
binds registration, source/stream sequence, previous source hash, event and recorded times,
artifact/input digests, dependencies, costs and evidence. Evidence records are separately
source-bound. Registration hashing excludes only stream terminal hashes to avoid a circular
hash: events bind registration; the complete bundle digest additionally binds all terminals.
Exact repeated event delivery is idempotent; conflicting IDs are inconsistent.

Streams require a declared checkpoint, complete sequence range and terminal commitment.
Missing IDs/ranges/costs and records unavailable at the cutoff remain incomplete. Even a
complete declared range cannot prove that an operator disclosed every real-world event.
Source authentication is always **unestablished** in this local profile. No signing adapter
or independently supplied trust material is implemented; caller signature flags are rejected.

JSON parsing rejects duplicate keys, nonfinite/floating numbers, arbitrary extra fields,
oversized inputs and nesting. Numbers in new records use reduced `p/q` strings or canonical
integer strings, e.g. `1/2`, `0`, `-3`; decimal strings are deliberately unsupported. Booleans
are not quantities. Numerator/denominator inputs are at most 128 bits, strings at most 81
characters. Exact rational arithmetic avoids rounding benefits up or costs down.

Limits: 2 MB source bundle, 50,000 JSON nodes, nesting/dependency depth 24, 256 event and
256 evidence deliveries, eight streams/arms/scenarios/coordinates/resource units/model
family members, 16 receivers, eight matrix types. `operation_budget` bounds dependency
visits and matrix entry checks in their respective stages, at most 100,000; optional vector
search separately reports its bounded attempt count. Ledger expansion is bounded by the
schema cardinalities. Local schemas contain no remote resolution or executable functions.

## Replay and conservation

Events are ordered by time and causal/stream dependencies; cycles never establish their own
premises. The reducer supports creation, qualified use, costs, expiry, withdrawal, repair,
revalidation, quantity correction and external-input records. Scope, arm, receiver and
evaluator bindings, check closure, validity periods, unresolved blocking defeaters and
required cost references are recomputed. A passing native check record is still a declared
source claim, not scientific truth or authenticated operator identity. Legacy Boolean witness
flags are not accepted as substitutes for this closure.

For each coordinate, arm and joint scenario:

`closing = opening + endogenous + external + unresolved - losses`.

Origin shares are a declared nonnegative partition summing exactly to one. Multi-parent
allocations, when supplied, also sum to one; a child is counted once, not once per parent.
These shares are bookkeeping conventions. They are not identified causal coefficients.
External model/data/tool/human inputs remain explicit unresolved causal influence; no last-input
subtraction or lineage-depth estimate upgrades them to endogenous evidence.

Exact copied artifact bytes create no additional stock. Parent validity and withdrawal are
checked; revocation propagates to descendants and cannot be repaired by wrapping the same
bytes in another ID. Semantic equivalence beyond byte identity is unsupported: do not interpret
unrecognized paraphrases as independently new capability. Initial endowments are isolated per arm.

A use is unique per arm/task/input/receiver/protocol/evaluator. Successful qualified use adds
service or registered finite coverage units, not new asset stock or a measured service rate.
Different receivers require their own bound evidence. Failure, rejection, timeout, pending and
censored records remain distinct; unsupported use creates a residual. Repair creates an obligation;
it does not restore stock. Qualified revalidation can restore expired stock as unresolved renewal,
preserving the earlier loss. Revoked stock is not renewed. Candidate creation without qualification
is uncredited; this release does not implement a general candidate-promotion workflow.

`resolve_use` binds an original pending/censored event and its unchanged receiver/input/protocol.
It supplies a new qualified result, costs and time, capped by the original registered quantity.
Only one resolution is admitted. Credit occurs at the resolution time, never before completion;
a result outside the fixed observation window leaves that window pending. Original source bytes
and earlier reports are preserved. The current trace shows the effective resolved outcome.

As-of interpretation uses the quantities originally recorded, with recorded cutoff filtering.
Corrected interpretation applies an explicitly linked, later quantity correction to its original
creation/use/cost event. Only one correction per target is admitted; ambiguous competing corrections
are inconsistent. Sources and earlier reports remain immutable. No field or metric is silently rewritten.

## Costs, resources and uncertainty

Physical cost IDs are globally unique. Formation, execution, transfer, validation, refresh,
maintenance and repair remain separate stages. A registered cross-arm allocation must charge
exactly the entire physical cost once. This profile does not amortize across unrelated studies;
that requires a broader common ledger. Failed formation still incurs its explicit cost event.

Work hours, currency, tokens and other units are never implicitly interchangeable. Resource checks
sum actual declared costs across arms against the registered shared limit. Missing limits are unknown;
exceeded limits remain infeasible even when a matrix is supercritical. These consumable limits do not
certify concurrency or simultaneously deliverable task/research/verification capacity.

A versioned valuation can convert each cost unit into one explicitly named coordinate. Only when
all cost units have rates is `declared_net = endogenous - losses - valued_cost` computed for that
target. Other units remain separate. Rates and quantities share the same scenario ID, so incompatible
extrema are not multiplied together. Per-scenario identities are exact; min/max projections are
conservative outer bounds. No probability or confidence level is inferred from enumerated scenarios.

External/unresolved shares use gross production in the same coordinate as denominator. A zero
denominator is `null` (undefined), never zero. Unresolved production does not enter the endogenous
lower amount. Missing obligatory negatives, unresolved qualification/resource obligations or source
truncation block the supported net bounds. Descriptive corrections need not be monotone; fixed-premise
guarantees cannot improve merely because mandatory evidence disappeared.

## Claim layers and migration

Reports separate source integrity, authentication, accounting consistency, model-conditional
mathematics, statistical coverage, causal attribution and execution authority. The latter empirical
and authority fields are null unless a future separately recognized profile establishes them.
This release implements no causal estimator, joint statistical-coverage combiner, e-process, server,
optimizer or external executor. Independent report checking is software conformance, not a proof
that the entire Python implementation is correct.

Legacy records and `cait-validate` still check shape and supplied lightweight flags. Their original
wire numbers/schema IDs remain. `legacy_partition` validates the legacy input then reports unsupported
mapping: legacy injection/human/tool fields may overlap inputs and output production. Migration requires
an explicitly registered disjoint source history; the tool never sums these legacy totals automatically.
