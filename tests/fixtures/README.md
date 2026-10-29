# Fixture provenance

`ir_registered.txt` and `ir_no_match.txt` derive from live TCP/43 responses from
`whois.nic.ir`, retrieved 2026-10-29. Only server comments, the queried name and
matching domain field were retained; all contact and account data were omitted.
Registered target: `nic.ir`. No-match target:
`netnama-unregistered-check-20261029-8b17f2.ir`.

No-match parser requires the IRNIC banner, exact target echo and both exact
no-match markers. It never makes a purchase guarantee. A subsequent change in
server wording yields unknown until reviewed. Terms URL advertised by the server
was checked at `https://www.nic.ir/Terms_and_Conditions` but returned HTTP 403
in this environment. No assertion of unrestricted service access is made. Keep
the conservative host limiter and review applicable operator terms before public
bulk deployment. Timeout/unknown/rate-limit tests use generated responses and
are not represented as real observed NIC.IR error transcripts.

RDAP classification tests construct minimal protocol objects to isolate status,
content type, object class and domain checks; these are unit fixtures, not
purported recorded public registration responses.
