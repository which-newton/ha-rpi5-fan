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
        # `manufacturer` is rendered as "by X" on the device page, which reads as
        # authorship rather than hardware origin. Naming Raspberry Pi there implied
        # they wrote or endorsed this integration — they did not. It now names what
        # is actually being driven: the kernel's pwm-fan driver.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Raspberry Pi 5 Fan",
            manufacturer="Linux pwm-fan driver",
            model="Pi 5 fan header, thermal-governor controlled",
            configuration_url="https://github.com/which-newton/ha-rpi5-fan",
        )
