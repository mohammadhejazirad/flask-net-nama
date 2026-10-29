import asyncio
import locale
import platform
import re
import shutil

from netnama.core.validation import ValidationError


def argv(binary, system, address, count):
    import ipaddress

    v6 = ipaddress.ip_address(address).version == 6
    if system == "Windows":
        return [binary, "-6" if v6 else "-4", "-n", str(count), "-w", "2000", address]
    if system == "Darwin":
        return [binary, "-n", "-c", str(count), "-W", "2000", address]
    return [binary, "-6" if v6 else "-4", "-n", "-c", str(count), "-W", "2", address]


async def run(target, options, policy, emit):
    count = options.get("count", 4)
    if type(count) is not int or not 1 <= count <= 10:
        raise ValidationError("invalid_count")
    system = platform.system()
    _, addresses = await policy.resolve(target, 0)
    address = addresses[0]
    binary = shutil.which("ping6" if system == "Darwin" and ":" in address else "ping")
    if not binary:
        return {"status": "unsupported", "reason_code": "ping_binary_missing"}
    proc = await asyncio.create_subprocess_exec(
        *argv(binary, system, address, count),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    lines = []
    size = 0
    try:
        async with asyncio.timeout(30):
            while line := await proc.stdout.readline():
                text = line.decode(locale.getpreferredencoding(False), errors="replace").rstrip()
                size += len(line)
                if size > 128 * 1024:
                    raise ValidationError("response_too_large")
                lines.append(text)
                emit("line", {"text": text})
            code = await proc.wait()
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
    raw = "\n".join(lines)
    status = "success" if code == 0 else "unknown"
    reason = "ping_replied" if code == 0 else "ping_no_reply"
    if any(x in raw.lower() for x in ("operation not permitted", "permission denied", "access denied")):
        status, reason = "error", "ping_permission"
    match = re.search(r"(\d+(?:\.\d+)?)% (?:packet )?loss", raw)
    return {
        "status": status,
        "reason_code": reason,
        "output": raw,
        "returncode": code,
        "summary": {"packet_loss_percent": float(match[1])} if match else None,
        "execution_origin": "server",
    }
