import asyncio
import json
import random
from urllib.parse import urlsplit

from netnama.core.network import request


def classify(response, target, kind="domain"):
    code = response["status_code"]
    content_type = response["headers"].get("content-type", "").split(";")[0].lower()
    if code == 429:
        return {"status": "rate_limited", "reason_code": "http_429"}
    if code >= 500:
        return {"status": "error", "reason_code": "upstream_error"}
    if content_type not in ("application/rdap+json", "application/json"):
        return {"status": "unknown", "reason_code": "invalid_rdap_content"}
    try:
        obj = json.loads(response["body"])
    except (ValueError, UnicodeError):
        return {"status": "unknown", "reason_code": "invalid_rdap_json"}
    if not isinstance(obj, dict):
        return {"status": "unknown", "reason_code": "invalid_rdap_object"}
    if (
        code == 404
        and obj.get("errorCode") == 404
        and isinstance(obj.get("rdapConformance"), list)
        and "rdap_level_0" in obj["rdapConformance"]
    ):
        return {
            "status": "likely_available" if kind == "domain" else "unknown",
            "reason_code": "rdap_not_found",
        }
    if code != 200:
        return {"status": "unknown", "reason_code": "http_" + str(code)}
    if kind == "domain":
        name = obj.get("ldhName", "").lower().rstrip(".")
        if obj.get("objectClassName") != "domain" or name != target:
            return {"status": "unknown", "reason_code": "rdap_mismatch"}
        return {
            "status": "registered",
            "reason_code": "rdap_domain_found",
            "evidence": {
                "ldhName": name,
                "status": obj.get("status", []),
                "events": obj.get("events", [])[:20],
            },
        }
    import ipaddress

    try:
        start = ipaddress.ip_address(obj["startAddress"])
        end = ipaddress.ip_address(obj["endAddress"])
        ip = ipaddress.ip_address(target)
        valid = obj.get("objectClassName") == "ip network" and start <= ip <= end
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        return {"status": "unknown", "reason_code": "rdap_mismatch"}
    return {
        "status": "success",
        "reason_code": "ip_allocation",
        "evidence": {
            k: obj.get(k)
            for k in ("name", "handle", "startAddress", "endAddress", "ipVersion", "country", "type")
        },
    }


async def lookup(target, endpoint, policy, limits, kind="domain"):
    url = endpoint.rstrip("/") + "/" + ("domain/" if kind == "domain" else "ip/") + target
    host = urlsplit(url).hostname
    result = None
    for attempt in range(1, 4):
        transient_error = None
        try:
            async with limits.slot(host):
                response = await request(
                    policy, url, headers={"Accept": "application/rdap+json"}, cap=512 * 1024
                )
        except (TimeoutError, OSError) as exc:
            transient_error = "timeout" if isinstance(exc, TimeoutError) else "network_error"
            response = {"status_code": 503, "headers": {}, "body": b""}
        result = (
            {"status": "error", "reason_code": transient_error}
            if transient_error
            else classify(response, target, kind)
        )
        result.update(source=url, attempts=attempt)
        if result["status"] != "rate_limited" and response["status_code"] not in (502, 503, 504):
            break
        if attempt < 3:
            retry = response["headers"].get("retry-after", "")
            try:
                delay = max(0, float(retry))
            except ValueError:
                from email.utils import parsedate_to_datetime
                from datetime import datetime, timezone

                try:
                    delay = max(
                        0, (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                    )
                except (ValueError, TypeError):
                    delay = 2**attempt + random.random()
            if delay > 15:
                break
            await asyncio.sleep(delay)
    return result
