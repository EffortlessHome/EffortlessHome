"""Cover group."""

from __future__ import annotations  # noqa: D100, EXE002

from functools import cached_property
import logging

from homeassistant.components.cover import (
    DEVICE_CLASSES as COVER_DEVICE_CLASSES,
    DOMAIN as COVER_DOMAIN,
    CoverDeviceClass,
)
from homeassistant.components.group.cover import CoverGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .auto_area import AutoArea
from .const import COVER_GROUP_ENTITY_PREFIX, COVER_GROUP_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


def set_cover_group_active(hass: HomeAssistant, unique_id: str, active: bool) -> None:
    """Enable or disable the cover group of this integration.

    A group with no covers is disabled by the integration, so it stays in the
    registry but is inactive. The entity is re-enabled as soon as the area has
    at least one cover.
    """
    registry = entity_registry.async_get(hass)
    entity_id = registry.async_get_entity_id(COVER_DOMAIN, DOMAIN, unique_id)
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entities."""
    areas = area_registry.async_get(hass)

    # Loop over each area and find associated motion sensors
    for area_id, area in areas.areas.items():
        auto_area = AutoArea(hass=hass, areaid=area_id)

        cover_entity_ids: list[str] = auto_area.get_area_entity_ids(
            COVER_DEVICE_CLASSES
        )

        if not cover_entity_ids:
            _LOGGER.info(
                "%s: No covers found in area. Cover group will be inactive.",
                auto_area.area_name,
            )

        # The cover group is created for every area, even when it has no
        # covers. An empty group is disabled by the integration ("inactive").
        set_cover_group_active(hass, f"{area_id}_cover_group", bool(cover_entity_ids))
        async_add_entities(
            [AutoCoverGroup(hass, auto_area, entity_ids=cover_entity_ids)]
        )


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the platform."""
    # We only want this platform to be set up via discovery.
    if discovery_info is None:
        return

    areas = area_registry.async_get(hass)

    # Loop over each area and find associated motion sensors
    for area_id, area in areas.areas.items():
        auto_area = AutoArea(hass=hass, areaid=area_id)

        cover_entity_ids: list[str] = auto_area.get_area_entity_ids(
            COVER_DEVICE_CLASSES
        )

        if not cover_entity_ids:
            _LOGGER.info(
                "%s: No covers found in area. Cover group will be inactive.",
                auto_area.area_name,
            )

        set_cover_group_active(hass, f"{area_id}_cover_group", bool(cover_entity_ids))
        add_entities([AutoCoverGroup(hass, auto_area, entity_ids=cover_entity_ids)])


class AutoCoverGroup(CoverGroup):
    """Cover group with area covers."""

    def __init__(self, hass, auto_area: AutoArea, entity_ids: list[str]) -> None:
        """Initialize cover group."""
        self.hass = hass
        self.auto_area = auto_area
        self._device_class = CoverDeviceClass.BLIND
        self._name_prefix = COVER_GROUP_PREFIX
        self._prefix = COVER_GROUP_ENTITY_PREFIX
        self.entity_ids: list[str] = entity_ids

        # An area without covers results in an inactive (disabled by the
        # integration) cover group.
        self._attr_entity_registry_enabled_default = bool(entity_ids)

        CoverGroup.__init__(
            self,
            entities=self.entity_ids,
            name="",
            unique_id=self._attr_unique_id,
        )
        _LOGGER.info(
            "%s (%s): Initialized cover group. Entities: %s",
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
        return f"{self.auto_area.area_id}_cover_group"

    @property
    def icon(self):
        # Return the specified icon or a default one
        return "mdi:garage-variant"
