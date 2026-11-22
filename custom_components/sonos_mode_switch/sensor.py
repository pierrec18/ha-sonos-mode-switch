"""Actual topology and operation result sensors."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .entity import SonosEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            SonosStatusSensor(entry.runtime_data, key)
            for key in ("observed_mode", "operation")
        ]
    )


class SonosStatusSensor(SonosEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self.key = key
        self._attr_translation_key = key
        self._attr_options = (
            ["music", "cinema", "standalone", "inconsistent", "unknown"]
            if key == "observed_mode"
            else [
                "idle",
                "accepted",
                "running",
                "succeeded",
                "failed",
                "stopped",
                "interrupted",
                "needs_attention",
            ]
        )

    @property
    def available(self):
        return bool(
            super().available
            and (
                self.key != "observed_mode"
                or not self.coordinator.data.get("stale", True)
            )
        )

    @property
    def native_value(self):
        data = self.coordinator.data
        value = (
            data.get("observed_mode")
            if self.key == "observed_mode"
            else (data.get("last_operation") or {}).get("result", "idle")
        )
        return value if value in self._attr_options else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if self.key == "observed_mode":
            return {
                key: data.get(key)
                for key in (
                    "observed_at",
                    "stale",
                    "devices_reachable",
                    "writes_enabled",
                )
            }
        operation = data.get("last_operation") or {}
        return {
            key: operation.get(key) for key in ("id", "mode", "error", "updated_at")
        }
