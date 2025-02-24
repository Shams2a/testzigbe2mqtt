#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def setup_environment():
    """Set up Python environment and install dependencies"""
    print("Setting up Python environment...")

    # Install system dependencies
    print("Installing system dependencies...")
    run_command("sudo apt-get update")
    run_command("sudo apt-get install -y python3-pip python3-venv python3-tk")

    # Create virtual environment
    run_command("python3 -m venv venv")

    # Install Python dependencies
    print("Installing Python dependencies...")
    run_command("./venv/bin/pip install paho-mqtt zigpy aiohttp asyncio")

def setup_usb_permissions():
    """Set up USB permissions for Zigbee adapter"""
    rules_file = "/etc/udev/rules.d/99-zigbee.rules"

    print("Setting up USB permissions for Zigbee adapter...")

    # Create udev rule for Zigbee USB adapter
    rule = 'SUBSYSTEM=="tty", ATTRS{idVendor}=="0451", ATTRS{idProduct}=="16a8", SYMLINK+="zigbee", GROUP="dialout", MODE="0660"'

    with open("/tmp/99-zigbee.rules", "w") as f:
        f.write(rule)

    run_command(f"sudo mv /tmp/99-zigbee.rules {rules_file}")
    run_command("sudo udevadm control --reload-rules")
    run_command("sudo udevadm trigger")

    # Add current user to dialout group
    run_command("sudo usermod -a -G dialout $USER")

def create_service():
    """Create systemd service for auto-start"""
    # Create both GUI and headless service files
    gui_service_content = f"""[Unit]
Description=Zigbee Manager Service (GUI)
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={os.getcwd()}
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/{os.getenv('USER')}/.Xauthority
ExecStart={os.getcwd()}/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
"""

    headless_service_content = f"""[Unit]
Description=Zigbee Manager Service (Headless)
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={os.getcwd()}
Environment=HEADLESS=1
ExecStart={os.getcwd()}/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    # Write service files
    with open("/tmp/zigbee-manager-gui.service", "w") as f:
        f.write(gui_service_content)

    with open("/tmp/zigbee-manager-headless.service", "w") as f:
        f.write(headless_service_content)

    # Install services
    run_command("sudo mv /tmp/zigbee-manager-gui.service /etc/systemd/system/")
    run_command("sudo mv /tmp/zigbee-manager-headless.service /etc/systemd/system/")
    run_command("sudo systemctl daemon-reload")

    # Enable headless service by default
    run_command("sudo systemctl enable zigbee-manager-headless.service")

    print("\nBoth GUI and headless services have been created.")
    print("Headless service is enabled by default.")
    print("To use GUI service instead:")
    print("  sudo systemctl disable zigbee-manager-headless.service")
    print("  sudo systemctl enable zigbee-manager-gui.service")

def main():
    if os.geteuid() != 0:
        print("Please run with sudo privileges")
        sys.exit(1)

    print("Installing Zigbee Manager...")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Setup steps
    setup_environment()
    setup_usb_permissions()
    create_service()

    print("""
Installation complete!

To start the headless service (default):
    sudo systemctl start zigbee-manager-headless

To start the GUI service:
    sudo systemctl start zigbee-manager-gui

To check status:
    sudo systemctl status zigbee-manager-headless
    or
    sudo systemctl status zigbee-manager-gui

To view logs:
    journalctl -u zigbee-manager-headless -f
    or
    journalctl -u zigbee-manager-gui -f

Note: Please reboot your system for USB permissions to take effect.
""")

if __name__ == "__main__":
    main()