# Third-party notices

NetNama original code is MIT. Upstream components retain their own licenses.
There is no runtime CDN. Font binaries are stored under `netnama/static/fonts`:

- Vazirmatn: copyright Saber Rastikerdar and contributors; SIL OFL 1.1.
  https://github.com/rastikerdar/vazirmatn — `docs/licenses/Vazirmatn-OFL.txt`
- Inter: copyright Rasmus Andersson and contributors; SIL OFL 1.1.
  https://github.com/rsms/inter — `docs/licenses/Inter-OFL.txt`
- JetBrains Mono: copyright JetBrains s.r.o.; SIL OFL 1.1.
  https://github.com/JetBrains/JetBrainsMono — `docs/licenses/JetBrainsMono-OFL.txt`

Lucide selected SVG icon data: ISC, copyright Lucide contributors; some inherited
Feather icon geometry is MIT, copyright Cole Bemis. Full package license is in
`docs/licenses/Lucide-LICENSE.txt`. Tailwind CSS and esbuild: MIT (build time).

Public Suffix List: Mozilla Public License 2.0, maintained by the PSL contributors.
The unchanged source is distributed as `netnama/resources/bundled/psl.data`, with
its upstream license header and source URL; https://publicsuffix.org/list/.
Full MPL 2.0: `docs/licenses/MPL-2.0.txt`.

IANA bootstrap and root TLD data: https://data.iana.org/rdap/ and
https://data.iana.org/TLD/. Original downloaded data, provenance, retrieval dates
and SHA-256 hashes appear in the bundled manifest. Attribution to IANA does not
imply endorsement. See https://www.iana.org/help/licensing-terms.

Runtime Python components: Flask/Jinja2/Werkzeug/MarkupSafe/ItsDangerous/Click
(BSD-3-Clause), Blinker (MIT), Flask-WTF/WTForms (BSD-3-Clause), httpx/httpcore/h11
(BSD-3-Clause/MIT), AnyIO (MIT), dnspython (ISC), idna (BSD-3-Clause), publicsuffix2
(MIT with MPL PSL data), platformdirs (MIT), filelock (Unlicense), Waitress
(ZPL-2.1), certifi (MPL-2.0), typing-extensions (PSF-2.0).
Exact runtime versions and integrity hashes are in `requirements.lock` / `uv.lock`;
full installed distribution notices are retained by Python package installers.
`pip-audit` may bring requests as a development dependency; requests is not a
runtime dependency and is not used for application network operations.

persian-names, version 2.0.0: MIT, copyright MohammadReza HejaziRad.
The given-name list used by the domain-name studio is stored as
`netnama/resources/persian_names.json`.
https://github.com/mohammadhejazirad/persian-names — `docs/licenses/persian-names-MIT.txt`

The supplied NetNama vector marks are used as project assets. Availability of
the brand name, repository name or trademark has not been verified.
