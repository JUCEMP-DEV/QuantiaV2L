from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def _build_supabase_admin_client() -> Client:
    if not settings.supabase_url or not settings.supabase_admin_key:
        raise RuntimeError(
            "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY o SUPABASE_KEY son obligatorios."
        )
    return create_client(settings.supabase_url, settings.supabase_admin_key)


def get_supabase_admin_client(force_refresh: bool = False) -> Client:
    if force_refresh:
        _build_supabase_admin_client.cache_clear()
    return _build_supabase_admin_client()
