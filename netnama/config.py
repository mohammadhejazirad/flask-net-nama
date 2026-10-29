"""Persistent configuration contains credentials, never query results."""

import json
import os
import secrets
from pathlib import Path

from filelock import FileLock
from platformdirs import user_data_dir
from werkzeug.security import generate_password_hash


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".new")
    try:
        with open(tmp, "w", encoding="utf-8") as file:
            if os.name != "nt":
                os.chmod(tmp, 0o600)
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


class Settings:
    def __init__(self, data_dir=None, testing=False):
        self.data_dir = Path(data_dir or os.getenv("NETNAMA_DATA_DIR") or user_data_dir("NetNama", "NetNama"))
        for name in ("config", "resources", "tmp"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        for leftover in (self.data_dir / "tmp").glob("netnama-*.tmp"):
            leftover.unlink(missing_ok=True)
        self.path = self.data_dir / "config" / "settings.json"
        self.public = os.getenv("NETNAMA_MODE", "local") == "public"
        self.allow_private = os.getenv("NETNAMA_ALLOW_PRIVATE_TARGETS", "false").lower() == "true"
        self.secure_cookie = os.getenv("NETNAMA_HTTPS", "false").lower() == "true"
        self.lock = FileLock(str(self.path) + ".lock")
        with self.lock:
            if self.path.exists():
                self.values = json.loads(self.path.read_text("utf-8"))
            else:
                password = os.getenv("NETNAMA_PASSWORD", "123456")
                self.values = {
                    "username": os.getenv("NETNAMA_USERNAME", "admin"),
                    "password_hash": os.getenv("NETNAMA_PASSWORD_HASH") or generate_password_hash(password),
                    "secret": os.getenv("NETNAMA_SECRET_KEY") or secrets.token_hex(32),
                    "auth_version": 1,
                }
                # Validate explicit options before persisting the first configuration.
                self.validate()
                atomic_json(self.path, self.values)
        self.validate()
        self.secret = os.getenv("NETNAMA_SECRET_KEY") or self.values["secret"]
        self.username = os.getenv("NETNAMA_USERNAME") or self.values["username"]
        self.result_ttl = int(os.getenv("NETNAMA_RESULT_TTL", "900"))
        self.max_ram_mb = int(os.getenv("NETNAMA_MAX_RAM_MB", "48"))
        if not 30 <= self.result_ttl <= 3600 or not 8 <= self.max_ram_mb <= 256:
            raise ValueError("Result TTL must be 30..3600 seconds; admission RAM must be 8..256 MiB.")
        self.testing = testing

    def validate(self):
        if self.public:
            secret = os.getenv("NETNAMA_SECRET_KEY") or self.values["secret"]
            if len(secret) < 32 or len(set(secret)) < 12:
                raise ValueError("NETNAMA_SECRET_KEY must have 32+ characters and sufficient variety.")
            if self.allow_private:
                raise ValueError("NETNAMA_ALLOW_PRIVATE_TARGETS is forbidden in public mode.")

    def change_password(self, password):
        with self.lock:
            self.values["password_hash"] = generate_password_hash(password)
            self.values["auth_version"] += 1
            atomic_json(self.path, self.values)
