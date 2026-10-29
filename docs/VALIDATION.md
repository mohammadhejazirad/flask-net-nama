# NetNama 0.1.0 verification

Date: 2026-10-29. Reference: `.docs/NETNAMA_AGENT_SPEC_FA.md`.
This report distinguishes real observations, mocked protocol tests and unverified
platforms. It does not certify registry service permission or a production SLA.

## Automated application checks

`pytest -q`: **64 passed in 5.51 seconds**, Linux, CPython 3.13.16.
`ruff check netnama tests scripts` and `ruff format --check`: passed.
`uv lock --check --offline`: passed. Python >=3.12 is declared; native execution
in this environment was on 3.13.16, not on every supported Python minor version.

Coverage includes local login/defaults, public startup guards, CSRF, logout,
server expiry, password invalidation, signed-cookie identity-only contents,
job/export/SSE isolation, owned job restoration, capacity/TTL, bounded replay and
ANSI filtering, Last-Event-ID resync, idempotent cancel, cancellation kill/reap,
IDNA/BOM/dedup/Unicode controls, co.uk/subdomain/private-hosting boundaries,
unknown suffixes, DNS SRV and RCODE distinctions, IPv4/IPv6/mapped-address policy,
mixed public/private DNS answers, HTTP numeric pinning/original SNI, private
redirect rejection, no second DNS lookup, RDAP mismatched objects/names,
HTML 404/invalid JSON/conformance/429/503, transient timeout retries,
Retry-After, NIC.IR recorded status fixtures, malformed-update preservation,
304, bilingual catalog parity and export parsing/redaction.

Network unit/integration tests replace external transports and do not claim
live success. Ping builders for Linux/macOS/Windows are unit tested. Real ICMP
was separately exercised only on Linux.

Runtime dependencies: `pip-audit -r requirements.lock --disable-pip` reports
**no known vulnerabilities**. `npm audit`: **0 vulnerabilities**. During development
filelock and esbuild advisories were resolved by upgrading to filelock 4.2.4
and esbuild 0.28.2. Audit results describe the advisory databases at verification
time, not a guarantee against unknown vulnerabilities.

## Browser verification

Headless installed Google Chrome via temporary Playwright tooling:

- 2 languages × 3 themes × 8 pages × 4 widths = **192 geometry combinations**.
- Widths: **360, 768, 1280, 1920**. No whole-document horizontal overflow.
- No JavaScript page errors in the matrix or focused final flow.
- Real login, locally calculated CIDR, event-driven result/progress, fa/en switch
  preserving job data, theme changes, drawer Escape/focus return verified.
- Focused final flow verified mobile inert background/sidebar behavior, job
  restoration after navigation, overview current-job counters, IDN conversion,
  real JSON.TXT download parsed with JSON.parse, and manual resource update.
- Screenshots were visually inspected for Persian light overview, Persian dark
  batch workspace and 360px layouts. Tables scroll within their own container.
- Reduced-motion CSS and visible focus are implemented. This is not an independent
  screen-reader or full WCAG conformance audit.

Production assets from `npm run build`, bytes / gzip bytes:

- app.css: **25,312 / 6,272** (budget <60 KiB gzip).
- app.js: **23,078 / 8,113** (budget <100 KiB gzip).
- first-paint theme.js: **307 / 190**.

Local WOFF2 fonts are excluded from those budgets; OFL texts are included.
Lucide uses selected named imports. No runtime CDN, Play CDN or remote font calls.

## Real network checks

All checks originated on this Linux server, outside ordinary tests. Observed:

- DNS A example.com through 1.1.1.1: NOERROR, **166 ms**.
- Authoritative IANA-discovered .com RDAP, example.com: registered, **680 ms**.
- NIC.IR TCP/43, nic.ir: registered, **229 ms**.
- HTTPS headers example.com: success, **564 ms**.
- TLS chain/hostname verification example.com: success, **579 ms**.
- Native ICMP 1.1.1.1, one packet: actual reply, **869 ms** including setup.
- PTR 1.1.1.1 through 1.1.1.1: NOERROR, **137 ms**.
- IANA-routed IP RDAP 1.1.1.1: matching allocation, **1,051 ms**.
- Authenticated manual IANA DNS bootstrap update through the application:
  HTTP **200**, updater status **updated**.

NIC.IR's explicit no-match wording was observed using a unique test target.
Sanitized registered/no-match fixtures and provenance are in `tests/fixtures`.
The parser requires the exact server banner, target echo and both no-match
markers. Empty/ambiguous wording stays unknown. The advertised NIC.IR terms page
returned HTTP 403; operator terms must be reviewed before public bulk deployment.

Small opt-in benchmark (`scripts/benchmark.py`): Linux 7.0.0 x86_64,
20 logical CPUs, CPython 3.13.16, three known registered domains
(example.com, example.net, nic.ir), cache bypassed, .com/.net IANA RDAP + NIC.IR.
**1.414 seconds**, **2.122 targets/second**, **0/3 errors** in this sample.
This is a tiny mixed-authority smoke benchmark, not sustained capacity or an
external-service SLA. Per-host pacing remains enabled. No thousands-per-second
claim is made. Reproduce explicitly with `uv run python scripts/benchmark.py`.

## Packaging and deployment

A wheel build succeeded and included templates, local fonts, compiled assets,
locale catalogs, bundled resources and license notices. Runtime requirements are
pinned with hashes; npm has a lockfile; no Node process is needed to serve.

The normal online Docker build could not resolve files.pythonhosted.org from
this environment's build container, including with host networking. An equivalent
temporary verification context supplied host-downloaded, hash-checked wheels and
used the production Dockerfile with offline pip source settings. The application
and lock were unchanged. This offline build succeeded.

That image ran successfully with **UID/GID 10001**, read-only root filesystem,
all capabilities dropped, no-new-privileges, tmpfs runtime data and loopback host
port mapping. Waitress `/healthz` returned **200**. Graceful SIGTERM/stop succeeded.
The minimal image intentionally lacks ping; capability detection reports this.
The ordinary online Docker download path still needs a DNS-functional build host.

## Boundaries and known limits

- Native Windows/macOS execution and remote CI runs are **unverified**. CI is
  configured for Linux/Windows/macOS and Python 3.12/3.13. Mocks are not native proof.
- One process only; restart loses jobs and sessions. No multi-worker shared state.
- No registrar purchase guarantee, paid provider adapter, full DNSSEC validation,
  native dig +trace, traceroute, arbitrary shell, port scan or persistent history.
- HTTP transport deliberately uses bounded pinned HTTP/1.1 streams instead of
  a default hostname-based httpx transport. Rationale: `ARCHITECTURE.md`.
- RAM admission limits cover stored job payloads; Python object/runtime overhead,
  shared resources and temporary serialization buffers add bounded overhead.
  NETNAMA_MAX_RAM_MB is not an operating-system RSS cap. No sustained multi-client
  load/RSS soak test was run; set deployment memory limits for the actual workload.
- Updater regression tests cover malformed downloads, old-copy preservation and
  304. Full crash/power-loss injection and an external multi-process updater stress
  audit were not performed. Resource commits use locks and atomic replacement.
- The included reference datasets are real snapshots with provenance; registry
  coverage, suffix rules, service policies and remote availability can change.

No mock data is used to make product operations report success. No real user
credentials, private targets or contact records were included in this report.
