"""Binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, enum_or_none, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "binary_sensor", HawbBinarySensor)


class HawbBinarySensor(HawbEntity, BinarySensorEntity):
    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        return enum_or_none(BinarySensorDeviceClass, self._def.get("device_class"))

    @property
    def is_on(self) -> bool | None:
        raw = self.raw_state
        return None if raw is None else raw == "ON"
