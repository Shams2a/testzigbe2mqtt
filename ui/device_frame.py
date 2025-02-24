import tkinter as tk
from tkinter import ttk, messagebox
import logging
import asyncio
import json
import time

class DeviceFrame(ttk.Frame):
    def __init__(self, parent, zigbee_manager):
        super().__init__(parent)
        self.zigbee_manager = zigbee_manager
        self.logger = logging.getLogger(__name__)

        # Create widgets
        self.create_widgets()

        # Start periodic updates
        self.update_status()

    def create_widgets(self):
        # Status frame
        status_frame = ttk.Frame(self)
        status_frame.pack(fill='x', padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Status: Not Connected")
        self.status_label.pack(side='left')

        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=5, pady=5)

        self.permit_join_btn = ttk.Button(toolbar, text="Permit Join (60s)",
                                        command=self.permit_join)
        self.permit_join_btn.pack(side='left', padx=5)

        self.refresh_btn = ttk.Button(toolbar, text="Refresh",
                                   command=self.refresh_devices)
        self.refresh_btn.pack(side='left', padx=5)

        # Create main panel with device list and details
        main_panel = ttk.PanedWindow(self, orient='horizontal')
        main_panel.pack(fill='both', expand=True, padx=5, pady=5)

        # Device list frame
        list_frame = ttk.Frame(main_panel)
        main_panel.add(list_frame, weight=1)

        # Device list
        columns = ('ID', 'Model', 'Manufacturer', 'Status', 'Last Seen')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        # Configure columns
        self.tree.heading('ID', text='Device ID')
        self.tree.heading('Model', text='Model')
        self.tree.heading('Manufacturer', text='Manufacturer')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Last Seen', text='Last Seen')

        # Column widths
        self.tree.column('ID', width=150)
        self.tree.column('Model', width=150)
        self.tree.column('Manufacturer', width=150)
        self.tree.column('Status', width=100)
        self.tree.column('Last Seen', width=150)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack list widgets
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Device details frame
        self.details_frame = ttk.LabelFrame(main_panel, text="Device Details")
        main_panel.add(self.details_frame, weight=1)

        # State display
        self.state_tree = ttk.Treeview(self.details_frame, 
                                     columns=('State', 'Value'),
                                     show='headings')
        self.state_tree.heading('State', text='State')
        self.state_tree.heading('Value', text='Value')
        self.state_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_device_selected)

        # Create right-click menu
        self.device_menu = tk.Menu(self, tearoff=0)
        self.device_menu.add_command(label="Remove Device", command=self.remove_device)
        self.device_menu.add_command(label="View Details", command=self.view_device_details)
        self.device_menu.add_command(label="Update State", command=self.update_device_state)

        # Bind right-click menu
        self.tree.bind("<Button-3>", self.show_device_menu)

    def on_device_selected(self, event):
        """Handle device selection"""
        try:
            selected = self.tree.selection()
            if not selected:
                return

            device_id = self.tree.item(selected[0])['values'][0]

            # Clear current states
            for item in self.state_tree.get_children():
                self.state_tree.delete(item)

            # Get device states
            states = asyncio.run_coroutine_threadsafe(
                self.zigbee_manager.get_device_state(device_id),
                self.zigbee_manager.loop
            ).result()

            # Display states
            for state_name, value in states.items():
                self.state_tree.insert('', 'end', values=(state_name, value))

        except Exception as e:
            self.logger.error(f"Error updating device states: {str(e)}")

    def update_device_state(self):
        """Update state for selected device"""
        selected = self.tree.selection()
        if not selected:
            return

        try:
            device_id = self.tree.item(selected[0])['values'][0]
            device = self.zigbee_manager.devices.get(device_id)

            if not device or not device.get('definition'):
                messagebox.showerror("Error", "No device definition available")
                return

            # Create dialog for state update
            dialog = tk.Toplevel(self)
            dialog.title("Update Device State")
            dialog.geometry("300x150")

            ttk.Label(dialog, text="State:").grid(row=0, column=0, padx=5, pady=5)
            state_var = tk.StringVar()
            state_combo = ttk.Combobox(dialog, textvariable=state_var)
            state_combo['values'] = [
                expose['name'] for expose in device['definition'].get('exposes', [])
            ]
            state_combo.grid(row=0, column=1, padx=5, pady=5)

            ttk.Label(dialog, text="Value:").grid(row=1, column=0, padx=5, pady=5)
            value_entry = ttk.Entry(dialog)
            value_entry.grid(row=1, column=1, padx=5, pady=5)

            def submit():
                try:
                    state = state_var.get()
                    value = value_entry.get()

                    success = asyncio.run_coroutine_threadsafe(
                        self.zigbee_manager.update_device_state(device_id, state, value),
                        self.zigbee_manager.loop
                    ).result()

                    if success:
                        messagebox.showinfo("Success", "State updated successfully")
                        self.on_device_selected(None)  # Refresh states
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Failed to update state")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to update state: {str(e)}")

            ttk.Button(dialog, text="Update", command=submit).grid(row=2, column=1, pady=10)

        except Exception as e:
            self.logger.error(f"Error updating device state: {str(e)}")
            messagebox.showerror("Error", f"Failed to update state: {str(e)}")

    def permit_join(self):
        """Enable permit join for new devices"""
        if not self.zigbee_manager.connected:
            messagebox.showerror("Error", "Zigbee manager is not connected")
            return

        try:
            if self.zigbee_manager.permit_join():
                self.permit_join_btn.config(state='disabled')
                self.update_permit_join_status()
                messagebox.showinfo("Success", 
                    "Network is now open for new devices to join for 60 seconds.\n"
                    "Please initiate the pairing process on your Zigbee device now.")
            else:
                messagebox.showerror("Error", "Failed to enable permit join")
        except Exception as e:
            self.logger.error(f"Error in permit join: {str(e)}")
            messagebox.showerror("Error", f"Failed to enable permit join: {str(e)}")

    def update_permit_join_status(self):
        """Update permit join button status"""
        if self.zigbee_manager.is_permit_join_active():
            remaining = int(self.zigbee_manager.permit_join_end_time - time.time())
            self.permit_join_btn.config(
                text=f"Joining Enabled ({remaining}s)",
                state='disabled'
            )
            if remaining > 0:
                self.after(1000, self.update_permit_join_status)
            else:
                self.permit_join_btn.config(
                    text="Permit Join (60s)",
                    state='normal'
                )
        else:
            self.permit_join_btn.config(
                text="Permit Join (60s)",
                state='normal' if self.zigbee_manager.connected else 'disabled'
            )

    def refresh_devices(self):
        try:
            # Clear current items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Add devices
            devices = self.zigbee_manager.get_devices()
            for device_id, device in devices.items():
                self.tree.insert('', 'end', values=(
                    device_id,
                    device.get('model', 'Unknown'),
                    device.get('manufacturer', 'Unknown'),
                    device.get('status', 'Unknown'),
                    device.get('last_seen', 'Never')
                ))
        except Exception as e:
            self.logger.error(f"Error refreshing devices: {str(e)}")

    def remove_device(self):
        """Remove selected device from the network"""
        selected = self.tree.selection()
        if not selected:
            return

        device_id = self.tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Remove device {device_id} from the network?"):
            try:
                # Use asyncio to run the coroutine
                success = asyncio.run_coroutine_threadsafe(
                    self.zigbee_manager.remove_device(device_id),
                    self.zigbee_manager.loop
                ).result()

                if success:
                    messagebox.showinfo("Success", f"Device {device_id} has been removed")
                    self.refresh_devices()
                else:
                    messagebox.showerror("Error", f"Failed to remove device {device_id}")
            except Exception as e:
                self.logger.error(f"Error removing device: {str(e)}")
                messagebox.showerror("Error", f"Failed to remove device: {str(e)}")

    def view_device_details(self):
        """Show detailed information about the selected device"""
        selected = self.tree.selection()
        if not selected:
            return

        try:
            device_id = self.tree.item(selected[0])['values'][0]
            devices = self.zigbee_manager.get_devices()
            device = devices.get(device_id)

            if device:
                details = "\n".join([
                    f"Device ID: {device_id}",
                    f"Model: {device.get('model', 'Unknown')}",
                    f"Manufacturer: {device.get('manufacturer', 'Unknown')}",
                    f"Network Address: {device.get('nwk', 'Unknown')}",
                    f"Status: {device.get('status', 'Unknown')}",
                    f"Last Seen: {device.get('last_seen', 'Never')}"
                ])
                messagebox.showinfo(f"Device Details - {device_id}", details)
            else:
                messagebox.showwarning("Warning", "Device information not found")
        except Exception as e:
            self.logger.error(f"Error viewing device details: {str(e)}")
            messagebox.showerror("Error", "Failed to retrieve device details")

    def update_status(self):
        """Periodically update the device list and status"""
        try:
            # Update status based on both MQTT and Zigbee connection
            if self.zigbee_manager.connected:
                if self.zigbee_manager.mqtt_client.connected:
                    self.status_label.config(text="Status: Connected")
                    # Only enable permit join when both connections are active
                    if not self.zigbee_manager.is_permit_join_active():
                        self.permit_join_btn.config(state='normal')
                else:
                    self.status_label.config(text="Status: Waiting for MQTT")
                    self.permit_join_btn.config(state='disabled')
            else:
                self.status_label.config(text="Status: Not Connected")
                self.permit_join_btn.config(state='disabled')

            # Refresh device list only if both connections are active
            if self.zigbee_manager.connected and self.zigbee_manager.mqtt_client.connected:
                self.refresh_devices()
        except Exception as e:
            self.logger.error(f"Error in periodic update: {str(e)}")
            self.status_label.config(text="Status: Error")
        finally:
            # Schedule next update
            self.after(5000, self.update_status)

    def show_device_menu(self, event):
        """Show the right-click menu for device management"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.device_menu.post(event.x_root, event.y_root)