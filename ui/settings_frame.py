import tkinter as tk
from tkinter import ttk, messagebox
import logging

class SettingsFrame(ttk.Frame):
    def __init__(self, parent, mqtt_client, config_manager):
        super().__init__(parent)
        self.mqtt_client = mqtt_client
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)

        self.create_widgets()
        self.load_settings()
        self.update_connection_status()

    def create_widgets(self):
        # MQTT Settings
        mqtt_frame = ttk.LabelFrame(self, text="MQTT Settings")
        mqtt_frame.pack(fill='x', padx=5, pady=5)

        # Connection status
        status_frame = ttk.Frame(mqtt_frame)
        status_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        self.status_label = ttk.Label(status_frame, text="Status: Disconnected")
        self.status_label.pack(side='left', padx=5)

        self.connect_btn = ttk.Button(status_frame, text="Connect",
                                    command=self.toggle_connection)
        self.connect_btn.pack(side='right', padx=5)

        # Default broker suggestion
        suggestion_frame = ttk.Frame(mqtt_frame)
        suggestion_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=0, sticky='w')
        ttk.Label(suggestion_frame, text="Using MQTT over WebSocket Secure (WSS). Default port: 443",
                 font=('TkDefaultFont', 8)).pack(side='left')

        ttk.Label(mqtt_frame, text="Broker:").grid(row=2, column=0, padx=5, pady=5)
        self.broker_entry = ttk.Entry(mqtt_frame)
        self.broker_entry.grid(row=2, column=1, padx=5, pady=5)
        self.broker_entry.insert(0, "6f66b254393d4dea9f6ed5d169c03469.s1.eu.hivemq.cloud")  # Set default broker

        ttk.Label(mqtt_frame, text="Port:").grid(row=3, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(mqtt_frame)
        self.port_entry.grid(row=3, column=1, padx=5, pady=5)
        self.port_entry.insert(0, "443")  # Set default WSS port

        ttk.Label(mqtt_frame, text="Username:").grid(row=4, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(mqtt_frame)
        self.username_entry.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(mqtt_frame, text="Password:").grid(row=5, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(mqtt_frame, show="*")
        self.password_entry.grid(row=5, column=1, padx=5, pady=5)

        # Zigbee Settings
        zigbee_frame = ttk.LabelFrame(self, text="Zigbee Settings")
        zigbee_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(zigbee_frame, text="Port:").grid(row=0, column=0, padx=5, pady=5)
        self.zigbee_port_entry = ttk.Entry(zigbee_frame)
        self.zigbee_port_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(zigbee_frame, text="Channel:").grid(row=1, column=0, padx=5, pady=5)
        self.channel_entry = ttk.Entry(zigbee_frame)
        self.channel_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(zigbee_frame, text="PAN ID:").grid(row=2, column=0, padx=5, pady=5)
        self.pan_id_entry = ttk.Entry(zigbee_frame)
        self.pan_id_entry.grid(row=2, column=1, padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=5, pady=5)

        self.save_btn = ttk.Button(button_frame, text="Save Settings",
                                  command=self.save_settings)
        self.save_btn.pack(side='right', padx=5)

    def toggle_connection(self):
        try:
            if not self.mqtt_client.connected:
                # Save current settings before attempting connection
                if not self.save_settings():
                    return  # Don't proceed if settings are invalid

                # Try to connect
                self.status_label.config(text="Status: Connecting...")
                self.connect_btn.config(state='disabled')
                self.update()  # Force GUI update

                try:
                    if self.mqtt_client.connect():
                        messagebox.showinfo("Success", "Connected to MQTT broker")
                except ValueError as ve:
                    messagebox.showerror("Configuration Error", str(ve))
                except TimeoutError as te:
                    messagebox.showerror("Connection Error", 
                        "Failed to connect to MQTT broker: Connection timed out.\n"
                        "Please verify the broker address and port are correct.")
                except Exception as e:
                    messagebox.showerror("Connection Error", 
                        f"Failed to connect to MQTT broker:\n{str(e)}\n"
                        "Please check your network connection and broker settings.")
            else:
                # Disconnect
                self.mqtt_client.disconnect()
                messagebox.showinfo("Success", "Disconnected from MQTT broker")

            self.update_connection_status()
        except Exception as e:
            self.logger.error(f"Error toggling connection: {str(e)}")
            messagebox.showerror("Error", f"Connection error: {str(e)}")
        finally:
            self.connect_btn.config(state='normal')

    def update_connection_status(self):
        if self.mqtt_client.connected:
            self.status_label.config(text="Status: Connected")
            self.connect_btn.config(text="Disconnect")
        else:
            self.status_label.config(text="Status: Disconnected")
            self.connect_btn.config(text="Connect")

        # Schedule next update
        self.after(1000, self.update_connection_status)

    def load_settings(self):
        try:
            mqtt_config = self.config_manager.get_mqtt_config()
            zigbee_config = self.config_manager.get_zigbee_config()

            # Clear existing values
            self.broker_entry.delete(0, tk.END)
            self.port_entry.delete(0, tk.END)
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            self.zigbee_port_entry.delete(0, tk.END)
            self.channel_entry.delete(0, tk.END)
            self.pan_id_entry.delete(0, tk.END)

            # Insert new values with defaults
            self.broker_entry.insert(0, mqtt_config.get('broker', '6f66b254393d4dea9f6ed5d169c03469.s1.eu.hivemq.cloud'))
            self.port_entry.insert(0, str(mqtt_config.get('port', 443)))  # Default WSS port
            self.username_entry.insert(0, mqtt_config.get('username', ''))
            self.password_entry.insert(0, mqtt_config.get('password', ''))

            self.zigbee_port_entry.insert(0, zigbee_config.get('port', '/dev/ttyACM0'))
            self.channel_entry.insert(0, str(zigbee_config.get('channel', 11)))
            self.pan_id_entry.insert(0, zigbee_config.get('pan_id', '0x1a62'))
        except Exception as e:
            self.logger.error(f"Error loading settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        try:
            # Validate input
            try:
                port = int(self.port_entry.get())
                channel = int(self.channel_entry.get())
                if not (1 <= channel <= 26):
                    raise ValueError("Channel must be between 1 and 26")
                if not (1024 <= port <= 65535):
                    raise ValueError("Port must be between 1024 and 65535")
            except ValueError as ve:
                messagebox.showerror("Validation Error", str(ve))
                return False

            mqtt_config = {
                'broker': self.broker_entry.get().strip(),
                'port': port,
                'username': self.username_entry.get().strip(),
                'password': self.password_entry.get()
            }

            zigbee_config = {
                'port': self.zigbee_port_entry.get().strip(),
                'channel': channel,
                'pan_id': self.pan_id_entry.get().strip()
            }

            self.config_manager.update_mqtt_config(mqtt_config)
            self.config_manager.update_zigbee_config(zigbee_config)

            messagebox.showinfo("Success", "Settings saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving settings: {str(e)}")
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            return False