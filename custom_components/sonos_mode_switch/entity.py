"""Shared entity identity and availability."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SonosCoordinator


class SonosEntity(CoordinatorEntity[SonosCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SonosCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sonos Mode Switch",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.api.url + "/docs",
        )
