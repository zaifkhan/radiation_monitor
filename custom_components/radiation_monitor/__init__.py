"""The Radiation Monitor integration."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
import random

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE_URL,
    CONF_STATION_CODE,
    CONF_STATION_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    STALE_AFTER_SECONDS,
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
        # Last outcome of a poll, used so we only log a problem once per
        # state change instead of on every scan interval.
        self._last_status: str | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"Radiation {station_name}",
            update_interval=timedelta(seconds=scan_interval),
        )
    
    def _record_status(self, status: str, message: str, level: int) -> None:
        """Record the outcome of a poll and log it, only on state change.

        A transition into a problem state (or between problem states) is logged
        at the requested level; while the same condition persists it drops to
        DEBUG so we don't spam the log. A return to "ok" emits a single INFO
        recovery line.
        """
        if status == "ok":
            if self._last_status not in (None, "ok"):
                _LOGGER.info(
                    "Radiation Monitor: station %s (%s) recovered — fresh data received again",
                    self.station_name,
                    self.station_code,
                )
            else:
                _LOGGER.debug(message)
        elif status == self._last_status:
            # Same problem as last time: keep it at DEBUG.
            _LOGGER.debug(message)
        else:
            _LOGGER.log(level, message)
        self._last_status = status

    def _fail(self, status: str, message: str, level: int):
        """Handle a failed poll: log on state change, then degrade or raise.

        If a last-known value exists we keep returning it (flagged with the
        failure status and ``is_stale``) so the entity doesn't flap. With no
        usable cache we raise ``UpdateFailed`` so HA marks the entity
        unavailable and the outage is visible in the UI as well as the log.
        """
        self._record_status(status, message, level)
        if self.data:
            degraded = dict(self.data)
            degraded["status"] = status
            degraded["is_stale"] = True
            return degraded
        raise UpdateFailed(message)

    def _parse_reading_datetime(self, value):
        """Best-effort parse of an API reading timestamp to an aware UTC datetime.

        Returns None if the value is missing or unparseable so the caller can
        skip the staleness check rather than crash.
        """
        if not isinstance(value, str) or not value.strip():
            return None
        text = value.strip()
        # Try ISO 8601 first (accepting a trailing "Z").
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        # Fall back to the compact API timestamp format (assumed UTC).
        try:
            return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        session = async_get_clientsession(self.hass)

        # Get current time and 72 hours ago in UTC (3 day window)
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(hours=72)

        # Format timestamps for API call (format must stay %Y%m%d%H%M%S)
        now_utc_str = now_utc.strftime("%Y%m%d%H%M%S")
        start_utc_str = start_utc.strftime("%Y%m%d%H%M%S")

        # Build URL from the single-source base URL in const.py
        url = f"{API_BASE_URL}/timeseries/{start_utc_str}/{now_utc_str}?codes={self.station_code}"

        # Prepare headers with our stamp
        headers = {"stamp": str(self.stamp)}

        max_retries = 3
        last_client_error = None

        for attempt in range(1, max_retries + 1):
            try:
                # HA owns the shared session's lifecycle — do not use `async with`.
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                    _LOGGER.debug(
                        "Raw response text (first 500 chars): %s", response_text[:500]
                    )

                    # HTTP error from the API
                    if response.status != 200:
                        return self._fail(
                            "http_error",
                            "Radiation Monitor: station %s (%s) returned HTTP status %s"
                            % (self.station_name, self.station_code, response.status),
                            logging.WARNING,
                        )

                    # Parse the response as JSON (with a Latin-1 fallback)
                    try:
                        data = json.loads(response_text)
                    except json.JSONDecodeError:
                        _LOGGER.debug("Trying alternative encoding for JSON parsing")
                        try:
                            data = json.loads(
                                response_text.encode("utf-8").decode("latin-1")
                            )
                        except Exception as enc_err:
                            return self._fail(
                                "bad_data",
                                "Radiation Monitor: station %s (%s) sent an unparseable "
                                "payload: %s"
                                % (self.station_name, self.station_code, enc_err),
                                logging.ERROR,
                            )

                    # Empty response / station not in payload → offline
                    if not data:
                        return self._fail(
                            "offline",
                            "Radiation Monitor: station %s (%s) returned no data — "
                            "treating as offline / not reporting"
                            % (self.station_name, self.station_code),
                            logging.WARNING,
                        )

                    if len(data) >= 2:
                        _LOGGER.debug("Received data: %s", data[:2])
                    else:
                        _LOGGER.debug("Received data: %s", data)

                    # Extract the newest reading
                    last_entry = data[-1]
                    try:
                        last_value = last_entry["value"]
                    except (KeyError, TypeError) as key_err:
                        return self._fail(
                            "bad_data",
                            "Radiation Monitor: station %s (%s) sent malformed data, "
                            "missing 'value': %s"
                            % (self.station_name, self.station_code, key_err),
                            logging.ERROR,
                        )

                    scaled_value = round(last_value / self.divisor, 3)
                    timestamp = last_entry.get("date", now_utc.isoformat())

                    # Freshness / staleness check
                    reading_dt = self._parse_reading_datetime(last_entry.get("date"))
                    if reading_dt is None:
                        _LOGGER.debug(
                            "Radiation Monitor: station %s (%s) has missing/unparseable "
                            "reading date %r — skipping staleness check",
                            self.station_name,
                            self.station_code,
                            last_entry.get("date"),
                        )
                    elif (now_utc - reading_dt).total_seconds() > STALE_AFTER_SECONDS:
                        # Degraded: keep the last-known value but flag it as stale.
                        self._record_status(
                            "stale",
                            "Radiation Monitor: station %s (%s) newest reading is older "
                            "than %s s — treating as stale"
                            % (
                                self.station_name,
                                self.station_code,
                                STALE_AFTER_SECONDS,
                            ),
                            logging.WARNING,
                        )
                        return {
                            "value": scaled_value,
                            "raw_value": last_value,
                            "timestamp": timestamp,
                            "station_code": self.station_code,
                            "returned_code": last_entry.get("code", "unknown"),
                            "stamp": self.stamp,
                            "divisor": self.divisor,
                            "status": "stale",
                            "is_stale": True,
                        }

                    # Fresh, valid data — success (also logs recovery if needed)
                    self._record_status(
                        "ok",
                        "Radiation Monitor: station %s (%s) updated successfully"
                        % (self.station_name, self.station_code),
                        logging.DEBUG,
                    )
                    return {
                        "value": scaled_value,
                        "raw_value": last_value,
                        "timestamp": timestamp,
                        "station_code": self.station_code,
                        "returned_code": last_entry.get("code", "unknown"),
                        "stamp": self.stamp,
                        "divisor": self.divisor,
                        "status": "online",
                        "is_stale": False,
                    }

            except (aiohttp.ClientError, asyncio.TimeoutError) as client_err:
                # Network/DNS/timeout — retry, then classify as unreachable.
                last_client_error = client_err
                if attempt < max_retries:
                    _LOGGER.debug(
                        "Radiation Monitor: station %s (%s) fetch attempt %s/%s failed: "
                        "%s — retrying",
                        self.station_name,
                        self.station_code,
                        attempt,
                        max_retries,
                        client_err,
                    )
                    await asyncio.sleep(2)
                    continue

        # Retries exhausted without a successful response → unreachable
        return self._fail(
            "unreachable",
            "Radiation Monitor: station %s (%s) unreachable after %s attempts: %s"
            % (self.station_name, self.station_code, max_retries, last_client_error),
            logging.ERROR,
        )
