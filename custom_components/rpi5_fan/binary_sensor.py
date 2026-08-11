"""Safety indicator: is the kernel still in charge of cooling?"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import Rpi5FanEntity


async def async_setup_entry(hass: HomeAssistant, entry, add: AddEntitiesCallback) -> None:
    add([Rpi5ManualProblem(entry.runtime_data)])


class Rpi5ManualProblem(Rpi5FanEntity, BinarySensorEntity):
    """On while manual control has the governor disabled.

    Exposed as a PROBLEM class deliberately: running without the kernel's
    thermal protection is a state worth alerting on, not a neutral mode. The
    coordinator's watchdog will clear it automatically, but a dashboard should
    still be able to show it.
    """

    _attr_name = "Manual control active"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "manual_problem")

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return bool(data.get("manual")) or data.get("governor") == "disabled"
