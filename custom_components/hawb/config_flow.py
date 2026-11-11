"""Config flow: zeroconf discovery or manual host, then a pairing code shown in HAWB's settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .client import CannotConnect, PairingFailed, async_hello, async_pair
from .const import CONF_DEVICE_ID, CONF_TOKEN, DEFAULT_PORT, DOMAIN

CODE_SCHEMA = vol.Schema({vol.Required("code"): str})


class HawbConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pair Home Assistant with one HAWB PC."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._device: dict[str, Any] = {}

    # -- entry points ---------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = user_input[CONF_PORT]
            try:
                self._device = await async_hello(async_get_clientsession(self.hass), self._host, self._port)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(self._device["id"])
                self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
                return await self.async_step_pair()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_PORT, default=DEFAULT_PORT): int}),
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        props = discovery_info.properties
        device_id = props.get("id")
        if not device_id:
            return self.async_abort(reason="not_hawb")
        self._host = discovery_info.host
        self._port = discovery_info.port or DEFAULT_PORT
        self._device = {"id": device_id, "name": props.get("name") or device_id, "version": props.get("version")}
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._host, CONF_PORT: self._port})
        self.context["title_placeholders"] = {"name": self._device["name"]}
        return await self.async_step_pair()

    # -- pairing --------------------------------------------------------------

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token, device = await async_pair(
                    async_get_clientsession(self.hass), self._host, self._port, user_input["code"].replace(" ", ""), "Home Assistant"
                )
            except PairingFailed:
                errors["base"] = "invalid_code"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=device["name"],
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_TOKEN: token,
                        CONF_DEVICE_ID: device["id"],
                        CONF_NAME: device["name"],
                    },
                )
        return self.async_show_form(
            step_id="pair",
            data_schema=CODE_SCHEMA,
            errors=errors,
            description_placeholders={"name": self._device.get("name", self._host)},
        )

    # -- re-authentication ----------------------------------------------------

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._host = entry_data[CONF_HOST]
        self._port = entry_data[CONF_PORT]
        self._device = {"id": entry_data[CONF_DEVICE_ID], "name": entry_data[CONF_NAME]}
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                token, device = await async_pair(
                    async_get_clientsession(self.hass), self._host, self._port, user_input["code"].replace(" ", ""), "Home Assistant"
                )
            except PairingFailed:
                errors["base"] = "invalid_code"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                if device["id"] != self._device["id"]:
                    return self.async_abort(reason="wrong_device")
                return self.async_update_reload_and_abort(self._get_reauth_entry(), data_updates={CONF_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=CODE_SCHEMA,
            errors=errors,
            description_placeholders={"name": self._device.get("name", self._host)},
        )
