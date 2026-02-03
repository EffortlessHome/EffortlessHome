from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
from os import path, walk
from pathlib import Path
import shutil
import subprocess
from typing import TYPE_CHECKING, List

import aiohttp

from google.api_core.exceptions import GoogleAPIError
from google import genai
import voluptuous as vol

from homeassistant.components.recorder import get_instance
from homeassistant.components import frontend
from homeassistant.components.alarm_control_panel import DOMAIN as PLATFORM
from homeassistant.components.notify import BaseNotificationService
from homeassistant.config import get_default_config_dir
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.core import ServiceCall
from homeassistant.components import webhook
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.persistent_notification import create as notify_create

import homeassistant.core
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    asyncio,  
    callback,
)
from homeassistant.exceptions import (
    HomeAssistantError,
)
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry,
    entity_registry as er,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import label_registry as lr

import homeassistant.util.dt as dt_util
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.http.view import HomeAssistantView
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components import conversation

from .alarm_common import (
    async_cancelalarm,
    async_confirmpendingalarm,
    async_getalarmstatus,
)
from .area_manager import AreaManager
from .auto_area import AutoArea

from .person import eh_person
from oasira import OasiraAPIClient, OasiraAPIError

from .const import (
    DOMAIN,
    LABELS,
    WEBHOOK_UPDATE_PUSH_TOKEN,
    CONF_EMAIL, 
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    NAME,
    name_internal
)


from .deviceclassgroupsync import async_setup_devicegroup
from .event import EventHandler
from .MotionSensorGrouper import MotionSensorGrouper
from .SecurityAlarmWebhook import SecurityAlarmWebhook, async_remove
from .BroadcastWebhook import BroadcastWebhook, async_remove

from .virtualpowersensor import VirtualPowerSensor

from .influx import process_trend_data
from .binary_sensor import updateEntity

from homeassistant.components import frontend
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.event import async_track_time_change
from homeassistant.components import person

try:
    # Older versions (pre-2025)
    from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
except ImportError:
    # Newer versions (2025+)
    SOURCE_TYPE_GPS = "gps"

from aiohttp import web

LOCATION_SERVICE_SCHEMA = vol.Schema({
    vol.Required("device_id"): str,
    vol.Required("latitude"): float,
    vol.Required("longitude"): float,
    vol.Optional("accuracy"): float,
})

