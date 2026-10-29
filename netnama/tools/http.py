import time
from netnama.core.network import request


async def inspect(target, policy):
    start = time.monotonic()
    response = await request(policy, target, method="HEAD")
    fallback = response["status_code"] in (405, 501)
    if fallback:
        response = await request(policy, target, method="GET", cap=65536)
    selected = {
        "server",
        "content-type",
        "content-length",
        "location",
        "cache-control",
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "date",
    }
    return {
        "status": "success",
        "http_status": response["status_code"],
        "url": response["url"],
        "headers": {k: v for k, v in response["headers"].items() if k in selected},
        "redirects": response["redirects"],
        "head_fallback": fallback,
        "duration_ms": round((time.monotonic() - start) * 1000),
    }
