"""Config flow for Mnemolis Intents."""
from __future__ import annotations

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_MNEMOLIS_URL, DEFAULT_MNEMOLIS_URL


async def _test_connection(url: str) -> bool:
    """Test connection to Mnemolis."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False


class MnemolistConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Mnemolis Intents."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_MNEMOLIS_URL].rstrip("/")
            if await _test_connection(url):
                return self.async_create_entry(
                    title="Mnemolis Intents",
                    data={CONF_MNEMOLIS_URL: url},
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_MNEMOLIS_URL,
                    default=DEFAULT_MNEMOLIS_URL,
                ): str,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MnemolistOptionsFlow:
        return MnemolistOptionsFlow(config_entry)


class MnemolistOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Mnemolis Intents."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        current_url = self.config_entry.options.get(
            CONF_MNEMOLIS_URL,
            self.config_entry.data.get(CONF_MNEMOLIS_URL, DEFAULT_MNEMOLIS_URL),
        )

        if user_input is not None:
            url = user_input[CONF_MNEMOLIS_URL].rstrip("/")
            if await _test_connection(url):
                return self.async_create_entry(data={CONF_MNEMOLIS_URL: url})
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_MNEMOLIS_URL, default=current_url): str,
            }),
            errors=errors,
        )
