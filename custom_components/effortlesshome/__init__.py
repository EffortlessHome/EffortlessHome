"""EffortlessHome integration."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import shutil
import subprocess
import time
from urllib.parse import quote

from google.auth import jwt
from google.auth.crypt import rsa
import voluptuous as vol
from .oasira import OasiraAPIClient, OasiraAPIError

from homeassistant.components import webhook
from homeassistant.components.notify import BaseNotificationService
from homeassistant.components.persistent_notification import create as notify_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    storage,
    label_registry as lr,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .alarm_common import (
    async_cancelalarm,
    async_confirmpendingalarm,
    async_getalarmstatus,
)
from .auto_area import AutoArea
from .auth_helper import (
    ensure_valid_id_token,
    refresh_firebase_id_token,
    safe_api_call,
)
from .const import (
    DOMAIN,
    LABELS,
    NAME,
    SUPERVISOR_ADDON_REPOSITORY,
    SUPERVISOR_ADDON_SLUG,
)
from .deviceclassgroupsync import async_setup_devicegroup
from .MotionSensorGrouper import MotionSensorGrouper
from .SecurityAlarmWebhook import SecurityAlarmWebhook, async_remove as security_async_remove
from .virtualpowersensor import VirtualPowerSensor

try:
    # Older versions (pre-2025)
    from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
except (ImportError, AttributeError, Exception):
    # Newer versions (2025+) or attribute not found
    SOURCE_TYPE_GPS = "gps"

from aiohttp import web
import aiohttp

ATTR_TITLE = "title"
ATTR_DATA = "data"

LOCATION_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("latitude"): float,
        vol.Required("longitude"): float,
        vol.Optional("accuracy"): float,
    }
)

_LOGGER = logging.getLogger(__name__)

GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/token"
FIREBASE_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_URL = "https://fcm.googleapis.com/v1/projects/oasira-oauth/messages:send"
PUSH_TOKEN_STORAGE_KEY = "effortlesshome_push_tokens"
PUSH_TOKEN_STORAGE_VERSION = 1
class HASSComponent:
    """Hasscomponent."""

    # Class-level property to hold the hass instance
    hass_instance = None

    @classmethod
    def set_hass(cls, hass: HomeAssistant) -> None:
        """Set Hass."""
        cls.hass_instance = hass

    @classmethod
    def get_hass(cls):
        """Get Hass."""
        return cls.hass_instance


class EffortlessHomeNotificationService(BaseNotificationService):
    """EffortlessHome notification service for all registered devices."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the service."""
        self.hass = hass

    async def async_send_message(self, message: str = "", **kwargs):
        """Send a notification message to all registered devices."""
        title = kwargs.get(ATTR_TITLE, "EffortlessHome")
        data = kwargs.get(ATTR_DATA, {})
        persistent_message = self._build_persistent_markdown(message, data)
        notify_create(self.hass, persistent_message, title=title)

        await self._send_fcm_notification(message, title, data)

    def _build_persistent_markdown(self, message: str, data: dict) -> str:
        if not data:
            return message

        lines = [message] if message else []

        links = []
        images = []
        extra_items = []

        for key, value in data.items():
            if value is None:
                continue

            key_str = str(key)
            value_str = (
                json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            )

            if key_str in {"url", "link"}:
                links.append(value_str)
                continue

            if key_str in {"image", "image_url", "photo", "photo_url"}:
                resolved = self._resolve_image_url(value_str, full_url=False)
                if resolved:
                    images.append(resolved)
                continue

            extra_items.append((key_str, value_str))

        compact_parts = []
        if links:
            compact_parts.append(
                "Links: "
                + " | ".join(f"[Link {i + 1}]({link})" for i, link in enumerate(links))
            )

        if images:
            # Always show images in persistent notifications
            for i, image in enumerate(images):
                lines.append(f"![Image {i + 1}]({image})")

        if extra_items:
            compact_parts.append(
                "Data: "
                + "; ".join(
                    f"`{key_str}`={value_str}" for key_str, value_str in extra_items
                )
            )

        if compact_parts:
            lines.append("\n" + " | ".join(compact_parts))

        return "\n".join(lines)

    async def _send_fcm_notification(
        self, message: str, title: str, data: dict
    ) -> None:
        tokens = self.hass.data.get(DOMAIN, {}).get("notification_tokens", [])
        if not tokens:
            _LOGGER.warning("No registered notification tokens")
            return

        access_token, project_id = await self._get_firebase_access_token()
        if not access_token or not project_id:
            _LOGGER.error("Unable to get Firebase access token")
            return

        fcm_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        _LOGGER.info("[EffortlessHome] Using FCM project: %s", project_id)

        session = async_get_clientsession(self.hass)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        image_url = None
        payload_data = None
        if data:
            payload_data = {}
            for k, v in data.items():
                key_str = str(k)
                value_str = str(v)
                if key_str in {"image", "image_url", "photo", "photo_url"}:
                    resolved = self._resolve_image_url(value_str, full_url=True)
                    if resolved:
                        value_str = resolved
                        if not image_url:
                            image_url = resolved
                payload_data[key_str] = value_str

        for token in tokens:
            payload = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": message},
                }
            }
            if payload_data:
                payload["message"]["data"] = payload_data

            if image_url:
                # Enhanced image handling for better native notification support
                payload["message"]["notification"]["image"] = image_url
                payload["message"]["android"] = {
                    "notification": {
                        "image": image_url,
                        "icon": "ic_stat_ic_notification",
                        "color": "#007bff",
                    }
                }
                payload["message"]["apns"] = {
                    "payload": {
                        "aps": {
                            "alert": {"title": title, "body": message},
                            "mutable-content": 1,
                        },
                        "image_url": image_url,
                    }
                }
                # Add webpush for web notifications
                payload["message"]["webpush"] = {
                    "notification": {
                        "image": image_url,
                        "icon": "/local/effortlesshome/user.png",
                    }
                }

            try:
                async with session.post(fcm_url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        _LOGGER.error("FCM push failed: %s", text)
                        # Check for UNREGISTERED token and remove it
                        try:
                            error_data = json.loads(text)
                            if (
                                error_data.get("error", {}).get("details") and
                                any(
                                    detail.get("errorCode") == "UNREGISTERED"
                                    for detail in error_data["error"]["details"]
                                    if detail.get("@type") == "type.googleapis.com/google.firebase.fcm.v1.FcmError"
                                )
                            ):
                                _LOGGER.warning("Removing unregistered FCM token: %s", token[:20] + "...")
                                domain_data = self.hass.data.get(DOMAIN, {})
                                tokens_list = domain_data.get("notification_tokens", [])
                                if token in tokens_list:
                                    tokens_list.remove(token)
                                    token_store = domain_data.get("token_store")
                                    if token_store is not None:
                                        await token_store.async_save(tokens_list)
                        except json.JSONDecodeError:
                            pass  # Not JSON, ignore
                    else:
                        _LOGGER.info(
                            "FCM push successful for token: %s", token[:20] + "..."
                        )
            except Exception as exc:
                _LOGGER.error("FCM push error: %s", exc)

    def _resolve_image_url(
        self, image_url: str | None, full_url: bool = True
    ) -> str | None:
        if not image_url:
            return None

        # Add cache buster to ensure latest image is always fetched
        cache_buster = f"v={int(time.time())}"

        if image_url.startswith(("http://", "https://")):
            separator = "&" if "?" in image_url else "?"
            return f"{image_url}{separator}{cache_buster}"

        # Handle local file paths
        clean_path = image_url.lstrip("/")

        # Handle existing query strings in local paths
        if "?" in clean_path:
            base_path, query = clean_path.split("?", 1)
            encoded_path = f"{quote(base_path, safe='/')}?{query}"
            path_with_buster = f"{encoded_path}&{cache_buster}"
        else:
            encoded_path = quote(clean_path, safe="/")
            path_with_buster = f"{encoded_path}?{cache_buster}"

        if full_url:
            ha_url = self.hass.data.get(DOMAIN, {}).get("ha_url", "")
            if ha_url:
                # Ensure no double slashes when joining
                return f"{ha_url.rstrip('/')}/{path_with_buster}"

        # Return as absolute path for local use (e.g. persistent notifications)
        return f"/{path_with_buster}"

    async def _get_firebase_access_token(self) -> tuple[str | None, str | None]:
        try:
            id_token = self.hass.data.get(DOMAIN, {}).get("id_token")
            if not id_token:
                _LOGGER.error("Missing id_token for Firebase access")
                return None, None

            async with OasiraAPIClient(id_token=id_token) as client:
                firebase_config = await client.get_firebase_config()

            google_firebase_raw = (
                firebase_config.get("Google_Firebase") if firebase_config else None
            )
            if not google_firebase_raw:
                _LOGGER.error("Missing Google_Firebase config from Oasira")
                return None, None

            service_account_info = json.loads(google_firebase_raw)
            private_key = service_account_info["private_key"]
            client_email = service_account_info["client_email"]
            project_id = service_account_info.get("project_id")
            if not project_id:
                _LOGGER.error("Missing project_id in Firebase service account")
                return None, None

            now = int(time.time())
            payload = {
                "iss": client_email,
                "scope": FIREBASE_SCOPE,
                "aud": GOOGLE_OAUTH_URL,
                "iat": now,
                "exp": now + 3600,
            }

            signer = rsa.RSASigner.from_string(private_key)
            assertion = jwt.encode(signer, payload)

            session = async_get_clientsession(self.hass)
            async with session.post(
                GOOGLE_OAUTH_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": assertion,
                },
            ) as resp:
                result = await resp.json()
                if "access_token" not in result:
                    _LOGGER.error("Firebase OAuth error: %s", result)
                    return None, None

                return result["access_token"], project_id
        except OasiraAPIError as exc:
            _LOGGER.error("Failed to fetch Firebase config: %s", exc)
            return None, None
        except Exception as exc:
            _LOGGER.exception("Failed to refresh Firebase access token: %s", exc)
            return None, None


