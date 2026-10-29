# NetNama · نِت‌نما

Clarity for domains and networks. A Persian/English Flask toolbox with a custom
RTL/LTR interface, light/dark/system themes, real server-side network tools,
live bounded output, and explicit TXT / JSON / JSON.TXT downloads.

[راهنمای فارسی](README.fa.md) · [Specification](.docs/NETNAMA_AGENT_SPEC_FA.md)
· [Verification](docs/VALIDATION.md) · [Security](SECURITY.md)

## Run locally

Python **3.12+** is required. Node is needed only when rebuilding frontend assets.
Compiled CSS/JS, local licensed fonts and current official datasets are included.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps -e .
python -m netnama
```

Open **http://127.0.0.1:8080**. Initial local login: **admin / 123456**.
Change it in Resources & settings. Use `python -m netnama --port 9090` for another port.
Alternatively: `uv sync --locked` then `uv run python -m netnama`.
The runner uses one Waitress process, 24 HTTP threads, one long-lived background
scheduler/event loop, a shared async client lifecycle and a bounded executor.
Do not use multiple WSGI workers or Flask's debug reloader.

Windows PowerShell (install Python from python.org first):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --require-hashes -r requirements.lock
python -m pip install --no-deps -e .
python -m netnama
```

If activation is blocked, invoke `.\.venv\Scripts\python.exe` directly. macOS uses
the Linux commands with an installed Python 3.12+. Native Windows/macOS execution
has **not been verified in this development environment**; CI is configured for
both. Mocked argument tests are not native verification.

## Tools and data semantics

- Batch domains: paste, UTF-8/BOM TXT import, name × suffix generator, IDNA,
  official TLD/PSL normalization, authoritative longest-suffix RDAP discovery.
  Subdomains are rejected with a suggestion; the parent is never silently checked.
- `.ir`: a dedicated NIC.IR WHOIS adapter validates matching registered records
  and exact observed no-match wording. Ambiguous/empty/error responses are unknown.
- DNS / Dig: dnspython structured sections and dig-style text, A/AAAA/CNAME/MX/NS/
  TXT/SOA/CAA/SRV/PTR, system/preset/local-custom resolver, UDP/TCP fallback.
  No full DNSSEC validation or `+trace` claim.
- Ping: real system ICMP binary, 1–10 packets, 30s deadline, cancellation kills
  and reaps the process. Linux uses `-W 2` seconds, macOS `-W 2000` milliseconds,
  Windows `-w 2000` milliseconds. macOS IPv6 uses `ping6`. Missing binary or
  permissions is reported; there is no fake ICMP/TCP fallback.
- IP classification, CIDR (no large subnet enumeration), PTR and RIR IP RDAP.
  Allocation metadata does not locate or prove ownership of a device.
- HTTP headers with bounded requests/redirects; TLS chain/hostname verification,
  SNI and certificate details. Only ports 80/443. Failed TLS stays an error.

All measurements originate **on the server**, or inside the container for Docker.
“Likely available” means a validated authoritative no-match, **not guaranteed
purchasable**. Premium names, reserved names and registry eligibility can differ.
A DNS failure, generic HTTP 404 or expiration date is not proof of availability.
No mandatory paid service, registrar credential or database is required.

## Privacy and limits

Only theme and locale persist in browser localStorage. Inputs, results, sessions,
registration cache and rate limits stay in process RAM. Results expire after
15 minutes; restart loses jobs and signs everyone out. Reports download only
when requested, and are never written as server-side history. Uploaded TXT is
stream-decoded and not saved. Raw WHOIS contacts are not returned.

Configuration defaults to `platformdirs.user_data_dir('NetNama', 'NetNama')`:
Linux `~/.local/share/NetNama`, Windows `%LOCALAPPDATA%\NetNama\NetNama`, macOS
`~/Library/Application Support/NetNama` (exact platformdirs result may vary).
Set `NETNAMA_DATA_DIR` to override. It stores hashed credentials/secret under
`config/`, validated datasets/manifest under `resources/`, and updater temporary
files only. Protect this directory. POSIX files use restricted permissions;
on Windows restrict its ACL to the service account and administrators.

