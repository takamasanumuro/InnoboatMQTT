import pygame
import paho.mqtt.publish as publish
import sys

# --- Configuration ---
MQTT_BROKER = "orangepi"  # IP address of your MQTT broker (e.g., "mqtt.example.com")
MQTT_PORT = 1883                # Default MQTT port
# --- End of Configuration ---

def publish_mqtt_message(topic, message):
    """Publish a message to the specified MQTT topic."""
    try:
        publish.single(topic, message, hostname=MQTT_BROKER, port=MQTT_PORT)
        print(f"Published '{message}' to topic '{topic}'")
    except Exception as e:
        print(f"Failed to publish message: {e}")

# --- Main Program ---

# Initialize Pygame and the joystick
pygame.init()
pygame.joystick.init()

# Check if any joysticks are connected
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("Error: No joystick connected.")
    sys.exit()

# Use the first joystick (index 0)
joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Initialized Joystick: {joystick.get_name()}")
print(f"Press joystick buttons. Press Ctrl+C in the terminal to quit.")

# Main event loop
try:
    while True:
        # Get events from the queue
        for event in pygame.event.get():    
            # Event: Joystick button pressed
            if event.type == pygame.JOYBUTTONDOWN:
                print(f"Button {event.button} pressed.")   

                if event.button == 11:
                    # You could change the topic or message payload here
                    print("Contatora ON command sent")
                    publish_mqtt_message(f"contatora/command", "ON")
                elif event.button == 12:
                    print("Contatora OFF command sent")
                    publish_mqtt_message(f"contatora/command", "OFF")
                    
            elif event.type == pygame.JOYHATMOTION:
                print(f"Hat {event.hat} moved to {event.value}.")

            # Event: Quit the program (e.g., closing the window if one existed)
            elif event.type == pygame.QUIT:
                print("Quitting...")
                pygame.quit()
                sys.exit()
        


except KeyboardInterrupt:
    # Handle Ctrl+C to quit gracefully
    print("\nQuitting...")
    pygame.quit()
    sys.exit()