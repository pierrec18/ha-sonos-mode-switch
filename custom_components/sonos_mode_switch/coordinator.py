"""Poll actual topology; request changes with a fresh fingerprint."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, InvalidAuth, SonosApi
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN, MODES

_LOGGER = logging.getLogger(__name__)


class SonosCoordinator(DataUpdateCoordinator[dict]):
    """A single poller and mutation gate per configured service."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: SonosApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            ),
        )
        self.api = api
        self.request_lock = asyncio.Lock()
        self.pending_operation: str | None = None

    async def _async_update_data(self) -> dict:
        try:
            status = await self.api.status()
            capabilities = await self.api.capabilities()
            if self.pending_operation:
                # Fetch the accepted operation directly: cached status can lag acceptance.
                operation = await self.api.request(
                    "GET", "/v1/operations/" + self.pending_operation
                )
                status["last_operation"] = {
                    key: operation.get(key)
                    for key in (
                        "id",
                        "mode",
                        "result",
                        "error",
                        "created_at",
                        "updated_at",
                    )
                }
                if operation.get("result") in ("accepted", "running"):
                    status["active_operation_id"] = self.pending_operation
                else:
                    self.pending_operation = None
            return {**status, "writes_enabled": capabilities["writes_enabled"]}
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("API token rejected") from err
        except ApiError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def busy(self) -> bool:
        return bool(
            self.request_lock.locked()
            or self.pending_operation
            or (self.data or {}).get("active_operation_id")
        )

    async def async_set_mode(self, mode: str) -> None:
        """Acceptance is not completion; leave observed state unchanged."""
        if mode not in MODES:
            raise HomeAssistantError("Unsupported Sonos mode")
        if self.busy:
            raise HomeAssistantError("A Sonos transition is already in progress")
        async with self.request_lock:
            try:
                state = await self.api.status()
                caps = await self.api.capabilities()
                if (
                    state["stale"]
                    or state.get("error")
                    or not state.get("devices_reachable")
                ):
                    raise HomeAssistantError("Speaker state is stale or unavailable")
                if state.get("active_operation_id"):
                    raise HomeAssistantError(
                        "A Sonos transition is already in progress"
                    )
                if not caps["writes_enabled"]:
                    raise HomeAssistantError(
                        "Writes are disabled in the mode-switch service"
                    )
                if state["observed_mode"] == mode:
                    return
                plan = await self.api.request("POST", "/v1/plans", {"mode": mode})
                fingerprint = plan.get("fingerprint")
                if not isinstance(fingerprint, str) or len(fingerprint) != 64:
                    raise HomeAssistantError(
                        "Service returned an invalid topology fingerprint"
                    )
                operation = await self.api.request(
                    "POST",
                    "/v1/mode",
                    {
                        "mode": mode,
                        "idempotency_key": "ha-" + uuid.uuid4().hex,
                        "expected_fingerprint": fingerprint,
                    },
                )
                if not isinstance(operation.get("id"), str):
                    raise HomeAssistantError(
                        "Missing operation ID; inspect service before retrying"
                    )
                if operation.get("result") in ("accepted", "running"):
                    self.pending_operation = operation["id"]
            except InvalidAuth as err:
                self.config_entry.async_start_reauth(self.hass)
                raise HomeAssistantError(
                    "API token rejected; reauthentication required"
                ) from err
            except ApiError as err:
                # An ambiguous timeout may mean the POST was accepted: never retry it.
                raise HomeAssistantError(
                    str(err) + "; check operation status before retrying"
                ) from err
        await self.async_request_refresh()
