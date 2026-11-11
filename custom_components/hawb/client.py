"""WebSocket client for the HAWB local API (protocol 1)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .const import PROTOCOL

_LOGGER = logging.getLogger(__name__)


class HawbError(Exception):
    """Base error."""


class CannotConnect(HawbError):
    """The PC could not be reached."""


class PairingFailed(HawbError):
    """Wrong or expired pairing code."""


class AuthFailed(HawbError):
    """The stored token is no longer accepted."""


def _url(host: str, port: int) -> str:
    return f"ws://{host}:{port}/"


async def async_pair(
    session: aiohttp.ClientSession, host: str, port: int, code: str, client_name: str
) -> tuple[str, dict[str, Any]]:
    """Exchange a pairing code for a token. Returns (token, device info)."""
    try:
        async with asyncio.timeout(15):
            async with session.ws_connect(_url(host, port)) as ws:
                hello = await ws.receive_json()
                if hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL:
                    raise CannotConnect("unsupported HAWB version")
                await ws.send_json({"type": "pair", "code": code, "client": client_name})
                msg = await ws.receive_json()
                if msg.get("type") != "paired":
                    raise PairingFailed(msg.get("message", "pairing refused"))
                return msg["token"], hello["device"]
    except (aiohttp.ClientError, TimeoutError, OSError) as err:
        raise CannotConnect(str(err)) from err


async def async_hello(session: aiohttp.ClientSession, host: str, port: int) -> dict[str, Any]:
    """Read the device info the PC announces before authentication."""
    try:
        async with asyncio.timeout(10):
            async with session.ws_connect(_url(host, port)) as ws:
                hello = await ws.receive_json()
                if hello.get("type") != "hello":
                    raise CannotConnect("not a HAWB agent")
                return hello["device"]
    except (aiohttp.ClientError, TimeoutError, OSError) as err:
        raise CannotConnect(str(err)) from err


class HawbClient:
    """Keeps one authenticated connection open and mirrors the PC's entities."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
        on_snapshot: Callable[[], None],
        on_update: Callable[[str], None],
        on_event: Callable[[str, dict[str, Any]], None],
        on_available: Callable[[bool], None],
        on_auth_failed: Callable[[], None],
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self._token = token
        self._on_snapshot = on_snapshot
        self._on_update = on_update
        self._on_event = on_event
        self._on_available = on_available
        self._on_auth_failed = on_auth_failed
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._task: asyncio.Task | None = None
        self.available = False
        self.version: str | None = None
        self.entities: dict[str, dict[str, Any]] = {}
        self.states: dict[str, str] = {}
        self.attrs: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws and not self._ws.closed:
            await self._ws.close()

    def update_address(self, host: str, port: int) -> None:
        """Called when zeroconf sees the PC at a new address; applied by reconnecting."""
        if (host, port) != (self.host, self.port):
            self.host, self.port = host, port
            if self._ws and not self._ws.closed:
                asyncio.create_task(self._ws.close())

    async def async_command(self, entity: str, payload: Any = "PRESS") -> None:
        if not self._ws or self._ws.closed or not self.available:
            raise HawbError("The PC is not connected")
        await self._ws.send_json({"type": "command", "entity": entity, "payload": payload})

    # ------------------------------------------------------------------ internals

    async def _run(self) -> None:
        backoff = 2
        while True:
            try:
                await self._session_once()
                backoff = 2
            except asyncio.CancelledError:
                raise
            except AuthFailed:
                _LOGGER.warning("HAWB at %s rejected our token; re-pairing is needed", self.host)
                self._set_available(False)
                self._on_auth_failed()
                return
            except (aiohttp.ClientError, TimeoutError, OSError, HawbError) as err:
                _LOGGER.debug("HAWB connection to %s lost: %s", self.host, err)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected HAWB error")
            self._set_available(False)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    def _set_available(self, value: bool) -> None:
        if self.available != value:
            self.available = value
            self._on_available(value)

    async def _session_once(self) -> None:
        async with self._session.ws_connect(_url(self.host, self.port), heartbeat=20) as ws:
            self._ws = ws
            hello = await asyncio.wait_for(ws.receive_json(), 10)
            if hello.get("type") != "hello" or hello.get("protocol") != PROTOCOL:
                raise HawbError("unsupported protocol")
            self.version = hello.get("device", {}).get("version")
            await ws.send_json({"type": "auth", "token": self._token})
            msg = await asyncio.wait_for(ws.receive_json(), 10)
            if msg.get("type") == "auth_error":
                raise AuthFailed
            if msg.get("type") != "auth_ok":
                raise HawbError("unexpected reply to auth")
            async for raw in ws:
                if raw.type == aiohttp.WSMsgType.TEXT:
                    self._handle(raw.json())
                elif raw.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.ERROR):
                    break

    def _handle(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind == "snapshot":
            self.entities = {e["id"]: e for e in msg["entities"]}
            self.states = dict(msg.get("states", {}))
            self.attrs = dict(msg.get("attrs", {}))
            self._on_snapshot()
            self._set_available(True)
        elif kind == "entities":
            self.entities = {e["id"]: e for e in msg["entities"]}
            self.states = {k: v for k, v in self.states.items() if k in self.entities}
            self.attrs = {k: v for k, v in self.attrs.items() if k in self.entities}
            self._on_snapshot()
        elif kind == "entity":
            self.entities[msg["entity"]["id"]] = msg["entity"]
            self._on_snapshot()
        elif kind == "state":
            self.states[msg["entity"]] = msg["value"]
            self._on_update(msg["entity"])
        elif kind == "attrs":
            self.attrs[msg["entity"]] = msg["value"]
            self._on_update(msg["entity"])
        elif kind == "event":
            self._on_event(msg["entity"], msg.get("value") or {})
