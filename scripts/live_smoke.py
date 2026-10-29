"""Explicit opt-in low-volume live checks. Prints statuses, never contact records."""

import asyncio
import json
import platform
import time

from netnama.core.limits import NetworkLimits
from netnama.core.target_policy import TargetPolicy
from netnama.resources.manager import ResourceManager, BUNDLED
from netnama.tools import dns, domain, http, ping, tls
from netnama.providers import rdap


async def main():
    policy = TargetPolicy()
    limits = NetworkLimits()
    resources = ResourceManager(BUNDLED).snapshot()
    results = {"platform": platform.platform(), "python": platform.python_version(), "checks": {}}
    checks = {
        "ptr": lambda: dns.ptr("1.1.1.1", {"resolver": "1.1.1.1"}),
        "ip_rdap": lambda: rdap.lookup(
            "1.1.1.1", resources.endpoint("ipv4", "1.1.1.1"), policy, limits, "ip"
        ),
        "dns": lambda: dns.query("example.com", {"resolver": "1.1.1.1"}),
        "domain": lambda: domain.check(
            {"input": "example.com", "ascii": "example.com"}, resources, policy, limits
        ),
        "ir": lambda: domain.check({"input": "nic.ir", "ascii": "nic.ir"}, resources, policy, limits),
        "http": lambda: http.inspect("https://example.com", policy),
        "tls": lambda: tls.inspect("example.com", policy),
        "ping": lambda: ping.run("1.1.1.1", {"count": 1}, policy, lambda *args: None),
    }
    for name, check in checks.items():
        start = time.monotonic()
        try:
            async with asyncio.timeout(50):
                result = await check()
            results["checks"][name] = {
                "status": result["status"],
                "reason_code": result.get("reason_code"),
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        except Exception as exc:
            results["checks"][name] = {
                "status": "error",
                "error_type": type(exc).__name__,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
