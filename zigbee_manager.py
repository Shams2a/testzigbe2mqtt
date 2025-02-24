import logging
from threading import Lock
import json
import time
import asyncio
import zigpy.config
from zigpy.application import ControllerApplication
from zigpy.exceptions import ZigbeeException
from zigpy.types import EUI64
from device_converters import DeviceConverters
from utils.logger import get_logger

class ZigbeeManager:
    def __init__(self, mqtt_client, config_manager):
        self.logger = get_logger(__name__)
        self.mqtt_client = mqtt_client
        self.config_manager = config_manager
        self.devices = {}
        self.device_states = {}  # Store device states
        self.lock = Lock()
        self.connected = False
        self.permit_join_active = False
        self.permit_join_end_time = 0
        self.app = None
        self.loop = asyncio.get_event_loop()
        self.converters = DeviceConverters()

    async def _init_controller(self):
        try:
            config = self.config_manager.get_zigbee_config()
            zigbee_config = {
                "device": {
                    "path": config.get('port', '/dev/ttyACM0'),
                },
                "database_path": "zigbee.db",
                "network": {
                    "channel": config.get('channel', 11),
                    "pan_id": int(config.get('pan_id', '0x1a62'), 16),
                    "extended_pan_id": None,
                }
            }

            # Initialize the Zigbee controller
            self.app = await ControllerApplication.new(
                config=zigbee_config,
                auto_form=True,
                start_radio=True
            )

            # Register callbacks
            self.app.add_listener(self._handle_device_joined)
            self.app.add_listener(self._handle_device_leave)
            self.app.add_listener(self._handle_device_relays)
            self.app.add_listener(self._handle_attribute_update)

            return True
        except ZigbeeException as ze:
            self.logger.error(f"Zigbee initialization error: {str(ze)}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize Zigbee controller: {str(e)}")
            return False

    def start(self):
        try:
            success = self.loop.run_until_complete(self._init_controller())
            if success:
                self.connected = True
                self.logger.info("Zigbee manager started successfully")
                # Try to start MQTT if not already connected
                if not self.mqtt_client.connected:
                    try:
                        self.mqtt_client.connect()
                    except Exception as e:
                        self.logger.warning(f"Could not connect to MQTT: {str(e)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start Zigbee manager: {str(e)}")
            self.connected = False
        return False

    async def _stop_controller(self):
        if self.app:
            await self.app.shutdown()
            self.app = None

    def stop(self):
        try:
            self.loop.run_until_complete(self._stop_controller())
            self.connected = False
            self.logger.info("Zigbee manager stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping Zigbee manager: {str(e)}")
            return False

    async def _permit_join(self, duration):
        try:
            await self.app.permit(duration)
            return True
        except Exception as e:
            self.logger.error(f"Error in permit join: {str(e)}")
            return False

    def permit_join(self, duration=60):
        """Enable permit join for new devices"""
        if not self.connected:
            self.logger.error("Cannot permit join: Zigbee manager not connected")
            return False

        try:
            self.logger.info(f"Enabling permit join for {duration} seconds")
            success = self.loop.run_until_complete(self._permit_join(duration))

            if success:
                self.permit_join_active = True
                self.permit_join_end_time = time.time() + duration

                # Notify via MQTT
                self.mqtt_client.publish(
                    "zigbee2mqtt/bridge/request/permit_join",
                    {"value": True, "time": duration}
                )

                # Schedule permit join disable
                self.loop.call_later(duration, self._disable_permit_join)

                self.logger.info("Permit join enabled successfully")
                return True

            self.logger.error("Failed to enable permit join")
            return False
        except Exception as e:
            self.logger.error(f"Error enabling permit join: {str(e)}")
            return False

    def _disable_permit_join(self):
        """Disable permit join"""
        if self.permit_join_active:
            self.permit_join_active = False
            self.loop.run_until_complete(self._permit_join(0))
            self.mqtt_client.publish(
                "zigbee2mqtt/bridge/request/permit_join",
                {"value": False}
            )
            self.logger.info("Permit join disabled")

    def is_permit_join_active(self):
        """Check if permit join is currently active"""
        if self.permit_join_active:
            # Check if the permit join period has expired
            if time.time() > self.permit_join_end_time:
                self.permit_join_active = False
                return False
            return True
        return False

    def get_devices(self):
        if not self.app:
            return {}

        with self.lock:
            devices = {}
            for ieee, dev in self.app.devices.items():
                devices[str(ieee)] = {
                    'model': dev.model if dev.model else 'Unknown',
                    'manufacturer': dev.manufacturer if dev.manufacturer else 'Unknown',
                    'nwk': dev.nwk,
                    'status': 'Ready' if dev.initialized else 'Initializing',
                    'last_seen': dev.last_seen.isoformat() if dev.last_seen else None,
                    'definition': self.converters.identify_device(dev.model, dev.manufacturer)
                }
            return devices

    async def _handle_device_joined(self, device):
        """Handle new device joining the network"""
        try:
            device_id = str(device.ieee)
            with self.lock:
                # Get device information
                model_id = device.model if device.model else "unknown"
                manufacturer = device.manufacturer if device.manufacturer else "unknown"

                # Get device definition
                definition = self.converters.identify_device(model_id, manufacturer)

                self.devices[device_id] = {
                    'model': model_id,
                    'manufacturer': manufacturer,
                    'definition': definition,
                    'status': 'Joining',
                    'joined_at': time.time()
                }

                # Initialize device state
                self.device_states[device_id] = {}
                if definition:
                    for expose in definition.get('exposes', []):
                        self.device_states[device_id][expose['name']] = None

                # Prepare MQTT message
                mqtt_message = {
                    'type': 'device_joined',
                    'device': {
                        'ieee_address': device_id,
                        'model': model_id,
                        'manufacturer': manufacturer,
                        'supported_features': definition.get('supports', []) if definition else []
                    }
                }

                # Publish to MQTT
                self.mqtt_client.publish(
                    "zigbee2mqtt/bridge/event/device_joined",
                    mqtt_message
                )

                self.logger.info(f"New device joined: {device_id} ({model_id})", 
                               extra={'data': mqtt_message})

        except Exception as e:
            self.logger.error(f"Error handling device join: {str(e)}", 
                            extra={'data': {
                                'device_id': device_id if 'device_id' in locals() else None
                            }})

    async def update_device_state(self, device_id, state_name, value):
        """Update device state and validate against definition"""
        try:
            device = self.devices.get(device_id)
            if not device:
                raise ValueError(f"Device {device_id} not found")

            model_id = device.get('model')
            if not self.converters.validate_state_value(model_id, state_name, value):
                raise ValueError(f"Invalid value {value} for state {state_name}")

            with self.lock:
                if device_id not in self.device_states:
                    self.device_states[device_id] = {}
                self.device_states[device_id][state_name] = value

                # Publish state update to MQTT
                self.mqtt_client.publish(
                    f"zigbee2mqtt/{device_id}/state",
                    {state_name: value}
                )
                return True
        except Exception as e:
            self.logger.error(f"Error updating device state: {str(e)}")
            return False

    async def get_device_state(self, device_id):
        """Get current state of a device"""
        with self.lock:
            return self.device_states.get(device_id, {})

    async def _handle_device_leave(self, device):
        """Handle device leaving the network"""
        with self.lock:
            device_id = str(device.ieee)
            if device_id in self.devices:
                del self.devices[device_id]
                if device_id in self.device_states:
                    del self.device_states[device_id]

                # Publish to MQTT
                self.mqtt_client.publish(
                    f"zigbee2mqtt/bridge/event/device_leave",
                    {"ieee_address": device_id}
                )
                self.logger.info(f"Device left: {device_id}")

    async def remove_device(self, ieee_address):
        """Remove a device from the network"""
        try:
            # Convert string IEEE address to EUI64
            ieee = EUI64.convert(ieee_address)
            device = self.app.devices.get(ieee)

            if device:
                # Force remove from network
                await device.leave()
                # Clean up device from internal storage
                del self.app.devices[ieee]
                # Remove from local cache
                with self.lock:
                    if str(ieee) in self.devices:
                        del self.devices[str(ieee)]
                    if str(ieee) in self.device_states:
                        del self.device_states[str(ieee)]

                # Notify via MQTT
                self.mqtt_client.publish(
                    "zigbee2mqtt/bridge/event/device_removed",
                    {"ieee_address": str(ieee)}
                )
                return True
            else:
                self.logger.warning(f"Device {ieee_address} not found in network")
                return False
        except Exception as e:
            self.logger.error(f"Error removing device {ieee_address}: {str(e)}")
            return False

    async def _handle_device_relays(self, message_type, device, message):
        """Handle device state updates and routing changes"""
        try:
            if message_type == "device_announce":
                # Device has rejoined or rebooted
                with self.lock:
                    device_id = str(device.ieee)
                    if device_id in self.devices:
                        self.devices[device_id]['status'] = 'Online'
                        self.mqtt_client.publish(
                            f"zigbee2mqtt/bridge/event/device_announce",
                            {
                                "ieee_address": device_id,
                                "status": "online"
                            }
                        )
            elif message_type == "attribute_updated":
                # Device attribute has changed
                device_id = str(device.ieee)
                self.mqtt_client.publish(
                    f"zigbee2mqtt/{device_id}",
                    {
                        "attribute": message.get("attribute"),
                        "value": message.get("value")
                    }
                )
        except Exception as e:
            self.logger.error(f"Error handling device relay: {str(e)}")

    async def _handle_attribute_update(self, device, cluster, attribute, value):
        """Handle device attribute updates and convert to MQTT messages"""
        try:
            device_id = str(device.ieee)
            device_info = self.devices.get(device_id)

            if device_info and device_info.get('definition'):
                # Map the cluster/attribute to a state name using the definition
                for expose in device_info['definition'].get('exposes', []):
                    if expose.get('cluster') == cluster and expose.get('attribute') == attribute:
                        # Update internal state
                        await self.update_device_state(device_id, expose['name'], value)

                        # Prepare MQTT message
                        mqtt_message = {
                            'type': 'attribute_update',
                            'device': {
                                'ieee_address': device_id,
                                'model': device_info.get('model', 'unknown'),
                                'manufacturer': device_info.get('manufacturer', 'unknown')
                            },
                            'cluster': cluster,
                            'attribute': attribute,
                            'value': value
                        }

                        # Publish to MQTT
                        self.mqtt_client.publish(
                            f"zigbee2mqtt/{device_id}/attribute",
                            mqtt_message
                        )

                        self.logger.debug("Published attribute update to MQTT", 
                                        extra={'data': mqtt_message})
                        break

        except Exception as e:
            self.logger.error(f"Error handling attribute update: {str(e)}", 
                            extra={'data': {
                                'device_id': device_id if 'device_id' in locals() else None,
                                'cluster': cluster,
                                'attribute': attribute,
                                'value': value
                            }})

    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop()
            if self.loop and self.loop.is_running():
                self.loop.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")