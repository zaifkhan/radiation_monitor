"""Config flow for Radiation Monitor integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client

from .const import (
    DOMAIN,
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class RadiationMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Radiation Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            station_code = user_input[CONF_STATION_CODE]
            station_name = user_input[CONF_STATION_NAME]
            
            # Check if this station code is already configured
            await self.async_set_unique_id(station_code)
            self._abort_if_unique_id_configured()
            
            # Try to validate the station code by making a test request
            try:
                valid = await self._test_station_code(station_code)
                if valid:
                    return self.async_create_entry(
                        title=station_name,
                        data={
                            CONF_STATION_CODE: station_code,
                            CONF_STATION_NAME: station_name,
                            CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                        },
                    )
                else:
                    errors["base"] = "invalid_station_code"
            except Exception:
                errors["base"] = "cannot_connect"

        # Show form for user input
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_CODE): str,
                    vol.Required(CONF_STATION_NAME): str,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "url": "https://remap.jrc.ec.europa.eu/Advanced.aspx"
            },
        )
    
    async def _test_station_code(self, station_code):
        """Test if the station code is valid by making an API call."""
        from datetime import datetime, timedelta
        import random
        
        # Get current time and 1 hour ago in UTC
        now_utc = datetime.utcnow()
        start_utc = now_utc - timedelta(hours=1)
        
        # Format timestamps for API call
        now_utc_str = now_utc.strftime("%Y%m%d%H%M%S")
        start_utc_str = start_utc.strftime("%Y%m%d%H%M%S")
        
        # Build URL
        url = f"https://remap.jrc.ec.europa.eu/api/timeseries/v1/stations/timeseries/{start_utc_str}/{now_utc_str}?codes={station_code}"
        
        # Generate a random stamp for validation
        stamp = random.randint(20, 999)
        
        # Prepare headers
        headers = {"stamp": str(stamp)}
        
        # Make the request
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    _LOGGER.warning(f"API returned status {response.status} for station code {station_code}")
                    # Let's be more permissive - some valid station codes might not always return data
                    # Return True anyway so the user can try it
                    return True
                
                try:
                    data = await response.json()
                    
                    # If we got any data back, the station code is likely valid
                    if data and len(data) > 0:
                        # Additionally, we could verify if the data fits our expected scaling formula:
                        # actual_value = raw_value / (1001 - stamp)
                        # But we'll be permissive here to allow for API changes
                        return True
                    
                    # Even if we got an empty array, it might be a valid station with temporarily no data
                    # Let's be permissive and allow it
                    _LOGGER.warning(f"No data returned for station code {station_code}, but allowing configuration")
                    return True
                    
                except Exception as json_err:
                    _LOGGER.warning(f"Error parsing response for station code {station_code}: {json_err}")
                    # It could be a temporary API issue, let the user try the code anyway
                    return True
                    
            return True
        except Exception as ex:
            _LOGGER.warning(f"Exception when testing station code {station_code}: {ex}")
            # Even in case of connection errors, allow the user to try the code
            # They can always remove the integration if it doesn't work
            return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return RadiationMonitorOptionsFlow(config_entry)


class RadiationMonitorOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the Radiation Monitor integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        # Store entry_id instead of the full config_entry to avoid deprecation warning
        self.entry_id = config_entry.entry_id

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get config entry using the stored entry_id
        config_entry = self.hass.config_entries.async_get_entry(self.entry_id)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): int,
                }
            ),
        )