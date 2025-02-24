import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for maximum verbosity

    # Create formatters
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'Path: %(pathname)s:%(lineno)d\n'
        'Function: %(funcName)s\n'
        '%(extra_data)s'
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Create file handler with rotation
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Main application log
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'zigbee_manager.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # MQTT specific log
    mqtt_handler = RotatingFileHandler(
        os.path.join(log_dir, 'mqtt.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    mqtt_handler.setLevel(logging.DEBUG)
    mqtt_handler.setFormatter(file_formatter)

    # Zigbee specific log
    zigbee_handler = RotatingFileHandler(
        os.path.join(log_dir, 'zigbee.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    zigbee_handler.setLevel(logging.DEBUG)
    zigbee_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Set up MQTT logger
    mqtt_logger = logging.getLogger('mqtt_client')
    mqtt_logger.addHandler(mqtt_handler)

    # Set up Zigbee logger
    zigbee_logger = logging.getLogger('zigbee_manager')
    zigbee_logger.addHandler(zigbee_handler)

    return logger

class LoggerAdapter(logging.LoggerAdapter):
    """Custom LoggerAdapter that handles additional data gracefully"""
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def process(self, msg, kwargs):
        # If extra not in kwargs, initialize it
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Get data from extra if it exists
        data = kwargs.get('extra', {}).get('data')

        # Format extra_data field
        if data:
            kwargs['extra']['extra_data'] = f"Additional Data: {data}\n"
        else:
            kwargs['extra']['extra_data'] = ""

        return msg, kwargs

def get_logger(name):
    """Get a logger with the custom adapter"""
    logger = logging.getLogger(name)
    return LoggerAdapter(logger)