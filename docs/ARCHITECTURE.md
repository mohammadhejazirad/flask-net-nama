# Architecture and implementation decisions

Flask factory + auth/web/api blueprints, Jinja templates and modular vanilla JS.
No ORM/database, Redis, Celery, SPA, shell endpoint or automatic history.

A process-lifetime scheduler owns an asyncio loop on one thread. Admission is
bounded before scheduling: twelve outstanding jobs, two per session; a separate
semaphore admits four running jobs. Each batch uses at most eight worker tasks
pulling from an iterator, rather than creating a task for every target. A shared
network semaphore caps eight operations; registry host limiters share host keys
across suffixes and start at most one request per second. The loop's DNS/blocking
executor has four workers; its submissions are bounded by the admitted coroutine
workers. Shutdown cancels tasks, reaps ping, closes the shared AsyncClient, stops
the loop and shuts down the executor.

Pinned HTTP/1.1 and TLS use asyncio streams and the standard SSL context to
connect directly to validated numeric IPs with the original hostname as Host/SNI.
This is an intentional transport-level implementation choice: passing a hostname
to a default httpx transport after policy validation could cause a second DNS
lookup. A shared httpx AsyncClient is lifecycle-managed for extension adapters;
current pinned core requests do not route through its default hostname transport.
No environment proxy is trusted by core network tools. HTTP parsing is bounded
and does not aim to implement a general-purpose browser (no cookies, compression,
arbitrary methods/bodies, user credentials, HTTP/2 or websocket support).

Only server-side RAM holds active sessions/CSRF state, results, input mappings,
cache and replay events. The signed cookie has only sid and auth_version.
The browser stores only locale/theme. On navigation the UI retrieves its latest
owned job from RAM; it does not persist target/result data in browser storage.
Every job retains an immutable resource-version snapshot; snapshots share the
parsed PSL and source bytes until a manual update creates a new snapshot.
ICANN PSL rules determine registry registration boundaries. Private hosting rules
must not cause foo.blogspot.com to be offered as a registrable domain.

Each job has 2 MiB detailed result storage (then compact flagged records), 1 MiB
replay buffer, at most 2,000 events, 1,000 domain targets. There are at most 48
retained jobs. Admission accounts for target/mapping/result/event bytes and stops
at NETNAMA_MAX_RAM_MB; it is not a process RSS limit. Python object overhead,
shared datasets, temporary snapshot/JSON copies, request/WSGI buffers and runtime
baseline are additional but bounded by request, job and thread limits. Container
operators should also set a service memory limit suitable for their workload.
Waitress input overflow exceeds the request cap to prevent uploads spilling to
disk, and output overflow exceeds bounded exports; high-water backpressure limits
stream buffering. There are no input/result/history application files.

Exports contain snapshots and explicit snapshot times; JSON.TXT is UTF-8 JSON.
SSE is a bounded reader with replay/resync, heartbeat, connection caps, lifetime
and polling fallback. It does not execute a job. Capacity errors return 429;
expiry returns 410 only to the owning session, preserving isolation.

Bundled and updated resources use fixed official URLs. Updater validation precedes
replacement; FileLock and os.replace protect commits, manifest and credential
updates. The previous validated runtime resource file is retained for operator
rollback. There is no automatic periodic update, install command or URL input.
