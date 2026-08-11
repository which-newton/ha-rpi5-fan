"""Raspberry Pi 5 Fan Control."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import hw
from .const import (
    CONF_ALLOW_MANUAL,
    CONF_SCAN_SECONDS,
    DEFAULT_SCAN_SECONDS,
    DOMAIN,
)
from .coordinator import FanCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]

type Rpi5FanEntry = ConfigEntry[FanCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: Rpi5FanEntry) -> bool:
    try:
        paths = await hass.async_add_executor_job(hw.discover)
    except hw.NotSupported as err:
        # Not retryable: no amount of waiting turns a non-Pi-5 into one.
        _LOGGER.error("%s: unsupported hardware: %s", DOMAIN, err)
        return False
    except OSError as err:
        raise ConfigEntryNotReady(f"sysfs not readable yet: {err}") from err

    coordinator = FanCoordinator(
        hass,
        paths,
        scan_seconds=entry.options.get(CONF_SCAN_SECONDS, DEFAULT_SCAN_SECONDS),
        allow_manual=entry.options.get(CONF_ALLOW_MANUAL, False),
    )
    await coordinator.async_prepare()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: Rpi5FanEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: Rpi5FanEntry) -> bool:
    """Unload, and never leave the governor disabled behind us.

    Removing or reloading the integration while manual mode is active would
    otherwise strand the machine with no thermal management.
    """
    coordinator = entry.runtime_data
    if coordinator.data and coordinator.data.get("manual"):
        _LOGGER.warning(
            "%s: unloading while in manual mode — restoring the kernel governor",
            DOMAIN,
        )
        try:
            await coordinator.async_set_governor(True)
        except RuntimeError:
            pass
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
