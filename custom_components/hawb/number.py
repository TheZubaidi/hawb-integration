"""Numbers."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "number", HawbNumber)


class HawbNumber(HawbEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER

    @property
    def native_min_value(self) -> float:
        return float(self._def.get("min") if self._def.get("min") is not None else 0)

    @property
    def native_max_value(self) -> float:
        return float(self._def.get("max") if self._def.get("max") is not None else 100)

    @property
    def native_step(self) -> float:
        return float(self._def.get("step") or 1)

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._def.get("unit")

    @property
    def native_value(self) -> float | None:
        raw = self.raw_state
        try:
            return None if raw is None else float(raw)
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self._command(str(int(value)) if float(value).is_integer() else str(value))
