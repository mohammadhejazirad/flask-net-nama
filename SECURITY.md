# Security

Local deployment binds loopback; initial credentials are `admin / 123456`.
Use the settings page to change the password. Public mode rejects the default
password, weak/missing environment secret and private-target allowance.
Terminate HTTPS at a trusted proxy and set `NETNAMA_HTTPS=true`. No proxy headers
are trusted by default. Do not expose the application through a public demo login.

Authenticated users can run bounded networking operations from the server.
Public targets must resolve entirely to globally routable addresses. HTTP/TLS
connect to checked IPs while retaining hostname verification. Redirects undergo
fresh validation. Environment HTTP proxy variables are not used by tools.
Local private targets require an explicit opt-in. ICMP has no shell execution.

Sessions, rate limits, caches, inputs and job results are process-local. Run one
process only. Exports require the creating session. Logout revokes that session;
password changes revoke all sessions. Restart invalidates all sessions and jobs.
Reference data and hashed credentials are the only persistent application data.

Report reproducible vulnerabilities privately to the deployment/repository
maintainer using their published security contact. This repository has no
invented security email or external reporting service. Do not include credentials,
private targets, raw contact records or session tokens in public reports.
