import asyncio
import concurrent.futures
import ipaddress
import threading
import time

import httpx

from netnama.core.jobs import TERMINAL
from netnama.core.limits import NetworkLimits
from netnama.core.validation import ValidationError
from netnama.providers import rdap
from netnama.resources.manager import now
from netnama.tools import dns, domain, http, ip, ping, tls


class Scheduler:
    def __init__(self, policy, public=False):
        self.policy = policy
        self.public = public
        self.ready = threading.Event()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._main, name="netnama-scheduler", daemon=True)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="netnama-blocking"
        )
        self.closed = False
        self.thread.start()
        if not self.ready.wait(10):
            raise RuntimeError("Scheduler startup failed")

    def _main(self):
        asyncio.set_event_loop(self.loop)
        self.loop.set_default_executor(self.executor)
        self.limits = NetworkLimits()
        self.active = asyncio.Semaphore(4)
        # Shared lifecycle client; pinned network tools use numeric-connect transport.
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10, connect=5), trust_env=False, limits=httpx.Limits(max_connections=8)
        )
        self.ready.set()
        self.loop.run_forever()
        self.loop.close()

    def submit(self, job):
        if self.closed:
            raise RuntimeError("Scheduler closed")
        return asyncio.run_coroutine_threadsafe(self._run(job), self.loop)

    async def _run(self, job):
        job.task = asyncio.current_task()
        try:
            async with self.active:
                if job.cancelled.is_set():
                    job.finish("cancelled")
                    return
                job.status = "running"
                job.emit("state", {"status": "running"})
                # At most eight target workers per job; never 1000 queued tasks.
                pending = iter(job.targets)

                async def worker():
                    for target in pending:
                        if job.cancelled.is_set():
                            return
                        start = time.monotonic()
                        try:
                            async with asyncio.timeout(45):
                                result = await self.execute(job, target)
                        except asyncio.CancelledError:
                            raise
                        except TimeoutError:
                            result = {"status": "error", "reason_code": "timeout"}
                        except ValidationError as exc:
                            result = {"status": "error", "reason_code": str(exc)}
                        except Exception as exc:
                            result = {"status": "error", "reason_code": type(exc).__name__}
                        label = target.get("input") if isinstance(target, dict) else target
                        result.setdefault("input", label)
                        result.setdefault("checked_at", now())
                        result.setdefault("reason_code", "completed")
                        result.setdefault("duration_ms", round((time.monotonic() - start) * 1000))
                        result.setdefault(
                            "explanation_key", "reason_" + result.get("reason_code", "completed")
                        )
                        result.setdefault("cached", False)
                        result.setdefault("attempts", 1)
                        job.result(result)

                await asyncio.gather(*(worker() for _ in range(min(8, len(job.targets)))))
                errors = sum(
                    r["status"] in ("error", "unknown", "rate_limited", "unsupported", "invalid")
                    for r in job.results
                )
                job.finish("failed" if errors == len(job.targets) else "partial" if errors else "completed")
        except asyncio.CancelledError:
            # Existing completed results remain intact; pending inputs get explicit cancellation.
            completed = {r.get("input") for r in job.results}
            for target in job.targets:
                label = target.get("input") if isinstance(target, dict) else target
                if label not in completed:
                    job.result({"input": label, "status": "cancelled", "reason_code": "cancelled"})
            job.finish("cancelled")
        finally:
            job.task = None

    async def execute(self, job, target):
        tool, opts = job.tool, job.options
        if tool == "domain_batch":
            return await domain.check(
                target, job.resources, self.policy, self.limits, opts.get("force_fresh", False)
            )
        if tool == "dns":
            async with self.limits.global_limit:
                return await dns.query(target, opts, self.public)
        if tool == "ip":
            return ip.inspect(target)
        if tool == "cidr":
            return ip.cidr(target)
        if tool == "ptr":
            async with self.limits.global_limit:
                return await dns.ptr(target, opts, self.public)
        if tool == "ip_rdap":
            address = ipaddress.ip_address(target)
            endpoint = job.resources.endpoint("ipv4" if address.version == 4 else "ipv6", str(address))
            if not endpoint:
                return {"status": "unsupported", "reason_code": "no_authoritative_adapter"}
            return await rdap.lookup(str(address), endpoint, self.policy, self.limits, "ip")
        async with self.limits.global_limit:
            if tool == "ping":
                return await ping.run(target, opts, self.policy, job.emit)
            if tool == "http":
                return await http.inspect(target, self.policy)
            if tool == "tls":
                return await tls.inspect(target, self.policy)
        raise ValidationError("invalid_tool")

    def cancel(self, job):
        with job.lock:
            if job.status in TERMINAL:
                return
            job.cancelled.set()
            if job.task:
                self.loop.call_soon_threadsafe(job.task.cancel)

    def update(self, manager, key):
        return asyncio.run_coroutine_threadsafe(manager.update(key), self.loop)

    def close(self):
        if self.closed:
            return
        self.closed = True

        async def shutdown():
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.client.aclose()

        try:
            asyncio.run_coroutine_threadsafe(shutdown(), self.loop).result(timeout=10)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)
            self.executor.shutdown(wait=False, cancel_futures=True)
