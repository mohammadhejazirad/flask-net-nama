import copy
import hashlib
import io
import ipaddress
import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from filelock import FileLock
from publicsuffix2 import PublicSuffixList

from netnama.config import atomic_json
from netnama.core.network import request
from netnama.core.target_policy import TargetPolicy
from netnama.core.validation import ValidationError

SOURCES = {
    "dns": "https://data.iana.org/rdap/dns.json",
    "ipv4": "https://data.iana.org/rdap/ipv4.json",
    "ipv6": "https://data.iana.org/rdap/ipv6.json",
    "tlds": "https://data.iana.org/TLD/tlds-alpha-by-domain.txt",
    "psl": "https://publicsuffix.org/list/public_suffix_list.dat",
}
BUNDLED = Path(__file__).parent / "bundled"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate(resource, content):
    text = content.decode("utf-8-sig")
    if resource in ("dns", "ipv4", "ipv6"):
        obj = json.loads(text)
        if not isinstance(obj.get("services"), list) or len(obj["services"]) < 5:
            raise ValueError("Invalid bootstrap schema")
        for suffixes, urls in obj["services"]:
            if not suffixes or not urls:
                raise ValueError("Empty service")
            for url in urls:
                parsed = urlsplit(url)
                # Some IANA entries include HTTP alternatives; only HTTPS is used.
                if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username:
                    raise ValueError("Invalid bootstrap URL")
            for suffix in suffixes:
                if resource in ("ipv4", "ipv6"):
                    ipaddress.ip_network(suffix)
        return obj
    if resource == "tlds":
        tlds = {line.strip() for line in text.splitlines() if line and not line.startswith("#")}
        if len(tlds) < 500 or not {"COM", "IR", "NET"}.issubset(tlds):
            raise ValueError("Invalid TLD list")
        return tlds
    if len(text.splitlines()) < 1000 or "co.uk" not in text or "BEGIN ICANN DOMAINS" not in text:
        raise ValueError("Invalid PSL")
    return PublicSuffixList(io.StringIO(text))


class Snapshot:
    def __init__(self, data, manifest):
        self.data = data
        self.manifest = manifest
        self.tlds = validate("tlds", data["tlds"]) if "tlds" in data else set()
        self.psl = None
        if "psl" in data:
            validate("psl", data["psl"])
            # Registry availability concerns ICANN registration boundaries. Private
            # hosting suffixes (e.g. blogspot.com) must not make subdomains purchasable.
            icann = data["psl"].decode("utf-8").split("// ===BEGIN PRIVATE DOMAINS===")[0]
            self.psl = PublicSuffixList(io.StringIO(icann))

    def endpoint(self, kind, target):
        if kind not in self.data:
            return None
        obj = validate(kind, self.data[kind])
        candidates = []
        for suffixes, urls in obj["services"]:
            urls = [u for u in urls if u.startswith("https://")]
            if not urls:
                continue
            for suffix in suffixes:
                if kind == "dns":
                    if target == suffix or target.endswith("." + suffix):
                        candidates.append((len(suffix), urls[0]))
                else:
                    network = ipaddress.ip_network(suffix)
                    ip = ipaddress.ip_address(target)
                    if network.version == ip.version and ip in network:
                        candidates.append((network.prefixlen, urls[0]))
        return max(candidates, default=(0, None))[1]


class ResourceManager:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.lock = threading.RLock()
        self.update_lock = threading.Lock()
        self.manifest_path = self.directory / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        self.data = {}
        bundled_manifest = (
            json.loads((BUNDLED / "manifest.json").read_text())
            if (BUNDLED / "manifest.json").exists()
            else {}
        )
        for key in SOURCES:
            path = self.directory / (key + ".data")
            if not path.exists():
                path = BUNDLED / (key + ".data")
            if path.exists():
                try:
                    content = path.read_bytes()
                    validate(key, content)
                    self.data[key] = content
                    self.manifest.setdefault(key, bundled_manifest.get(key, {"status": "bundled"}))
                except (ValueError, UnicodeError, TypeError):
                    self.manifest[key] = {"status": "unavailable"}

    def snapshot(self):
        with self.lock:
            if not hasattr(self, "_snapshot"):
                self._snapshot = Snapshot(self.data.copy(), copy.deepcopy(self.manifest))
            return self._snapshot

    def info(self):
        with self.lock:
            return {
                key: {**self.manifest.get(key, {}), "available": key in self.data, "source": url}
                for key, url in SOURCES.items()
            }

    async def update(self, key):
        if key not in SOURCES:
            raise ValidationError("invalid_resource")
        if not self.update_lock.acquire(blocking=False):
            raise ValidationError("update_busy")
        try:
            old = self.manifest.get(key, {})
            entry = {**old, "last_attempt": now()}
            headers = {}
            if old.get("etag"):
                headers["If-None-Match"] = old["etag"]
            if old.get("last_modified"):
                headers["If-Modified-Since"] = old["last_modified"]
            try:
                response = await request(TargetPolicy(), SOURCES[key], headers=headers, cap=4 * 1024 * 1024)
                if response["status_code"] == 304 and key in self.data:
                    entry.update(status="not_modified", last_success=now())
                elif response["status_code"] == 200:
                    content = response["body"]
                    validate(key, content)
                    with FileLock(str(self.manifest_path) + ".lock"):
                        path = self.directory / (key + ".data")
                        if path.exists():
                            shutil.copyfile(path, path.with_suffix(".previous"))
                        tmp = path.with_suffix(".tmp")
                        try:
                            tmp.write_bytes(content)
                            tmp.replace(path)
                        finally:
                            tmp.unlink(missing_ok=True)
                    with self.lock:
                        self.data[key] = content
                    entry.update(
                        status="updated",
                        last_success=now(),
                        retrieved_at=now(),
                        sha256=hashlib.sha256(content).hexdigest(),
                        etag=response["headers"].get("etag"),
                        last_modified=response["headers"].get("last-modified"),
                    )
                else:
                    raise ValueError("http_" + str(response["status_code"]))
            except Exception as exc:
                entry.update(status="error", error=type(exc).__name__)
            with self.lock:
                self.manifest[key] = entry
                self._snapshot = Snapshot(self.data.copy(), copy.deepcopy(self.manifest))
                with FileLock(str(self.manifest_path) + ".lock"):
                    atomic_json(self.manifest_path, self.manifest)
            return self.info()[key]
        finally:
            self.update_lock.release()
