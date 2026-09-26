"""
db/client.py
Supabase Python client factory.
Two clients are maintained:
  - anon client  : uses SUPABASE_ANON_KEY (safe for row-level-security-restricted ops)
  - admin client : uses SUPABASE_SERVICE_ROLE_KEY (bypasses RLS — backend only)

Both are singletons to avoid re-creating the HTTP session on every request.
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_anon() -> Client:
    """Return a singleton Supabase client using the anon key (respects RLS)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin() -> Client:
    """
    Return a singleton Supabase client using the service-role key.
    This client BYPASSES Row Level Security — use only in the backend.
    NEVER expose this key to the frontend.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
