"""Shared entity base."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FanCoordinator


class Rpi5FanEntity(CoordinatorEntity[FanCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Raspberry Pi 5 Fan",
            manufacturer="Raspberry Pi",
            model="Pi 5 pwm-fan (thermal governor)",
            configuration_url="https://github.com/which-newton/ha-rpi5-fan",
        )
