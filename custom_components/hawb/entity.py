"""Shared entity base and platform setup helper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry, HawbData
from .const import DOMAIN, SIGNAL_AVAILABLE, SIGNAL_ENTITIES, SIGNAL_STATE

NO_VALUE = {None, "", "None", "unknown", "unavailable"}


def enum_or_none(enum_cls: Any, value: str | None) -> Any:
    """Map a device-class string to an enum member, or None if HA does not know it."""
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


class HawbEntity(Entity):
    """One entity published by the PC; its definition and value live in the client."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, data: HawbData, entity_id: str) -> None:
        self._data = data
        self._eid = entity_id
        self._attr_unique_id = f"hawb_{data.device_id}_{entity_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.device_id)},
            name=data.name,
            manufacturer="HAWB",
            model="HAWB",
            sw_version=data.sw_version,
        )

    # -- definition -----------------------------------------------------------

    @property
    def _def(self) -> dict[str, Any]:
        return self._data.client.entities.get(self._eid, {})

    @property
    def name(self) -> str | None:
        return self._def.get("name") or self._eid

    @property
    def icon(self) -> str | None:
        return self._def.get("icon")

    @property
    def entity_category(self) -> EntityCategory | None:
        return enum_or_none(EntityCategory, self._def.get("category"))

    @property
    def entity_registry_enabled_default(self) -> bool:
        return not self._def.get("disabled_by_default", False)

    def _exists(self) -> bool:
        """Whether the PC still publishes this entity (composite entities override)."""
        return self._eid in self._data.client.entities

    @property
    def available(self) -> bool:
        return self._data.client.available and self._exists()

    # -- value ----------------------------------------------------------------

    @property
    def raw_state(self) -> str | None:
        value = self._data.client.states.get(self._eid)
        return None if value in NO_VALUE else value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._def.get("attributes"):
            return self._data.client.attrs.get(self._eid)
        return None

    async def _command(self, payload: Any = "PRESS", entity: str | None = None) -> None:
        await self._data.client.async_command(entity or self._eid, payload)

    # -- updates --------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        entry_id = self._data.entry_id

        @callback
        def on_state(entity: str) -> None:
            if entity == self._eid or self._eid in self._related():
                self.async_write_ha_state()

        @callback
        def refresh() -> None:
            if not self._exists() and self.registry_entry is not None:
                # Disabled in HAWB's settings: remove it from Home Assistant as well.
                er.async_get(self.hass).async_remove(self.entity_id)
            else:
                self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_STATE.format(entry_id=entry_id), on_state))
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_ENTITIES.format(entry_id=entry_id), refresh))
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_AVAILABLE.format(entry_id=entry_id), refresh))

    def _related(self) -> set[str]:
        """Other PC entities whose changes affect this entity (composite entities override)."""
        return set()


def setup_platform(
    hass: HomeAssistant,
    entry: HawbConfigEntry,
    async_add_entities: AddEntitiesCallback,
    component: str,
    factory: Callable[[HawbData, str], Entity],
) -> None:
    """Create entities of one component now and whenever the PC's entity list changes."""
    data = entry.runtime_data
    known: set[str] = set()

    @callback
    def sync() -> None:
        known.intersection_update(data.client.entities)  # re-enabled entities get created again
        new = []
        for eid, definition in data.client.entities.items():
            if definition.get("component") == component and eid not in known:
                known.add(eid)
                new.append(factory(data, eid))
        if new:
            async_add_entities(new)

    sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_ENTITIES.format(entry_id=entry.entry_id), sync))
