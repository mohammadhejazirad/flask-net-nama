"""Resolve once, check every address, connect to a checked numeric address."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

from .validation import ValidationError, hostname


def allowed_ip(value, allow_private=False):
    ip = ipaddress.ip_address(value)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return False
    if ip.is_multicast or ip.is_unspecified:
        return False
    return allow_private or ip.is_global


class TargetPolicy:
    def __init__(self, allow_private=False):
        self.allow_private = allow_private

    async def resolve(self, target, port):
        target = hostname(target)
        try:
            records = await asyncio.wait_for(
                asyncio.get_running_loop().getaddrinfo(target, port, type=socket.SOCK_STREAM), 5
            )
        except (OSError, TimeoutError) as exc:
            raise ValidationError("resolve_failed") from exc
        addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or any(not allowed_ip(ip, self.allow_private) for ip in addresses):
            raise ValidationError("blocked_target")
        return target, addresses

    def url(self, value):
        try:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
                or parsed.port not in (None, 80, 443)
            ):
                raise ValueError
            return parsed, hostname(parsed.hostname), parsed.port or (443 if parsed.scheme == "https" else 80)
        except ValueError as exc:
            raise ValidationError("invalid_url") from exc
