"""Button platform for EffortlessHome."""

import logging
import os

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    """Set up button entities."""
    buttons = [DeployLatestConfigButton(hass, entry)]
    if os.environ.get("SUPERVISOR_TOKEN"):
        buttons.extend(
            [
                AddEffortlessHomeAddonRepositoryButton(hass, entry),
                InstallEffortlessHomeAddonButton(hass, entry),
                StartEffortlessHomeAddonButton(hass, entry),
                StopEffortlessHomeAddonButton(hass, entry),
            ]
        )
    async_add_entities(buttons)


class DeployLatestConfigButton(ButtonEntity):
    """Button to deploy latest EffortlessHome config."""

    _attr_name = "Deploy Latest EffortlessHome Config"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize button."""
        self.hass = hass
        self._attr_unique_id = (
            f"deploy_latest_effortlesshome_config_button_{entry.entry_id}"
        )
        self._attr_config_entry_id = entry.entry_id

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
            "model": NAME,
        }

    async def async_press(self) -> None:
        """Handle button press."""
        from . import deploy_latest_config

        _LOGGER.info("[EffortlessHome] Button pressed: Deploying latest config...")
        await deploy_latest_config(self.hass)


class AddEffortlessHomeAddonRepositoryButton(ButtonEntity):
    """Button to add the EffortlessHome add-on repository to Supervisor."""

    _attr_name = "Add EffortlessHome Add-on Repository"
    _attr_icon = "mdi:package-variant-plus"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize button."""
        self.hass = hass
        self._attr_unique_id = (
            f"add_effortlesshome_addon_repository_button_{entry.entry_id}"
        )
        self._attr_config_entry_id = entry.entry_id

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
            "model": NAME,
        }

    async def async_press(self) -> None:
        """Add the EffortlessHome add-on repository to Supervisor."""
        from . import async_add_effortlesshome_addon_repository

        _LOGGER.info("[EffortlessHome] Adding EffortlessHome add-on repository")
        await async_add_effortlesshome_addon_repository(self.hass)


class InstallEffortlessHomeAddonButton(ButtonEntity):
    """Button to install the EffortlessHome add-on through Supervisor."""

    _attr_name = "Install EffortlessHome Add-on"
    _attr_icon = "mdi:download"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize button."""
        self.hass = hass
        self._attr_unique_id = f"install_effortlesshome_addon_button_{entry.entry_id}"
        self._attr_config_entry_id = entry.entry_id

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
            "model": NAME,
        }

    async def async_press(self) -> None:
        """Start installing the EffortlessHome add-on through Supervisor."""
        from . import async_install_effortlesshome_addon

        _LOGGER.info("[EffortlessHome] Installing EffortlessHome add-on")
        await async_install_effortlesshome_addon(self.hass)


class StartEffortlessHomeAddonButton(ButtonEntity):
    """Button to start the EffortlessHome add-on through Supervisor."""

    _attr_name = "Start EffortlessHome Add-on"
    _attr_icon = "mdi:play"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize button."""
        self.hass = hass
        self._attr_unique_id = f"start_effortlesshome_addon_button_{entry.entry_id}"
        self._attr_config_entry_id = entry.entry_id

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
            "model": NAME,
        }

    async def async_press(self) -> None:
        """Start the EffortlessHome add-on through Supervisor."""
        from . import async_control_effortlesshome_addon

        _LOGGER.info("[EffortlessHome] Starting EffortlessHome add-on")
        await async_control_effortlesshome_addon(self.hass, "start")


class StopEffortlessHomeAddonButton(ButtonEntity):
    """Button to stop the EffortlessHome add-on through Supervisor."""

    _attr_name = "Stop EffortlessHome Add-on"
    _attr_icon = "mdi:stop"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, entry) -> None:
        """Initialize button."""
        self.hass = hass
        self._attr_unique_id = f"stop_effortlesshome_addon_button_{entry.entry_id}"
        self._attr_config_entry_id = entry.entry_id

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
            "model": NAME,
        }

    async def async_press(self) -> None:
        """Stop the EffortlessHome add-on through Supervisor."""
        from . import async_control_effortlesshome_addon

        _LOGGER.info("[EffortlessHome] Stopping EffortlessHome add-on")
        await async_control_effortlesshome_addon(self.hass, "stop")
