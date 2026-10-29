"""Small opt-in real authority benchmark; no random availability assumptions."""

import asyncio
import json
import os
import platform
import time

from netnama.core.limits import NetworkLimits
from netnama.core.target_policy import TargetPolicy
from netnama.resources.manager import BUNDLED, ResourceManager
from netnama.tools.domain import check


async def main():
    targets = ["example.com", "example.net", "nic.ir"]
    limits, policy = NetworkLimits(), TargetPolicy()
    resources = ResourceManager(BUNDLED).snapshot()
    start = time.monotonic()
    results = await asyncio.gather(
        *(check({"input": target, "ascii": target}, resources, policy, limits, True) for target in targets),
        return_exceptions=True,
    )
    seconds = time.monotonic() - start
    statuses = [
        result.get("status") if isinstance(result, dict) else type(result).__name__ for result in results
    ]
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "logical_cpus": os.cpu_count(),
                "targets": targets,
                "cache": False,
                "authorities": ["IANA-discovered .com/.net RDAP", "NIC.IR WHOIS"],
                "seconds": round(seconds, 3),
                "targets_per_second": round(len(targets) / seconds, 3),
                "statuses": statuses,
                "error_rate": sum(status != "registered" for status in statuses) / len(targets),
                "note": "Three known registered domains; not a capacity or registry SLA benchmark.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
