# ponytail: per-process limiter; replace with Redis/provider WAF when multiple API instances or high traffic matter
from collections import defaultdict
from time import time
from typing import Optional
from fastapi import Request


_window_seconds = 60
_rules = {
    "auth": 10,
    "workspace-write": 20,
    "expensive-ai": 30,
    "upload": 10,
}

_exact_paths = {
    "POST /api/v1/auth/login": "auth",
    "POST /api/v1/auth/register": "auth",
    "POST /api/v1/auth/refresh": "auth",
    "POST /api/v1/workspaces": "workspace-write",
    "POST /api/v1/workspaces/join": "workspace-write",
}

_store: defaultdict[str, list[float]] = defaultdict(list)


def _match_rule(method: str, path: str) -> str | None:
    method_path = f"{method} {path}"
    return _exact_paths.get(method_path)


def check_rate_limit(request: Request) -> Optional[int]:
    """Return retry_after seconds if rate limited, else None."""
    try:
        client_host = request.client.host if request.client else "unknown"
        rule_name = _match_rule(request.method, request.url.path)

        if not rule_name:
            return None

        key = f"{client_host}:{rule_name}"
        now = time()
        limit = _rules[rule_name]

        _store[key] = [t for t in _store[key] if now - t < _window_seconds]

        if len(_store[key]) >= limit:
            retry_after = int(_window_seconds - (now - _store[key][0]))
            return retry_after

        _store[key].append(now)
        return None
    except Exception:
        return None
