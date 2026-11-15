from __future__ import annotations  # noqa: D100, EXE002

import logging
from functools import cached_property

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry, entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_platforms,
)
from homeassistant.util import slugify

from .auto_area import AutoArea
from .const import DOMAIN, LIGHT_GROUP_ENTITY_PREFIX, LIGHT_GROUP_PREFIX, NAME
from .ha_helpers import creates_group_cycle, get_all_entities
from .sensor import VirtualPowerSensor

_LOGGER = logging.getLogger(__name__)

ALL_LIGHT_GROUP_UNIQUE_ID = "all_light_group"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    areas = area_registry.async_get(hass)

    # Initialize a list for all light entity IDs across areas
    all_light_entity_ids = []

    # Loop over each area to find associated light entities
    for area_id, area in areas.areas.items():
        auto_area = AutoArea(hass=hass, areaid=area_id)

        light_entity_ids = get_area_light_entity_ids(hass, auto_area)

        if not light_entity_ids:
            _LOGGER.info(
                "%s: No lights found in area. Light group will be inactive.",
                auto_area.area_name,
            )
        else:
            all_light_entity_ids.extend(light_entity_ids)  # Extend instead of append

        # The group is created for every area, even when it has no members.
        # An empty group is disabled by the integration ("inactive").
        set_light_group_active(
            hass,
            get_area_light_group_unique_id(area_id),
            bool(light_entity_ids),
        )
        async_add_entities(
            [AutoLightGroup(hass, auto_area, entity_ids=light_entity_ids)]
        )

    # Add an AllLightGroup with all light entities across areas
    all_light_entity_ids = get_all_light_entity_ids(hass, all_light_entity_ids)
    set_light_group_active(hass, ALL_LIGHT_GROUP_UNIQUE_ID, bool(all_light_entity_ids))
    async_add_entities(
        [
            AllLightGroup(
                hass,
                entity_ids=all_light_entity_ids,
            )
        ]
    )


def get_light_group_entity_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Return the entity id of a light group created by this integration."""
    registry = entity_registry.async_get(hass)
    return registry.async_get_entity_id(LIGHT_DOMAIN, DOMAIN, unique_id)


def get_area_light_group_unique_id(area_id: str) -> str:
    """Return the unique id of the light group for an area."""
    return f"{area_id}_light_group"


def set_light_group_active(hass: HomeAssistant, unique_id: str, active: bool) -> None:
    """Enable or disable the light group of this integration.

    A group with no members is disabled by the integration, so it stays in the
    registry but is inactive. The entity is re-enabled as soon as the area has
    at least one light.
    """
    registry = entity_registry.async_get(hass)
    entity_id = registry.async_get_entity_id(LIGHT_DOMAIN, DOMAIN, unique_id)
    if entity_id is None:
        return

    entry = registry.async_get(entity_id)
    if entry is None:
        return

    if active:
        if entry.disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity_id, disabled_by=None)
        return

    if entry.disabled_by is None:
        registry.async_update_entity(
            entity_id, disabled_by=entity_registry.RegistryEntryDisabler.INTEGRATION
        )


def get_area_light_entity_ids(hass: HomeAssistant, auto_area: AutoArea) -> list[str]:
    """Return the light entity ids to group for an area."""
    group_entity_id = get_light_group_entity_id(
        hass, get_area_light_group_unique_id(auto_area.area_id)
    )

    entity_ids: list[str] = []
    for entity in get_all_entities(
        auto_area.entity_registry,
        auto_area.device_registry,
        auto_area.area_id,
        [LIGHT_DOMAIN],
    ):
        # Light groups created by this integration are never a member of an
        # area light group. They would end up referencing each other.
        if entity.platform == DOMAIN:
            continue

        # Skip anything that would make the group reference itself.
        if creates_group_cycle(hass, group_entity_id, entity.entity_id):
            _LOGGER.warning(
                "%s: Not adding %s to the area light group, it would create a "
                "circular reference.",
                auto_area.area_name,
                entity.entity_id,
            )
            continue

        entity_ids.append(entity.entity_id)

    return entity_ids


def get_all_light_entity_ids(hass: HomeAssistant, entity_ids: list[str]) -> list[str]:
    """Return the light entity ids to group for all areas."""
    group_entity_id = get_light_group_entity_id(hass, ALL_LIGHT_GROUP_UNIQUE_ID)

    filtered_entity_ids: list[str] = []
    for entity_id in entity_ids:
        # Skip anything that would make the group reference itself.
        if creates_group_cycle(hass, group_entity_id, entity_id):
            _LOGGER.warning(
                "All Lights: Not adding %s to the light group, it would create a "
                "circular reference.",
                entity_id,
            )
            continue

        filtered_entity_ids.append(entity_id)

    return filtered_entity_ids


class AutoLightGroup(LightGroup):
    """Area Lights."""

    def __init__(self, hass, auto_area: AutoArea, entity_ids: list[str]) -> None:
        """Initialize light group."""
        self.hass = hass
        self.auto_area = auto_area
        self._name_prefix = LIGHT_GROUP_PREFIX
        self._prefix = LIGHT_GROUP_ENTITY_PREFIX
        self.entity_ids: list[str] = entity_ids
        # An area without lights results in an inactive (disabled by the
        # integration) light group.
        self._attr_entity_registry_enabled_default = bool(entity_ids)
        # Ensure entity_id is 'light.area_<areaname>'
        self._entity_id = (
            f"{LIGHT_GROUP_ENTITY_PREFIX}{slugify(self.auto_area.area_name)}"
        )

        LightGroup.__init__(
            self,
            unique_id=self._attr_unique_id,
            name="",
            entity_ids=self.entity_ids,
            mode=None,
        )
        _LOGGER.info(
            "%s (%s): Initialized light group. Entities: %s",
            self.auto_area.area_name,
            self.device_class,
            self.entity_ids,
        )

    @cached_property
    def name(self):
        """Name of this entity."""
        return f"{self._name_prefix}{self.auto_area.area_name}"

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Information about this device."""
        return self.auto_area.device_info

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return get_area_light_group_unique_id(self.auto_area.area_id)

    @property
    def icon(self):
        # Return the specified icon or a default one
        return "mdi:ceiling-light-multiple-outline"


class AllLightGroup(LightGroup):
    """Cover group with area covers."""

    def __init__(self, hass, entity_ids: list[str]) -> None:
        """Initialize cover group."""
        self.hass = hass
        self.entity_ids: list[str] = entity_ids

        # An empty all-lights group is inactive (disabled by the integration).
        self._attr_entity_registry_enabled_default = bool(entity_ids)

        LightGroup.__init__(
            self,
            unique_id=self._attr_unique_id,
            name="",
            entity_ids=self.entity_ids,
            mode=None,
        )

    @cached_property
    def name(self):
        """Name of this entity."""
        return "All Lights"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, NAME)},
            "name": NAME,
            "manufacturer": NAME,
        }

    @cached_property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return ALL_LIGHT_GROUP_UNIQUE_ID

    @property
    def icon(self):
        # Return the specified icon or a default one
        return "mdi:ceiling-light-multiple-outline"