async def async_setup_notification_platform(hass: HomeAssistant):
    """Set up the EffortlessHome notification platform."""
    try:
        service = EffortlessHomeNotificationService(hass)

        async def handle_notify_service(call: ServiceCall) -> None:
            """Handle notify.effortlesshome service calls."""
            message = call.data.get("message", "")
            title = call.data.get("title")
            data = call.data.get("data")

            kwargs = {}
            if title is not None:
                kwargs[ATTR_TITLE] = title
            if data is not None:
                kwargs[ATTR_DATA] = data

            await service.async_send_message(message=message, **kwargs)

        # Register the notification service
        hass.services.async_register(
            "notify",
            "effortlesshome",
            handle_notify_service,
            schema=vol.Schema(
                {
                    vol.Required("message"): cv.string,
                    vol.Optional("title"): cv.string,
                    vol.Optional("data"): dict,
                }
            ),
        )

        _LOGGER.info(
            "✅ EffortlessHome notification service registered: notify.effortlesshome"
        )
        return True

    except Exception as e:
        _LOGGER.error(f"Failed to setup notification platform: {e}", exc_info=True)
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry_id"] = entry.entry_id
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    token_store: Store = storage.Store(
        hass, PUSH_TOKEN_STORAGE_VERSION, PUSH_TOKEN_STORAGE_KEY
    )
    hass.data[DOMAIN]["token_store"] = token_store
    stored_tokens = await token_store.async_load() or []
    hass.data[DOMAIN]["notification_tokens"] = list(dict.fromkeys(stored_tokens))

    system_id = entry.data["system_id"]
    customer_id = entry.data["customer_id"]
    id_token = entry.data.get("id_token")
    refresh_token = entry.data.get("refresh_token")

    if not system_id:
        raise HomeAssistantError("System ID is missing in configuration.")

    if not customer_id:
        raise HomeAssistantError("Customer ID is missing in configuration.")
    if not refresh_token:
        raise ConfigEntryAuthFailed(
            "Firebase refresh token is missing; please reauthenticate."
        )

    HASSComponent.set_hass(hass)
    hass.data[DOMAIN].update(
        {
            "entry_id": entry.entry_id,
            "config_entry": entry,
            "id_token": id_token,
            "refresh_token": refresh_token,
        }
    )

    if not await ensure_valid_id_token(hass, entry):
        raise ConfigEntryAuthFailed(
            "Firebase authentication expired; please reauthenticate."
        )

    async def _fetch_customer_and_system():
        token = hass.data[DOMAIN].get("id_token")
        if not token:
            raise OasiraAPIError("Missing Firebase ID token")
        async with OasiraAPIClient(system_id=system_id, id_token=token) as client:
            return await client.get_customer_and_system()

    try:
        parsed_data = await safe_api_call(
            hass, entry, _fetch_customer_and_system
        )
    except OasiraAPIError as err:
        if "401" in str(err):
            raise ConfigEntryAuthFailed(
                "Firebase authentication failed; please reauthenticate."
            ) from err
        raise HomeAssistantError(
            f"Failed to fetch customer/system data: {err}"
        ) from err

    if parsed_data is None:
        raise HomeAssistantError("Could not retrieve customer/system data.")

    async def _fetch_plan_features():
        token = hass.data[DOMAIN].get("id_token")
        if not token:
            raise OasiraAPIError("Missing Firebase ID token")
        async with OasiraAPIClient(system_id=system_id, id_token=token) as client:
            return await client.get_plan_features_by_system_id()

    try:
        plan_features = await safe_api_call(
            hass, entry, _fetch_plan_features
        )
    except OasiraAPIError as plan_error:
        _LOGGER.warning("Failed to fetch plan features: %s", plan_error)
        plan_features = None

    try:
        from .mobile_app_config import setup_mobile_app_integration

        async def _setup_mobile_app():
            token = hass.data[DOMAIN].get("id_token")
            if not token:
                raise OasiraAPIError("Missing Firebase ID token")
            async with OasiraAPIClient(system_id=system_id, id_token=token) as client:
                return await setup_mobile_app_integration(hass, client)

        mobile_app_success = await safe_api_call(
            hass, entry, _setup_mobile_app
        )
        if mobile_app_success:
            _LOGGER.info(
                "Firebase config retrieved from Oasira and stored for EffortlessHome services. "
                "Note: Home Assistant's mobile_app integration requires manual configuration.yaml setup. "
                "Use 'effortlesshome.get_firebase_config' service to view the config."
            )
        else:
            _LOGGER.info(
                "Firebase config not available from Oasira. "
                "This is optional and does not affect other features."
            )
    except Exception as mobile_exc:
        _LOGGER.warning(
            "Could not setup mobile app integration: %s",
            mobile_exc,
            exc_info=True,
        )

    hass.data[DOMAIN].update(
        {
            "entry_id": entry.entry_id,
            "config_entry": entry,
            "token_store": token_store,
            "notification_tokens": hass.data[DOMAIN]["notification_tokens"],
            "fullname": parsed_data["fullname"],
            "phonenumber": parsed_data["phonenumber"],
            "emailaddress": parsed_data["emailaddress"],
            "ha_token": parsed_data["ha_token"],
            "ha_url": parsed_data["ha_url"],
            "ai_key": parsed_data["ai_key"],
            "ai_model": parsed_data["ai_model"],
            "email": parsed_data["emailaddress"],
            "username": parsed_data["emailaddress"],
            "systemid": system_id,
            "customerid": customer_id,
            "id_token": hass.data[DOMAIN].get("id_token"),
            "refresh_token": entry.data.get("refresh_token"),
            "DaysHistoryToKeep": parsed_data["DaysHistoryToKeep"],
            "LowTemperatureWarning": parsed_data["LowTemperatureWarning"],
            "HighTemperatureWarning": parsed_data["HighTemperatureWarning"],
            "LowHumidityWarning": parsed_data["LowHumidityWarning"],
            "HighHumidityWarning": parsed_data["HighHumidityWarning"],
            "address_json": parsed_data["address_json"],
            "systemphotolurl": parsed_data["systemphotolurl"],
            "testmode": parsed_data["testmode"],
            "additional_contacts_json": parsed_data["additional_contacts_json"],
            "instructions_json": parsed_data["instructions_json"],
            "plan": parsed_data["name"],
            "plan_features": plan_features,
        }
    )

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, NAME)},
        name=NAME,
        manufacturer=NAME,
        model=NAME,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        [
            "switch",
            "binary_sensor",
            "sensor",
            "cover",
            "light",
            "alarm_control_panel",
            "button",
        ],
    )

    # Register custom notification platform
    await async_setup_notification_platform(hass)

    # Unregister if already registered
    webhook.async_unregister(hass, "effortlesshome_push_token")
    webhook.async_unregister(hass, "effortlesshome_remove_push_token")
    webhook.async_unregister(hass, "effortlesshome_location_update")

    security_webhook = SecurityAlarmWebhook(hass)
    await SecurityAlarmWebhook.async_setup_webhook(security_webhook)


    webhook.async_register(
        hass,
        DOMAIN,
        "EffortlessHome Push Token",
        "effortlesshome_push_token",
        handle_effortlesshome_push_token_webhook,
    )

    _LOGGER.info("[EffortlessHome] Webhook registered: %s", "effortlesshome_push_token")

    webhook.async_register(
        hass,
        DOMAIN,
        "EffortlessHome Remove Push Token",
        "effortlesshome_remove_push_token",
        handle_effortlesshome_remove_push_token_webhook,
    )

    _LOGGER.info(
        "[EffortlessHome] Webhook registered: %s",
        "effortlesshome_remove_push_token",
    )

    webhook_id = "effortlesshome_location_update"

    webhook.async_register(
        hass,
        DOMAIN,
        "EffortlessHome Location Update",
        webhook_id,
        handle_effortlesshome_location_update,
    )

    _LOGGER.info("[EffortlessHome] Webhook registered: %s", webhook_id)

    register_services(hass)

    # Removed deploy_latest_config(hass) from initialization. Now triggered by button entity.
    label_registry = lr.async_get(hass)

    for desired in LABELS:
        try:
            label_registry.async_create(desired)
            _LOGGER.info("Created missing label: %s", desired)
        except ValueError:
            # Label already exists → ignore
            _LOGGER.info("Label already exists: %s", desired)

    async def refresh_firebase_token():
        """Keep Firebase credentials fresh and persist rotated refresh tokens."""
        while True:
            retry_delay = 50 * 60
            try:
                if not await refresh_firebase_id_token(hass, entry):
                    _LOGGER.error("Failed to refresh Firebase token")
                    retry_delay = 5 * 60
            except Exception:
                _LOGGER.exception("Unexpected error refreshing Firebase token")
                retry_delay = 5 * 60
            await asyncio.sleep(retry_delay)

    async def after_home_assistant_started(_event):
        """Call this function after Home Assistant has started."""
        # Create motion sensor groups
        try:
            grouper = MotionSensorGrouper(hass)
            await grouper.create_sensor_groups()
            await grouper.create_security_sensor_group()
        except Exception as e:
            _LOGGER.info("Failed to create motion sensor groups: %s", e)

        await loaddevicegroups(None)

        refresh_task = hass.async_create_task(refresh_firebase_token())

        @callback
        def cancel_refresh_task() -> None:
            refresh_task.cancel()

        entry.async_on_unload(cancel_refresh_task)

    # Listen for the 'homeassistant_started' event
    remove_start_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED, after_home_assistant_started
    )
    entry.async_on_unload(remove_start_listener)

    return True


