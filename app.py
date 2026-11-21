"""Vercel entrypoint: the hosted, synthetic-only cockpit as a WSGI app."""
from cockpit.wsgi import app  # noqa: F401
