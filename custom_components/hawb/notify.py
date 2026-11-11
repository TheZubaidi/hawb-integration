"""Notifications: notify.send_message plus a richer ``hawb.send_rich_notification`` service."""

from __future__ import annotations

import json
from typing import Any

import voluptuous as vol
from homeassistant.components.notify import NotifyEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry
from .const import DOMAIN
from .entity import HawbEntity, setup_platform

ACTION_SCHEMA = vol.Schema({vol.Required("action"): cv.string, vol.Required("title"): cv.string})

RICH_SCHEMA = {
    vol.Optional("message", default=""): cv.string,
    vol.Optional("title"): cv.string,
    vol.Optional("image"): cv.string,
    vol.Optional("icon"): cv.string,
    vol.Optional("tag"): cv.string,
    vol.Optional("silent"): cv.boolean,
    vol.Optional("reply"): vol.Any(cv.boolean, cv.string),
    vol.Optional("actions"): vol.All(cv.ensure_list, [ACTION_SCHEMA]),
    vol.Optional("clear"): cv.boolean,
}


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    setup_platform(hass, entry, async_add_entities, "notify", HawbNotify)
    entity_platform.async_get_current_platform().async_register_entity_service(
        "send_rich_notification", RICH_SCHEMA, "async_send_rich"
    )


class HawbNotify(HawbEntity, NotifyEntity):
    """Shows a Windows toast; the entity is ``notify.<pc>_notify``."""

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        payload: dict[str, Any] = {"message": message}
        if title:
            payload["title"] = title
        await self._command(json.dumps(payload))

    async def async_send_rich(self, **fields: Any) -> None:
        await self._command(json.dumps({k: v for k, v in fields.items() if v is not None}))