_LOGGER = logging.getLogger(__name__)

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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})   

    system_id = entry.data["system_id"]
    customer_id = entry.data["customer_id"]
    id_token = entry.data.get("id_token")

    if not system_id:
        raise HomeAssistantError("System ID is missing in configuration.")

    if not customer_id:
        raise HomeAssistantError("Customer ID is missing in configuration.")

    HASSComponent.set_hass(hass)

    # Initialize API client and fetch customer/system data
    async with OasiraAPIClient(
        system_id=system_id,
        id_token=id_token,
    ) as api_client:
        try:
            parsed_data = await api_client.get_customer_and_system()

            # Fetch plan features for this system
            plan_features = None
            try:
                plan_features = await api_client.get_plan_features_by_system_id()
            except Exception as pf_exc:
                _LOGGER.warning("Failed to fetch plan features: %s", pf_exc)
                plan_features = None

            # Setup mobile_app integration with Firebase config from Oasira
            try:
                from .mobile_app_config import setup_mobile_app_integration
                mobile_app_success = await setup_mobile_app_integration(hass, api_client)
                if mobile_app_success:
                    _LOGGER.info("Mobile app integration configured from Oasira Firebase config")
                else:
                    _LOGGER.warning("Failed to configure mobile app integration from Oasira")
            except Exception as mobile_exc:
                _LOGGER.warning("Could not setup mobile app integration: %s", mobile_exc)

            hass.data[DOMAIN] = {
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
                "id_token": id_token,
                "influx_url": parsed_data["influx_url"],
                "influx_token": parsed_data["influx_token"],
                "influx_bucket": parsed_data["influx_bucket"],
                "influx_org": parsed_data["influx_org"],
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
        except OasiraAPIError as e:
            _LOGGER.error("Failed to fetch customer/system data: %s", e)
            raise HomeAssistantError(f"Failed to fetch customer/system data: {e}") from e

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

    # Unregister if already registered
    webhook.async_unregister(hass, "effortlesshome_push_token")
    webhook.async_unregister(hass, "effortlesshome_location_update")

    security_webhook = SecurityAlarmWebhook(hass)
    await SecurityAlarmWebhook.async_setup_webhook(security_webhook)

    broadcast_webhook = BroadcastWebhook(hass)
    await BroadcastWebhook.async_setup_webhook(broadcast_webhook)

    webhook_id = "effortlesshome_push_token"

    webhook.async_register(
        hass,
        DOMAIN,
        "EffortlessHome Push Token",
        webhook_id,
        handle_effortlesshome_push_token_webhook,
    )

    _LOGGER.info("[EffortlessHome] Webhook registered: %s", webhook_id)

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

    # Initialize the Motion Sensor Grouper
    grouper = MotionSensorGrouper(hass)

    # Create groups for motion sensors
    await grouper.create_sensor_groups()
    await grouper.create_security_sensor_group()

    # Removed deploy_latest_config(hass) from initialization. Now triggered by button entity.
    label_registry = lr.async_get(hass)

    for desired in LABELS:
        try:
            label_registry.async_create(desired)
            _LOGGER.info("Created missing label: %s", desired)
        except ValueError:
            # Label already exists → ignore
            _LOGGER.info("Label already exists: %s", desired)
    
    async def after_home_assistant_started(event):
        """Call this function after Home Assistant has started."""
        await loaddevicegroups(None)

        #TODO: Update the link below with the actual add-on slug
        #notify_create(
        #    hass,
        #    title="EffortlessHome Add-on Required",
        #    message=(
        #        "The EffortlessHome integration needs the EffortlessHome Add-on. "
        #        "Click [here](https://my.home-assistant.io/redirect/supervisor_addon/?addon=<your_slug>) to install it."
        #    ),
        #)

    # Listen for the 'homeassistant_started' event
    hass.bus.async_listen_once(
        homeassistant.core.EVENT_HOMEASSISTANT_STARTED, after_home_assistant_started
    )

    # Start Firebase token refresh task (refresh every 50 minutes, tokens expire in 60 minutes)
    async def refresh_firebase_token():
        """Periodically refresh the Firebase ID token."""
        refresh_token = entry.data.get("refresh_token")
        
        if not refresh_token:
            _LOGGER.warning("No refresh token available - cannot refresh Firebase token")
            return
        
        while True:
            try:
                # Wait 50 minutes before refreshing (tokens expire in 60 minutes)
                await asyncio.sleep(50 * 60)
                
                _LOGGER.info("Refreshing Firebase ID token...")
                
                async with OasiraAPIClient() as api_client:
                    result = await api_client.firebase_refresh_token(refresh_token)
                    
                    new_id_token = result.get("idToken")
                    new_refresh_token = result.get("refreshToken")
                    
                    if new_id_token:
                        # Update the token in hass.data
                        hass.data[DOMAIN]["id_token"] = new_id_token
                        
                        # Update the config entry data
                        hass.config_entries.async_update_entry(
                            entry,
                            data={
                                **entry.data,
                                "id_token": new_id_token,
                                "refresh_token": new_refresh_token or refresh_token,
                            }
                        )
                        
                        # Update the refresh token for next iteration
                        if new_refresh_token:
                            refresh_token = new_refresh_token
                        
                        _LOGGER.info("✅ Firebase ID token refreshed successfully")
                    else:
                        _LOGGER.error("Failed to refresh Firebase token - no idToken in response")
                        
            except OasiraAPIError as e:
                _LOGGER.error("Failed to refresh Firebase token: %s", e)
                # Continue trying even if refresh fails
            except Exception as e:
                _LOGGER.exception("Unexpected error refreshing Firebase token: %s", e)
    
    # Start the refresh task
    hass.async_create_task(refresh_firebase_token())

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
        shutil.copytree(source_blueprints_dir, target_blueprints_dir, dirs_exist_ok=True)

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
    webhook.async_unregister(hass, "effortlesshome_location_update")

    return True

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

    hass.services.async_register(
        DOMAIN, "createcleanmotionfilesservice", cleanmotionfiles
    )

    hass.services.async_register(
        DOMAIN,
        "notify_person_service",
        handle_notify_person_service,
    )

    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, "createeventservice", createevent)
    hass.services.async_register(DOMAIN, "cancelalarmservice", cancelalarm)
    hass.services.async_register(DOMAIN, "getalarmstatusservice", getalarmstatus)
    hass.services.async_register(
        DOMAIN, "confirmpendingalarmservice", confirmpendingalarm
    )

    hass.services.async_register(DOMAIN, "update_entity", update_entity)

    hass.services.async_register(DOMAIN, "create_alert_service", createalert)

    hass.services.async_register(DOMAIN, "deploylatestconfig", handle_deploy_latest_config)
    
    hass.services.async_register(DOMAIN, "get_firebase_config", handle_get_firebase_config)

    hass.services.async_register(
        DOMAIN,
        "add_label_to_entity",
        add_label_to_entity,
        schema=vol.Schema(
            {vol.Required("entity_id"): cv.entity_id, vol.Required("label"): cv.string}
        ),
    )

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

