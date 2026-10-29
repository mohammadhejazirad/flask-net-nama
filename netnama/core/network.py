"""Pinned HTTP/1.1 transport: numeric connect with original Host and SNI."""

import asyncio
import ssl
from urllib.parse import urljoin

from .validation import ValidationError


async def _request(policy, url, method="GET", headers=None, cap=65536, redirects=5):
    chain = []
    for hop in range(redirects + 1):
        parsed, host, port = policy.url(url)
        _, addresses = await policy.resolve(host, port)
        secure = parsed.scheme == "https"
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                addresses[0],
                port,
                ssl=ssl.create_default_context() if secure else None,
                server_hostname=host if secure else None,
                limit=65536,
            ),
            10,
        )
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            if any(ord(c) < 33 or ord(c) > 126 for c in path):
                raise ValidationError("invalid_url")
            host_header = f"[{host}]" if ":" in host else host
            default = 443 if secure else 80
            if port != default:
                host_header += f":{port}"
            pairs = {
                "Host": host_header,
                "User-Agent": "NetNama/0.1",
                "Connection": "close",
                "Accept-Encoding": "identity",
                **(headers or {}),
            }
            raw = (
                f"{method} {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in pairs.items()) + "\r\n"
            )
            writer.write(raw.encode("ascii"))
            await writer.drain()
            block = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            if len(block) > 32768:
                raise ValidationError("response_too_large")
            lines = block.decode("iso-8859-1").split("\r\n")
            status = int(lines[0].split()[1])
            response_headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    response_headers[key.lower()] = value.strip()
            location = response_headers.get("location")
            if status in (301, 302, 303, 307, 308) and location:
                if hop == redirects:
                    raise ValidationError("too_many_redirects")
                chain.append({"url": url, "status": status})
                url = urljoin(url, location)
                continue
            body = b""
            if method != "HEAD" and status not in (204, 304):
                if response_headers.get("transfer-encoding", "").lower() == "chunked":
                    while True:
                        size_line = await asyncio.wait_for(reader.readline(), 10)
                        size = int(size_line.split(b";")[0].strip(), 16)
                        if size == 0:
                            break
                        if len(body) + size > cap:
                            raise ValidationError("response_too_large")
                        body += await asyncio.wait_for(reader.readexactly(size), 10)
                        if await reader.readexactly(2) != b"\r\n":
                            raise ValidationError("invalid_response")
                elif "content-length" in response_headers:
                    size = int(response_headers["content-length"])
                    if size < 0 or size > cap:
                        raise ValidationError("response_too_large")
                    body = await asyncio.wait_for(reader.readexactly(size), 10)
                else:
                    while len(body) <= cap:
                        part = await asyncio.wait_for(reader.read(min(16384, cap + 1 - len(body))), 10)
                        if not part:
                            break
                        body += part
                    if len(body) > cap:
                        raise ValidationError("response_too_large")
            return {
                "status_code": status,
                "headers": response_headers,
                "body": body,
                "url": url,
                "redirects": chain,
            }
        finally:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 2)
            except (OSError, TimeoutError):
                pass
    raise ValidationError("too_many_redirects")


async def request(policy, url, **kwargs):
    async with asyncio.timeout(30):
        return await _request(policy, url, **kwargs)
