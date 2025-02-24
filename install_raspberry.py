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
    service_content = f"""[Unit]
Description=Zigbee Manager Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER')}
WorkingDirectory={os.getcwd()}
Environment=DISPLAY=:0
ExecStart={os.getcwd()}/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    
    # Write service file
    with open("/tmp/zigbee-manager.service", "w") as f:
        f.write(service_content)
    
    # Install service
    run_command("sudo mv /tmp/zigbee-manager.service /etc/systemd/system/")
    run_command("sudo systemctl daemon-reload")
    run_command("sudo systemctl enable zigbee-manager.service")

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

To start the service:
    sudo systemctl start zigbee-manager

To check status:
    sudo systemctl status zigbee-manager

To view logs:
    journalctl -u zigbee-manager -f

Note: Please reboot your system for USB permissions to take effect.
""")

if __name__ == "__main__":
    main()