async def createevent(calldata) -> None:  
    """Create event."""
    _LOGGER.info("create event calldata =" + str(calldata.data))

    hass = HASSComponent.get_hass()

    devicestate = hass.states.get(calldata.data["entity_id"])
    sensor_device_class = None
    sensor_device_name = None

    if devicestate and devicestate.attributes.get("friendly_name"):
        sensor_device_name = devicestate.attributes["friendly_name"]

    if devicestate and devicestate.attributes.get("device_class"):
        sensor_device_class = devicestate.attributes["device_class"]

    if sensor_device_class is not None and sensor_device_name is not None:
        alarmstate = hass.data[DOMAIN]["alarm_id"]

        if alarmstate is not None and alarmstate != "":
            alarmstatus = hass.data[DOMAIN]["alarmstatus"]

            if alarmstatus == "ACTIVE":
                alarmid = hass.data[DOMAIN]["alarm_id"]
                _LOGGER.info("alarm id =" + alarmid)

                # Call the API to create event
                systemid = hass.data[DOMAIN]["systemid"]
                id_token = hass.data[DOMAIN].get("id_token")

                event_data = {
                    "sensor_device_class": sensor_device_class,
                    "sensor_device_name": sensor_device_name,
                }

                _LOGGER.info("Calling create event API with payload: %s", event_data)

                async with OasiraAPIClient(
                    system_id=systemid,
                    id_token=id_token,
                ) as api_client:
                    try:
                        result = await api_client.create_event(alarmid, event_data)
                        _LOGGER.info("API response content: %s", result)
                        return result
                    except OasiraAPIError as e:
                        _LOGGER.error("Failed to create event: %s", e)
                        return None
            return None
        return None
    return None

async def createalert(calldata) -> None:  
    """Create alert."""
    _LOGGER.info("create alert calldata =" + str(calldata.data))

    hass = HASSComponent.get_hass()
    alert_type = calldata.data["alert_type"]
    alert_description = calldata.data["alert_description"]
    status = calldata.data["status"]

    alert_data = {
        "alert_type": alert_type,
        "alert_description": alert_description,
        "status": status,
    }

    # Call the API to create alert
    systemid = hass.data[DOMAIN]["systemid"]  
    id_token = hass.data[DOMAIN].get("id_token")

    _LOGGER.info("Calling alert API with payload: %s", alert_data)

    async with OasiraAPIClient(
        system_id=systemid,
        id_token=id_token,
    ) as api_client:
        try:
            result = await api_client.create_alert(alert_data)
            _LOGGER.info("API response content: %s", result)
            return result
        except OasiraAPIError as e:
            _LOGGER.error("Failed to create alert: %s", e)
            return None

async def cancelalarm(calldata):
    """Cancel alarm."""
    hass = HASSComponent.get_hass()
    return await async_cancelalarm(hass)

async def getalarmstatus(calldata):
    """Get alarm status."""
    hass = HASSComponent.get_hass()

    return await async_getalarmstatus(hass)

