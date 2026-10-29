import asyncio
import time

import dns.asyncquery
import dns.asyncresolver
import dns.flags
import dns.message
import dns.rcode
import dns.reversename

from netnama.core.validation import ValidationError, dns_name

TYPES = {"A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "CAA", "SRV", "PTR"}
PRESETS = {"system", "1.1.1.1", "8.8.8.8"}


async def query(target, options, public=False):
    name = dns_name(target)
    record = options.get("record", "A")
    resolver = options.get("resolver", "system")
    if record not in TYPES:
        raise ValidationError("invalid_record")
    if public and resolver not in PRESETS:
        raise ValidationError("blocked_resolver")
    import ipaddress

    if resolver != "system":
        ipaddress.ip_address(resolver)
        server = resolver
    else:
        servers = dns.asyncresolver.Resolver().nameservers
        if not servers:
            raise ValidationError("resolve_failed")
        server = str(servers[0])
    message = dns.message.make_query(name, record)
    start = time.monotonic()
    transport = "TCP" if options.get("tcp") else "UDP"
    if transport == "TCP":
        response = await dns.asyncquery.tcp(message, server, timeout=5)
    else:
        response, tcp = await dns.asyncquery.udp_with_fallback(message, server, timeout=5)
        transport = "TCP" if tcp else "UDP"
    rcode = dns.rcode.to_text(response.rcode())

    def section(records):
        return [
            {
                "name": str(rr.name),
                "ttl": rr.ttl,
                "type": dns.rdatatype.to_text(rr.rdtype),
                "data": [r.to_text() for r in rr],
            }
            for rr in records
        ]

    return {
        "status": "success" if rcode == "NOERROR" else "unknown",
        "reason_code": "dns_" + rcode.lower(),
        "question": name,
        "record": record,
        "resolver": server,
        "transport": transport,
        "rcode": rcode,
        "answer": section(response.answer),
        "authority": section(response.authority),
        "additional": section(response.additional),
        "duration_ms": round((time.monotonic() - start) * 1000),
        "dnssec_validated": False,
        "output": response.to_text(),
    }


async def ptr(target, options, public=False):
    name = str(dns.reversename.from_address(target))
    return await asyncio.wait_for(query(name, {**options, "record": "PTR"}, public), 10)
