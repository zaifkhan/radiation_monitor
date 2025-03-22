"""The Radiation Monitor integration."""
import asyncio
import logging
from datetime import datetime, timedelta
import random

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Radiation Monitor component."""
    hass.data.setdefault(DOMAIN, {})
    
    # Set up services
    from .services import async_setup_services
    await async_setup_services(hass)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Radiation Monitor from a config entry."""
    station_code = entry.data[CONF_STATION_CODE]
    station_name = entry.data[CONF_STATION_NAME]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    # Generate a random stamp between 20 and 999 when setting up the integration
    # This will be used throughout the life of the integration
    stamp = random.randint(20, 999)
    
    # Calculate the divisor based on our refined formula: divisor = 1001 - stamp
    divisor = 1001 - stamp
    
    coordinator = RadiationUpdateCoordinator(
        hass,
        station_code=station_code,
        station_name=station_name,
        scan_interval=scan_interval,
        stamp=stamp,
        divisor=divisor,
    )
    
    await coordinator.async_config_entry_first_refresh()
    
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Use the new async_forward_entry_setups method instead of async_forward_entry_setup
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Use the new unload_platforms method instead of async_forward_entry_unload
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # If there are no more entries, unload services
        if not hass.data[DOMAIN]:
            from .services import async_unload_services
            await async_unload_services(hass)
    
    return unload_ok

class RadiationUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching radiation data."""

    def __init__(
        self,
        hass: HomeAssistant,
        station_code: str,
        station_name: str,
        scan_interval: int,
        stamp: int,
        divisor: float,
    ):
        """Initialize."""
        self.station_code = station_code
        self.station_name = station_name
        self.stamp = stamp
        self.divisor = divisor
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Radiation {station_name}",
            update_interval=timedelta(seconds=scan_interval),
        )
    
    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Get current time and 24 hours ago in UTC
            now_utc = datetime.utcnow()
            start_utc = now_utc - timedelta(hours=24)
            
            # Format timestamps for API call
            now_utc_str = now_utc.strftime("%Y%m%d%H%M%S")
            start_utc_str = start_utc.strftime("%Y%m%d%H%M%S")
            
            # Build URL
            url = f"https://remap.jrc.ec.europa.eu/api/timeseries/v1/stations/timeseries/{start_utc_str}/{now_utc_str}?codes={self.station_code}"
            
            # Prepare headers with our stamp
            headers = {"stamp": str(self.stamp)}
            
            # Fetch data
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status != 200:
                            _LOGGER.warning(f"API returned status {response.status} for station {self.station_name} ({self.station_code})")
                            # Return last known good data if available
                            if self.data:
                                return self.data
                            raise UpdateFailed(f"Error fetching data: {response.status}")
                        
                        data = await response.json()
                        
                        if not data or len(data) == 0:
                            _LOGGER.warning(f"No data returned from API for station {self.station_name} ({self.station_code})")
                            # Return last known good data if available
                            if self.data:
                                return self.data
                            raise UpdateFailed("No data returned from API")
                        
                        # Extract the last value and scale appropriately
                        last_value = data[-1]["value"]
                        scaled_value = round(last_value / self.divisor, 3)
                        
                        return {
                            "value": scaled_value,
                            "raw_value": last_value,
                            "timestamp": data[-1]["date"],
                            "station_code": self.station_code,
                            "stamp": self.stamp,
                            "divisor": self.divisor,
                        }
                except aiohttp.ClientError as client_err:
                    _LOGGER.error(f"Client error for {self.station_name}: {client_err}")
                    if self.data:
                        return self.data
                    raise UpdateFailed(f"Connection error: {client_err}")
        
        except Exception as err:
            _LOGGER.exception(f"Error updating radiation data for {self.station_name}: {err}")
            # Return last known good data if available
            if self.data:
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}")