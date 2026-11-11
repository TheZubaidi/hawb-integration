"""Event entities (notification actions, hotkeys)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry, signal_event
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "event", HawbEvent)


class HawbEvent(HawbEntity, EventEntity):
    @property
    def event_types(self) -> list[str]:
        return list(self._def.get("event_types", []))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def on_event(entity: str, payload: dict[str, Any]) -> None:
            if entity != self._eid:
                return
            payload = dict(payload)
            event_type = payload.pop("event_type", None)
            if event_type in self.event_types:
                self._trigger_event(event_type, payload)
                self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, signal_event(self._data.entry_id), on_event))
