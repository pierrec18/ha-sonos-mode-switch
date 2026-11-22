"""Target-Core fixtures; only the independent aiohttp mock helper is reused.

PyPI's latest full HA fixture plugin targets 2026.10.4 and is incompatible
with 2026.11 logger internals, so bootstrap the actual 2026.11.2 Core here.
"""

from pathlib import Path
from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio
from homeassistant import bootstrap, loader
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import mock_aiohttp_client


@pytest_asyncio.fixture
async def hass(tmp_path):
    (tmp_path / "custom_components").symlink_to(
        Path(__file__).resolve().parents[1] / "custom_components",
        target_is_directory=True,
    )
    hass = HomeAssistant(str(tmp_path))
    hass.config.skip_pip = True
    loader.async_setup(hass)
    from homeassistant.config_entries import ConfigEntries

    hass.config_entries = ConfigEntries(hass, {})
    assert await bootstrap.async_load_base_functionality(hass)
    hass.config.components.add("persistent_notification")
    with patch(
        "homeassistant.helpers.aiohttp_client._async_make_resolver",
        return_value=aiohttp.ThreadedResolver(),
    ):
        yield hass
    for entry in hass.config_entries.async_entries():
        if entry.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_stop(force=True)


class MockConfigEntry(ConfigEntry):
    def __init__(self, *, domain, data, unique_id):
        super().__init__(
            domain=domain,
            data=data,
            unique_id=unique_id,
            discovery_keys={},
            minor_version=1,
            options={},
            source="user",
            subentries_data=(),
            title="Sonos Mode Switch",
            version=1,
        )

    def add_to_hass(self, hass):
        hass.config_entries._entries[self.entry_id] = self


@pytest.fixture
def aioclient_mock():
    with mock_aiohttp_client() as client:
        yield client


@pytest.fixture
def status():
    return {
        "observed_mode": "cinema",
        "stale": False,
        "active_operation_id": None,
        "devices_reachable": True,
        "last_operation": None,
        "error": None,
    }


@pytest.fixture
def api_mock(aioclient_mock, status):
    aioclient_mock.get("http://sonos.test:8765/v1/status", json=status)
    aioclient_mock.get(
        "http://sonos.test:8765/v1/capabilities", json={"writes_enabled": True}
    )
    return aioclient_mock
