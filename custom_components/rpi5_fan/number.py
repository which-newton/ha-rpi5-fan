"""One number entity per active trip point — the live curve editor."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TRIP_MAX_C, TRIP_MIN_C
from .entity import Rpi5FanEntity


async def async_setup_entry(hass: HomeAssistant, entry, add: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    count = len(coordinator.paths.active_trips)
    add([Rpi5Trip(coordinator, i) for i in range(count)])


class Rpi5Trip(Rpi5FanEntity, NumberEntity):
    """Trip N temperature. Writing it retunes the curve live.

    The kernel governor stays in charge throughout, which is what makes live
    editing safe: whatever is set here keeps being enforced even if Home
    Assistant stops running.
    """

    _attr_native_min_value = TRIP_MIN_C
    _attr_native_max_value = TRIP_MAX_C
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = None

    def __init__(self, coordinator, position: int) -> None:
        super().__init__(coordinator, f"trip_{position + 1}")
        self._position = position
        self._attr_name = f"Fan level {position + 1} threshold"
        self._attr_entity_registry_enabled_default = coordinator.can_write

    @property
    def native_value(self) -> float | None:
        trips = (self.coordinator.data or {}).get("trips_c") or []
        if self._position < len(trips):
            return trips[self._position]
        return None

    @property
    def available(self) -> bool:
        return super().available and bool((self.coordinator.data or {}).get("can_write"))

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_trip(self._position, int(value))
