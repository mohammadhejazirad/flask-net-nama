# Contributing

Read `.docs/NETNAMA_AGENT_SPEC_FA.md` before changing architecture or behavior.
Use Python 3.12+ and Node 24 for asset builds. Install with `uv sync --locked --extra dev`
and `npm ci`. Run `uv run pytest`, `uv run ruff check netnama tests`,
`uv run ruff format --check netnama tests`, and `npm run build`.

Network integration fixtures must not contain personal contact records. Unknown
responses must remain unknown. Real external checks are opt-in and must be
reported separately from mocked tests. Do not commit configuration, tokens,
exports, uploaded input or runtime data. Update both locale catalogs together.
Changes to bundled data use `scripts/bundle_resources.py`; retain provenance,
validate schemas, and review upstream licenses. No automated background updater.
