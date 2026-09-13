# Verification and release procedure

Run from the repository root:

```sh
uv sync --locked --dev
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov --cov-report=json:coverage.json
uv run python scripts/check_coverage.py
uv run python scripts/check_source.py
uv run python scripts/check_faults.py
uv run pip-audit
uv run mkdocs build --strict
uv build --no-sources
uv run twine check dist/*.whl dist/*.tar.gz
uv run python scripts/check_artifacts.py
uv run python scripts/check_installed.py
```

The workflow runs Python 3.11–3.14 on Linux. A single build from the sdist generates the wheel;
both distributions are inspected, and the wheel is installed outside the checkout on Linux,
Windows and macOS. Checksums bind the uploaded artifact. The tag-triggered publish job requires
all these gates, downloads the exact build, rechecks its manifest and uses OIDC with the registered
`workflow.yml` / `pypi` identity. It never rebuilds and never uses `skip-existing`. The release job
attaches those same files only after publication succeeds. No administrator override is used.

Use a feature branch and normal reviewed/checked PR, verify the final merged tree, then push an
unused version tag at that exact commit. Check the exact run and attempt, environment approval,
publish and release jobs separately. Missing account-side publisher permission is BLOCKED.

After publication install exact `cait-certificate-schema==0.2.0` from the public simple index with
isolated pip, disabled cache and an installation report in a new environment outside the checkout.
Remove PYTHONPATH/editable/private-index influence. Check package metadata/import location,
`pip check`, legacy fixtures and new offline replay/window/matrix/report/interchange examples.
Compare public wheel/sdist hashes, pip download hash, workflow artifacts, release assets and
SHA256SUMS. Verify real attestations if present; absence is not a verified signature.

Wiki: repository settings allow Wiki, but the actual separate Wiki git remote does not exist.
There are no pages to update; no new Wiki hosting/pages are initialized. Canonical documentation
is maintained here. Public-index success and post-publication docs are recorded below when performed.

## Verified 0.2.0 publication

[PR #1](https://github.com/kadubon/cait-certificate-schema/pull/1) merged normally at
`7d12bcf0bc4c6eae2acdd177175b6be414a274f6`. Its tree exactly matches tested PR head
`6b543f17b2132d05118d1c5f1be9ef7e7723986d`. No review, environment or check bypass was used.
The immutable tag `v0.2.0` points to that merge commit.

The [PR run](https://github.com/kadubon/cait-certificate-schema/actions/runs/34727609127),
[merged-main run](https://github.com/kadubon/cait-certificate-schema/actions/runs/34727688387)
and [tag run 34727774455, attempt 1](https://github.com/kadubon/cait-certificate-schema/actions/runs/34727774455)
passed all tests/quality/build and Linux/Windows/macOS installed-artifact gates. The tag run's
actual `publish` and `release` jobs also succeeded. No environment approval remained pending.
The supplied pending publisher worked with the actual `workflow.yml` / `pypi` identity.

[GitHub Release](https://github.com/kadubon/cait-certificate-schema/releases/tag/v0.2.0)
and [public PyPI 0.2.0](https://pypi.org/project/cait-certificate-schema/0.2.0/) contain these
identical workflow-built artifacts, verified against both checksum manifests:

```text
b0cbfcfdc31bd0e170b75e8567dd5ff6c1565ed5bd808610d6a8aa5f093d1837  cait_certificate_schema-0.2.0-py3-none-any.whl
cf3aa4768ff1b12b4d8b46436eb0eb2159b6877f5be9c9585178f6b06527a878  cait_certificate_schema-0.2.0.tar.gz
```

Fresh public-index verification on Windows/Python 3.13 installed exact
`cait-certificate-schema==0.2.0` using isolated pip, `--no-cache-dir`, explicit
`https://pypi.org/simple` and an installation report, outside the checkout. All package/dependency
download URLs were public `files.pythonhosted.org` URLs. Metadata/version and import origin
inside the fresh virtual environment, `pip check`, eight legacy examples, all 11 native histories,
matrix/check-report operations and actual pinned interchange passed with socket connections blocked
during runtime execution. The intentionally inconsistent history was correctly rejected.

Public downloads match workflow and release asset SHA-256 values; the pip installation report
matches the wheel. PyPI's simple JSON index advertises no provenance for either file, so no
attestation verification is claimed. This post-publication record does not alter the tagged files.

| Delivery state | Evidence |
| --- | --- |
| IMPLEMENTED | C1–C4 bounded native path and released companion subset |
| LOCALLY_VERIFIED | Tests, exact mathematical checks, six faults and installed examples passed |
| CI_PASSED | PR, merged-main and release-tag runs passed |
| PUSHED | Feature branch and immutable version tag |
| MERGED | PR #1 at the commit above |
| DOCS_UPDATED | Canonical English guides and this post-publication record |
| WIKI_UPDATED_OR_NOT_APPLICABLE | Not applicable: no actual Wiki repository |
| GITHUB_RELEASED | v0.2.0 with identical wheel/sdist/SHA256SUMS |
| PYPI_PUBLISHED | 0.2.0 via actual successful OIDC publication |
| PUBLIC_INDEX_VERIFIED | Exact public-index installation, offline checks and byte identity passed |
| BLOCKED | None remaining for the declared finite release scope |

Candidate validation: 166 tests passed on Windows/Python 3.11, 3.12, 3.13 and 3.14.
Final CI is tracked separately. New-core coverage on Python 3.14 is 99.64% statements
and 97.34% branches. All six selected faults were killed. Legacy identity/generated drift,
strict types, formatting/lint, schema checks, source/archive scans, dependency audit and strict
documentation build passed. The unpublished wheel completed an external Python 3.13 install
with all eight legacy examples and 11 new histories offline. These are local results, not
public-PyPI installation evidence.

The final time-unit/empty-model regression adds one test: 167 tests passed on Python 3.13,
with 99.65% statement and 97.34% branch coverage on the new core. Final-head CI covers
all four supported Python versions and the identical artifact across all three OSs.
