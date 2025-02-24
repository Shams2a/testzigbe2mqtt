import json
import logging
from pathlib import Path
import os

class DeviceConverters:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.definitions = {}
        self.load_definitions()

    def load_definitions(self):
        """Load device definitions from the definitions directory"""
        try:
            definitions_dir = Path("definitions")
            if not definitions_dir.exists():
                definitions_dir.mkdir()
                self._create_sample_definition()

            for file in definitions_dir.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        definition = json.load(f)
                        model_id = definition.get('model_id')
                        if model_id:
                            self.definitions[model_id] = definition
                            self.logger.info(f"Loaded device definition for {model_id}")
                except Exception as e:
                    self.logger.error(f"Error loading definition file {file}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Error loading device definitions: {str(e)}")

    def _create_sample_definition(self):
        """Create a sample device definition file"""
        sample = {
            "model_id": "TS0001",
            "vendor": "TuYa",
            "description": "Smart switch",
            "supports": ["on_off", "brightness"],
            "exposes": [
                {
                    "type": "binary",
                    "name": "state",
                    "property": "state",
                    "access": 7,
                    "values": ["ON", "OFF"]
                },
                {
                    "type": "numeric",
                    "name": "brightness",
                    "property": "brightness",
                    "access": 7,
                    "value_min": 0,
                    "value_max": 254
                }
            ]
        }
        
        with open("definitions/sample_device.json", 'w') as f:
            json.dump(sample, f, indent=2)

    def identify_device(self, model_id, manufacturer=None):
        """Identify a device and return its definition"""
        definition = self.definitions.get(model_id)
        if definition:
            return definition
        
        # Try to find a matching definition based on manufacturer
        if manufacturer:
            for def_id, def_data in self.definitions.items():
                if def_data.get('vendor', '').lower() == manufacturer.lower():
                    return def_data
        
        return None

    def get_device_features(self, model_id):
        """Get supported features for a device"""
        definition = self.definitions.get(model_id)
        if definition:
            return {
                'supports': definition.get('supports', []),
                'exposes': definition.get('exposes', [])
            }
        return None

    def get_state_definition(self, model_id, state_name):
        """Get the definition for a specific state"""
        definition = self.definitions.get(model_id)
        if definition:
            for expose in definition.get('exposes', []):
                if expose.get('name') == state_name:
                    return expose
        return None

    def validate_state_value(self, model_id, state_name, value):
        """Validate a state value against its definition"""
        state_def = self.get_state_definition(model_id, state_name)
        if not state_def:
            return False

        if state_def['type'] == 'binary':
            return value in state_def.get('values', [])
        elif state_def['type'] == 'numeric':
            try:
                val = float(value)
                min_val = state_def.get('value_min')
                max_val = state_def.get('value_max')
                return (min_val is None or val >= min_val) and \
                       (max_val is None or val <= max_val)
            except (ValueError, TypeError):
                return False
        return False
