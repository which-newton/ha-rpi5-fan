"""The fan entity — preset curves, plus opt-in manual speed."""
from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import PRESET_BALANCED, PRESET_MANUAL, PRESETS
from .entity import Rpi5FanEntity


async def async_setup_entry(hass: HomeAssistant, entry, add: AddEntitiesCallback) -> None:
    add([Rpi5Fan(entry.runtime_data)])


class Rpi5Fan(Rpi5FanEntity, FanEntity):
    _attr_name = None  # the device name is the fan name
    _attr_translation_key = "fan"
    _attr_preset_modes = PRESETS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "fan")
        features = FanEntityFeature.PRESET_MODE
        # SET_SPEED is only advertised when manual control is both permitted by
        # the user and physically possible. Offering a slider that silently does
        # nothing (because the governor overwrites it) is worse than not having one.
        if coordinator.allow_manual and coordinator.can_write:
            features |= FanEntityFeature.SET_SPEED
        self._attr_supported_features = features

    @property
    def percentage(self) -> int | None:
        """Actual measured duty cycle, not the requested one."""
        return (self.coordinator.data or {}).get("pwm_percent")

    @property
    def is_on(self) -> bool | None:
        pct = self.percentage
        return None if pct is None else pct > 0

    @property
    def preset_mode(self) -> str | None:
        return (self.coordinator.data or {}).get("preset")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "rpm": data.get("rpm"),
            "cpu_temperature": data.get("temp_c"),
            "trip_points_c": data.get("trips_c"),
            "governor": data.get("governor"),
            "manual_control": data.get("manual"),
            "writable": data.get("can_write"),
        }

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_MANUAL:
            # 'manual' is a reported state, not a settable one: it means "a raw
            # PWM value is being held". Selecting it directly would disable the
            # governor with no speed to hold, so it is a no-op by design.
            return
        await self.coordinator.async_set_preset(preset_mode)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            # Never spin the fan down to a stop on request — hand back to the
            # kernel instead, which will stop it only if the die is actually cool.
            await self.coordinator.async_set_governor(True)
            return
        await self.coordinator.async_set_percent(percentage)

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage:
            await self.coordinator.async_set_percent(percentage)
        else:
            await self.coordinator.async_set_preset(PRESET_BALANCED)

    async def async_turn_off(self, **kwargs) -> None:
        """'Off' means 'kernel decides', never 'fan stops'.

        A fan entity that can genuinely stop the only cooling on a passively
        awkward SBC is a footgun; returning control to the governor is the honest
        interpretation and cannot overheat the machine.
        """
        await self.coordinator.async_set_governor(True)