def _deploy_latest_config_sync(hass: HomeAssistant):
    """Synchronous helper for deploying config."""
    integration_dir = os.path.dirname(os.path.abspath(__file__))

    source_themes_dir = os.path.join(integration_dir, "themes")
    source_blueprints_dir = os.path.join(integration_dir, "blueprints")
    source_dir = os.path.join(integration_dir, "www/effortlesshome")

    target_themes_dir = hass.config.path("themes")
    target_dir = hass.config.path("www/effortlesshome")
    target_blueprints_dir = hass.config.path("blueprints")

    # Ensure destination directories exist
    os.makedirs(target_themes_dir, exist_ok=True)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(target_blueprints_dir, exist_ok=True)

    # Copy entire themes directory including subfolders and files
    if os.path.exists(source_themes_dir):
        shutil.copytree(source_themes_dir, target_themes_dir, dirs_exist_ok=True)

    if os.path.exists(source_blueprints_dir):
        shutil.copytree(
            source_blueprints_dir, target_blueprints_dir, dirs_exist_ok=True
        )

    if os.path.exists(source_dir):
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)


async def deploy_latest_config(hass: HomeAssistant):
    """Deploy latest: theme, cards, blueprints, etc."""
    _LOGGER.info("[EffortlessHome] Deploying latest configuration files...")
    await hass.async_add_executor_job(_deploy_latest_config_sync, hass)
    _LOGGER.info("[EffortlessHome] Configuration deployment complete.")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    await hass.config_entries.async_unload_platforms(
        entry,
        [
            "switch",
            "binary_sensor",
            "sensor",
            "cover",
            "light",
            "alarm_control_panel",
            "button",
        ],
    )

    # Unregister the notify service
    hass.services.async_remove("effortlesshome", "notify")

    webhook.async_unregister(hass, "effortlesshome_push_token")
    webhook.async_unregister(hass, "effortlesshome_remove_push_token")
    webhook.async_unregister(hass, "effortlesshome_location_update")

    return True


