import asyncio
import time
from collections import OrderedDict
from contextlib import asynccontextmanager


class NetworkLimits:
    def __init__(self):
        self.global_limit = asyncio.Semaphore(8)
        self.hosts = {}
        self.cache = OrderedDict()

    @asynccontextmanager
    async def slot(self, host):
        entry = self.hosts.setdefault(host, {"sem": asyncio.Semaphore(2), "lock": asyncio.Lock(), "next": 0})
        async with self.global_limit, entry["sem"]:
            async with entry["lock"]:
                await asyncio.sleep(max(0, entry["next"] - time.monotonic()))
                entry["next"] = time.monotonic() + 1
            yield

    def get(self, key):
        entry = self.cache.get(key)
        if entry and entry[0] > time.monotonic():
            self.cache.move_to_end(key)
            return {**entry[1], "cached": True}
        self.cache.pop(key, None)
        return None

    def put(self, key, result):
        if result.get("status") not in ("registered", "likely_available"):
            return
        self.cache[key] = (time.monotonic() + 60, result.copy())
        while len(self.cache) > 1000:
            self.cache.popitem(last=False)
