# Changelog

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
