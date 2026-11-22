"""Authenticated client for the local mode-switch service."""

from __future__ import annotations

from typing import Any

import aiohttp
from yarl import URL


class ApiError(Exception):
    """The service is unavailable or returned invalid data."""


class InvalidAuth(ApiError):
    """The service rejected the credentials."""


class Conflict(ApiError):
    """The topology changed or an operation is active."""


def normalize_url(value: str) -> str:
    """Accept an explicit HTTP(S) origin only, never embedded credentials."""
    url = URL(value.strip())
    if (
        url.scheme not in ("http", "https")
        or not url.host
        or url.user
        or url.password
        or url.query_string
        or url.fragment
        or url.path not in ("", "/")
    ):
        raise ValueError("Expected an HTTP(S) origin")
    _ = url.port
    return str(url.origin())


class SonosApi:
    """Use HA's managed session; never follow credential-bearing redirects."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self.session = session
        self.url = normalize_url(url)
        self._token = token.strip()

    async def request(
        self, method: str, path: str, data: dict | None = None
    ) -> dict[str, Any]:
        """Send exactly one request: never blindly retry a mutation."""
        try:
            async with self.session.request(
                method,
                self.url + path,
                json=data,
                headers={"Authorization": "Bearer " + self._token},
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise InvalidAuth("Authentication rejected")
                if response.status == 409:
                    raise Conflict("Another operation is active or topology changed")
                if response.status not in (200, 202):
                    raise ApiError(f"Service returned HTTP {response.status}")
                result = await response.json()
                if not isinstance(result, dict):
                    raise ApiError("Invalid service response")
                return result
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise ApiError("Cannot communicate with the mode-switch service") from err

    async def status(self) -> dict:
        data = await self.request("GET", "/v1/status")
        if data.get("observed_mode") not in (
            "music",
            "cinema",
            "standalone",
            "inconsistent",
            "unknown",
        ) or not isinstance(data.get("stale"), bool):
            raise ApiError("Incompatible status response")
        return data

    async def capabilities(self) -> dict:
        data = await self.request("GET", "/v1/capabilities")
        if not isinstance(data.get("writes_enabled"), bool):
            raise ApiError("Incompatible capabilities response")
        return data
