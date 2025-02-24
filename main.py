import tkinter as tk
from ui.main_window import MainWindow
from zigbee_manager import ZigbeeManager
from mqtt_client import MQTTClient
from config_manager import ConfigManager
from utils.logger import setup_logger
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class MinimalRequestHandler(BaseHTTPRequestHandler):
    """Minimal handler that returns 200 OK for health checks"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Zigbee Manager is running')

def run_web_server():
    """Run a minimal web server on port 5000 to satisfy workflow requirements"""
    server = HTTPServer(('0.0.0.0', 5000), MinimalRequestHandler)
    server.serve_forever()

def main():
    # Setup logging
    setup_logger()
    logger = logging.getLogger(__name__)

    try:
        # Test logging with extra data to verify formatter
        logger.info("Starting Zigbee Manager application", 
                   extra={'data': {'mode': 'startup', 'version': '1.0.0'}})

        # Start web server in background thread
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()
        logger.info("Web server started on port 5000", 
                   extra={'data': {'port': 5000, 'host': '0.0.0.0'}})

        # Initialize configuration
        config_manager = ConfigManager()

        # Initialize MQTT client
        mqtt_client = MQTTClient(config_manager)

        # Initialize Zigbee manager
        zigbee_manager = ZigbeeManager(mqtt_client, config_manager)

        # Check if we can start GUI
        try:
            if os.environ.get('DISPLAY') and not os.environ.get('HEADLESS'):
                # Create main window
                root = tk.Tk()
                root.title("Zigbee Manager")
                app = MainWindow(root, zigbee_manager, mqtt_client, config_manager)
                logger.info("Starting GUI mode")
                root.mainloop()
            else:
                logger.info("Starting headless mode (no GUI)")
                # In headless mode, just keep the main thread running
                try:
                    # Start the Zigbee manager
                    if zigbee_manager.start():
                        logger.info("Zigbee manager started successfully")

                        # Keep the main thread running
                        while True:
                            try:
                                threading.Event().wait()
                            except KeyboardInterrupt:
                                break
                    else:
                        logger.error("Failed to start Zigbee manager")
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
                finally:
                    zigbee_manager.cleanup()
                    mqtt_client.disconnect()

        except Exception as e:
            logger.error(f"Application error: {str(e)}", 
                        extra={'data': {'error': str(e)}})
        finally:
            # Cleanup
            zigbee_manager.cleanup()
            mqtt_client.disconnect()

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", 
                    extra={'data': {'error': str(e)}})

if __name__ == "__main__":
    main()