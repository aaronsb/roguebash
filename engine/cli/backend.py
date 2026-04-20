"""Probe the llama.cpp-compatible endpoint.

Just a health check. We don't auto-start the backend — that's the
adapter's (and user's) job.
"""

from __future__ import annotations

import urllib.request


def check_endpoint(config: dict) -> tuple[bool, str]:
    """Return (up, endpoint_str). Never raises; timeouts/errors → (False, ...)."""
    endpoint = config["agent"].get("endpoint", "127.0.0.1:8765")
    try:
        req = urllib.request.Request(f"http://{endpoint}/health")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = r.read().decode("utf-8", "replace").lower()
            if "ok" in data:
                return True, endpoint
    except Exception:
        pass
    return False, endpoint
