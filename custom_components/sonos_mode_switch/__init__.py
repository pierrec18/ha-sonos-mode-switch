"""Home Assistant integration for the local Sonos Mode Switch API."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SonosApi
from .const import CONF_TOKEN, CONF_URL
from .coordinator import SonosCoordinator

PLATFORMS = [Platform.SELECT, Platform.SENSOR, Platform.BINARY_SENSOR]
type SonosConfigEntry = ConfigEntry[SonosCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: SonosConfigEntry) -> bool:
    """Set up one service, without sending any Sonos mutation."""
    coordinator = SonosCoordinator(
        hass,
        entry,
        SonosApi(
            async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN]
        ),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SonosConfigEntry) -> bool:
    """Unload entities; HA owns the HTTP session and coordinator shutdown."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: SonosConfigEntry) -> None:
    """Apply changed credentials or polling options."""
    await hass.config_entries.async_reload(entry.entry_id)
