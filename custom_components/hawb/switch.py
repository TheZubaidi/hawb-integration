"""Switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "switch", HawbSwitch)


class HawbSwitch(HawbEntity, SwitchEntity):
    @property
    def is_on(self) -> bool | None:
        raw = self.raw_state
        return None if raw is None else raw == "ON"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._command("ON")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._command("OFF")
