# NetNama delivery checklist

Reference: `.docs/NETNAMA_AGENT_SPEC_FA.md` (normative). Delivery: 0.1.0.
Details and verification limits: `docs/VALIDATION.md`.

- [x] A: Flask factory, blueprints, file settings, hash bootstrap, CSRF, RAM sessions
- [x] A: local admin/123456; public credential/secret/private-target startup guards
- [x] A: bilingual responsive sidebar/pages, RTL/LTR, light/dark/system themes
- [x] A: supplied SVG branding, local licensed fonts, compiled Tailwind + selected Lucide
- [x] B: current official bundled IANA/PSL datasets, provenance and SHA-256 manifest
- [x] B: independent conditional manual updates, validation, atomic writes, previous good copy
- [x] B: IDNA, TLD/ICANN PSL, subdomain rejection/suggestion, paste/TXT/generator/helpers
- [x] B: longest-match authoritative RDAP, strict classification, tested NIC.IR adapter
- [x] B: host/global pacing, temporary retries, RAM cache and force-fresh semantics
- [x] C: process scheduler, bounded admission/workers/output/RAM/TTL, session ownership
- [x] C: SSE replay/resync/heartbeat/limits, polling fallback, current-job restoration
- [x] C: cancel (including subprocess kill/reap), partial results and explicit downloads
- [x] C: TXT/JSON/JSON.TXT, valid UTF-8 JSON, no server-side export/history files
- [x] C: real DNS, native ICMP builders, IP/CIDR/PTR/IP-RDAP, pinned HTTP and verified TLS
- [x] D: destination policy, all resolved addresses, redirect revalidation and original SNI
- [x] D: authentication, ownership, expiry, CSRF, memory, retry and cancellation regression tests
- [x] D: reproducible dependency locks, audited runtime/build dependencies and size budgets
- [x] D: browser language/theme/page/viewport matrix and keyboard/mobile drawer checks
- [x] D: Linux real-network smoke and small authority throughput benchmark
- [x] D: non-root Docker packaging and offline-equivalent container health verification
- [x] D: bilingual README, MIT, third-party/font/PSL notices, security/contribution docs
- [x] D: Linux/Windows/macOS CI definitions and honest native deployment instructions

Explicit verification boundaries (not falsely checked as executed):

- [ ] Run native Windows and macOS smoke checks on those operating systems. CI is configured,
  but has not run remotely in this environment. Argument unit tests are not native smoke.
- [ ] Verify standard online Docker build on a host with functioning build-container DNS.
  This environment required a temporary offline wheelhouse; its container runtime was tested.
- [ ] Complete independent assistive-technology/WCAG audit and sustained multi-client load test.
  Automated browser geometry/keyboard checks and bounded lifecycle tests passed.
- [ ] Review NIC.IR's currently applicable service terms before public bulk deployment.
  Live WHOIS status fixtures are verified; the advertised terms web page returned 403 here.

No credentials, runtime input/results, uploaded TXT or export artifacts are committed.
No network failure is converted into availability or success.

## Interface controls update

- [x] Icon-only theme button cycles system → light → dark and preserves preference.
- [x] Icon-triggered language dropdown has checked selection, arrow navigation and Escape.
- [x] Bilingual native logout dialog requires confirmation and preserves CSRF protection.
- [x] Cancel/Escape restores focus; modal traps Tab and works inside the mobile drawer.
- [x] Browser flow verified theme/system persistence, RTL/LTR, no premature logout requests,
  actual confirmed logout, mobile layout and no JavaScript errors; all 64 backend tests pass.
