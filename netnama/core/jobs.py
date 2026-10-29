import copy
import json
import re
import secrets
import threading
import time
from collections import deque

from netnama.resources.manager import now

TERMINAL = {"completed", "partial", "failed", "cancelled"}
CONTROL = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(value):
    if isinstance(value, str):
        return CONTROL.sub("", value)[:65536]
    if isinstance(value, list):
        return [clean(x) for x in value[:2000]]
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    return value


class CapacityError(Exception):
    pass


class Job:
    def __init__(self, owner, tool, targets, options, sources, mapping=None):
        self.id = secrets.token_urlsafe(24)
        self.owner = owner
        self.tool = tool
        self.targets = targets
        self.options = options
        self.resources = sources
        self.created = time.monotonic()
        self.touched = self.created
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.cancelled = threading.Event()
        self.results = []
        self.events = deque(maxlen=2000)
        self.event_bytes = 0
        self.result_bytes = 0
        self.sequence = 0
        self.status = "queued"
        self.started_at = now()
        self.finished_at = None
        self.truncated = False
        self.mapping = mapping or []
        self.task = None

    def emit(self, kind, data):
        with self.changed:
            data = clean(data)
            self.sequence += 1
            event = {"id": self.sequence, "type": kind, "data": data}
            size = len(json.dumps(event, ensure_ascii=False).encode())
            while self.events and (self.event_bytes + size > 1024 * 1024 or len(self.events) >= 2000):
                self.event_bytes -= self.events.popleft()["_size"]
                self.truncated = True
            event["_size"] = size
            self.events.append(event)
            self.event_bytes += size
            self.touched = time.monotonic()
            self.changed.notify_all()

    def result(self, result):
        with self.lock:
            result = clean(result)
            size = len(json.dumps(result, ensure_ascii=False).encode())
            if self.result_bytes + size > 2 * 1024 * 1024:
                self.truncated = True
                result = {k: result[k] for k in ("input", "status", "reason_code") if k in result}
                result["output_truncated"] = True
                size = len(json.dumps(result).encode())
            self.result_bytes += size
            self.results.append(result)
            self.emit("result", result)
            self.emit("progress", self.summary())

    def summary(self):
        counts = {}
        for result in self.results:
            status = result["status"]
            counts[status] = counts.get(status, 0) + 1
        return {"total": len(self.targets), "completed": len(self.results), "statuses": counts}

    def finish(self, status):
        with self.lock:
            if self.status in TERMINAL:
                return
            self.status = status
            self.finished_at = now()
            self.emit("done", {"status": status, "summary": self.summary()})

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(
                {
                    "schema_version": "1.0",
                    "app": {"name": "NetNama", "version": "0.1.0"},
                    "tool": self.tool,
                    "job_id": self.id,
                    "started_at": self.started_at,
                    "finished_at": self.finished_at,
                    "snapshot_at": now(),
                    "execution_origin": "server",
                    "status": self.status,
                    "parameters": self.options,
                    "inputs": self.targets,
                    "input_mapping": self.mapping,
                    "sources": self.resources.manifest,
                    "summary": self.summary(),
                    "results": self.results,
                    "events": [{k: v for k, v in e.items() if k != "_size"} for e in self.events],
                    "truncated": self.truncated,
                }
            )


class JobStore:
    def __init__(self, ttl=900, max_ram_mb=48):
        self.lock = threading.RLock()
        self.jobs = {}
        self.expired = deque(maxlen=2048)
        self.ttl = ttl
        self.max_bytes = max_ram_mb * 1024 * 1024

    def prune(self):
        with self.lock:
            for key, job in list(self.jobs.items()):
                if job.status in TERMINAL and time.monotonic() - job.touched > self.ttl:
                    self.expired.append((key, job.owner))
                    del self.jobs[key]

    def add(self, owner, tool, targets, options, resources, mapping=None):
        self.prune()
        with self.lock:
            active = [j for j in self.jobs.values() if j.status not in TERMINAL]
            own = [j for j in active if j.owner == owner]
            memory = sum(
                j.result_bytes + j.event_bytes + len(str(j.mapping)) + len(str(j.targets))
                for j in self.jobs.values()
            )
            if len(active) >= 12 or len(own) >= 2 or len(self.jobs) >= 48 or memory > self.max_bytes:
                raise CapacityError
            job = Job(owner, tool, targets, options, resources, mapping)
            self.jobs[job.id] = job
            return job

    def get(self, key, owner):
        self.prune()
        with self.lock:
            job = self.jobs.get(key)
            if job and job.owner == owner:
                return job
            if (key, owner) in self.expired:
                raise TimeoutError
            raise KeyError
