import pygame
import paho.mqtt.publish as publish
import sys
import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser(description="Joystick to MQTT Bridge for Ship Console")
parser.add_argument("--broker", type=str, default="localhost", help="MQTT Broker IP or hostname")
parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
parser.add_argument("--publish", action="store_true", help="Enable publishing to MQTT")
parser.add_argument("--debug", action="store_true", help="Enable debug mode for verbose output")
parser.add_argument("--mappings-file", type=str, default="mappings.json", help="Path to joystick mappings JSON file")
args,_ = parser.parse_known_args()


# ==========================================
# ---       MQTT & BROKER CONFIG        ---
# ==========================================
MQTT_BROKER = args.broker
MQTT_PORT = args.port

# ==========================================
# ---     SCALABLE CONTROL MAPPINGS      ---
# ==========================================

def load_mappings(mappings_file):
    resolved_path = Path(mappings_file)
    if not resolved_path.is_absolute():
        resolved_path = Path(__file__).resolve().parent / resolved_path 

    if not resolved_path.exists():
        raise FileNotFoundError(f"Mappings file not found: {resolved_path}")

    with resolved_path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    buttons_raw = raw_data.get("buttons", {})
    axes_raw = raw_data.get("axes", {})
    hats_raw = raw_data.get("hats", {})

    button_mappings = {int(button_id): config for button_id, config in buttons_raw.items()}
    axis_mappings = {int(axis_id): config for axis_id, config in axes_raw.items()}
    hat_mappings = {
        tuple(int(coord) for coord in hat_value.split(",")): config
        for hat_value, config in hats_raw.items()
    }

    return button_mappings, hat_mappings, axis_mappings


BUTTON_MAPPINGS, HAT_MAPPINGS, AXIS_MAPPINGS = load_mappings(args.mappings_file)

# Advanced Tuning for Analog Spams
AXIS_THRESHOLD = 0.02  # Only publish changes larger than this to prevent MQTT spam
last_axis_values = {}   # Keeps track of the last sent values

# ==========================================
# ---            CORE LOGIC              ---
# ==========================================

def disable_if(condition):
    def decorator(func):
        if condition:
            print(f"Debug Mode: {func.__name__} is disabled. No MQTT messages will be sent.")
            return lambda *args, **kwargs: None #Returns dummy function
        return func #Returns original function
    return decorator #Returns which function to use

@disable_if(not args.publish)
def publish_mqtt_message(topic, message):
    """Publish a message to the specified MQTT topic."""
    try:
        publish.single(topic, message, hostname=MQTT_BROKER, port=MQTT_PORT)
        print(f"Published '{message}' to topic '{topic}'")
    except Exception as e:
        print(f"Failed to publish message: {e}")

# Initialize Pygame and the joystick
pygame.init()
pygame.joystick.init()

joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("Error: No joystick connected.")
    sys.exit()

joystick = pygame.joystick.Joystick(0)

print(f"Initialized Joystick: {joystick.get_name()}")
print(f"Console active. Press Ctrl+C in the terminal to quit.\n")

try:
    while True:
        for event in pygame.event.get():    
            # --- Handle Button Presses ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in BUTTON_MAPPINGS:
                    config = BUTTON_MAPPINGS[event.button]
                    print(f"[{config['label']}] Pressed")
                    publish_mqtt_message(config["topic"], config["payload"])
                else:
                    print(f"Unmapped Button {event.button} pressed.")   

            # --- Handle D-Pad / Hat Motion ---
            elif event.type == pygame.JOYHATMOTION:
                if event.value in HAT_MAPPINGS:
                    config = HAT_MAPPINGS[event.value]
                    print(f"[{config['label']}] Activated")
                    publish_mqtt_message(config["topic"], config["payload"])
                elif event.value == (0, 0):
                    # Optional: Handle return-to-center event if required
                    pass

            # --- Handle Helm Wheel & Throttle Levers ---
            elif event.type == pygame.JOYAXISMOTION:
                if event.axis in AXIS_MAPPINGS:
                    config = AXIS_MAPPINGS[event.axis]
                    
                    # Rounding to 2 decimal places smoothens jitter
                    current_value = round(event.value, 2)
                    previous_value = last_axis_values.get(event.axis, 0.0)
                    
                    # Only send updates if the hardware moved significantly
                    if abs(current_value - previous_value) >= AXIS_THRESHOLD:
                        last_axis_values[event.axis] = current_value
                        print(f"[{config['label']}] Position: {current_value}")
                        #publish_mqtt_message(config["topic"], str(current_value))

            # --- Handle Quit ---
            elif event.type == pygame.QUIT:
                print("Quitting...")
                pygame.quit()
                sys.exit()

except KeyboardInterrupt:
    print("\nQuitting gracefully...")
    pygame.quit()
    sys.exit()