"""Curve profile selector."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PRESET_MANUAL, PRESETS
from .entity import Rpi5FanEntity


async def async_setup_entry(hass: HomeAssistant, entry, add: AddEntitiesCallback) -> None:
    add([Rpi5FanProfile(entry.runtime_data)])


class Rpi5FanProfile(Rpi5FanEntity, SelectEntity):
    _attr_translation_key = "profile"
    _attr_name = "Profile"
    _attr_options = PRESETS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "profile")
        self._attr_entity_registry_enabled_default = coordinator.can_write

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("preset")

    @property
    def available(self) -> bool:
        return super().available and bool((self.coordinator.data or {}).get("can_write"))

    async def async_select_option(self, option: str) -> None:
        if option == PRESET_MANUAL:
            return
        await self.coordinator.async_set_preset(option)
