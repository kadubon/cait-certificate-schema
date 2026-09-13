# CLI, API and agent operations

The existing `cait-validate FILE [--schema NAME]` behavior and public validator imports remain.
New operations use `cait-analyze` and accept only local source JSON:

```text
cait-analyze validate-bundle bundle.json
cait-analyze replay bundle.json
cait-analyze window bundle.json --out report.json
cait-analyze reproduction model.json
cait-analyze check-report bundle.json --report report.json
cait-analyze export-ccr bundle.json --created-at 2026-09-13T00:00:00Z --out sidecar.json
cait-analyze example interchange
```

`example NAME` returns a source bundle, computed report and independent check. `inconsistent`
deliberately demonstrates failed dependency closure. Examples are listed in the generated reference
and packaged in the wheel. They do not need network access, API keys or companion installations.

Typed Python entry points:

| Operation | Function |
| --- | --- |
| Strict parsing | `accounting.numeric.parse(text)` |
| Source validation/dependency closure | `accounting.source.prepare(bundle)` |
| Scenario replay | `accounting.replay.replay(prepared, scenario)` |
| Window report | `accounting.report.window(bundle)` / `analyze(bundle)` |
| Matrix witness check/search | `accounting.reproduction.reproduction(model)` / `propose_lower` |
| Independent source reconstruction | `accounting.checker.check_report(bundle, report)` |
| Companion operations | `accounting.interchange.import_vek`, `import_ccr_task`, `export_ccr`, `integration` |

`window` raises typed `AnalysisError`; `analyze` returns explicit failure status/code/detail.
The CLI exits 2 for invalid input, 3 for inconsistent records, 4 for exhausted computation,
and 0 for completed processing (including explicit unknown mathematical classification).
Running the intentionally inconsistent *example demonstration* succeeds as a command and returns
the failed analysis/check inside its output. Process success never implies positive growth.

Analysis is read-only. `--out` requires a new path, distinct from every source path. The writer
fsyncs a temporary sibling and creates the destination with an atomic hard link; an existing or
concurrently created destination fails rather than overwriting evidence. It removes temporary files
on failure. This requires a filesystem supporting hard links; unsupported filesystems fail closed.
There is no shared database, distributed reservation, asynchronous executor or background service.

Agent guide: register premises first; inspect unknowns; check original source digests and dependency
closure; compute; independently check; preserve costs/adverse outcomes; export only the supported
sidecar. Read [accounting](accounting.md) and [interchange](interchange.md) before interpreting results.
