import time

from netnama.providers import rdap, whois_ir
from netnama.resources.manager import now


async def check(item, resources, policy, limits, force=False):
    start = time.monotonic()
    if item.get("status") == "invalid":
        result = item.copy()
    elif not force and (cached := limits.get(item["ascii"])):
        return {**cached, **item}
    else:
        target = item["ascii"]
        endpoint = resources.endpoint("dns", target)
        if endpoint:
            result = await rdap.lookup(target, endpoint, policy, limits)
        elif target.endswith(".ir"):
            result = await whois_ir.lookup(target, policy, limits)
        else:
            result = {"status": "unsupported", "reason_code": "no_authoritative_adapter"}
    result = {
        **item,
        **result,
        "checked_at": now(),
        "duration_ms": round((time.monotonic() - start) * 1000),
        "cached": False,
        "attempts": result.get("attempts", 0),
    }
    result["explanation_key"] = "reason_" + result["reason_code"]
    if item.get("ascii"):
        limits.put(item["ascii"], result)
    return result
