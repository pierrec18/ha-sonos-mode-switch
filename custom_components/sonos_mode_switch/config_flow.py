"""UI setup, options and standard token reauthentication."""

from __future__ import annotations

import hashlib

import probatio as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import ApiError, InvalidAuth, SonosApi, normalize_url
from .const import (
    CONF_POLL_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class SonosConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                token = user_input[CONF_TOKEN].strip()
                api = SonosApi(async_get_clientsession(self.hass), url, token)
                await api.status()
                await api.capabilities()
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(hashlib.sha256(url.encode()).hexdigest())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Sonos Mode Switch", data={CONF_URL: url, CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL): str,
                    vol.Required(vol.Secret(CONF_TOKEN)): TOKEN_SELECTOR,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            try:
                await SonosApi(
                    async_get_clientsession(self.hass), entry.data[CONF_URL], token
                ).status()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {vol.Required(vol.Secret(CONF_TOKEN)): TOKEN_SELECTOR}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SonosOptionsFlow()


class SonosOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=60))
                }
            ),
        )
