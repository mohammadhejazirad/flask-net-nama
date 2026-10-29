"""Build and exercise the real Compose service in a disposable project (no external lookups)."""

import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Image tag to build or reuse")
    parser.add_argument("--skip-build", action="store_true", help="Reuse --image without building")
    parser.add_argument("--defaults", action="store_true", help="Test first startup with only .env.example")
    args = parser.parse_args()
    if args.skip_build and not args.image:
        parser.error("--skip-build requires --image")
    project = f"netnama-smoke-{secrets.token_hex(5)}"
    environment = {key: value for key, value in os.environ.items() if not key.startswith("NETNAMA_")}
    password = "123456" if args.defaults else secrets.token_hex(24)
    username = "admin" if args.defaults else "deploycheck"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request_http(path, body=None, csrf=None):
        headers = {"Content-Type": "application/json"}
        if csrf:
            headers["X-CSRFToken"] = csrf
        request = urllib.request.Request(
            origin + path, data=json.dumps(body).encode() if body is not None else None, headers=headers
        )
        with client.open(request, timeout=10) as response:
            return response.read(), response.headers

    def login():
        body, _ = request_http("/auth/login")
        token = re.search(rb'name="csrf-token" content="([^"]+)"', body)[1].decode()
        body, _ = request_http("/auth/login", {"username": username, "password": password}, token)
        assert json.loads(body)["ok"]
        body, _ = request_http("/tools/domain_names")
        assert b'id="name-studio"' in body
        assert b'id="check-domains"' in body
        return re.search(rb'name="csrf-token" content="([^"]+)"', body)[1].decode()

    with tempfile.TemporaryDirectory(prefix="netnama-docker-smoke-") as directory:
        folder = Path(directory)
        shutil.copy2(ROOT / "compose.yaml", folder / "compose.yaml")
        shutil.copy2(ROOT / ".env.example", folder / ".env.example")
        env_file = folder / "compose-interpolation.env"
        env_file.write_text(f"NETNAMA_HTTP_PORT={port}\nNETNAMA_BIND_ADDRESS=127.0.0.1\n", encoding="utf-8")
        env_file.chmod(0o600)
        command = [
            "docker",
            "compose",
            "--project-directory",
            str(folder),
            "--env-file",
            str(env_file),
            "-p",
            project,
            "-f",
            str(folder / "compose.yaml"),
        ]
        service = {"build": {"context": str(ROOT)}}
        if args.image:
            service["image"] = args.image
        if not args.defaults:
            settings_file = folder / ".env"
            settings_file.write_text(
                f"NETNAMA_USERNAME={username}\nNETNAMA_PASSWORD={password}\n"
                f"NETNAMA_SECRET_KEY={secrets.token_hex(32)}\nNETNAMA_HTTPS=false\n",
                encoding="utf-8",
            )
            settings_file.chmod(0o600)
        override = folder / "override.json"
        override.write_text(json.dumps({"services": {"netnama": service}}), encoding="utf-8")
        command += ["-f", str(override)]
        assert (folder / ".env").exists() is (not args.defaults)

        def compose(*arguments, capture=False):
            return subprocess.run(
                [*command, *arguments],
                cwd=ROOT,
                env=environment,
                check=True,
                text=True,
                stdout=subprocess.PIPE if capture else None,
            ).stdout

        try:
            compose("config", "--quiet")
            if not args.skip_build:
                compose("build")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
            identifier = compose("ps", "-q", "netnama", capture=True).strip()
            container = json.loads(subprocess.check_output(["docker", "inspect", identifier], text=True))[0]
            assert container["Config"]["User"] == "10001:10001"
            assert container["State"]["Health"]["Status"] == "healthy"
            assert container["HostConfig"]["ReadonlyRootfs"]
            assert container["HostConfig"]["Init"]
            assert "ALL" in [item.upper() for item in container["HostConfig"]["CapDrop"]]
            assert "no-new-privileges:true" in container["HostConfig"]["SecurityOpt"]
            assert container["HostConfig"]["Memory"] == 512 * 1024 * 1024
            assert container["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostIp"] == "127.0.0.1"
            body, _ = request_http("/healthz")
            assert json.loads(body) == {"status": "ok"}
            token = login()
            for asset in ["app.js", "app.css", "theme.js"]:
                body, _ = request_http(f"/static/dist/{asset}")
                assert len(body) > 100
            for asset in ["logo.svg", "fonts/vazirmatn.woff2"]:
                body, _ = request_http(f"/static/{asset}")
                assert body
            body, _ = request_http("/api/capabilities")
            capabilities = json.loads(body)
            assert capabilities["mode"] == "public" and not capabilities["allow_private_targets"]
            assert all(item["available"] for item in capabilities["resources"].values())
            body, _ = request_http(
                "/api/names/compose", {"tokens": [{"fa": "نگین"}], "tlds": ["com", "ir"]}, token
            )
            assert {item["domain"] for item in json.loads(body)["domains"]} == {"negin.com", "negin.ir"}
            body, _ = request_http("/api/jobs", {"tool": "cidr", "targets": ["192.0.2.0/31"]}, token)
            key = json.loads(body)["job_id"]
            for _ in range(50):
                body, _ = request_http(f"/api/jobs/{key}")
                job = json.loads(body)
                if job["status"] == "completed":
                    break
                time.sleep(0.1)
            assert job["status"] == "completed" and job["results"][0]["usable"] == "2"
            body, _ = request_http(f"/api/jobs/{key}/events")
            assert b"event: result" in body and b"event: done" in body
            body, headers = request_http(f"/api/jobs/{key}/export?format=json")
            assert (
                json.loads(body)["status"] == "completed" and "attachment" in headers["Content-Disposition"]
            )

            def settings_hash():
                return compose(
                    "exec",
                    "-T",
                    "netnama",
                    "python",
                    "-c",
                    "import hashlib; from pathlib import Path; "
                    "print(hashlib.sha256(Path('/data/config/settings.json').read_bytes()).hexdigest())",
                    capture=True,
                ).strip()

            before = settings_hash()
            compose(
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                "NETNAMA_HTTPS=true",
                "--entrypoint",
                "python",
                "netnama",
                "-c",
                "from netnama import create_app; app=create_app(); "
                "r=app.test_client().get('/auth/login'); "
                "assert 'Secure' in r.headers['Set-Cookie']; "
                "assert r.headers['Strict-Transport-Security'] == 'max-age=31536000'; "
                "app.extensions['scheduler'].close()",
            )
            compose("restart", "netnama")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
            assert before == settings_hash()
            login()
            compose("stop", "netnama")
            state = json.loads(subprocess.check_output(["docker", "inspect", identifier], text=True))[0][
                "State"
            ]
            assert state["ExitCode"] == 0 and not state["OOMKilled"]
            backup = subprocess.check_output(
                [
                    *command,
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "--entrypoint",
                    "python",
                    "netnama",
                    "-c",
                    "import sys, tarfile; t=tarfile.open(fileobj=sys.stdout.buffer, mode='w|'); "
                    "t.add('/data', arcname='data'); t.close()",
                ],
                env=environment,
            )
            assert len(backup) > 1024
            subprocess.run(
                [
                    *command,
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "--entrypoint",
                    "python",
                    "netnama",
                    "-c",
                    "import sys, tarfile; t=tarfile.open(fileobj=sys.stdin.buffer, mode='r|*'); "
                    "t.extractall(path='/', filter='data')",
                ],
                input=backup,
                env=environment,
                check=True,
            )
            # Restore touches only this invocation's disposable volume.
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
            assert before == settings_hash()
            login()
            logs = compose("logs", "--no-color", "netnama", capture=True)
            if not args.defaults:
                assert password not in logs
            print(
                "PASS: Compose health, isolation, login, assets, names, jobs, SSE, export, "
                "persistence, secure cookies, backup/restore and SIGTERM"
            )
            print(f"Image ping capability: {capabilities['ping']}")
        finally:
            # Only this invocation's randomly named project and disposable volume are removed.
            compose("down", "--volumes", "--remove-orphans", "--timeout", "30")


if __name__ == "__main__":
    main()
