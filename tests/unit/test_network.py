import asyncio
import socket

import pytest

from netnama.core import network
from netnama.core.target_policy import TargetPolicy
from netnama.core.validation import ValidationError


class Reader:
    def __init__(self, blocks):
        self.blocks = iter(blocks)

    async def readuntil(self, sep):
        return next(self.blocks)

    async def read(self, n):
        return next(self.blocks, b"")


class Writer:
    def __init__(self):
        self.data = b""
        self.closed = False

    def write(self, value):
        self.data += value

    async def drain(self):
        pass

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


def test_pinned_connect_and_original_sni(monkeypatch):
    async def run():
        calls = []
        writer = Writer()

        async def resolve(*args):
            return "example.com", ["93.184.215.14"]

        async def connect(host, port, **kwargs):
            calls.append((host, port, kwargs["server_hostname"]))
            return Reader([b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"]), writer

        policy = TargetPolicy()
        monkeypatch.setattr(policy, "resolve", resolve)
        monkeypatch.setattr(network.asyncio, "open_connection", connect)
        result = await network.request(policy, "https://example.com", method="HEAD")
        assert result["status_code"] == 200
        assert calls == [("93.184.215.14", 443, "example.com")]
        assert b"Host: example.com\r\n" in writer.data
        assert writer.closed

    asyncio.run(run())


def test_redirect_private_is_checked_again(monkeypatch):
    async def run():
        calls = []
        writer = Writer()

        async def resolve(host, port):
            calls.append(host)
            if host == "127.0.0.1":
                raise ValidationError("blocked_target")
            return host, ["1.1.1.1"]

        async def connect(*args, **kwargs):
            return Reader([b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1/\r\n\r\n"]), writer

        policy = TargetPolicy()
        monkeypatch.setattr(policy, "resolve", resolve)
        monkeypatch.setattr(network.asyncio, "open_connection", connect)
        with pytest.raises(ValidationError, match="blocked_target"):
            await network.request(policy, "https://example.com")
        assert calls == ["example.com", "127.0.0.1"]
        assert writer.closed

    asyncio.run(run())


def test_dns_rebinding_no_second_resolution(monkeypatch):
    async def run():
        loop = asyncio.get_running_loop()
        lookups = []

        async def getaddrinfo(*args, **kwargs):
            lookups.append(args[0])
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443))]

        async def connect(host, port, **kwargs):
            assert host == "1.1.1.1"
            return Reader([b"HTTP/1.1 200 OK\r\n\r\n"]), Writer()

        monkeypatch.setattr(loop, "getaddrinfo", getaddrinfo)
        monkeypatch.setattr(network.asyncio, "open_connection", connect)
        await network.request(TargetPolicy(), "https://example.com", method="HEAD")
        assert lookups == ["example.com"]

    asyncio.run(run())


def test_ping_cancellation_kills_and_reaps(monkeypatch):
    from netnama.tools import ping

    async def run():
        started = asyncio.Event()

        class Output:
            async def readline(self):
                started.set()
                await asyncio.sleep(60)

        class Process:
            returncode = None
            stdout = Output()
            killed = False
            waited = False

            def kill(self):
                self.killed = True

            async def wait(self):
                self.waited = True
                self.returncode = -9

        process = Process()

        class Policy:
            async def resolve(self, *args):
                return "example.com", ["1.1.1.1"]

        async def create(*args, **kwargs):
            assert isinstance(args[0], str)
            assert "shell" not in kwargs
            return process

        monkeypatch.setattr(ping.shutil, "which", lambda name: "/usr/bin/ping")
        monkeypatch.setattr(ping.asyncio, "create_subprocess_exec", create)
        task = asyncio.create_task(ping.run("example.com", {}, Policy(), lambda *args: None))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert process.killed and process.waited

    asyncio.run(run())


@pytest.mark.parametrize("rcode", [0, 3, 2, 5])
def test_dns_rcodes_preserved(monkeypatch, rcode):
    from netnama.tools import dns as tool
    import dns.message

    async def response(message, *args, **kwargs):
        value = dns.message.make_response(message)
        value.set_rcode(rcode)
        return value, False

    monkeypatch.setattr(tool.dns.asyncquery, "udp_with_fallback", response)
    result = asyncio.run(tool.query("_sip._tcp.example.com.", {"record": "SRV", "resolver": "1.1.1.1"}))
    assert result["rcode"] == {0: "NOERROR", 3: "NXDOMAIN", 2: "SERVFAIL", 5: "REFUSED"}[rcode]
    assert result["answer"] == []
    assert result["status"] == ("success" if rcode == 0 else "unknown")
