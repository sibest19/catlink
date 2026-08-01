"""Config flow for CatLink integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    API_SERVERS,
    CONF_API_BASE,
    CONF_DEVICE_IDS,
    CONF_PHONE,
    CONF_PHONE_IAC,
    CONF_REGION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ERROR_INVALID_AUTH,
    REGION_AUTO,
    SUPPORTED_DEVICE_TYPES,
)
from .helpers import discover_region, parse_phone_number
from .modules.account import Account


def _device_label(dat: dict, supported: bool) -> str:
    """Build a human-readable label for a device."""
    name = dat.get("deviceName") or dat.get("model") or "Unknown"
    model = dat.get("model", "")
    device_type = dat.get("deviceType", "")
    suffix = "Supported" if supported else "Limited support"
    if model and model != name:
        return f"{name} ({model}) - {suffix}"
    return f"{name} ({device_type}) - {suffix}"


def _password_field() -> TextSelector:
    """Return a masked password input."""
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _region_field() -> SelectSelector:
    """Return the API region dropdown, including the auto-detect option."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[REGION_AUTO, *API_SERVERS],
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="region",
        )
    )


def _interval_field() -> NumberSelector:
    """Return the refresh interval input, in seconds."""
    return NumberSelector(
        NumberSelectorConfig(
            min=30,
            max=3600,
            step=30,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="s",
        )
    )


class CatlinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a CatLink config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> CatlinkOptionsFlowHandler:
        """Get the options flow for this handler."""
        return CatlinkOptionsFlowHandler()

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._account: Account | None = None
        self._config: dict[str, Any] = {}
        self._title = ""
        self._device_options: dict[str, str] = {}
        self._supported_ids: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether the account signs in with an email or a phone number."""
        return self.async_show_menu(step_id="user", menu_options=["email", "phone"])

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Perform reauth upon an authentication error.

        Go straight to the form matching how the entry was set up rather than
        asking the user to pick the sign-in method again.
        """
        if entry_data.get(CONF_EMAIL):
            return await self.async_step_email()
        return await self.async_step_phone()

    async def async_step_email(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle sign-in with an email address."""
        errors: dict[str, str] = {}
        defaults = self._reauth_defaults()

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            result = await self._async_validate_and_continue(
                {CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                region=user_input.get(CONF_REGION, REGION_AUTO),
                title=email,
            )
            if result is not None:
                return result
            errors["base"] = ERROR_INVALID_AUTH
            defaults = {
                CONF_EMAIL: email,
                CONF_REGION: user_input.get(CONF_REGION, REGION_AUTO),
            }

        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.EMAIL)),
                    vol.Required(CONF_PASSWORD): _password_field(),
                    vol.Optional(
                        CONF_REGION, default=defaults.get(CONF_REGION, REGION_AUTO)
                    ): _region_field(),
                }
            ),
            errors=errors,
        )

    async def async_step_phone(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle sign-in with a phone number."""
        errors: dict[str, str] = {}
        defaults = self._reauth_defaults()

        if user_input is not None:
            phone_raw = user_input[CONF_PHONE].strip()
            phone_iac, phone_number = parse_phone_number(phone_raw)
            result = await self._async_validate_and_continue(
                {
                    CONF_PHONE: phone_number,
                    CONF_PHONE_IAC: phone_iac,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                },
                region=user_input.get(CONF_REGION, REGION_AUTO),
                title=f"+{phone_iac}{phone_number}",
            )
            if result is not None:
                return result
            errors["base"] = ERROR_INVALID_AUTH
            defaults = {
                CONF_PHONE: phone_raw,
                CONF_REGION: user_input.get(CONF_REGION, REGION_AUTO),
            }

        return self.async_show_form(
            step_id="phone",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PHONE, default=defaults.get(CONF_PHONE, "")
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEL)),
                    vol.Required(CONF_PASSWORD): _password_field(),
                    vol.Optional(
                        CONF_REGION, default=defaults.get(CONF_REGION, REGION_AUTO)
                    ): _region_field(),
                }
            ),
            errors=errors,
        )

    def _reauth_defaults(self) -> dict[str, str]:
        """Pre-fill the sign-in form from the entry being re-authenticated."""
        if self.source != SOURCE_REAUTH:
            return {}
        data = self._get_reauth_entry().data
        piac = data.get(CONF_PHONE_IAC, "")
        pnum = data.get(CONF_PHONE, "")
        return {
            CONF_EMAIL: data.get(CONF_EMAIL, ""),
            CONF_PHONE: f"+{piac}{pnum}" if piac and pnum else "",
            CONF_REGION: data.get(CONF_REGION, REGION_AUTO),
        }

    async def _async_validate_and_continue(
        self,
        credentials: dict[str, Any],
        region: str,
        title: str,
    ) -> ConfigFlowResult | None:
        """Validate credentials and advance the flow.

        Returns None when the credentials were rejected, so the calling step
        can re-show its own form with an error.
        """
        resolved = await discover_region(
            self.hass, credentials, None if region == REGION_AUTO else region
        )
        if resolved is None:
            return None

        config = {
            CONF_API_BASE: API_SERVERS[resolved],
            CONF_REGION: resolved,
            **credentials,
        }
        account = Account(self.hass, config)
        await account.async_check_auth()
        self._account = account
        self._config = config
        self._title = title

        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data=config
            )

        # Claim the unique ID before creating anything, so an account with no
        # devices cannot be added twice.
        await self.async_set_unique_id(account.uid)
        self._abort_if_unique_id_configured()

        devices = await account.get_devices()
        if not devices:
            return self.async_create_entry(
                title=title,
                data=config,
                options={
                    CONF_DEVICE_IDS: [],
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                },
            )

        self._device_options = {}
        self._supported_ids = []
        for dat in devices:
            did = dat.get("id")
            if not did:
                continue
            supported = dat.get("deviceType", "") in SUPPORTED_DEVICE_TYPES
            self._device_options[did] = _device_label(dat, supported)
            if supported:
                self._supported_ids.append(did)

        return await self.async_step_discovery()

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the device discovery step."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._title,
                data=self._config,
                options={
                    CONF_DEVICE_IDS: user_input.get(CONF_DEVICE_IDS, []),
                    CONF_UPDATE_INTERVAL: user_input.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                },
            )

        supported_count = len(self._supported_ids)
        unsupported_count = len(self._device_options) - supported_count

        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE_IDS,
                        default=self._supported_ids,
                    ): cv.multi_select(self._device_options),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL,
                    ): _interval_field(),
                }
            ),
            description_placeholders={
                "supported_count": str(supported_count),
                "unsupported_count": str(unsupported_count),
                "total_count": str(len(self._device_options)),
            },
        )


class CatlinkOptionsFlowHandler(OptionsFlowWithReload):
    """Handle CatLink options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage device selection and refresh interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        account = Account(
            self.hass,
            {**dict(self.config_entry.data), **dict(self.config_entry.options or {})},
        )
        await account.async_check_auth()
        devices = await account.get_devices() or []

        device_options: dict[str, str] = {}
        supported_ids: list[str] = []
        for dat in devices:
            did = dat.get("id")
            if not did:
                continue
            supported = dat.get("deviceType", "") in SUPPORTED_DEVICE_TYPES
            device_options[did] = _device_label(dat, supported)
            if supported:
                supported_ids.append(did)

        # Treat an empty selection the same as an absent one: the entry may have
        # been created before any device was shared with the account.
        current_ids = self.config_entry.options.get(CONF_DEVICE_IDS)
        if not current_ids:
            current_ids = (
                supported_ids if supported_ids else list(device_options.keys())
            )

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE_IDS,
                        default=current_ids,
                    ): cv.multi_select(device_options),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current_interval,
                    ): _interval_field(),
                }
            ),
        )
