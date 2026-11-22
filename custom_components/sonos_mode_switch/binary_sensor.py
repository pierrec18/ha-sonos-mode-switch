"""Transition-in-progress indicator."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import SonosEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SonosBusySensor(entry.runtime_data)])


class SonosBusySensor(SonosEntity, BinarySensorEntity):
    _attr_translation_key = "transition"
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, coordinator):
        super().__init__(coordinator, "transition")

    @property
    def is_on(self):
        return self.coordinator.busy
