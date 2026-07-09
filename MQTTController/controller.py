import paho.mqtt.client as mqtt
import subprocess
import sys
import time  # <-- Added for the periodic delay

# --- Config ---
MQTT_BROKER = "localhost" # Connect to the broker on the same machine
MQTT_TOPIC = "contatora/cmd"
STATUS_TOPIC = "contatora/status"
POLL_INTERVAL = 2  # <-- Time in seconds between periodic checks

# Define your GPIO pin number here (using your existing wiringPi pin numbering)
CONTATORA_PIN = 28

# ==========================================
# ---        GPIO DIRECT CLI ENGINE      ---
# ==========================================

def init_gpio():
    """Sets the GPIO pin to output mode on script startup."""
    try:
        # Replaces wiringpi.pinMode(pin, GPIO.OUTPUT)
        subprocess.run(["gpio", "mode", str(CONTATORA_PIN), "out"], check=True)
        print(f"GPIO Pin {CONTATORA_PIN} successfully initialized to OUTPUT mode.")
    except Exception as e:
        print(f"Hardware Init Error: Could not set GPIO mode. Is the 'gpio' utility installed? ({e})", file=sys.stderr)

def gpio_read(pin):
    """Reads the pin state directly using the 'gpio read <pin>' command."""
    try:
        result = subprocess.run(["gpio", "read", str(pin)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error reading GPIO pin {pin}: {e}", file=sys.stderr)
        return "1"  # Default fallback to a safe state (HIGH/OFF) if reading fails

def gpio_write(pin, value):
    """Writes the state directly using the 'gpio write <pin> <val>' command."""
    try:
        # value expects a string or int: 0 for LOW, 1 for HIGH
        subprocess.run(["gpio", "write", str(pin), str(value)], check=True)
    except Exception as e:
        print(f"Error writing {value} to GPIO pin {pin}: {e}", file=sys.stderr)

# ==========================================
# ---            MQTT FUNCTIONS          ---
# ==========================================

def on_connect(client, userdata, flags, rc):
    print(f"Connected to local MQTT with result code {rc}")
    # Subscribe to the command topic
    client.subscribe(MQTT_TOPIC)
    
    # Report current status immediately on connect
    publish_status(client)

def on_message(client, userdata, msg):
    payload = msg.payload.decode().upper()
    print(f"[{msg.topic}] Received command: {payload}")
    
    if payload == "ON":
        # Replaces wiringpi.digitalWrite(pin, GPIO.LOW) -> 0
        gpio_write(CONTATORA_PIN, 0)
        client.publish(STATUS_TOPIC, "ON", retain=True)
    elif payload == "OFF":
        # Replaces wiringpi.digitalWrite(pin, GPIO.HIGH) -> 1
        gpio_write(CONTATORA_PIN, 1)
        client.publish(STATUS_TOPIC, "OFF", retain=True)

def publish_status(client):
    """Reads the current GPIO state and publishes it to the status topic."""
    pin_state = gpio_read(CONTATORA_PIN)
    # '0' represents LOW (matches original active-low relay logic for ON)
    current_status = "ON" if pin_state == "0" else "OFF"
    client.publish(STATUS_TOPIC, current_status, retain=True)
    return current_status

# --- Main ---
# Initialize the pin direction before connecting to the broker
init_gpio()

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, 1883, 60)
    print("Starting MQTT listener thread...")
    
    # loop_start() runs the network loop in a background thread
    client.loop_start() 

    print(f"Beginning periodic status checks every {POLL_INTERVAL} seconds.")
    last_status = None
    
    while True:
        current_status = publish_status(client)
        
        # Optional: Print to console only if the status actually changed
        if current_status != last_status:
            print(f"Status updated/verified: {current_status}")
            last_status = current_status
            
        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\nQuitting...")
    client.loop_stop()  # Cleanly stop the background thread
except Exception as e:
    print(f"Error: {e}")
