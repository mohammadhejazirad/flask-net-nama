import json
import pytest
from netnama.providers.rdap import classify
from netnama.providers.whois_ir import classify as classify_ir


def response(code, obj, content_type="application/rdap+json"):
    return {"status_code": code, "body": json.dumps(obj).encode(), "headers": {"content-type": content_type}}


@pytest.mark.parametrize(
    "code,obj,expected",
    [
        (200, {"objectClassName": "domain", "ldhName": "EXAMPLE.COM"}, "registered"),
        (404, {"errorCode": 404, "rdapConformance": ["rdap_level_0"]}, "likely_available"),
        (404, {"errorCode": 404}, "unknown"),
        (404, {"errorCode": 404, "rdapConformance": []}, "unknown"),
        (200, {"objectClassName": "entity", "ldhName": "example.com"}, "unknown"),
        (200, {"objectClassName": "domain", "ldhName": "other.com"}, "unknown"),
        (429, {}, "rate_limited"),
        (503, {}, "error"),
        (403, {}, "unknown"),
    ],
)
def test_rdap_classification(code, obj, expected):
    assert classify(response(code, obj), "example.com")["status"] == expected


def test_html_and_invalid_json():
    assert classify(response(404, {}, "text/html"), "example.com")["status"] == "unknown"
    assert (
        classify(
            {"status_code": 200, "headers": {"content-type": "application/json"}, "body": b"!"}, "x.com"
        )["status"]
        == "unknown"
    )


def test_ir_conservative():
    assert classify_ir("domain: example.ir\n", "example.ir")["status"] == "registered"
    assert classify_ir("domain: other.ir\n", "example.ir")["status"] == "unknown"
    for text in ("", "No entries found", "% ERROR: unknown message"):
        assert classify_ir(text, "example.ir")["status"] == "unknown"
    assert classify_ir("Too many requests", "example.ir")["status"] == "rate_limited"


def test_bootstrap(app):
    resource = app.extensions["resources"].snapshot()
    assert "verisign.com/com/" in resource.endpoint("dns", "example.com")
    assert "verisign.com/net/" in resource.endpoint("dns", "example.net")
    assert resource.endpoint("dns", "example.ir") is None
    assert resource.endpoint("ipv4", "1.1.1.1").startswith("https://")


def test_ir_recorded_fixtures():
    from pathlib import Path

    registered = Path("tests/fixtures/ir_registered.txt").read_text()
    missing = Path("tests/fixtures/ir_no_match.txt").read_text()
    assert classify_ir(registered, "nic.ir")["status"] == "registered"
    target = "netnama-unregistered-check-20261029-8b17f2.ir"
    assert classify_ir(missing, target)["status"] == "likely_available"
    assert classify_ir(missing, "other.ir")["status"] == "unknown"


def test_transient_timeout_retries_remain_error(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager
    from netnama.providers import rdap

    calls = []

    @asynccontextmanager
    async def slot(host):
        yield

    class Limits:
        pass

    limits = Limits()
    limits.slot = slot

    async def failed(*args, **kwargs):
        calls.append(1)
        raise TimeoutError

    async def sleep(delay):
        pass

    monkeypatch.setattr(rdap, "request", failed)
    monkeypatch.setattr(rdap.asyncio, "sleep", sleep)
    result = asyncio.run(rdap.lookup("example.com", "https://authority.example/", None, limits))
    assert len(calls) == 3
    assert result["status"] == "error"
    assert result["reason_code"] == "timeout"
    assert result["attempts"] == 3


def test_long_retry_after_is_not_ignored(monkeypatch):
    import asyncio
    from contextlib import asynccontextmanager
    from netnama.providers import rdap

    calls = []

    @asynccontextmanager
    async def slot(host):
        yield

    class Limits:
        pass

    limits = Limits()
    limits.slot = slot

    async def limited(*args, **kwargs):
        calls.append(1)
        return {"status_code": 429, "body": b"{}", "headers": {"retry-after": "120"}}

    monkeypatch.setattr(rdap, "request", limited)
    result = asyncio.run(rdap.lookup("example.com", "https://authority.example/", None, limits))
    assert len(calls) == 1
    assert result["status"] == "rate_limited"
