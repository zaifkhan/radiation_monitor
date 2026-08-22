"""Constants for the Radiation Monitor integration."""

DOMAIN = "radiation_monitor"

# Configuration constants
CONF_STATION_CODE = "station_code"
CONF_STATION_NAME = "station_name"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL = 3600  # 60 minutes

# Base URL for the JRC REMap timeseries API.
# Full path: {API_BASE_URL}/timeseries/{start}/{now}?codes={code}
API_BASE_URL = "https://remap.jrc.ec.europa.eu/mapSvc/api/timeseries/v1/stations"

# If the newest reading is older than this, treat the station as offline/stale.
STALE_AFTER_SECONDS = 3 * DEFAULT_SCAN_INTERVAL

# Platform definitions
PLATFORMS = ["sensor"]

# Sensor attributes
ATTR_TIMESTAMP = "timestamp"
ATTR_STATION_CODE = "station_code"
ATTR_RAW_VALUE = "raw_value"
ATTR_STAMP = "stamp"
ATTR_DIVISOR = "divisor"