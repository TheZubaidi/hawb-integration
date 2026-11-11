"""The HAWB (Home Assistant Windows Buddy) integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .client import HawbClient
from .const import (
    CONF_DEVICE_ID,
    CONF_TOKEN,
    SIGNAL_AVAILABLE,
    SIGNAL_ENTITIES,
    SIGNAL_STATE,
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.MEDIA_PLAYER,
    Platform.NOTIFY,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]


def signal_event(entry_id: str) -> str:
    return f"hawb_event_{entry_id}"


@dataclass
class HawbData:
    """Runtime data of one config entry (one PC)."""

    client: HawbClient
    device_id: str
    name: str
    entry_id: str

    @property
    def sw_version(self) -> str | None:
        return self.client.version


type HawbConfigEntry = ConfigEntry[HawbData]


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry) -> bool:
    """Connect to the PC and set up the platforms."""
    entry_id = entry.entry_id

    @callback
    def on_snapshot() -> None:
        async_dispatcher_send(hass, SIGNAL_ENTITIES.format(entry_id=entry_id))

    @callback
    def on_update(entity: str) -> None:
        async_dispatcher_send(hass, SIGNAL_STATE.format(entry_id=entry_id), entity)

    @callback
    def on_event(entity: str, payload: dict[str, Any]) -> None:
        async_dispatcher_send(hass, signal_event(entry_id), entity, payload)

    @callback
    def on_available(_available: bool) -> None:
        async_dispatcher_send(hass, SIGNAL_AVAILABLE.format(entry_id=entry_id))

    @callback
    def on_auth_failed() -> None:
        entry.async_start_reauth(hass)

    client = HawbClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_TOKEN],
        on_snapshot,
        on_update,
        on_event,
        on_available,
        on_auth_failed,
    )
    entry.runtime_data = HawbData(client, entry.data[CONF_DEVICE_ID], entry.data[CONF_NAME], entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    client.start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HawbConfigEntry) -> bool:
    """Disconnect and unload."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.stop()
    return unloaded
