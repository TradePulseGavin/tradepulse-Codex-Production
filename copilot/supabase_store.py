from __future__ import annotations

from typing import Any

import requests

from .config import settings


class SupabaseStore:
    """Small REST helper for server-side Supabase persistence.

    The app can still run in demo mode without Supabase service credentials.
    When SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is configured, these
    helpers can read/write the user-owned tables created by the MVP migration.
    """

    def __init__(self) -> None:
        self.base_url = (settings.supabase_url or "").rstrip("/")
        self.secret_key = settings.supabase_secret_key

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.secret_key)

    def _headers(self, prefer: str | None = None, auth_token: str | None = None) -> dict[str, str]:
        api_key = settings.supabase_publishable_key if auth_token else self.secret_key
        bearer = auth_token or self.secret_key
        if not api_key or not bearer:
            raise RuntimeError("Supabase credentials are not configured.")
        headers = {
            "apikey": api_key,
            "authorization": f"Bearer {bearer}",
            "content-type": "application/json",
        }
        if prefer:
            headers["prefer"] = prefer
        return headers

    def _url(self, table: str, query: str = "") -> str:
        if not self.base_url:
            raise RuntimeError("Supabase URL is not configured.")
        suffix = f"?{query}" if query else ""
        return f"{self.base_url}/rest/v1/{table}{suffix}"

    def select(self, table: str, query: str, timeout: int = 8, auth_token: str | None = None) -> list[dict[str, Any]]:
        response = requests.get(self._url(table, query), headers=self._headers(auth_token=auth_token), timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def insert(self, table: str, payload: dict[str, Any], timeout: int = 8, auth_token: str | None = None) -> dict[str, Any]:
        response = requests.post(
            self._url(table),
            headers=self._headers("return=representation", auth_token=auth_token),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]
        return payload

    def upsert(
        self,
        table: str,
        payload: dict[str, Any],
        on_conflict: str | None = None,
        timeout: int = 8,
        auth_token: str | None = None,
    ) -> dict[str, Any]:
        query = f"on_conflict={on_conflict}" if on_conflict else ""
        response = requests.post(
            self._url(table, query),
            headers=self._headers("resolution=merge-duplicates,return=representation", auth_token=auth_token),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]
        return payload

    def patch(
        self,
        table: str,
        query: str,
        payload: dict[str, Any],
        timeout: int = 8,
        auth_token: str | None = None,
    ) -> list[dict[str, Any]]:
        response = requests.patch(
            self._url(table, query),
            headers=self._headers("return=representation", auth_token=auth_token),
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def user_plan(self, user_id: str) -> dict[str, Any] | None:
        if not user_id:
            return None
        rows = self.select(
            "subscriptions",
            f"user_id=eq.{user_id}&select=plan,status,stripe_customer_id,stripe_subscription_id,updated_at&order=updated_at.desc.nullslast&limit=1",
        )
        return rows[0] if rows else None

    def user_plan_with_token(self, auth_token: str) -> dict[str, Any] | None:
        rows = self.select(
            "subscriptions",
            "select=plan,status,stripe_customer_id,stripe_subscription_id,updated_at&order=updated_at.desc.nullslast&limit=1",
            auth_token=auth_token,
        )
        return rows[0] if rows else None

    def upsert_subscription(
        self,
        *,
        user_id: str,
        plan: str,
        status: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "plan": plan,
            "status": status,
            "stripe_customer_id": stripe_customer_id,
            "stripe_subscription_id": stripe_subscription_id,
        }
        rows = self.select("subscriptions", f"user_id=eq.{user_id}&select=id&limit=1")
        if rows:
            updated = self.patch("subscriptions", f"id=eq.{rows[0]['id']}", payload)
            return updated[0] if updated else payload
        return self.insert("subscriptions", payload)


store = SupabaseStore()
