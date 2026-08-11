"""Config + options flow. Single instance, no YAML."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    ConfigEntry,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import hw
from .const import (
    CONF_ALLOW_MANUAL,
    CONF_SCAN_SECONDS,
    DEFAULT_SCAN_SECONDS,
    DOMAIN,
)


class Rpi5FanConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        try:
            paths = await self.hass.async_add_executor_job(hw.discover)
        except hw.NotSupported:
            return self.async_abort(reason="not_supported")
        except OSError:
            return self.async_abort(reason="sysfs_unreadable")

        writable = await self.hass.async_add_executor_job(hw.writable, paths)
        if user_input is not None:
            return self.async_create_entry(
                title="Raspberry Pi 5 Fan",
                data={},
                options={CONF_ALLOW_MANUAL: False, CONF_SCAN_SECONDS: DEFAULT_SCAN_SECONDS},
            )

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                "zone": paths.zone,
                "hwmon": paths.hwmon,
                "trips": str(len(paths.active_trips)),
                "writable": "yes" if writable else "NO — read-only mode",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return Rpi5FanOptionsFlow()


class Rpi5FanOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_SECONDS,
                        default=options.get(CONF_SCAN_SECONDS, DEFAULT_SCAN_SECONDS),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5, max=300, step=1, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(
                        CONF_ALLOW_MANUAL,
                        default=options.get(CONF_ALLOW_MANUAL, False),
                    ): selector.BooleanSelector(),
                }
            ),
        )
