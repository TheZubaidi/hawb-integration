"""Text entities (e.g. "Speak" and "Play audio URL")."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "text", HawbText)


class HawbText(HawbEntity, TextEntity):
    _attr_native_min = 0
    _attr_native_max = 255

    @property
    def native_value(self) -> str | None:
        # An empty value is a normal state for these (nothing queued), so do not map it to unknown.
        return self._data.client.states.get(self._eid, "")

    async def async_set_value(self, value: str) -> None:
        await self._command(value)
