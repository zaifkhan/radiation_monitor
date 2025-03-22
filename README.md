# Radiation Monitor

This custom component for Home Assistant allows you to monitor radiation levels from radiation monitoring stations across Europe using the REMAP JRC network.

## Features

- Easy setup through config flow UI
- Automatic data retrieval and calculation of accurate radiation values
- Configurable update intervals
- Support for multiple stations

## Installation

### HACS Installation (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Go to HACS → Integrations → Click the three dots in the upper right corner → Custom repositories
3. Add this repository URL: `https://github.com/zaifkhan/radiation_monitor`
4. Select "Integration" as the category
5. Click "Add"
6. Search for "Radiation Monitor" in the HACS Integrations store
7. Click Install

### Manual Installation

1. Download the latest release
2. Unpack the release and copy the `custom_components/radiation_monitor` directory into your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "Add Integration" and search for "Radiation Monitor"
3. Follow the configuration steps:
   - Visit [REMAP JRC Advanced Map](https://remap.jrc.ec.europa.eu/Advanced.aspx) to find your local station
   - Enter the station code (e.g., EE20395 for Tallinn, Estonia)
   - Provide a name for the station (e.g., "Radiation Tallinn")
   - Set your preferred update interval (please use sensible values, recommended 60 minutes)

## Finding Your Station Code

1. Visit [REMAP JRC Advanced Map](https://remap.jrc.ec.europa.eu/Advanced.aspx)
2. Navigate to your location on the map
3. Click on the nearest station marker
4. Note the station code (usually a country code followed by numbers, e.g., EE20395)

## Technical Details

This integration uses the REMAP JRC API to fetch radiation data and applies a mathematical formula to calculate the actual radiation values in nSv/h. The integration randomizes the stamp parameter to ensure stability and reliability of the data retrieval process.

The formula used to calculate the actual radiation value is:
```
actual_value = raw_value / (1001 - stamp)
```

Where:
- `raw_value` is the value returned by the API
- `stamp` is a random number between 20 and 999 generated when the integration is set up
- The division factor `(1001 - stamp)` is calculated automatically

## Troubleshooting

If you encounter any issues:

1. Check that your station code is correct
2. Verify your Home Assistant can access the internet
3. Check the logs for any error messages
4. Try increasing the update interval if you experience API timeouts

## Credits

- Data source: REMAP JRC network
- This integration is not affiliated with or endorsed by the European Commission's Joint Research Centre

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Feel free to submit pull requests or suggest features/improvements.