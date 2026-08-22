# Changelog

## v1.2.0 (2026-08-23)

### Changed
- Updated the JRC REMap API base URL to the new `/mapSvc` path (the old endpoint no longer works). The base URL now lives in a single `API_BASE_URL` constant in `const.py`.
- Switched to Home Assistant's shared aiohttp session instead of creating a new session on every poll.
- Replaced the deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` (API timestamp format unchanged).

### Added
- Clear Home Assistant logging for offline, stale, unreachable, HTTP-error, and malformed-data conditions, each naming the affected station. Messages are logged on state change (repeats drop to DEBUG) to avoid log spam, with a single INFO recovery line when a station comes back.
- Entities now go `unavailable` on hard failure (no fresh data and no usable cached value) via `UpdateFailed`.
- New `status` and `is_stale` attributes so degraded/stale conditions are visible in the entity state, not just the logs.

## v1.1.0 (2025-04-06)

### Fixed
- Resolved API encoding issues with station codes in responses
- Fixed AttributeError related to response charset property
- Improved error handling for empty or unexpected API responses

### Added
- Retry mechanism (3 attempts) for handling transient errors
- Extended data fetch window from 24 to 72 hours
- Multiple encoding fallbacks (UTF-8 and Latin-1)
- Additional attributes for debugging (returned_code, status)

### Changed
- Enhanced logging with more detailed diagnostic information
- Improved data state persistence during API failures
- More resilient JSON parsing for handling encoding variations

## v1.0.0 (2025-03-15)

### Initial Release
- First public release of the Radiation Monitor integration
- Support for REMAP JRC radiation monitoring stations
- Configurable update intervals
- Custom services for forcing data updates
