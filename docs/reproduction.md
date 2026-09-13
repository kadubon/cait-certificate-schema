# Conditional reproduction witnesses

The model is supplied, not estimated from lineage links. `K[i,j]` means child/output type i
per parent/input type j. The record binds type basis, parent exposure/cohort, generation or
elapsed-time interpretation, retention, external-input boundary, scope/source references,
horizon and uncertainty basis. Births-only and total-next-state models are distinct; CAIT never
silently adds the identity or clips negative empirical effects to obtain nonnegativity.

For every declared family member, exact entrywise enclosures require `0 <= L <= U` (or a
missing upper envelope). A lower witness has a strictly positive rational vector v and r > 1:

`L v >= r v` componentwise implies `rho(K) >= r` for every K >= L.

Indeed nonnegativity gives `K^n v >= r^n v`; growth of these powers and the finite-dimensional
spectral-radius formula imply the bound. A declared principal block also establishes a lower
bound for the full nonnegative matrix, with its subset explicitly retained in the source witness.

For an upper witness w > 0 and 0 <= s < 1, `U w <= s w` bounds the induced weighted infinity
norm by s, hence `rho(K) <= s`. Upper witnesses must cover every declared type. Missing upper
envelopes cannot support subcritical classification. Empty families are invalid, lower > upper
is inconsistent, and incomplete family enumeration or budget exhaustion returns unknown.

These are sufficient witnesses. Reducible, zero, nonsymmetric, poorly scaled and threshold-one
examples are covered. `propose_lower` enumerates bounded integer-vector candidates and rechecks
them exactly. Failure to find one is unknown, not subcriticality or evidence against a correlated
family. A complete finite family checks the witness against every member; an entrywise enclosure
can conservatively miss a bound that another correlated-set argument could establish.

Expected offspring matrices support only expected/model spectral conclusions: no certain survival
or realized growth follows. A `uniform_pathwise` premise may additionally produce a finite iterated
factor, conditional on the registered vector/block initial lower state and the uniform transition
inequality holding over every step of that horizon. This premise is supplied, not authenticated or
inferred from observations. Iteration is capped at 64 steps. Time-varying products and local nonlinear
Jacobians are explicitly unsupported: individual spectral radii do not establish product growth,
and a local derivative does not establish global AND-composition reproduction.

The independent checker uses weighted row ratios and its own source reconstruction; it does not
import the production inequality/replay functions. The proofs above justify the finite mathematical
objects only. Resource feasibility, verification debt, statistical coverage, causal attribution and
execution authority remain separate and cannot be overridden by spectral classification.