async def confirmpendingalarm(calldata):
    """Confirm pending alarm."""
    hass = HASSComponent.get_hass()

    return await async_confirmpendingalarm(hass)


async def cleanmotionfiles(calldata):
    """Execute the shell command to delete old snapshots."""

    age = "30"

    try:
        age = calldata.data["age"]
    except:
        _LOGGER.error("Invalid Args To Clean Motion Service. Using Default 30 days")

    command = "find /media/snapshots/* -mtime +" + str(age) + " -exec rm {} \\;"

    # Use subprocess to execute the shell command
    process = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )

    if process.returncode == 0:
        _LOGGER.info("Successfully deleted old snapshots.")
    else:
        _LOGGER.error(f"Error deleting snapshots: {process.stderr.decode()}")


async def handle_notify_person_service(calldata):
    """Send a notification message only to a person’s Mobile App device trackers. Now with error handling and debug logging."""
    _LOGGER.info("[handle_notify_person_service] Called with calldata: %s", calldata.data)

    try:
        hass = HASSComponent.get_hass()
        person_name_list = calldata.data.get("target")

        if not person_name_list:
            _LOGGER.info("[handle_notify_person_service] No person provided in target list.")
            return

        message = calldata.data.get("message")
        if not message:
            _LOGGER.info("[handle_notify_person_service] No message provided.")
            return

        title = calldata.data.get("title")
        data = calldata.data.get("data")

        ent_reg = entity_registry.async_get(hass)

        for person_name in person_name_list:
            try:
                person_entity = f"{person_name.lower()}"
                _LOGGER.debug(f"[handle_notify_person_service] Looking up person entity: {person_entity}")
                person_entry = ent_reg.async_get(person_entity)

                if person_entry is None:
                    _LOGGER.warning(f"[handle_notify_person_service] Person entity {person_entity} not found.")
                    continue

                _LOGGER.debug(f"[handle_notify_person_service] Person entry found: {person_entry}")

                # Get device trackers associated with this person
                device_trackers = person.entities_in_person(hass, person_entity)
                _LOGGER.debug(f"[handle_notify_person_service] Device trackers for {person_name}: {device_trackers}")

                if not device_trackers:
                    _LOGGER.warning(f"[handle_notify_person_service] No device trackers found for person {person_name}.")
                    continue

                # Filter only device_trackers from the Mobile App integration
                mobile_app_devices = []
                for device_tracker in device_trackers:
                    tracker_entry = ent_reg.async_get(device_tracker)
                    if tracker_entry and tracker_entry.platform == "mobile_app":
                        mobile_app_devices.append(device_tracker)

                _LOGGER.debug(f"[handle_notify_person_service] Mobile App device trackers for {person_name}: {mobile_app_devices}")

                if not mobile_app_devices:
                    _LOGGER.warning(f"[handle_notify_person_service] No Mobile App device trackers found for {person_name}.")
                    continue

                # Send notifications to Mobile App notify services
                for device_tracker in mobile_app_devices:
                    try:
                        notify_service = device_tracker.replace("device_tracker.", "mobile_app_")
                        _LOGGER.info(f"[handle_notify_person_service] Sending notification to {notify_service} for {person_name}")
                        await hass.services.async_call(
                            "notify",
                            notify_service,
                            {"message": message, "title": title, "data": data},
                            blocking=False,
                        )
                    except Exception as notify_err:
                        _LOGGER.error(f"[handle_notify_person_service] Error sending notification to {notify_service} for {person_name}: {notify_err}")
            except Exception as person_err:
                _LOGGER.error(f"[handle_notify_person_service] Error processing person {person_name}: {person_err}")
    except Exception as err:
        _LOGGER.exception(f"[handle_notify_person_service] Unexpected error: {err}")

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
                title="EffortlessHome"
            )
            return
        
        # Get Firebase config from Oasira
        async with OasiraAPIClient(system_id=system_id, id_token=id_token) as api_client:
            from .mobile_app_config import setup_mobile_app_config, generate_mobile_app_config_yaml
            
            mobile_app_config = await setup_mobile_app_config(hass, api_client)
            
            if mobile_app_config:
                # Generate YAML config for display
                yaml_config = generate_mobile_app_config_yaml(mobile_app_config)
                
                # Create a persistent notification with the config
                message = f"""
Firebase Configuration retrieved from Oasira:

```yaml
{yaml_config}
```

**Note:** This configuration has been automatically applied to your Home Assistant mobile_app integration. 
You do NOT need to manually add this to configuration.yaml.

For manual configuration, copy the above YAML to your configuration.yaml file.
"""
                notify_create(
                    hass,
                    message,
                    title="Firebase Configuration"
                )
                
                _LOGGER.info("Firebase config retrieved and displayed to user")
            else:
                _LOGGER.error("Failed to retrieve Firebase config from Oasira")
                notify_create(
                    hass,
                    "Failed to retrieve Firebase configuration from Oasira",
                    title="Firebase Config Error"
                )
                
    except Exception as e:
        _LOGGER.error(f"Error retrieving Firebase config: {e}", exc_info=True)
        notify_create(
            hass,
            f"Error retrieving Firebase config: {str(e)}",
            title="Firebase Config Error"
        )