Limits: 1 MiB / 1,000 unique domains; 2 outstanding jobs per session; 4 running
jobs + 8 waiting globally; 8 network operations globally and 2 per RDAP/WHOIS
host with 1 request/second host pacing; up to two temporary-failure retries;
60-second successful registration cache. Force fresh never bypasses pacing.
Result/event buffers, retained jobs and admission RAM have hard caps.
`NETNAMA_RESULT_TTL` (30–3600 seconds) and `NETNAMA_MAX_RAM_MB` (8–256 MiB)
configure retention/admission; the latter is not a process RSS limit. SSE has
8 global / 2 per-session connections, 60s stream lifetime, 15s heartbeats,
Last-Event-ID replay/resync and snapshot polling fallback. See code for exact
limits; they are conservative ceilings, not external-service permission or SLA.

## Public deployment

Set environment variables explicitly; `.env` is an example and is **not loaded
automatically**. Password/hash settings apply on first bootstrap only. Later
password changes go through the authenticated settings page.

```sh
export NETNAMA_MODE=public
export NETNAMA_HOST=0.0.0.0
export NETNAMA_PASSWORD='your-long-unique-password'
export NETNAMA_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
# With HTTPS at a reverse proxy:
export NETNAMA_HTTPS=true
python -m netnama
```

Public mode refuses default credentials, weak/missing explicit secrets and
private-target allowance. Private, loopback, metadata, link-local, multicast
and IPv4-mapped IPv6 targets are blocked. Every resolved address is checked;
HTTP/TLS use checked numeric connections and original Host/SNI. Each redirect
is validated again. Local testing of private hosts needs
`NETNAMA_ALLOW_PRIVATE_TARGETS=true`, with an in-app warning.

Place behind HTTPS; proxy SSE needs buffering disabled and read timeout over
75s. Waitress trusts no forwarded headers by default. If adding ProxyFix, use
an exact known hop count and prevent direct access to the backend. Keep access
logs disabled or remove target/query/token data. GitHub Pages/static hosting
cannot run this backend. Do not expose a shared default-credential demo.

Docker: export a unique `NETNAMA_PASSWORD` and random `NETNAMA_SECRET_KEY`, then
`docker compose up --build`. The host port is loopback-only. Container internal
binding requires public mode. The image is non-root, read-only with a writable
data volume, and drops all capabilities. Ping is **unavailable** in the minimal
image; install a system ping binary and grant only necessary capabilities in a
reviewed derived image if needed. Do not use privileged mode. Docker execution
has not been verified unless noted in the verification report.

## Reference updates and development

Resources & settings offers independent manual updates for official IANA RDAP
DNS/IPv4/IPv6, IANA TLDs and PSL. Conditional requests, schema checks, locks and
atomic replace preserve the last good copy. Old versions get a visible age
badge. Active jobs hold the resource snapshot they started with. No scheduled
updater exists. Bundled provenance/hashes are in the bundled manifest.
NIC.IR's advertised terms page returned 403 during verification; review applicable
terms before public bulk deployment. No unlimited query entitlement is assumed.

```sh
uv sync --locked --extra dev
npm ci
npm run build
uv run pytest -q
uv run ruff check netnama tests
uv run ruff format --check netnama tests
uv run pip-audit -r requirements.lock --disable-pip
npm audit
# Explicit live checks, never part of ordinary CI:
uv run python scripts/live_smoke.py
```

The frontend imports only selected Lucide icons. Release assets require no Node.
For official data refresh during release, run `python scripts/bundle_resources.py`
and verify datasets, licenses and manifest before shipping.

Code: MIT. Fonts: SIL OFL. PSL: MPL 2.0. See [notices](THIRD_PARTY_NOTICES.md).
