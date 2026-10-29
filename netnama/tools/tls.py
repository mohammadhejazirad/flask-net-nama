import asyncio
import ssl
from datetime import datetime, timezone


async def inspect(target, policy):
    host, addresses = await policy.resolve(target, 443)
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(addresses[0], 443, ssl=ssl.create_default_context(), server_hostname=host), 10
    )
    try:
        ssl_object = writer.get_extra_info("ssl_object")
        cert = ssl_object.getpeercert()
        expiry = datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), timezone.utc)
        return {
            "status": "success",
            "verified": True,
            "hostname": host,
            "protocol": ssl_object.version(),
            "issuer": cert.get("issuer"),
            "san": cert.get("subjectAltName"),
            "not_before": cert.get("notBefore"),
            "not_after": cert.get("notAfter"),
            "days_remaining": (expiry - datetime.now(timezone.utc)).days,
        }
    finally:
        writer.close()
        await writer.wait_closed()
