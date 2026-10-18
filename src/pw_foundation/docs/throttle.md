# Throttle — client-side request pacing

`pw_foundation.utils.throttle.Throttle` enforces a **minimum interval between operations** so a client stays under a fixed request rate. Foundation tier — pure stdlib, no extra, importable on the bare install.

Reach for it whenever you call a rate-limited service yourself: many open-data / public APIs cap callers at ~1 req/s (OSM Nominatim and Wikipedia, for example) and answer `429`/`503` if you exceed it. Instead of re-implementing the sleep-between-calls dance in every client, share one `Throttle`.

> Outbound pacing only: limiting the requests a server *receives* is a web-framework concern.

## API

```python
from pw_foundation.utils.throttle import Throttle

throttle = Throttle.per_second(1)  # ≤ 1 request/second
# or: Throttle(min_interval_s=1.0)

for name in names:
    throttle.acquire()  # blocks until this caller's slot is due
    resp = httpx.get(url, params={"q": name})
```

- **`Throttle(min_interval_s=...)`** — minimum seconds between grants. `<= 0` disables throttling (e.g. pointing at a local mirror); negative values clamp to `0`.
- **`Throttle.per_second(rate)`** — convenience constructor; `rate <= 0` is unthrottled.
- **`acquire() -> float`** — block until the slot is due; returns the seconds actually slept (`0.0` when the slot was already available — useful for logging effective wait).

## Thread safety

`acquire()` reserves its slot under a lock and sleeps outside it, so N threads calling a shared `Throttle` are handed staggered slots `t, t+Δ, t+2Δ, …`. The aggregate outbound rate respects the interval even when calls fan out through [`pw_foundation.parallel.run_parallel`](parallel.md) — share a single instance across the workers.

## Scope

`Throttle` paces calls; it does not retry, cache, or wrap HTTP. Compose it with `httpx` and your own response handling — building a client for one specific service (its endpoints, auth, response shapes) is consumer-project work, not framework work (per the repo's `scope` rule).
