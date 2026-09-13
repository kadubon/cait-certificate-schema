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

## Current publication state

Implementation and local verification are in progress. CI, merge, tag, GitHub Release, PyPI upload
and fresh public-index installation must each be evidenced before being marked complete.

Candidate validation: 166 tests passed on Windows/Python 3.11, 3.12, 3.13 and 3.14.
Final CI is tracked separately. New-core coverage on Python 3.14 is 99.64% statements
and 97.34% branches. All six selected faults were killed. Legacy identity/generated drift,
strict types, formatting/lint, schema checks, source/archive scans, dependency audit and strict
documentation build passed. The unpublished wheel completed an external Python 3.13 install
with all eight legacy examples and 11 new histories offline. These are local results, not
public-PyPI installation evidence.