async def handle_deploy_latest_config(call: ServiceCall) -> None:
    """Handle the service call."""
    hass = HASSComponent.get_hass()

    await deploy_latest_config(hass)

#sampledata
#{
#    email: 
#    token: 
#    device_name: master_bedroom_tv
#    platform: android
#}

async def handle_effortlesshome_push_token_webhook(hass, webhook_id, request):
    """Handle incoming EffortlessHome Push Token webhook (device token)."""

    _LOGGER.info("[EffortlessHome] 🔔 Handling push token webhook")
    _LOGGER.info("[EffortlessHome] Request headers: %s", dict(request.headers))

    try:
        data = await request.json()
        _LOGGER.info("[EffortlessHome] 🔔 Push token payload: %s", {k: v if k != 'token' else f"{v[:20]}..." for k, v in data.items()})
    except Exception as e:
        _LOGGER.error("[EffortlessHome] ❌ Invalid JSON payload: %s", e)
        return web.Response(status=400, text="Invalid JSON")

    email = data.get("email")
    token = data.get("token")
    device_name = data.get("device_name")
    platform_name = data.get("platform")

    _LOGGER.info("[EffortlessHome] 🔔 Parsed data - email: %s, device_name: %s, platform: %s, token_length: %s", 
                 email, device_name, platform_name, len(token) if token else 0)

    if not email:
        _LOGGER.error("[EffortlessHome] ❌ Webhook called without 'email' field.")
        return web.Response(status=400, text="Missing email field")

    persons = hass.data.get(DOMAIN, {}).get("persons", [])
    _LOGGER.info("[EffortlessHome] 🔔 Searching for person among %s registered persons", len(persons))
    
    targetperson = None
    for person in persons:
        if person.name == email:
            targetperson = person
            break

    if targetperson is not None:
        _LOGGER.info("[EffortlessHome] 🔔 Found target person: %s", targetperson.name)
        await targetperson.async_set_notification_devices(hass, token, device_name, platform_name)
        _LOGGER.info("[EffortlessHome] ✅ Push token registered successfully for %s", email)
        return web.json_response({"status": "success", "message": "Token registered"})
    else:
        _LOGGER.warning("[EffortlessHome] ❌ Person not found for email: %s (available: %s)", 
                       email, [p.name for p in persons])
        return web.Response(status=404, text="Person not found")


#{
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
#}
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

    _LOGGER.info("[EffortlessHome] 📍 Parsed data - device_id: %s, lat: %s, lon: %s, accuracy: %s", device_id, lat, lon, accuracy)

    if not device_id or lat is None or lon is None:
        _LOGGER.error("[EffortlessHome] ❌ Missing required fields - device_id: %s, lat: %s, lon: %s", device_id, lat, lon)
        return web.Response(status=400, text="Missing required fields")

    device_id_new = device_id.lower().replace('@', '_').replace('.', '_').replace('-', '_').replace('{', '').replace('}', '')
    entity_id = f"device_tracker.{device_id_new}"

    _LOGGER.info("[EffortlessHome] 📍 Creating/updating device tracker: %s", entity_id)

    # Update or create entity
    hass.states.async_set(
        entity_id,
        "home",  # You can change this dynamically later
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