import asyncio
import json
import time
from pathlib import Path

import pytest

from netnama.config import Settings
from netnama.core.jobs import CapacityError, JobStore
from netnama.core.target_policy import TargetPolicy
from netnama.core.validation import ValidationError
from netnama.resources.manager import validate


def test_public_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("NETNAMA_MODE", "public")
    with pytest.raises(ValueError):
        Settings(tmp_path)
    monkeypatch.setenv("NETNAMA_SECRET_KEY", "strong-random-example-0123456789abcdef")
    with pytest.raises(ValueError):
        Settings(tmp_path)
    monkeypatch.setenv("NETNAMA_PASSWORD", "real-new-password-123")
    settings = Settings(tmp_path)
    assert "real-new-password-123" not in settings.path.read_text()
    monkeypatch.setenv("NETNAMA_ALLOW_PRIVATE_TARGETS", "true")
    with pytest.raises(ValueError):
        Settings(tmp_path)


def test_store_capacity_ttl_and_output(app):
    store = JobStore(ttl=0.01)
    resources = app.extensions["resources"].snapshot()
    job = store.add("owner", "ip", ["::1"], {}, resources)
    store.add("owner", "ip", ["::1"], {}, resources)
    with pytest.raises(CapacityError):
        store.add("owner", "ip", ["::1"], {}, resources)
    for _ in range(2100):
        job.emit("line", {"text": "\x1b[31mhello\x00"})
    assert len(job.events) == 2000
    assert job.event_bytes <= 1024 * 1024
    assert job.truncated
    assert "\x1b" not in job.events[-1]["data"]["text"]
    job.finish("completed")
    time.sleep(0.02)
    with pytest.raises(TimeoutError):
        store.get(job.id, "owner")
    with pytest.raises(KeyError):
        store.get(job.id, "intruder")


def test_cancel_and_capacity(app, monkeypatch):
    scheduler = app.extensions["scheduler"]

    async def slow(job, target):
        await asyncio.sleep(20)
        return {"status": "success"}

    monkeypatch.setattr(scheduler, "execute", slow)
    job = app.extensions["jobs"].add("owner", "ip", ["1.1.1.1"], {}, app.extensions["resources"].snapshot())
    future = scheduler.submit(job)
    time.sleep(0.03)
    scheduler.cancel(job)
    future.result(3)
    assert job.status == "cancelled"
    assert job.results[0]["status"] == "cancelled"
    scheduler.cancel(job)
    assert job.status == "cancelled"


def test_mixed_addresses_blocked(monkeypatch):
    async def check():
        loop = asyncio.get_running_loop()

        async def resolve(*args, **kwargs):
            return [(2, 1, 6, "", ("1.1.1.1", 443)), (2, 1, 6, "", ("127.0.0.1", 443))]

        monkeypatch.setattr(loop, "getaddrinfo", resolve)
        with pytest.raises(ValidationError, match="blocked_target"):
            await TargetPolicy().resolve("example.com", 443)

    asyncio.run(check())


def test_catalog_parity():
    root = Path("netnama/locales")
    en = json.loads((root / "en.json").read_text())
    fa = json.loads((root / "fa.json").read_text())
    assert en.keys() == fa.keys()
    assert all(en.values()) and all(fa.values())


def test_updater_preserves_good_copy(app, monkeypatch):
    from netnama.resources import manager

    original = app.extensions["resources"].snapshot().data["dns"]

    async def broken(*args, **kwargs):
        return {"status_code": 200, "body": b"{}", "headers": {}}

    monkeypatch.setattr(manager, "request", broken)
    result = app.extensions["scheduler"].update(app.extensions["resources"], "dns").result(3)
    assert result["status"] == "error"
    assert app.extensions["resources"].snapshot().data["dns"] == original
    with pytest.raises(ValueError):
        validate("tlds", b"COM")


def test_updater_304(app, monkeypatch):
    from netnama.resources import manager

    async def unchanged(*args, **kwargs):
        return {"status_code": 304, "body": b"", "headers": {}}

    monkeypatch.setattr(manager, "request", unchanged)
    result = app.extensions["scheduler"].update(app.extensions["resources"], "dns").result(3)
    assert result["status"] == "not_modified"
