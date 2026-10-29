from netnama._version import __version__
import ipaddress
import json
import platform
import shutil
import threading
import time

from flask import Blueprint, Response, current_app, g, jsonify, request, stream_with_context

from netnama.auth.routes import authenticated
from netnama.core.export import serialize
from netnama.core.jobs import CapacityError, TERMINAL
from netnama.core.validation import ValidationError, dns_name, hostname, prepare_inputs
from netnama.resources.manager import SOURCES
from netnama.tools.dns import PRESETS, TYPES

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/capabilities")
@authenticated
def capabilities():
    settings = current_app.extensions["settings"]
    return jsonify(
        version=__version__,
        platform=platform.system(),
        execution_origin="server",
        ping=bool(shutil.which("ping")),
        mode="public" if settings.public else "local",
        allow_private_targets=settings.allow_private,
        single_process=True,
        resources=current_app.extensions["resources"].info(),
    )


def owned_job(key):
    try:
        return current_app.extensions["jobs"].get(key, g.owner)
    except TimeoutError:
        from flask import abort

        abort(410)
    except KeyError:
        from flask import abort

        abort(404)


def parameters(data, resources):
    tool = data.get("tool")
    options = data.get("options", {})
    if not isinstance(options, dict):
        raise ValidationError("invalid_options")
    options = {k: v for k, v in options.items() if k in ("force_fresh", "record", "resolver", "tcp", "count")}
    for key in ("force_fresh", "tcp"):
        if key in options and type(options[key]) is not bool:
            raise ValidationError("invalid_options")
    if tool == "domain_batch":
        if not resources.psl or not resources.tlds:
            raise ValidationError("resources_unavailable")
        text = data.get("text", "")
        if not isinstance(text, str):
            raise ValidationError("invalid_input")
        if data.get("bases") or data.get("suffixes"):
            bases, suffixes = data.get("bases", []), data.get("suffixes", [])
            if (
                not isinstance(bases, list)
                or not isinstance(suffixes, list)
                or len(bases) * len(suffixes) > 1000
                or any(not isinstance(x, str) or "." in x for x in bases)
                or any(not isinstance(x, str) for x in suffixes)
            ):
                raise ValidationError("too_many_inputs")
            text += "\n" + "\n".join(
                f"{b.strip()}.{s.strip().removeprefix('.')}" for b in bases for s in suffixes
            )
        targets, mapping = prepare_inputs(text, resources)
        return tool, targets, options, mapping
    if tool not in ("dns", "ping", "ip", "cidr", "ptr", "ip_rdap", "http", "tls"):
        raise ValidationError("invalid_tool")
    targets = data.get("targets", [])
    if (
        not isinstance(targets, list)
        or not 1 <= len(targets) <= 20
        or any(not isinstance(t, str) for t in targets)
    ):
        raise ValidationError("invalid_input")
    normalized = []
    for target in targets:
        if len(target) > 2048:
            raise ValidationError("invalid_input")
        if tool in ("ip", "ptr", "ip_rdap"):
            target = str(ipaddress.ip_address(target))
        elif tool == "cidr":
            target = str(ipaddress.ip_network(target, strict=False))
        elif tool == "dns":
            target = dns_name(target)
        elif tool == "http":
            current_app.extensions["scheduler"].policy.url(target)
        else:
            target = hostname(target)
        normalized.append(target)
    if tool in ("dns", "ptr"):
        if options.get("record", "A") not in TYPES:
            raise ValidationError("invalid_record")
        resolver = options.get("resolver", "system")
        if resolver not in PRESETS:
            if current_app.extensions["settings"].public:
                raise ValidationError("blocked_resolver")
            ipaddress.ip_address(resolver)
    if tool == "ping" and (
        type(options.get("count", 4)) is not int or not 1 <= options.get("count", 4) <= 10
    ):
        raise ValidationError("invalid_count")
    return tool, list(dict.fromkeys(normalized)), options, []


@bp.post("/jobs")
@authenticated
def create_job():
    if request.mimetype == "multipart/form-data":
        text = request.form.get("text", "")
        file = request.files.get("file")
        if file:
            if not file.filename.lower().endswith(".txt"):
                raise ValidationError("invalid_file")
            # Stream decode line-by-line, never write uploaded input to disk.
            import codecs

            decoded, size = [], 0
            for line in codecs.getreader("utf-8-sig")(file.stream):
                size += len(line.encode("utf-8"))
                if size > 1024 * 1024:
                    raise ValidationError("input_too_large")
                decoded.append(line)
            text += "\n" + "".join(decoded)
        data = {
            "tool": "domain_batch",
            "text": text,
            "options": {"force_fresh": request.form.get("force_fresh") == "true"},
        }
    else:
        data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("invalid_input")
    resources = current_app.extensions["resources"].snapshot()
    tool, targets, options, mapping = parameters(data, resources)
    job = current_app.extensions["jobs"].add(g.owner, tool, targets, options, resources, mapping)
    current_app.extensions["scheduler"].submit(job)
    return jsonify(job.snapshot()), 202


