import os
import time
import json
import random
import uuid
import datetime
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIG =====
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("MQTT_TOPIC", "sensors/temperature") 

client = mqtt.Client(client_id="malicious_sensor_temp")

def connect():
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()

def make_data():
    value = round(random.uniform(35.0, 45.0), 2) 
    return {
        "msg_id": str(uuid.uuid4()),
        "device_id": "dev-temp-malicious-01", 
        "sensor": "temperature",
        "value": value,
        "unit": "C",
        "anomaly": True,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

def publish_loop():
    while True:
        data = make_data()
        payload_str = json.dumps(data)
        client.publish(TOPIC, payload_str, qos=1)
        print(f"[MALICIOUS TEMP] Publicado DADO NÃO CRIPTOGRAFADO: {data}")
        time.sleep(10)

if __name__ == "__main__":
    connect()
    try:
        publish_loop()
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()