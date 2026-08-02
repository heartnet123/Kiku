from typing import Any

from supabase import Client, create_client

from app.core.config import settings


def create_supabase_client(
    access_token: str | None = None,
    *,
    service_role: bool = False,
) -> Client | None:
    """Create a Supabase client bound to the caller when a token is provided."""
    key = settings.supabase_service_role_key if service_role else settings.supabase_key
    if not settings.supabase_url or not key:
        return None

    client = create_client(settings.supabase_url, key)
    if access_token and not service_role:
        client.postgrest.auth(access_token)
        # supabase-py exposes PostgREST auth publicly but keeps the storage headers
        # internal; keep Storage calls under the same caller identity as the DB calls.
        client.storage._headers["authorization"] = f"Bearer {access_token}"  # type: ignore[attr-defined]
    return client


def response_data(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    return data if isinstance(data, list) else []
