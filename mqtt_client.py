import paho.mqtt.client as mqtt
import logging
import json
import time
import socket
from utils.logger import get_logger

class MQTTClient:
    def __init__(self, config_manager):
        self.logger = get_logger(__name__)
        self.config_manager = config_manager
        # Use websockets transport
        self.client = mqtt.Client(transport="websockets")
        self.connected = False

        # Setup callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish

    def connect(self):
        try:
            # First disconnect if already connected
            if self.connected:
                self.disconnect()

            config = self.config_manager.get_mqtt_config()
            broker = config.get('broker', '6f66b254393d4dea9f6ed5d169c03469.s1.eu.hivemq.cloud').strip()
            port = int(config.get('port', 443))  # Default to WSS port
            username = config.get('username', '').strip()
            password = config.get('password', '')

            # Basic validation
            if not broker:
                error_msg = "MQTT broker address not configured"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            if not (1024 <= port <= 65535):
                error_msg = f"Invalid MQTT port: {port}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            # Log connection attempt (without sensitive data)
            self.logger.info(f"Attempting to connect to MQTT broker", 
                           extra={'data': {
                               'broker': broker,
                               'port': port,
                               'transport': 'websockets',
                               'has_credentials': bool(username)
                           }})

            # Verify DNS resolution before attempting connection
            try:
                socket.gethostbyname(broker)
            except socket.gaierror as e:
                error_msg = f"Failed to resolve broker hostname: {broker}"
                self.logger.error(error_msg, extra={'data': {'error': str(e)}})
                raise ValueError(error_msg)

            # Set credentials if provided
            if username:
                self.client.username_pw_set(username, password)

            # Configure WSS with TLS
            self.client.ws_set_options(path="/mqtt")
            self.client.tls_set()  # Enable TLS for WSS

            # Connect with proper error handling
            self.logger.info(f"Connecting to MQTT broker at {broker}:{port}")

            # Set shorter keepalive and connection timeout
            self.client.connect(broker, port, keepalive=60)
            self.client.loop_start()

            # Wait briefly for connection to establish
            timeout = 5  # 5 second timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.connected:
                    self.logger.info("Successfully connected to MQTT broker")
                    return True
                time.sleep(0.1)

            # If we get here, connection failed
            self.client.loop_stop()
            error_msg = f"Connection timeout after {timeout} seconds"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg)

        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker", 
                            extra={'data': {'error': str(e)}})
            self.connected = False
            raise  # Re-raise the exception for the UI to handle

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.logger.info("Disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error disconnecting from MQTT", 
                            extra={'data': {'error': str(e)}})

    def publish(self, topic, message):
        try:
            if not self.connected:
                error_msg = "Cannot publish: Not connected to MQTT broker"
                self.logger.warning(error_msg)
                return False

            payload = json.dumps(message)
            result = self.client.publish(topic, payload)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                error_msg = f"Failed to publish message: {mqtt.error_string(result.rc)}"
                self.logger.error(error_msg)
                return False

            self.logger.debug(f"Published to {topic}: {message}", 
                            extra={'data': {'topic': topic, 'payload': message}})
            return True

        except Exception as e:
            self.logger.error(f"Error publishing message", 
                            extra={'data': {
                                'topic': topic, 
                                'payload': message,
                                'error': str(e)
                            }})
            return False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            self.connected = True
            # Subscribe to required topics
            self.client.subscribe("zigbee2mqtt/#")
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code {rc}")
            self.logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            self.connected = False

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            self.logger.error(f"Unexpected MQTT disconnection", 
                            extra={'data': {'code': rc}})
        else:
            self.logger.info("Disconnected from MQTT broker")

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            self.logger.debug(f"Received message", 
                            extra={'data': {
                                'topic': message.topic,
                                'payload': payload
                            }})
        except Exception as e:
            self.logger.error(f"Error processing message", 
                            extra={'data': {
                                'topic': message.topic,
                                'payload': message.payload,
                                'error': str(e)
                            }})

    def on_publish(self, client, userdata, mid):
        self.logger.debug(f"Message {mid} published successfully")