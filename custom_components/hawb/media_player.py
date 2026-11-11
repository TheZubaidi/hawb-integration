"""A real media_player for the PC, built from HAWB's media, volume and audio entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HawbConfigEntry, HawbData
from .const import SIGNAL_ENTITIES
from .entity import HawbEntity

# PC entities the player is composed from.
SOURCES = {"media_state", "now_playing", "volume", "muted"}


async def async_setup_entry(hass: HomeAssistant, entry: HawbConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = entry.runtime_data
    created = False

    @callback
    def sync() -> None:
        nonlocal created
        # Only worth having once the PC publishes something to play or control.
        if not created and "media_state" in data.client.entities:
            created = True
            async_add_entities([HawbMediaPlayer(data)])

    sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_ENTITIES.format(entry_id=entry.entry_id), sync))


class HawbMediaPlayer(HawbEntity, MediaPlayerEntity):
    _attr_name = None  # the device name

    def __init__(self, data: HawbData) -> None:
        super().__init__(data, "media_player")

    def _related(self) -> set[str]:
        return SOURCES

    def _exists(self) -> bool:
        return "media_state" in self._data.client.entities

    def _has(self, entity: str) -> bool:
        return entity in self._data.client.entities

    @property
    def name(self) -> str | None:
        return None

    @property
    def icon(self) -> str | None:
        return "mdi:laptop"

    @property
    def entity_category(self) -> None:
        return None

    @property
    def entity_registry_enabled_default(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return self._data.client.available

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        f = MediaPlayerEntityFeature(0)
        if self._has("media_play_pause"):
            f |= MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE
        if self._has("media_next"):
            f |= MediaPlayerEntityFeature.NEXT_TRACK
        if self._has("media_previous"):
            f |= MediaPlayerEntityFeature.PREVIOUS_TRACK
        if self._has("volume"):
            f |= MediaPlayerEntityFeature.VOLUME_SET | MediaPlayerEntityFeature.VOLUME_STEP
        if self._has("muted"):
            f |= MediaPlayerEntityFeature.VOLUME_MUTE
        if self._has("play_url"):
            f |= MediaPlayerEntityFeature.PLAY_MEDIA | MediaPlayerEntityFeature.BROWSE_MEDIA
        if self._has("stop_audio"):
            f |= MediaPlayerEntityFeature.STOP
        return f

    # -- state ----------------------------------------------------------------

    def _state_of(self, entity: str) -> str | None:
        value = self._data.client.states.get(entity)
        return None if value in (None, "", "None", "unknown") else value

    @property
    def state(self) -> MediaPlayerState:
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "buffering": MediaPlayerState.BUFFERING,
        }.get(self._state_of("media_state") or "idle", MediaPlayerState.IDLE)

    def _attrs(self) -> dict[str, Any]:
        return self._data.client.attrs.get("now_playing") or {}

    @property
    def media_title(self) -> str | None:
        return self._attrs().get("title") or None

    @property
    def media_artist(self) -> str | None:
        return self._attrs().get("artist") or None

    @property
    def media_album_name(self) -> str | None:
        return self._attrs().get("album") or None

    @property
    def app_name(self) -> str | None:
        return self._attrs().get("app") or None

    @property
    def volume_level(self) -> float | None:
        v = self._state_of("volume")
        try:
            return None if v is None else float(v) / 100
        except ValueError:
            return None

    @property
    def is_volume_muted(self) -> bool | None:
        v = self._state_of("muted")
        return None if v is None else v == "ON"

    # -- commands -------------------------------------------------------------

    async def async_media_play(self) -> None:
        if self.state != MediaPlayerState.PLAYING:
            await self._command("PRESS", "media_play_pause")

    async def async_media_pause(self) -> None:
        if self.state == MediaPlayerState.PLAYING:
            await self._command("PRESS", "media_play_pause")

    async def async_media_play_pause(self) -> None:
        await self._command("PRESS", "media_play_pause")

    async def async_media_next_track(self) -> None:
        await self._command("PRESS", "media_next")

    async def async_media_previous_track(self) -> None:
        await self._command("PRESS", "media_previous")

    async def async_media_stop(self) -> None:
        await self._command("PRESS", "stop_audio")

    async def async_set_volume_level(self, volume: float) -> None:
        await self._command(str(round(volume * 100)), "volume")

    async def async_volume_up(self) -> None:
        await self._step_volume(+5)

    async def async_volume_down(self) -> None:
        await self._step_volume(-5)

    async def _step_volume(self, delta: int) -> None:
        current = self.volume_level
        level = max(0, min(100, round((current or 0) * 100) + delta))
        await self._command(str(level), "volume")

    async def async_mute_volume(self, mute: bool) -> None:
        await self._command("ON" if mute else "OFF", "muted")

    async def async_play_media(self, media_type: MediaType | str, media_id: str, **kwargs: Any) -> None:
        if media_source.is_media_source_id(media_id):
            resolved = await media_source.async_resolve_media(self.hass, media_id, self.entity_id)
            media_id = async_process_play_media_url(self.hass, resolved.url)
        elif media_id.startswith("/"):
            media_id = async_process_play_media_url(self.hass, media_id)
        await self._command(media_id, "play_url")

    async def async_browse_media(self, media_content_type: str | None = None, media_content_id: str | None = None) -> Any:
        return await media_source.async_browse_media(
            self.hass, media_content_id, content_filter=lambda item: item.media_content_type.startswith("audio/")
        )
