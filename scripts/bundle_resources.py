"""Release-only download of official data; never invoked by application startup."""

import hashlib
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

sources = {
    "dns": "https://data.iana.org/rdap/dns.json",
    "ipv4": "https://data.iana.org/rdap/ipv4.json",
    "ipv6": "https://data.iana.org/rdap/ipv6.json",
    "tlds": "https://data.iana.org/TLD/tlds-alpha-by-domain.txt",
    "psl": "https://publicsuffix.org/list/public_suffix_list.dat",
}
folder = Path("netnama/resources/bundled")
manifest = {}
for key, url in sources.items():
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read(4 * 1024 * 1024)
        (folder / (key + ".data")).write_bytes(content)
        manifest[key] = {
            "source": url,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "publication": response.headers.get("Last-Modified"),
            "status": "bundled",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
(folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
