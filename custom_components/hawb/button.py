"""Buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .entity import HawbEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "button", HawbButton)


class HawbButton(HawbEntity, ButtonEntity):
    async def async_press(self) -> None:
        await self._command("PRESS")