def _get_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Get the active EffortlessHome config entry for token refresh."""
    entry_id = hass.data.get(DOMAIN, {}).get("entry_id")
    entry = hass.config_entries.async_get_entry(entry_id) if entry_id else None
    if entry is None:
        raise HomeAssistantError("EffortlessHome config entry is unavailable.")
    return entry


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload EffortlessHome when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_init(hass: HomeAssistant, entry: ConfigEntry, auto_area: AutoArea):
    """Initialize component."""
    await asyncio.sleep(5)  # wait for all area devices to be initialized

    return True


async def add_label_to_entity(call: ServiceCall) -> None:
    """Add a label to an entity."""
    entity_id = call.data.get("entity_id")
    label = call.data.get("label")

    if not entity_id or not label:
        _LOGGER.error(
            "entity_id and label are required for add_label_to_entity service"
        )
        return

    hass = HASSComponent.get_hass()
    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get(entity_id)

    if not entity_entry:
        _LOGGER.error(f"Entity not found: {entity_id}")
        return

    new_labels = set(entity_entry.labels)
    new_labels.add(label)

    ent_reg.async_update_entity(entity_id, labels=new_labels)
    _LOGGER.info(f"Added label '{label}' to entity '{entity_id}'")


@callback
def register_services(hass: HomeAssistant) -> None:
    """Register effortlesshome services."""

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, "create_event", create_event)
    hass.services.async_register(DOMAIN, "cancel_alarm", cancel_alarm)
    hass.services.async_register(DOMAIN, "get_alarm_status", get_alarm_status)
    hass.services.async_register(DOMAIN, "confirm_pending_alarm", confirm_pending_alarm)

    hass.services.async_register(DOMAIN, "update_entity", update_entity)

    hass.services.async_register(
        DOMAIN, "deploy_latest_config", handle_deploy_latest_config
    )

    hass.services.async_register(
        DOMAIN, "get_firebase_config", handle_get_firebase_config
    )

    hass.services.async_register(
        DOMAIN,
        "add_label_to_entity",
        add_label_to_entity,
        schema=vol.Schema(
            {vol.Required("entity_id"): cv.entity_id, vol.Required("label"): cv.string}
        ),
    )


async def async_add_effortlesshome_addon_repository(
    hass: HomeAssistant,
) -> None:
    """Register the EffortlessHome add-on repository with Supervisor."""
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        raise HomeAssistantError(
            "Cannot add the EffortlessHome add-on repository: "
            "the Supervisor token is unavailable."
        )

    session = async_get_clientsession(hass)
    try:
        async with session.post(
            "http://supervisor/store/repositories",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json={"repository": SUPERVISOR_ADDON_REPOSITORY},
        ) as response:
            if response.status < 200 or response.status >= 300:
                _LOGGER.error(
                    "Supervisor rejected the EffortlessHome add-on repository "
                    "with HTTP %s",
                    response.status,
                )
                raise HomeAssistantError(
                    "Supervisor could not add the EffortlessHome add-on repository "
                    f"(HTTP {response.status})."
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.exception("Failed to contact Supervisor to add the add-on repository")
        raise HomeAssistantError(
            "Unable to contact Supervisor to add the EffortlessHome add-on repository."
        ) from err

    _LOGGER.info("Added EffortlessHome add-on repository to Supervisor")
    notify_create(
        hass,
        "EffortlessHome add-on repository added. Press the integration's Install "
        "EffortlessHome Add-on button to start installation.",
        title="EffortlessHome",
        notification_id="effortlesshome_addon_repository_added",
    )


async def async_install_effortlesshome_addon(
    hass: HomeAssistant,
) -> None:
    """Start installing the EffortlessHome add-on through Supervisor."""
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        raise HomeAssistantError(
            "Cannot install the EffortlessHome add-on: "
            "the Supervisor token is unavailable."
        )

    session = async_get_clientsession(hass)
    try:
        async with session.post(
            f"http://supervisor/store/addons/{SUPERVISOR_ADDON_SLUG}/install",
            headers={"Authorization": f"Bearer {supervisor_token}"},
            json={"background": True},
        ) as response:
            if response.status < 200 or response.status >= 300:
                _LOGGER.error(
                    "Supervisor rejected the EffortlessHome add-on installation "
                    "with HTTP %s. Ensure the EffortlessHome add-on repository "
                    "has been added first.",
                    response.status,
                )
                raise HomeAssistantError(
                    "Supervisor could not start installing the EffortlessHome "
                    "add-on (HTTP "
                    f"{response.status}). Add the EffortlessHome add-on repository "
                    "first if it has not been added."
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.exception("Failed to contact Supervisor to install the add-on")
        raise HomeAssistantError(
            "Unable to contact Supervisor to install the EffortlessHome add-on."
        ) from err

    _LOGGER.info("Started EffortlessHome add-on installation through Supervisor")
    notify_create(
        hass,
        "Supervisor has started installing the EffortlessHome add-on. Check "
        "Settings > Add-ons for installation progress and configuration.",
        title="EffortlessHome",
        notification_id="effortlesshome_addon_installation_started",
    )


async def async_control_effortlesshome_addon(
    hass: HomeAssistant, action: str
) -> None:
    """Start or stop the EffortlessHome add-on through Supervisor."""
    if action not in {"start", "stop"}:
        raise ValueError(f"Unsupported EffortlessHome add-on action: {action}")

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        raise HomeAssistantError(
            f"Cannot {action} the EffortlessHome add-on: "
            "the Supervisor token is unavailable."
        )

    session = async_get_clientsession(hass)
    try:
        async with session.post(
            f"http://supervisor/addons/{SUPERVISOR_ADDON_SLUG}/{action}",
            headers={"Authorization": f"Bearer {supervisor_token}"},
        ) as response:
            if response.status < 200 or response.status >= 300:
                _LOGGER.error(
                    "Supervisor rejected the EffortlessHome add-on %s request "
                    "with HTTP %s",
                    action,
                    response.status,
                )
                raise HomeAssistantError(
                    f"Supervisor could not {action} the EffortlessHome add-on "
                    f"(HTTP {response.status})."
                )
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        _LOGGER.exception(
            "Failed to contact Supervisor to %s the EffortlessHome add-on", action
        )
        raise HomeAssistantError(
            f"Unable to contact Supervisor to {action} the EffortlessHome add-on."
        ) from err

    _LOGGER.info("Requested Supervisor to %s the EffortlessHome add-on", action)


async def update_entity(call):
    """Handle the service call."""
    entity_id = call.data.get("entity_id")
    new_area = call.data.get("area_id")

    hass = HASSComponent.get_hass()
    ent_reg = entity_registry.async_get(hass)

    ent_reg.async_update_entity(entity_id, area_id=new_area)


async def loaddevicegroups(calldata) -> None:
    """Load device groups."""
    hass = HASSComponent.get_hass()
    await async_setup_devicegroup(hass)


async def create_event(call: ServiceCall) -> None:
    """Create event."""
    _LOGGER.info("create event calldata =%s", call.data)

    hass = HASSComponent.get_hass()

    entity_id = call.data.get("entity_id")
    if not entity_id:
        _LOGGER.error("entity_id is required for create_event service")
        return

    devicestate = hass.states.get(entity_id)
    sensor_device_class = None
    sensor_device_name = None

    if devicestate and devicestate.attributes.get("friendly_name"):
        sensor_device_name = devicestate.attributes["friendly_name"]

    if devicestate and devicestate.attributes.get("device_class"):
        sensor_device_class = devicestate.attributes["device_class"]

    if sensor_device_class is not None and sensor_device_name is not None:
        alarmstate = hass.data[DOMAIN].get("alarm_id")

        if alarmstate and alarmstate != "":
            alarmstatus = hass.data[DOMAIN].get("alarmstatus")

            if alarmstatus == "ACTIVE":
                alarmid = alarmstate
                _LOGGER.info("alarm id =%s", alarmid)

                # Call the API to create event
                systemid = hass.data[DOMAIN].get("systemid")

                event_data = {
                    "sensor_device_class": sensor_device_class,
                    "sensor_device_name": sensor_device_name,
                }

                _LOGGER.info("Calling create event API with payload: %s", event_data)

                async def _create_event():
                    token = hass.data[DOMAIN].get("id_token")
                    if not token:
                        raise OasiraAPIError("Missing Firebase ID token")
                    async with OasiraAPIClient(
                        system_id=systemid, id_token=token
                    ) as api_client:
                        return await api_client.create_event(alarmid, event_data)

                try:
                    return await safe_api_call(
                        hass, _get_config_entry(hass), _create_event
                    )
                except OasiraAPIError as e:
                    _LOGGER.error("Failed to create event: %s", e)
                    return None
                except HomeAssistantError as e:
                    _LOGGER.error("Failed to create event: %s", e)
                    return None
    return None


# Keep old name for backward compatibility
async def createevent(calldata) -> None:
    """Create event (deprecated name)."""
    await create_event(calldata)


async def cancel_alarm(call: ServiceCall) -> None:
    """Cancel alarm."""
    hass = HASSComponent.get_hass()
    return await async_cancelalarm(hass)


# Keep old name for backward compatibility
async def cancelalarm(calldata) -> None:
    """Cancel alarm (deprecated name)."""
    await cancel_alarm(calldata)


async def get_alarm_status(call: ServiceCall) -> None:
    """Get alarm status."""
    hass = HASSComponent.get_hass()
    return await async_getalarmstatus(hass)


# Keep old name for backward compatibility
async def getalarmstatus(calldata) -> None:
    """Get alarm status (deprecated name)."""
    await get_alarm_status(calldata)


async def confirm_pending_alarm(call: ServiceCall) -> None:
    """Confirm pending alarm."""
    hass = HASSComponent.get_hass()
    return await async_confirmpendingalarm(hass)


# Keep old name for backward compatibility
async def confirmpendingalarm(calldata) -> None:
    """Confirm pending alarm (deprecated name)."""
    await confirm_pending_alarm(calldata)


async def handle_get_firebase_config(call: ServiceCall) -> None:
    """Handle the get_firebase_config service call."""
    hass = HASSComponent.get_hass()

    try:
        # Get credentials from hass.data
        system_id = hass.data[DOMAIN].get("systemid")
        id_token = hass.data[DOMAIN].get("id_token")

        if not system_id or not id_token:
            _LOGGER.error("System ID or ID token not found in configuration")
            notify_create(
                hass,
                "Firebase Config Error: System ID or ID token not found",
                title="EffortlessHome",
            )
            return

        # Get Firebase config from Oasira
        async def _get_mobile_app_config():
            token = hass.data[DOMAIN].get("id_token")
            if not token:
                raise OasiraAPIError("Missing Firebase ID token")
            async with OasiraAPIClient(
                system_id=system_id, id_token=token
            ) as api_client:
                return await api_client.setup_mobile_app_integration(hass, api_client)

        try:
            mobile_app_config = await safe_api_call(
                hass, _get_config_entry(hass), _get_mobile_app_config
            )
            if mobile_app_config:
                # Generate YAML config for display
                yaml_config = generate_mobile_app_config_yaml(mobile_app_config)

                # Create a persistent notification with the config
                message = f"""
        Firebase Configuration retrieved from Oasira:

        ```yaml
        {yaml_config}
        ```

        **Important:** Home Assistant's mobile_app integration requires manual configuration.
        To enable mobile app notifications, add the above YAML to your configuration.yaml file, then restart Home Assistant.

        Without this configuration, mobile app notifications will not work.
        """
                notify_create(hass, message, title="Firebase Configuration")
                _LOGGER.info("Firebase config retrieved and displayed to user")
            else:
                _LOGGER.error("Failed to retrieve Firebase config from Oasira")
                notify_create(
                    hass,
                    "Failed to retrieve Firebase configuration from Oasira",
                    title="Firebase Config Error",
                )
        except Exception as e:
            _LOGGER.error(f"Error retrieving Firebase config: {e}", exc_info=True)
            notify_create(
                hass,
                f"Error retrieving Firebase config: {str(e)}",
                title="Firebase Config Error",
            )

    except Exception as e:
        _LOGGER.error(f"Error retrieving Firebase config: {e}", exc_info=True)
        notify_create(
            hass,
            f"Error retrieving Firebase config: {str(e)}",
            title="Firebase Config Error",
        )


async def handle_deploy_latest_config(call: ServiceCall) -> None:
    """Handle the service call."""
    hass = HASSComponent.get_hass()

    await deploy_latest_config(hass)


# sampledata
# {
#    email:
#    token:
#    device_name: master_bedroom_tv
#    platform: android
# }


async def handle_effortlesshome_push_token_webhook(hass, webhook_id, request):
    """Handle incoming EffortlessHome Push Token webhook (device token)."""

    _LOGGER.info("[EffortlessHome] 🔔 Handling push token webhook")
    _LOGGER.info("[EffortlessHome] Request headers: %s", dict(request.headers))

    try:
        data = await request.json()
        _LOGGER.info(
            "[EffortlessHome] 🔔 Push token payload: %s",
            {k: v if k != "token" else f"{v[:20]}..." for k, v in data.items()},
        )
    except Exception as e:
        _LOGGER.error("[EffortlessHome] ❌ Invalid JSON payload: %s", e)
        return web.Response(status=400, text="Invalid JSON")

    token = data.get("token")
    device_name = data.get("device_name")
    platform_name = data.get("platform")

    _LOGGER.info(
        "[EffortlessHome] 🔔 Parsed data - device_name: %s, platform: %s, token_length: %s",
        device_name,
        platform_name,
        len(token) if token else 0,
    )

    if not token:
        _LOGGER.error(
            "[EffortlessHome] ❌ Webhook called without required field (token)."
        )
        return web.Response(status=400, text="Missing token")

    domain_data = hass.data.setdefault(DOMAIN, {})
    tokens = domain_data.setdefault("notification_tokens", [])
    _LOGGER.info(
        "[EffortlessHome] Current token count: %s",
        len(tokens),
    )
    if token not in tokens:
        tokens.append(token)
        token_store = domain_data.get("token_store")
        if token_store is not None:
            await token_store.async_save(tokens)
        _LOGGER.info(
            "[EffortlessHome] Token added. New token count: %s",
            len(tokens),
        )
    else:
        _LOGGER.info("[EffortlessHome] Token already registered")

    _LOGGER.info(
        "[EffortlessHome] ✅ Push token registered successfully for %s", device_name
    )
    return web.json_response({"status": "success", "message": "Token registered"})


async def handle_effortlesshome_remove_push_token_webhook(hass, webhook_id, request):
    """Handle incoming EffortlessHome remove push token webhook."""

    _LOGGER.info("[EffortlessHome] 🔔 Handling remove push token webhook")
    _LOGGER.info("[EffortlessHome] Request headers: %s", dict(request.headers))

    try:
        data = await request.json()
        _LOGGER.info(
            "[EffortlessHome] 🔔 Remove token payload: %s",
            {k: v if k != "token" else f"{v[:20]}..." for k, v in data.items()},
        )
    except Exception as e:
        _LOGGER.error("[EffortlessHome] ❌ Invalid JSON payload: %s", e)
        return web.Response(status=400, text="Invalid JSON")

    token = data.get("token")
    if not token:
        _LOGGER.error(
            "[EffortlessHome] ❌ Webhook called without required field (token)."
        )
        return web.Response(status=400, text="Missing token")

    domain_data = hass.data.setdefault(DOMAIN, {})
    tokens = domain_data.setdefault("notification_tokens", [])

    if token in tokens:
        tokens.remove(token)
        token_store = domain_data.get("token_store")
        if token_store is not None:
            await token_store.async_save(tokens)
        _LOGGER.info("[EffortlessHome] ✅ Push token removed successfully")
        return web.json_response({"status": "success", "message": "Token removed"})

    _LOGGER.info("[EffortlessHome] Token not found - nothing to remove")
    return web.json_response({"status": "success", "message": "Token not found"})


# {
#  "device_id": "unique_device_identifier",
#  "device_name": "Samsung Galaxy S21",
#  "latitude": 37.7749,
#  "longitude": -122.4194,
#  "gps_accuracy": 10.5,
#  "altitude": 15.0,
#  "speed": 0.0,
#  "heading": 0.0,
#  "timestamp": "2026-01-30T10:30:00.000Z",
#  "attributes": {
#    "platform": "android",
#    "brand": "Samsung",
#    "model": "SM-G991B",
#    "version": "13",
#    "sdk_int": 33
#  }
# }
async def handle_effortlesshome_location_update(hass, webhook_id, request):
    """Register EffortlessHome location update service."""

    _LOGGER.info("[EffortlessHome] 📍 Handling location update webhook")
    _LOGGER.info("[EffortlessHome] Request headers: %s", dict(request.headers))
    try:
        data = await request.json()
        _LOGGER.info("[EffortlessHome] 📍 Location update payload: %s", data)
    except Exception as e:
        _LOGGER.error("[EffortlessHome] ❌ Invalid JSON payload: %s", e)
        return web.Response(status=400, text="Invalid JSON")

    ####TODO: get user's email here and link this device tracker to them (local and online) #####

    device_name = data.get("device_name")
    device_id = data.get("device_id")
    lat = data.get("latitude")
    lon = data.get("longitude")
    accuracy = data.get("accuracy", 30.0)

    _LOGGER.info(
        "[EffortlessHome] 📍 Parsed data - device_id: %s, lat: %s, lon: %s, accuracy: %s",
        device_id,
        lat,
        lon,
        accuracy,
    )

    if not device_id or lat is None or lon is None:
        _LOGGER.error(
            "[EffortlessHome] ❌ Missing required fields - device_id: %s, lat: %s, lon: %s",
            device_id,
            lat,
            lon,
        )
        return web.Response(status=400, text="Missing required fields")

    device_id_new = (
        device_id.lower()
        .replace("@", "_")
        .replace(".", "_")
        .replace("-", "_")
        .replace("{", "")
        .replace("}", "")
    )
    entity_id = f"device_tracker.{device_id_new}"

    domain_data = hass.data.setdefault(DOMAIN, {})
    entry_id = domain_data.get("entry_id")
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry_id,
        identifiers={(DOMAIN, device_id_new)},
        name=device_name or device_id_new,
        manufacturer=NAME,
        model="Mobile Device",
    )

    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_or_create(
        domain="device_tracker",
        platform=DOMAIN,
        unique_id=f"{DOMAIN}_tracker_{device_id_new}",
        suggested_object_id=device_id_new,
        device_id=device_entry.id,
        original_name=device_name or device_id_new,
    )
    entity_id = entity_entry.entity_id

    _LOGGER.info("[EffortlessHome] 📍 Creating/updating device tracker: %s", entity_id)

    # Update or create entity with immediate geofencing state determination
    # Calculate the state based on location coordinates right away
    state = "unknown"

    try:
        # Try to get home coordinates for immediate state calculation
        home_coords = None
        system_data = hass.data.get(DOMAIN, {})
        address_json = system_data.get("address_json")

        if address_json:
            if isinstance(address_json, str):
                address_data = json.loads(address_json)
            else:
                address_data = address_json

            home_lat = address_data.get("latitude")
            home_lon = address_data.get("longitude")

            if home_lat is not None and home_lon is not None:
                home_coords = (float(home_lat), float(home_lon))

        # Fallback to HA config coordinates
        if not home_coords:
            try:
                home_lat = hass.config.latitude
                home_lon = hass.config.longitude
                if home_lat is not None and home_lon is not None:
                    home_coords = (float(home_lat), float(home_lon))
            except (AttributeError, ValueError, TypeError):
                pass

        # Calculate distance and determine state
        if home_coords:
            home_lat, home_lon = home_coords

            # Earth's radius in meters
            R = 6371000

            # Convert degrees to radians
            lat1_rad = math.radians(home_lat)
            lon1_rad = math.radians(home_lon)
            lat2_rad = math.radians(lat)
            lon2_rad = math.radians(lon)

            # Haversine formula
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad

            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            distance = R * c
            radius = 100.0  # 100 meter radius

            if distance <= radius:
                state = "home"
            else:
                state = "not_home"

    except Exception as e:
        _LOGGER.debug("[EffortlessHome] Could not calculate geofence state: %s", e)
        state = "unknown"

    hass.states.async_set(
        entity_id,
        state,
        {
            "latitude": lat,
            "longitude": lon,
            "gps_accuracy": accuracy,
            "source_type": SOURCE_TYPE_GPS,
            "friendly_name": f" {device_name}",
        },
    )

    _LOGGER.info("[EffortlessHome] ✅ Location update successful for %s", entity_id)
    return web.json_response({"status": "success", "message": "Location updated"})
