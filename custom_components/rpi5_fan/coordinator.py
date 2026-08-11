"""Coordinator + safety watchdog for Raspberry Pi 5 Fan Control."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import hw
from .const import (
    DOMAIN,
    MANUAL_WATCHDOG_SECONDS,
    PRESET_MANUAL,
    PROFILES,
)

_LOGGER = logging.getLogger(__name__)


class FanCoordinator(DataUpdateCoordinator[dict]):
    """Polls sysfs, applies changes, and guarantees the governor comes back."""

    def __init__(
        self,
        hass: HomeAssistant,
        paths: hw.Paths,
        *,
        scan_seconds: int,
        allow_manual: bool,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds),
        )
        self.paths = paths
        self.allow_manual = allow_manual
        self.can_write = False
        self.preset: str = "balanced"
        # Set whenever manual PWM is applied; the watchdog uses it to decide the
        # user has gone away and the kernel should be back in charge.
        self._manual_since: datetime | None = None
        self._manual_percent: int | None = None

    async def async_prepare(self) -> None:
        """One-off capability probe, before entities are created."""
        self.can_write = await self.hass.async_add_executor_job(hw.writable, self.paths)
        if not self.can_write:
            _LOGGER.warning(
                "%s: trip points are not writable on this install — running "
                "read-only (temperature, RPM and PWM still reported). This is "
                "normal on Home Assistant Container with a read-only /sys",
                DOMAIN,
            )
        # Adopt whatever curve is already live rather than imposing one at startup.
        state = await self.hass.async_add_executor_job(hw.read_state, self.paths)
        self.preset = self._match_preset(state.get("trips_c") or [])

    @staticmethod
    def _match_preset(trips_c: list[int | None]) -> str:
        clean = [t for t in trips_c if t is not None]
        for name, values in PROFILES.items():
            # Tolerate ±1 C: the kernel rounds 67.5 C to 67 on readback.
            if len(clean) == len(values) and all(
                abs(a - b) <= 1 for a, b in zip(clean, values, strict=False)
            ):
                return name
        return PRESET_MANUAL

    async def _async_update_data(self) -> dict:
        try:
            state = await self.hass.async_add_executor_job(hw.read_state, self.paths)
        except OSError as err:  # pragma: no cover - sysfs vanishing mid-run
            raise UpdateFailed(f"reading sysfs failed: {err}") from err

        await self._async_watchdog(state)

        if state.get("governor") == "enabled":
            self.preset = self._match_preset(state.get("trips_c") or [])
        state["preset"] = self.preset
        state["can_write"] = self.can_write
        state["manual"] = self._manual_since is not None
        return state

    async def _async_watchdog(self, state: dict) -> None:
        """Restore kernel control if manual mode has gone stale.

        This is the whole reason manual mode is safe to offer. Without it, an HA
        crash or a forgotten slider would leave the governor disabled and the fan
        pinned at its last value — on an unattended machine that is how you cook
        an NVMe.
        """
        if self._manual_since is None:
            return
        age = (dt_util.utcnow() - self._manual_since).total_seconds()
        if age < MANUAL_WATCHDOG_SECONDS:
            return
        _LOGGER.warning(
            "%s: manual fan control has been idle for %ds — handing the fan back "
            "to the kernel governor",
            DOMAIN,
            int(age),
        )
        await self.async_set_governor(True)

    async def async_set_preset(self, preset: str) -> None:
        """Apply a curve profile. Always returns the governor to enabled."""
        if preset == PRESET_MANUAL:
            return
        if not self.can_write:
            raise RuntimeError("trip points are not writable on this install")
        temps = list(PROFILES[preset])
        await self.hass.async_add_executor_job(hw.set_trips, self.paths, temps)
        # A profile is a governor-managed curve by definition, so leaving manual
        # mode is part of applying one.
        await self.async_set_governor(True)
        self.preset = preset
        await self.async_request_refresh()

    async def async_set_trip(self, position: int, temp_c: int) -> None:
        """Change one trip point live, keeping the rest."""
        if not self.can_write:
            raise RuntimeError("trip points are not writable on this install")
        current = [t for t in (self.data or {}).get("trips_c", []) if t is not None]
        if position >= len(current):
            raise ValueError(f"trip {position} does not exist on this machine")
        current[position] = int(temp_c)
        await self.hass.async_add_executor_job(hw.set_trips, self.paths, current)
        await self.async_request_refresh()

    async def async_set_governor(self, enabled: bool) -> None:
        if not self.can_write:
            raise RuntimeError("this install cannot change fan control")
        await self.hass.async_add_executor_job(hw.governor_enabled, self.paths, enabled)
        self._manual_since = None if enabled else dt_util.utcnow()
        if enabled:
            self._manual_percent = None
        await self.async_request_refresh()

    async def async_set_percent(self, percent: int) -> None:
        """Take manual control and set raw fan speed."""
        if not self.allow_manual:
            raise RuntimeError(
                "manual fan control is disabled for this entry — enable it in the "
                "integration options, and read the watchdog note first"
            )
        if not self.can_write:
            raise RuntimeError("this install cannot change fan control")
        if self._manual_since is None:
            await self.hass.async_add_executor_job(hw.governor_enabled, self.paths, False)
        await self.hass.async_add_executor_job(hw.set_pwm, self.paths, percent)
        # Refresh the deadline on every write, so an active user keeps control and
        # an idle one loses it.
        self._manual_since = dt_util.utcnow()
        self._manual_percent = percent
        self.preset = PRESET_MANUAL
        await self.async_request_refresh()
