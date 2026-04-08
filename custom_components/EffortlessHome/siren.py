import logging  # noqa: D100, EXE002, N999

from homeassistant.helpers import entity_registry

_LOGGER = logging.getLogger(__name__)

DOMAIN = "siren_groups"


class SirenGrouper:
    """Class to group all sirens."""

    def __init__(self, hass) -> None:
        """Initialize the siren grouper."""
        self.hass = hass
        _LOGGER.debug("[SirenGrouper] Initialized with hass object.")

    async def create_siren_group(self) -> None:
        """Create a group of all sirens."""
        _LOGGER.debug("[SirenGrouper] create_siren_group called.")
        entities = entity_registry.async_get(self.hass)
        sirens = [
            entity.entity_id
            for entity in entities.entities.values()
            if entity.domain == "siren"
        ]
        _LOGGER.debug(f"[SirenGrouper] Found sirens: {sirens}")
        group_name = "group.all_sirens"
        await self._create_group(group_name, sirens)

    async def _create_group(self, group_name, entity_ids) -> None:  # noqa: ANN001
        """Create a group of entities in Home Assistant."""
        _LOGGER.debug(
            f"[SirenGrouper] Creating group '{group_name}' with entities: {entity_ids}"
        )
        service_data = {
            "object_id": group_name.split(".")[-1],
            "name": group_name.split(".")[-1].replace("_", " ").title(),
            "entities": entity_ids,
        }
        await self.hass.services.async_call("group", "set", service_data, blocking=True)
        _LOGGER.debug(
            f"[SirenGrouper] Group '{group_name}' created with entities: {entity_ids}"
        )