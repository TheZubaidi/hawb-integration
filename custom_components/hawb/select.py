"""Selects."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "select", HawbSelect)


class HawbSelect(HawbEntity, SelectEntity):
    @property
    def options(self) -> list[str]:
        return list(self._def.get("options", []))

    @property
    def current_option(self) -> str | None:
        raw = self.raw_state
        return raw if raw in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self._command(option)