@bp.get("/jobs/<key>")
@authenticated
def snapshot(key):
    return jsonify(owned_job(key).snapshot())


@bp.post("/jobs/<key>/cancel")
@authenticated
def cancel(key):
    job = owned_job(key)
    current_app.extensions["scheduler"].cancel(job)
    return jsonify(ok=True, status=job.status)


@bp.get("/jobs/<key>/export")
@authenticated
def export(key):
    job = owned_job(key)
    fmt = request.args.get("format", "json")
    if fmt not in ("json", "txt", "json.txt"):
        raise ValidationError("invalid_format")
    snapshot = job.snapshot()
    catalog = current_app.extensions["catalogs"][g.locale]
    body = serialize(snapshot, fmt, catalog)
    name = f"netnama-{job.tool}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.{fmt}"
    return Response(
        body,
        content_type="text/plain; charset=utf-8" if fmt == "txt" else "application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"},
    )


class StreamLimit:
    def __init__(self):
        self.lock = threading.Lock()
        self.owners = {}
        self.total = 0

    def acquire(self, owner):
        with self.lock:
            if self.total >= 8 or self.owners.get(owner, 0) >= 2:
                raise CapacityError
            self.total += 1
            self.owners[owner] = self.owners.get(owner, 0) + 1

    def release(self, owner):
        with self.lock:
            self.total -= 1
            self.owners[owner] -= 1
            if not self.owners[owner]:
                del self.owners[owner]


@bp.get("/jobs/<key>/events")
@authenticated
def events(key):
    job = owned_job(key)
    limiter = current_app.extensions["streams"]
    owner = g.owner
    try:
        last = int(request.headers.get("Last-Event-ID") or request.args.get("after", 0))
        if last < 0:
            raise ValueError
    except ValueError as exc:
        raise ValidationError("invalid_event_id") from exc
    limiter.acquire(owner)
    store = current_app.extensions["sessions"]
    version = current_app.extensions["settings"].values["auth_version"]
    released = False
    release_lock = threading.Lock()

    def release():
        nonlocal released
        with release_lock:
            if not released:
                released = True
                limiter.release(owner)

    @stream_with_context
    def stream():
        nonlocal last
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline and store.valid(owner, version):
                with job.changed:
                    resync = None
                    if (job.events and last < job.events[0]["id"] - 1) or last > job.sequence:
                        resync = job.snapshot()
                        last = job.sequence
                    batch = [e.copy() for e in job.events if e["id"] > last]
                    done = job.status in TERMINAL
                if resync is not None:
                    yield f"id: {last}\nevent: resync\ndata: {json.dumps(resync, ensure_ascii=False)}\n\n"
                for event in batch:
                    last = event["id"]
                    yield f"id: {last}\nevent: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                if done:
                    break
                with job.changed:
                    if job.sequence == last:
                        job.changed.wait(timeout=15)
                yield ": heartbeat\n\n"
        finally:
            release()

    response = Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    response.call_on_close(release)
    return response


@bp.get("/resources")
@authenticated
def resources():
    return jsonify(current_app.extensions["resources"].info())


@bp.post("/resources/update")
@authenticated
def update_resources():
    data = request.get_json(silent=True) or {}
    key = data.get("resource")
    if key not in SOURCES:
        raise ValidationError("invalid_resource")
    result = (
        current_app.extensions["scheduler"]
        .update(current_app.extensions["resources"], key)
        .result(timeout=65)
    )
    return jsonify(result), 502 if result.get("status") == "error" else 200


@bp.post("/domain/normalize")
@authenticated
def normalize_domain():
    from netnama.core.validation import domain

    value = (request.get_json(silent=True) or {}).get("target", "")
    if not isinstance(value, str) or len(value) > 1024:
        raise ValidationError("invalid_input")
    resources = current_app.extensions["resources"].snapshot()
    if not resources.psl:
        raise ValidationError("resources_unavailable")
    return jsonify(domain(value, resources).dict())


@bp.get("/suffixes")
@authenticated
def suffixes():
    return jsonify(sorted(current_app.extensions["resources"].snapshot().tlds))


@bp.get("/jobs")
@authenticated
def current_job():
    groups = {"ip": {"ip", "cidr", "ptr", "ip_rdap"}, "http": {"http", "tls"}}
    tool = request.args.get("tool")
    accepted = groups.get(tool, {tool}) if tool else None
    store = current_app.extensions["jobs"]
    store.prune()
    with store.lock:
        jobs = [
            job
            for job in store.jobs.values()
            if job.owner == g.owner and (accepted is None or job.tool in accepted)
        ]
        job = max(jobs, key=lambda j: j.created, default=None)
    return jsonify(current=job.snapshot() if job else None)
