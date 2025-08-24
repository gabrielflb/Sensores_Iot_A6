import asyncio
import json
import base64
import uuid
from aiocoap import Context, Message, PUT
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from dotenv import load_dotenv
import random
from datetime import datetime, timezone

load_dotenv()

# -------------------- Config --------------------
BACKEND_COAP_HOST = "127.0.0.1"
BACKEND_COAP_PORT = 5683
RESOURCE_PATH = "gas_level"  
AES_KEY = os.getenv("AES_KEY", "").encode()

if len(AES_KEY) != 32:
    raise RuntimeError("AES_KEY deve ter 32 bytes")

# -------------------- Funções --------------------
def encrypt_payload(data: dict) -> str:
    """Criptografa o JSON usando AES-GCM e retorna base64(nonce + ciphertext)."""
    aesgcm = AESGCM(AES_KEY)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    payload_b64 = base64.b64encode(nonce + ciphertext).decode("utf-8")
    return payload_b64

def make_gas_data(level: float) -> dict:
    """Monta o payload padronizado para o sensor de gás."""
    anomaly = level > 450  
    return {
        "msg_id": str(uuid.uuid4()),
        "device_id": "dev-gas-01",
        "sensor": "gas",
        "value": level,
        "unit": "ppm",
        "anomaly": anomaly,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def send_gas_level(level: float):
    context = await Context.create_client_context()
    payload = encrypt_payload(make_gas_data(level))
    request = Message(
        code=PUT,
        payload=payload.encode("utf-8"),
        uri=f"coap://{BACKEND_COAP_HOST}:{BACKEND_COAP_PORT}/{RESOURCE_PATH}"
    )
    try:
        response = await context.request(request).response
        print(f"[CoAP] Resposta do backend: {response.code}")
    except Exception as e:
        print(f"[CoAP] Erro ao enviar: {e}")

# -------------------- Loop principal --------------------
async def main():
    print("[CoAP] Sensor de gás iniciado")
    while True:
        level = round(random.uniform(200, 600), 2)  # ppm
        await send_gas_level(level)
        await asyncio.sleep(5)  

if __name__ == "__main__":
    asyncio.run(main())
