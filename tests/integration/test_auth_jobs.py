import json
import time

from tests.conftest import csrf


def wait(client, key):
    for _ in range(100):
        response = client.get("/api/jobs/" + key)
        value = response.json
        if value["status"] in ("completed", "partial", "failed", "cancelled"):
            return value
        time.sleep(0.02)
    raise AssertionError("Job did not complete")


def test_auth_csrf_logout(client, login):
    assert client.get("/api/capabilities").status_code == 200
    assert client.post("/api/jobs", json={}).status_code == 400
    assert client.post("/auth/logout", json={}, headers=login).status_code == 200
    assert client.get("/api/capabilities").status_code == 401


def test_auth_required(client):
    for path in [
        "/api/capabilities",
        "/api/resources",
        "/api/jobs/opaque",
        "/api/jobs/opaque/events",
        "/api/jobs/opaque/export",
    ]:
        assert client.get(path).status_code == 401
    assert client.post("/auth/login", json={"username": "admin", "password": "123456"}).status_code == 400


def test_real_local_computation_and_exports(client, login):
    response = client.post("/api/jobs", json={"tool": "cidr", "targets": ["192.0.2.0/31"]}, headers=login)
    assert response.status_code == 202
    key = response.json["job_id"]
    value = wait(client, key)
    assert value["results"][0]["usable"] == "2"
    for fmt in ("json", "json.txt"):
        result = client.get("/api/jobs/" + key + "/export?format=" + fmt)
        exported = json.loads(result.data)
        assert exported["schema_version"] == "1.0"
        assert exported["status"] == "completed"
        assert "attachment;" in result.headers["Content-Disposition"]
        for secret in ("csrf_token", "password_hash", "auth_version", "secret_key"):
            assert secret not in result.get_data(as_text=True)
    assert "NetNama" in client.get("/api/jobs/" + key + "/export?format=txt").text
    events = client.get("/api/jobs/" + key + "/events").text
    assert "event: result" in events
    assert "event: done" in events


def test_job_isolation(app, client, login):
    result = client.post("/api/jobs", json={"tool": "ip", "targets": ["::1"]}, headers=login)
    key = result.json["job_id"]
    other = app.test_client()
    token = csrf(other)
    other.post(
        "/auth/login", json={"username": "admin", "password": "123456"}, headers={"X-CSRFToken": token}
    )
    assert other.get("/api/jobs/" + key).status_code == 404
    assert other.get("/api/jobs/" + key + "/export").status_code == 404
    assert other.get("/api/jobs/" + key + "/events").status_code == 404


def test_invalid_batch_never_available(client, login):
    response = client.post(
        "/api/jobs",
        json={"tool": "domain_batch", "text": "https://example.com\nwww.example.co.uk\nx.invalidtld"},
        headers=login,
    )
    assert response.status_code == 202
    value = wait(client, response.json["job_id"])
    assert value["status"] == "failed"
    assert all(r["status"] == "invalid" for r in value["results"])


def test_validation_and_password(client, login):
    assert (
        client.post(
            "/api/jobs", json={"tool": "ping", "targets": ["-c"], "options": {"count": 100}}, headers=login
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/jobs", json={"tool": "http", "targets": ["http://user:password@example.com"]}, headers=login
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/resources/update", json={"resource": "https://evil.invalid"}, headers=login
        ).status_code
        == 422
    )
    response = client.post(
        "/auth/password",
        json={"current_password": "123456", "new_password": "a-strong-password-1234"},
        headers=login,
    )
    assert response.status_code == 200
    assert client.get("/api/capabilities").status_code == 401


def test_cookie_only_identity_and_version(app, client, login):
    serializer = app.session_interface.get_signing_serializer(app)
    cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
    value = serializer.loads(cookie.value)
    assert set(value) == {"sid", "auth_version"}


def test_server_expiry(client, app, login):
    with client.session_transaction() as session:
        sid = session["sid"]
    app.extensions["sessions"].active[sid] = 0
    assert client.get("/api/capabilities").status_code == 401


def test_bom_file_import(client, login, app, monkeypatch):
    async def fake_execute(*args):
        return {"status": "unknown"}

    monkeypatch.setattr(app.extensions["scheduler"], "execute", fake_execute)
    import io

    response = client.post(
        "/api/jobs",
        data={
            "text": "example.com",
            "file": (io.BytesIO(b"\xef\xbb\xbfEXAMPLE.COM.\r\nhttps://invalid.com\n"), "targets.txt"),
        },
        headers=login,
    )
    assert response.status_code == 202
    assert response.json["summary"]["total"] == 2
    # Cancel to avoid making any external network request in ordinary tests.
    client.post("/api/jobs/" + response.json["job_id"] + "/cancel", json={}, headers=login)


def test_domain_helpers(client, login):
    result = client.post("/api/domain/normalize", json={"target": "www.example.co.uk"}, headers=login)
    assert result.json["registrable"] == "example.co.uk"
    assert "COM" in client.get("/api/suffixes").json


def test_unauthenticated_mutations(client):
    for path in (
        "/api/jobs",
        "/api/jobs/opaque/cancel",
        "/api/resources/update",
        "/auth/logout",
        "/auth/password",
    ):
        assert client.post(path, json={}).status_code == 401


def test_resync_and_idempotent_cancel(client, login, app):
    from netnama.core.jobs import Job

    job = Job("owner", "ip", ["1.1.1.1"], {}, app.extensions["resources"].snapshot())
    with client.session_transaction() as session:
        job.owner = session["sid"]
    app.extensions["jobs"].jobs[job.id] = job
    for n in range(2010):
        job.emit("line", {"text": str(n)})
    job.finish("completed")
    response = client.get("/api/jobs/" + job.id + "/events", headers={"Last-Event-ID": "1"})
    assert "event: resync" in response.text
    assert app.extensions["streams"].total == 0
    client.post("/api/jobs/" + job.id + "/cancel", json={}, headers=login)
    assert job.status == "completed"


def test_restore_latest_job_owned_only(app, client, login):
    result = client.post("/api/jobs", json={"tool": "cidr", "targets": ["192.0.2.1/32"]}, headers=login)
    wait(client, result.json["job_id"])
    restored = client.get("/api/jobs?tool=ip").json["current"]
    assert restored["job_id"] == result.json["job_id"]
    assert client.get("/api/jobs?tool=domain_batch").json["current"] is None
