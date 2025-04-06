"""Sensor platform for Radiation Monitor integration."""
from datetime import datetime
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
try:
    # Try importing the radiation device class (may be available in future versions)
    from homeassistant.components.sensor import SensorDeviceClass
    HAS_RADIATION_DEVICE_CLASS = hasattr(SensorDeviceClass, "RADIATION")
except (ImportError, AttributeError):
    HAS_RADIATION_DEVICE_CLASS = False

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_DIVISOR,
    ATTR_RAW_VALUE,
    ATTR_STAMP,
    ATTR_STATION_CODE,
    ATTR_TIMESTAMP,
    CONF_STATION_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Radiation Monitor sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    station_name = entry.data[CONF_STATION_NAME]
    
    async_add_entities([RadiationSensor(coordinator, station_name)], True)


class RadiationSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Radiation sensor."""

    # Use a custom device class for radiation
    _attr_device_class = "radiation" if HAS_RADIATION_DEVICE_CLASS else None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "nSv/h"
    _attr_has_entity_name = True
    
    @property
    def device_class(self):
        """Return the device class of the sensor."""
        # Return 'radiation' as a custom device class
        return "radiation"
    
    def __init__(self, coordinator: DataUpdateCoordinator, station_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"Radiation {station_name}"
        self._attr_unique_id = f"radiation_{coordinator.station_code}"
        
        # Set suggested area based on the station name
        self._attr_suggested_area = station_name
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data["value"]
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        if not self.coordinator.data:
            return {}
            
        attrs = {
            ATTR_TIMESTAMP: self.coordinator.data["timestamp"],
            ATTR_STATION_CODE: self.coordinator.data["station_code"],
            ATTR_RAW_VALUE: self.coordinator.data["raw_value"],
            ATTR_STAMP: self.coordinator.data["stamp"],
            ATTR_DIVISOR: self.coordinator.data["divisor"],
        }
        
        # Add any additional attributes that might be in the data
        for key in ["returned_code", "status"]:
            if key in self.coordinator.data:
                attrs[key] = self.coordinator.data[key]
        
        return attrs
    
    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:radioactive"
