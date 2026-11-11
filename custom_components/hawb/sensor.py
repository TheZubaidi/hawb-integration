"""Sensors."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HawbConfigEntry, HawbData
from .entity import HawbEntity, enum_or_none, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "sensor", HawbSensor)


class HawbSensor(HawbEntity, SensorEntity):
    def __init__(self, data: HawbData, entity_id: str) -> None:
        super().__init__(data, entity_id)

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return enum_or_none(SensorDeviceClass, self._def.get("device_class"))

    @property
    def state_class(self) -> SensorStateClass | None:
        return enum_or_none(SensorStateClass, self._def.get("state_class"))

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._def.get("unit")

    @property
    def native_value(self) -> Any:
        raw = self.raw_state
        if raw is None:
            return None
        if self.device_class == SensorDeviceClass.TIMESTAMP:
            parsed: datetime | None = dt_util.parse_datetime(raw)
            if parsed is not None and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            return parsed
        if self.device_class == SensorDeviceClass.DATE:
            parsed_date: date | None = dt_util.parse_date(raw)
            return parsed_date
        # Anything with a unit or state class must be numeric.
        if self.native_unit_of_measurement or self.state_class:
            try:
                number = float(raw)
            except ValueError:
                return None
            return int(number) if number.is_integer() and "." not in raw else number
        return raw
