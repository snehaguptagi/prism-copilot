"""Serverless entry point.

Exists only so a platform that looks for a module-level ASGI `app` has one at a
filename that does not collide with `api.py`. All behaviour lives in api.py; this
adds nothing and must keep adding nothing.

Local development still runs `uvicorn api:app` directly.
"""

from api import app  # noqa: F401  (re-exported for the platform to discover)
