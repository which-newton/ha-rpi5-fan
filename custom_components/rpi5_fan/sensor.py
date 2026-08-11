"""Fan speed, duty cycle and CPU temperature."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import Rpi5FanEntity


@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    value: Callable[[dict], float | int | str | None]


SENSORS: tuple[Desc, ...] = (
    Desc(
        key="rpm",
        name="Speed",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value=lambda d: d.get("rpm"),
    ),
    Desc(
        key="duty",
        name="Duty cycle",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value=lambda d: d.get("pwm_percent"),
    ),
    Desc(
        key="cpu_temp",
        name="CPU temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value=lambda d: d.get("temp_c"),
    ),
    Desc(
        key="governor",
        name="Governor",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:shield-check",
        value=lambda d: d.get("governor"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry, add: AddEntitiesCallback) -> None:
    add([Rpi5Sensor(entry.runtime_data, d) for d in SENSORS])


class Rpi5Sensor(Rpi5FanEntity, SensorEntity):
    entity_description: Desc

    def __init__(self, coordinator, description: Desc) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator.data or {})
