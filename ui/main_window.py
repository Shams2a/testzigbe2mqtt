import tkinter as tk
from tkinter import ttk
from .device_frame import DeviceFrame
from .settings_frame import SettingsFrame

class MainWindow:
    def __init__(self, root, zigbee_manager, mqtt_client, config_manager):
        self.root = root
        self.zigbee_manager = zigbee_manager
        self.mqtt_client = mqtt_client
        self.config_manager = config_manager
        
        # Configure root window
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create frames
        self.devices_frame = DeviceFrame(self.notebook, self.zigbee_manager)
        self.settings_frame = SettingsFrame(self.notebook, self.mqtt_client, 
                                          self.config_manager)
        
        # Add frames to notebook
        self.notebook.add(self.devices_frame, text='Devices')
        self.notebook.add(self.settings_frame, text='Settings')
        
        # Status bar
        self.status_bar = tk.Frame(self.root)
        self.status_bar.pack(fill='x', side='bottom')
        
        self.mqtt_status = tk.Label(self.status_bar, text="MQTT: Disconnected")
        self.mqtt_status.pack(side='left', padx=5)
        
        self.zigbee_status = tk.Label(self.status_bar, text="Zigbee: Disconnected")
        self.zigbee_status.pack(side='left', padx=5)
        
        # Start periodic status updates
        self.update_status()
    
    def update_status(self):
        mqtt_text = "MQTT: Connected" if self.mqtt_client.connected else "MQTT: Disconnected"
        zigbee_text = "Zigbee: Connected" if self.zigbee_manager.connected else "Zigbee: Disconnected"
        
        self.mqtt_status.config(text=mqtt_text)
        self.zigbee_status.config(text=zigbee_text)
        
        # Schedule next update
        self.root.after(1000, self.update_status)
