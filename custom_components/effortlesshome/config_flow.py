"""Config flow for EffortlessHome integration."""

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .auth_helper import safe_api_call
from .oasira import OasiraAPIClient, OasiraAPIError
from .const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SYSTEM_ID = "system_id"
CONF_CUSTOMER_ID = "customer_id"
CONF_FIREBASE_UID = "firebase_uid"
CONF_ID_TOKEN = "id_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_HA_URL = "ha_url"
CONF_HA_TOKEN = "ha_token"
CONF_ALARM_PIN = "alarm_pin"
CONF_ADDRESS = "address"
CREATE_NEW_SYSTEM = "Create a new system"

OPTION_ADDRESS = "system_address"
OPTION_PHOTO_URL = "system_photo_url"
OPTION_HA_TOKEN = "system_ha_token"
OPTION_ALARM_PIN = "system_alarm_pin"
OPTION_HISTORY_DAYS = "system_history_days"
OPTION_LOW_TEMP = "system_low_temp"
OPTION_HIGH_TEMP = "system_high_temp"
OPTION_LOW_HUMIDITY = "system_low_humidity"
OPTION_HIGH_HUMIDITY = "system_high_humidity"
OPTION_GUEST_PERMISSIONS = "system_guest_permissions"

GUEST_PERMISSION_DOMAINS = (
    "alarm_control_panel",
    "automation",
    "camera",
    "climate",
    "cover",
    "device_tracker",
    "group",
    "lock",
    "light",
    "media_player",
    "script",
    "switch",
    "vacuum",
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the EffortlessHome integration setup with Firebase OAuth."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""
        self._firebase_uid = None
        self._id_token = None
        self._refresh_token = None
        self._email = None
        self._customer_id = None
        self._system_id = None
        self._available_systems = []
        self._system_creation_complete = False

    async def async_step_user(self, user_input: dict | None = None) -> Any:
        """Handle the initial step - collect email and password for Firebase auth."""
        errors = {}

        if user_input is not None:
            email = user_input.get(CONF_EMAIL)
            password = user_input.get(CONF_PASSWORD)

            if not email or not password:
                errors["base"] = "missing_fields"
            else:
                # Attempt Firebase authentication
                try:
                    auth_result = await self._authenticate_firebase(email, password)

                    if auth_result:
                        self._firebase_uid = auth_result["firebase_uid"]
                        self._id_token = auth_result["id_token"]
                        self._refresh_token = auth_result["refresh_token"]
                        self._email = email

                        # Fetch system list from API
                        try:
                            systems = await self._fetch_system_list(email)

                            if not systems:
                                _LOGGER.info(
                                    "No systems found for user %s; offering system creation",
                                    email,
                                )
                                return await self.async_step_create_system()
                            else:
                                # Let the user select an existing system or create one.
                                self._available_systems = systems
                                return await self.async_step_select_system()

                        except OasiraAPIError as err:
                            _LOGGER.error("Failed to fetch system list: %s", err)
                            errors["base"] = "cannot_connect"
                    else:
                        errors["base"] = "invalid_auth"

                except Exception as err:
                    _LOGGER.exception("Unexpected error during authentication: %s", err)
                    errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Enter your EffortlessHome account credentials to link your system."
            },
        )

    async def async_step_select_system(
        self, user_input: dict | None = None
    ) -> Any:
        """Handle selecting an existing system or creating a new one."""
        errors = {}

        if user_input is not None:
            selected_system_key = user_input.get(CONF_SYSTEM_ID)
            if selected_system_key == CREATE_NEW_SYSTEM:
                return await self.async_step_create_system()

            # Find the selected system
            selected_system = None
            for system in self._available_systems:
                system_key = f"{system['customer_id']}_{system['SystemID']}"
                if system_key == selected_system_key:
                    selected_system = system
                    break

            if selected_system:
                return await self._async_create_entry_for_system(selected_system)
            else:
                errors["base"] = "invalid_system"

        # Build system selection options
        system_options = {}
        for system in self._available_systems:
            system_key = f"{system['customer_id']}_{system['SystemID']}"
            ha_url = system.get("ha_url", "Unknown")
            system_options[system_key] = f"System {system['SystemID']} - {ha_url}"
        system_options[CREATE_NEW_SYSTEM] = CREATE_NEW_SYSTEM

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SYSTEM_ID): vol.In(system_options),
            }
        )

        return self.async_show_form(
            step_id="select_system",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Select a system to configure or create a new system."
            },
        )

    async def async_step_create_system(
        self, user_input: dict | None = None
    ) -> Any:
        """Create a new EffortlessHome system for the signed-in account."""
        errors = {}

        if user_input is not None:
            ha_url = user_input[CONF_HA_URL].strip()
            try:
                parsed_ha_url = urlsplit(ha_url)
                valid_ha_url = (
                    parsed_ha_url.scheme in {"http", "https"}
                    and parsed_ha_url.hostname is not None
                )
                if parsed_ha_url.port is not None:
                    valid_ha_url = valid_ha_url and 0 < parsed_ha_url.port < 65536
            except ValueError:
                valid_ha_url = False

            if not valid_ha_url:
                errors["base"] = "invalid_ha_url"

            if not errors and not self._system_creation_complete:
                system_data = {
                    "ha_url": ha_url.rstrip("/"),
                    "ha_token": user_input[CONF_HA_TOKEN],
                    "alarmpin": user_input[CONF_ALARM_PIN],
                    "cloudflare_token": "",
                    "ha_security_token": "",
                    "active": "1",
                    "systemphotolurl": user_input[OPTION_PHOTO_URL].strip(),
                    "testmode": "1",
                    "address_json": {
                        "address": OptionsFlowHandler._parse_system_address(
                            user_input.get(CONF_ADDRESS, "").strip()
                        )
                    },
                    "additional_contacts_json": [],
                    "instructions": "",
                    "ai_key": "",
                    "ai_model": "",
                    "influx_url": "",
                    "influx_token": "",
                    "influx_bucket": "",
                    "influx_org": "",
                    "DaysHistoryToKeep": str(user_input[OPTION_HISTORY_DAYS]),
                    "LowTemperatureWarning": str(user_input[OPTION_LOW_TEMP]),
                    "HighTemperatureWarning": str(user_input[OPTION_HIGH_TEMP]),
                    "LowHumidityWarning": str(user_input[OPTION_LOW_HUMIDITY]),
                    "HighHumidityWarning": str(user_input[OPTION_HIGH_HUMIDITY]),
                    "guestpermissions": (
                        f"[{', '.join(user_input[OPTION_GUEST_PERMISSIONS])}]"
                    ),
                }

                try:
                    async with OasiraAPIClient(id_token=self._id_token) as client:
                        customer = await client.get_customer_by_email(self._email)
                        customer_id = customer.get("id") or customer.get(
                            CONF_CUSTOMER_ID
                        )
                        if not customer_id:
                            raise OasiraAPIError(
                                "Could not resolve the EffortlessHome customer ID"
                            )
                        self._customer_id = str(customer_id)
                        result = await client.add_system(
                            self._customer_id, system_data
                        )
                    if result.get("success") is False:
                        raise OasiraAPIError(
                            result.get("message", "The system could not be created")
                        )
                    self._system_creation_complete = True
                except OasiraAPIError as err:
                    _LOGGER.error("Failed to create EffortlessHome system: %s", err)
                    errors["base"] = "system_creation_failed"
                except Exception:
                    _LOGGER.exception("Unexpected error creating EffortlessHome system")
                    errors["base"] = "unknown"

            if not errors:
                try:
                    systems = await self._fetch_system_list(self._email)
                    existing_system_keys = {
                        f"{system['customer_id']}_{system['SystemID']}"
                        for system in self._available_systems
                    }
                    new_systems = [
                        system
                        for system in systems
                        if f"{system['customer_id']}_{system['SystemID']}"
                        not in existing_system_keys
                    ]
                    if len(new_systems) == 1:
                        return await self._async_create_entry_for_system(
                            new_systems[0]
                        )
                    elif not systems:
                        errors["base"] = "system_not_available"
                    else:
                        self._available_systems = systems
                        return await self.async_step_select_system()
                except OasiraAPIError as err:
                    _LOGGER.error("Failed to fetch the newly created system: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception(
                        "Unexpected error fetching the newly created system"
                    )
                    errors["base"] = "unknown"

        form_data = user_input or {}
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HA_URL, default=form_data.get(CONF_HA_URL, "")
                ): str,
                vol.Required(
                    CONF_HA_TOKEN, default=form_data.get(CONF_HA_TOKEN, "")
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Required(
                    CONF_ALARM_PIN, default=form_data.get(CONF_ALARM_PIN, "1234")
                ): vol.Match(r"^\d{4}$"),
                vol.Optional(
                    CONF_ADDRESS, default=form_data.get(CONF_ADDRESS, "")
                ): str,
                vol.Required(
                    OPTION_PHOTO_URL,
                    default=form_data.get(
                        OPTION_PHOTO_URL,
                        "https://cdn-icons-png.flaticon.com/512/171/171532.png",
                    ),
                ): str,
                vol.Required(
                    OPTION_HISTORY_DAYS,
                    default=form_data.get(OPTION_HISTORY_DAYS, 30),
                ): int,
                vol.Required(
                    OPTION_LOW_TEMP, default=form_data.get(OPTION_LOW_TEMP, 65)
                ): int,
                vol.Required(
                    OPTION_HIGH_TEMP, default=form_data.get(OPTION_HIGH_TEMP, 80)
                ): int,
                vol.Required(
                    OPTION_LOW_HUMIDITY,
                    default=form_data.get(OPTION_LOW_HUMIDITY, 30),
                ): int,
                vol.Required(
                    OPTION_HIGH_HUMIDITY,
                    default=form_data.get(OPTION_HIGH_HUMIDITY, 60),
                ): int,
                vol.Required(
                    OPTION_GUEST_PERMISSIONS,
                    default=form_data.get(
                        OPTION_GUEST_PERMISSIONS, ["light", "climate", "lock"]
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": domain,
                                "label": domain.replace("_", " ").title(),
                            }
                            for domain in GUEST_PERMISSION_DOMAINS
                        ],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="create_system",
            data_schema=data_schema,
            errors=errors,
        )

    async def _async_create_entry_for_system(
        self, system: dict[str, Any]
    ) -> FlowResult:
        """Create a config entry from an EffortlessHome system record."""
        self._customer_id = str(system["customer_id"])
        self._system_id = str(system["SystemID"])
        await self.async_set_unique_id(f"{self._customer_id}_{self._system_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"{NAME} ({self._email})",
            data={
                CONF_EMAIL: self._email,
                CONF_FIREBASE_UID: self._firebase_uid,
                CONF_ID_TOKEN: self._id_token,
                CONF_REFRESH_TOKEN: self._refresh_token,
                CONF_CUSTOMER_ID: self._customer_id,
                CONF_SYSTEM_ID: self._system_id,
            },
        )

    async def async_step_manual_entry(
        self, user_input: dict | None = None
    ) -> Any:
        """Handle manual entry of customer_id and system_id if API lookup fails."""
        errors = {}

        if user_input is not None:
            customer_id = user_input.get(CONF_CUSTOMER_ID)
            system_id = user_input.get(CONF_SYSTEM_ID)

            if not customer_id or not system_id:
                errors["base"] = "missing_fields"
            else:
                # Store the manually entered IDs
                self._customer_id = customer_id
                self._system_id = system_id

                # Check if already configured
                await self.async_set_unique_id(f"{self._customer_id}_{self._system_id}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"{NAME} ({self._email})",
                    data={
                        CONF_EMAIL: self._email,
                        CONF_FIREBASE_UID: self._firebase_uid,
                        CONF_ID_TOKEN: self._id_token,
                        CONF_REFRESH_TOKEN: self._refresh_token,
                        CONF_CUSTOMER_ID: self._customer_id,
                        CONF_SYSTEM_ID: self._system_id,
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CUSTOMER_ID): str,
                vol.Required(CONF_SYSTEM_ID): str,
            }
        )

        return self.async_show_form(
            step_id="manual_entry",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "info": "Enter your Customer ID and System ID to complete setup."
            },
        )

    async def _authenticate_firebase(
        self, email: str, password: str
    ) -> dict[str, Any] | None:
        """Authenticate with Firebase and return user credentials.

        Args:
            email: User's email
            password: User's password

        Returns:
            Dictionary with firebase_uid and id_token, or None if authentication fails
        """
        try:
            async with OasiraAPIClient() as client:
                data = await client.firebase_sign_in(email, password)

                # Validate that we got the required tokens
                firebase_uid = data.get("localId")
                id_token = data.get("idToken")
                refresh_token = data.get("refreshToken")

                if not firebase_uid or not id_token or not refresh_token:
                    _LOGGER.error("Firebase auth response is missing required tokens")
                    return None

                return {
                    "firebase_uid": firebase_uid,
                    "id_token": id_token,
                    "refresh_token": refresh_token,
                }
        except OasiraAPIError as err:
            _LOGGER.error("Firebase auth error: %s", err)
            return None
        except Exception as err:
            _LOGGER.exception("Error calling Firebase auth API: %s", err)
            return None

    async def _fetch_system_list(self, email: str) -> list[dict[str, Any]]:
        """Fetch list of systems for the user from EffortlessHome API.

        Args:
            email: User's email address

        Returns:
            List of system dictionaries, each containing SystemID, customer_id, ha_url, etc.
        """
        _LOGGER.debug("Fetching system list for email %s", email)

        if not self._id_token:
            _LOGGER.error("Cannot fetch system list: id_token is not set")
            raise OasiraAPIError("Authentication token is missing")

        try:
            async with OasiraAPIClient(id_token=self._id_token) as client:
                systems = await client.get_system_list_by_email(email)
                _LOGGER.info("Found %d system(s) for email %s", len(systems), email)
                return systems
        except OasiraAPIError as err:
            _LOGGER.exception("Failed to fetch system list: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching system list: %s", err)
            raise OasiraAPIError(f"Unexpected error: {err}") from err

    async def async_step_reauth(self, user_input=None):
        """Handle reauth by replacing the saved Firebase credentials."""
        errors = {}
        entry = None
        entry_id = self.context.get("entry_id")
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)

        if user_input is not None:
            email = user_input.get(CONF_EMAIL)
            password = user_input.get(CONF_PASSWORD)
            if not email or not password:
                errors["base"] = "missing_fields"
            else:
                auth_result = await self._authenticate_firebase(email, password)
                if auth_result and entry is not None:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_EMAIL: email,
                            CONF_FIREBASE_UID: auth_result["firebase_uid"],
                            CONF_ID_TOKEN: auth_result["id_token"],
                            CONF_REFRESH_TOKEN: auth_result["refresh_token"],
                        },
                    )
                    return self.async_abort(reason="reauth_successful")
                errors["base"] = "invalid_auth"

        default_email = entry.data.get(CONF_EMAIL, "") if entry else ""
        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=default_email): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "info": "Enter your EffortlessHome account credentials to reauthenticate."
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for EffortlessHome."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry
        self._system_data: dict[str, Any] = {}

    async def async_step_init(self, user_input=None):
        """Load and update EffortlessHome system settings."""
        if user_input is not None:
            alarm_pin = str(user_input[OPTION_ALARM_PIN]).strip()
            if len(alarm_pin) != 4 or not alarm_pin.isdigit():
                return self._show_settings_form(
                    user_input, errors={"base": "invalid_alarm_pin"}
                )

            system_data = {
                "ha_url": self._system_data.get("ha_url", ""),
                "testmode": self._system_data.get("testmode", "1"),
                "address_json": {
                    "address": self._parse_system_address(
                        user_input[OPTION_ADDRESS].strip()
                    )
                },
                "systemphotolurl": user_input[OPTION_PHOTO_URL].strip(),
                "alarmpin": alarm_pin,
                "DaysHistoryToKeep": str(user_input[OPTION_HISTORY_DAYS]),
                "LowTemperatureWarning": str(user_input[OPTION_LOW_TEMP]),
                "HighTemperatureWarning": str(user_input[OPTION_HIGH_TEMP]),
                "LowHumidityWarning": str(user_input[OPTION_LOW_HUMIDITY]),
                "HighHumidityWarning": str(user_input[OPTION_HIGH_HUMIDITY]),
                "guestpermissions": (
                    f"[{', '.join(user_input[OPTION_GUEST_PERMISSIONS])}]"
                ),
            }
            ha_token = user_input.get(OPTION_HA_TOKEN, "").strip()
            if ha_token:
                system_data["ha_token"] = ha_token

            try:
                await safe_api_call(
                    self.hass,
                    self._config_entry,
                    self._async_update_system,
                    system_data,
                )
            except OasiraAPIError as err:
                _LOGGER.error("Failed to update EffortlessHome system settings: %s", err)
                return self._show_settings_form(
                    user_input, errors={"base": "cannot_connect"}
                )
            except Exception:
                _LOGGER.exception("Unexpected error updating EffortlessHome system settings")
                return self._show_settings_form(
                    user_input, errors={"base": "unknown"}
                )

            return self.async_create_entry(
                title="",
                data={
                    "debug_mode": user_input.get(
                        "debug_mode",
                        self._config_entry.options.get("debug_mode", False),
                    ),
                    "system_settings_updated_at": int(time.time()),
                },
            )

        try:
            self._system_data = await safe_api_call(
                self.hass,
                self._config_entry,
                self._async_fetch_system,
            )
        except OasiraAPIError as err:
            _LOGGER.error("Failed to load EffortlessHome system settings: %s", err)
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error loading EffortlessHome system settings")
            return self.async_abort(reason="unknown")

        return self._show_settings_form()

    async def _async_fetch_system(self) -> dict[str, Any]:
        """Fetch the configured system from the customer's full system list."""
        id_token = self.hass.data.get(DOMAIN, {}).get("id_token") or self._config_entry.data.get(
            CONF_ID_TOKEN
        )
        async with OasiraAPIClient(
            id_token=id_token,
        ) as client:
            systems = await client.get_systems_by_customer_id(
                self._config_entry.data[CONF_CUSTOMER_ID]
            )

        configured_system_id = str(self._config_entry.data[CONF_SYSTEM_ID])
        for system in systems:
            system_id = system.get(
                "id_new",
                system.get("SystemID", system.get("system_id")),
            )
            if system_id is not None and str(system_id) == configured_system_id:
                return system

        raise OasiraAPIError(
            f"System {configured_system_id} was not found in the account's system list"
        )

    async def _async_update_system(self, system_data: dict[str, Any]) -> None:
        """Update system settings using the current Firebase token."""
        id_token = self.hass.data.get(DOMAIN, {}).get("id_token") or self._config_entry.data.get(
            CONF_ID_TOKEN
        )
        async with OasiraAPIClient(
            system_id=self._config_entry.data[CONF_SYSTEM_ID],
            id_token=id_token,
        ) as client:
            response = await client.update_system(
                self._config_entry.data[CONF_CUSTOMER_ID], system_data
            )
        if response.get("success") is False:
            raise OasiraAPIError(
                response.get("message", "Unable to update system settings")
            )

    def _show_settings_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> FlowResult:
        """Build the system settings form with current or submitted values."""
        form_data = user_input or {}
        address = self._get_system_address(self._system_data)
        guest_permissions = self._get_guest_permissions(self._system_data)
        schema = vol.Schema(
            {
                vol.Optional(
                    "debug_mode",
                    default=form_data.get(
                        "debug_mode",
                        self._config_entry.options.get("debug_mode", False),
                    ),
                ): bool,
                vol.Required(
                    OPTION_ADDRESS,
                    default=form_data.get(OPTION_ADDRESS, address),
                ): str,
                vol.Required(
                    OPTION_PHOTO_URL,
                    default=form_data.get(
                        OPTION_PHOTO_URL,
                        self._system_data.get("systemphotolurl", ""),
                    ),
                ): str,
                vol.Optional(OPTION_HA_TOKEN, default=""): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Required(
                    OPTION_ALARM_PIN,
                    default=form_data.get(
                        OPTION_ALARM_PIN, str(self._system_data.get("alarmpin", ""))
                    ),
                ): str,
                vol.Required(
                    OPTION_HISTORY_DAYS,
                    default=form_data.get(
                        OPTION_HISTORY_DAYS,
                        self._get_integer(self._system_data, "DaysHistoryToKeep", 30),
                    ),
                ): int,
                vol.Required(
                    OPTION_LOW_TEMP,
                    default=form_data.get(
                        OPTION_LOW_TEMP,
                        self._get_integer(
                            self._system_data, "LowTemperatureWarning", 65
                        ),
                    ),
                ): int,
                vol.Required(
                    OPTION_HIGH_TEMP,
                    default=form_data.get(
                        OPTION_HIGH_TEMP,
                        self._get_integer(
                            self._system_data, "HighTemperatureWarning", 80
                        ),
                    ),
                ): int,
                vol.Required(
                    OPTION_LOW_HUMIDITY,
                    default=form_data.get(
                        OPTION_LOW_HUMIDITY,
                        self._get_integer(
                            self._system_data, "LowHumidityWarning", 30
                        ),
                    ),
                ): int,
                vol.Required(
                    OPTION_HIGH_HUMIDITY,
                    default=form_data.get(
                        OPTION_HIGH_HUMIDITY,
                        self._get_integer(
                            self._system_data, "HighHumidityWarning", 60
                        ),
                    ),
                ): int,
                vol.Required(
                    OPTION_GUEST_PERMISSIONS,
                    default=form_data.get(OPTION_GUEST_PERMISSIONS, guest_permissions),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": domain,
                                "label": domain.replace("_", " ").title(),
                            }
                            for domain in GUEST_PERMISSION_DOMAINS
                        ],
                        multiple=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors or {},
            description_placeholders={
                "system_id": str(self._config_entry.data[CONF_SYSTEM_ID]),
                "ha_url": str(self._system_data.get("ha_url", "")),
            },
        )

    @staticmethod
    def _get_system_address(system: dict[str, Any]) -> str:
        """Convert API address data into the editable address field."""
        address = system.get("address_json") or system.get("address") or ""
        if isinstance(address, str):
            try:
                address = json.loads(address)
            except json.JSONDecodeError:
                return address
        if isinstance(address, dict):
            address = address.get("address", address)
        if isinstance(address, dict):
            return ", ".join(
                str(address[key])
                for key in ("line1", "line2", "city", "state", "zip")
                if address.get(key)
            )
        return str(address or "")

    @staticmethod
    def _get_guest_permissions(system: dict[str, Any]) -> list[str]:
        """Normalize stored guest permission formats for the selector."""
        permissions = system.get("guestpermissions") or [
            "light",
            "climate",
            "lock",
        ]
        if isinstance(permissions, str):
            try:
                parsed = json.loads(permissions)
            except json.JSONDecodeError:
                parsed = permissions.strip().strip("[]").split(",")
            permissions = parsed
        if isinstance(permissions, list):
            return [
                str(permission).strip()
                for permission in permissions
                if str(permission).strip() in GUEST_PERMISSION_DOMAINS
            ]
        return ["light", "climate", "lock"]

    @staticmethod
    def _parse_system_address(full_address: str) -> dict[str, str]:
        """Convert the editable address into the API's address object."""
        components = [part.strip() for part in full_address.split(",")]
        address = {"line1": "", "line2": "", "city": "", "state": "", "zip": ""}
        if len(components) < 3:
            address["line1"] = full_address
            return address

        state_zip = components.pop()
        address["city"] = components.pop()
        address["line1"] = ", ".join(components)
        state_zip_match = re.search(
            r"\b([A-Z]{2})\b\s+(\d{5}(?:-\d{4})?)$", state_zip
        )
        if state_zip_match:
            address["state"] = state_zip_match.group(1)
            address["zip"] = state_zip_match.group(2)
        else:
            address["city"] = f"{address['city']}, {state_zip}"
        return address

    @staticmethod
    def _get_integer(system: dict[str, Any], key: str, default: int) -> int:
        """Convert an API setting to an integer with a documented default."""
        try:
            return int(system.get(key, default))
        except (TypeError, ValueError):
            return default
