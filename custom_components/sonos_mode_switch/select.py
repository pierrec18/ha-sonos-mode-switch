"""Select the desired topology while displaying only the observed mode."""

from homeassistant.components.select import SelectEntity

from .const import MODES
from .entity import SonosEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SonosModeSelect(entry.runtime_data)])


class SonosModeSelect(SonosEntity, SelectEntity):
    _attr_translation_key = "mode"
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, coordinator):
        super().__init__(coordinator, "mode")
        self._attr_options = list(MODES)

    @property
    def current_option(self):
        mode = self.coordinator.data.get("observed_mode")
        return mode if mode in MODES else None

    @property
    def available(self):
        data = self.coordinator.data or {}
        return bool(
            super().available
            and not data.get("stale", True)
            and data.get("devices_reachable")
            and data.get("writes_enabled")
            and not self.coordinator.busy
        )

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_mode(option)
