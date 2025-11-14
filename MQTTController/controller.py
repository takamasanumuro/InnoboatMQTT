import paho.mqtt.client as mqtt
import wiringpi
from wiringpi import GPIO

wiringpi.wiringPiSetupSys() # Initialize wiringPi for controlling GPIOs
contatora_wpi_number = 14

# --- Config ---
MQTT_BROKER = "localhost" # Connect to the broker on the same machine
MQTT_TOPIC = "contatora/command"
STATUS_TOPIC = "contatora/status"

# --- MQTT Functions ---
def on_connect(client, userdata, flags, rc):
    print(f"Connected to local MQTT with result code {rc}")
    # Subscribe to the command topic
    client.subscribe(MQTT_TOPIC)
    # Report current status on connect
    current_status = "ON" if wiringpi.digitalRead(contatora_wpi_number) == GPIO.LOW else "OFF"
    print(f"Current status: {current_status}")
    client.publish(STATUS_TOPIC, current_status, retain=True)

def on_message(client, userdata, msg):
    payload = msg.payload.decode().upper()
    print(f"[{msg.topic}] Received message: {payload}")
    
    if payload == "ON":
        wiringpi.digitalWrite(contatora_wpi_number, GPIO.LOW)
        client.publish(STATUS_TOPIC, "ON", retain=True)
    elif payload == "OFF":
        wiringpi.digitalWrite(contatora_wpi_number, GPIO.HIGH)
        client.publish(STATUS_TOPIC, "OFF", retain=True)

# --- Main ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883, 60)
    print("Starting MQTT listener...")
    # loop_forever() blocks and keeps the script running
    client.loop_forever() 

except KeyboardInterrupt:
    print("Quitting...")
except Exception as e:
    print(f"Error: {e}")