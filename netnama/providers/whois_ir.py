"""Conservative IR adapter. Unknown wording never means available."""

import asyncio


def classify(text, target):
    lines = [line.strip() for line in text.splitlines()]
    folded = text.lower()
    if any(x in folded for x in ("rate limit", "too many requests", "query limit", "access denied")):
        return {"status": "rate_limited", "reason_code": "whois_rate_limited"}
    for line in lines:
        if line.lower().startswith("domain:") and line.split(":", 1)[1].strip().lower() == target:
            return {
                "status": "registered",
                "reason_code": "whois_domain_found",
                "evidence": {"domain": target},
            }
    if (
        lines
        and lines[0] == "% This is the IRNIC Whois server v2.0.0."
        and f"% Information related to '{target}'" in lines
        and "%ERROR:101: no entries found" in lines
        and "% No entries found in the selected source(s)." in lines
    ):
        return {
            "status": "likely_available",
            "reason_code": "whois_no_match",
            "evidence": {"marker": "IRNIC ERROR:101"},
        }
    return {"status": "unknown", "reason_code": "whois_unverified_no_match"}


async def lookup(target, policy, limits):
    _, addresses = await policy.resolve("whois.nic.ir", 43)
    async with limits.slot("whois.nic.ir"):
        reader, writer = await asyncio.wait_for(asyncio.open_connection(addresses[0], 43), 5)
        try:
            writer.write((target + "\r\n").encode("ascii"))
            await writer.drain()
            content = bytearray()
            while True:
                part = await asyncio.wait_for(reader.read(8192), 10)
                if not part:
                    break
                content.extend(part)
                if len(content) > 128 * 1024:
                    raise ValueError("response_too_large")
            result = classify(content.decode("utf-8", errors="replace"), target)
            return {**result, "source": "whois://whois.nic.ir:43", "attempts": 1}
        finally:
            writer.close()
            await writer.wait_closed()
