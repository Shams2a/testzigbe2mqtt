import json
import os
import logging

class ConfigManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_file = "config.json"
        self.config = self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return self.get_default_config()
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return self.get_default_config()
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            return False
    
    def get_default_config(self):
        return {
            'mqtt': {
                'broker': 'localhost',
                'port': 1883,
                'username': '',
                'password': ''
            },
            'zigbee': {
                'port': '/dev/ttyACM0',
                'channel': 11,
                'pan_id': '0x1a62'
            }
        }
    
    def get_mqtt_config(self):
        return self.config.get('mqtt', {})
    
    def get_zigbee_config(self):
        return self.config.get('zigbee', {})
    
    def update_mqtt_config(self, config):
        self.config['mqtt'] = config
        return self.save_config()
    
    def update_zigbee_config(self, config):
        self.config['zigbee'] = config
        return self.save_config()
