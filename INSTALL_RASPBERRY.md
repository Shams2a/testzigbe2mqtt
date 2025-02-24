# Installing Zigbee Manager on Raspberry Pi

## Prerequisites

1. Raspberry Pi with Raspberry Pi OS (previously called Raspbian)
2. Python 3.7 or higher
3. A supported Zigbee adapter (e.g., CC2531, CC2538, or similar)
4. Internet connection for downloading dependencies

## Installation Steps

1. First, clone the repository:
   ```bash
   git clone <repository-url>
   cd zigbee-manager
   ```

2. Run the installation script with sudo:
   ```bash
   sudo python3 install_raspberry.py
   ```

   This script will:
   - Install required system dependencies
   - Set up a Python virtual environment
   - Install Python packages
   - Configure USB permissions for the Zigbee adapter
   - Create and enable systemd services

3. Reboot your Raspberry Pi:
   ```bash
   sudo reboot
   ```

4. After reboot, check the service status:
   ```bash
   sudo systemctl status zigbee-manager-headless
   ```

## Operating Modes

### Headless Mode (Default)
- Runs without GUI, suitable for running as a service
- Enabled by default during installation
- All operations can be monitored through logs

To manage the headless service:
```bash
# Start the service
sudo systemctl start zigbee-manager-headless

# Check status
sudo systemctl status zigbee-manager-headless

# View logs
journalctl -u zigbee-manager-headless -f
```

### GUI Mode
- Provides a graphical interface for management
- Requires X11 display access

To switch to GUI mode:
```bash
# Disable headless service
sudo systemctl disable zigbee-manager-headless
sudo systemctl stop zigbee-manager-headless

# Enable and start GUI service
sudo systemctl enable zigbee-manager-gui
sudo systemctl start zigbee-manager-gui
```

## Configuration

1. The MQTT broker settings can be configured through the UI or by editing `config.json`:
   ```json
   {
     "mqtt": {
       "broker": "your-broker-address",
       "port": 443,
       "username": "your-username",
       "password": "your-password"
     }
   }
   ```

2. The Zigbee adapter is automatically detected, but you can specify a custom port in `config.json`:
   ```json
   {
     "zigbee": {
       "port": "/dev/ttyACM0",
       "channel": 11,
       "pan_id": "0x1a62"
     }
   }
   ```

## Troubleshooting

1. If the Zigbee adapter is not detected:
   - Check if it's properly plugged in
   - Verify the USB port permissions:
     ```bash
     ls -l /dev/ttyACM*
     ```
   - The device should be accessible by your user (in the 'dialout' group)

2. If the MQTT connection fails:
   - Verify your internet connection
   - Check the broker address and credentials in settings
   - Look for detailed error messages in the logs:
     ```bash
     tail -f logs/mqtt.log
     ```

3. For X11 display issues in GUI mode:
   - Ensure X11 is running and DISPLAY is set correctly
   - Check the Xauthority file permissions
   - Consider using headless mode if GUI is not required

4. For other issues:
   - Check the application logs:
     ```bash
     tail -f logs/zigbee_manager.log
     ```
   - Restart the appropriate service:
     ```bash
     sudo systemctl restart zigbee-manager-headless
     # or
     sudo systemctl restart zigbee-manager-gui
     ```

## Support

For issues and support:
1. Check the logs in the `logs` directory
2. Look for error messages in the systemd journal
3. File an issue in the project repository with:
   - Detailed error description
   - Relevant log entries
   - Your configuration (without sensitive data)