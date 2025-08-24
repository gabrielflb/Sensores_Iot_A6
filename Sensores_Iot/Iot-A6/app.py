import os
import json
import base64
import asyncio
import threading
from typing import Set
from fastapi import FastAPI, WebSocket
from paho.mqtt.client import Client as MqttClient
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import jwt
from fastapi import Query
from datetime import datetime, timedelta
import uvicorn
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from aiocoap import resource, Message, Code
from aiocoap import resource, Context
import asyncio


load_dotenv()

# -------------------- Config --------------------
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", ""))
MQTT_TOPICS = [("sensors/#", 1)]
AES_KEY_ENV = os.getenv("AES_KEY", "")
SECRET_KEY = os.getenv("JWT_SECRET", "")

if not AES_KEY_ENV:
    raise RuntimeError("AES_KEY não definida. Exemplo: export AES_KEY='32-bytes-string...'")

AES_KEY = AES_KEY_ENV.encode()
if len(AES_KEY) != 32:
    raise RuntimeError("AES_KEY deve ter exatamente 32 bytes quando codificada em UTF-8 (AES-256).")

# -------------------- App & state --------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)
connected_websockets = set()
ASYNCIO_LOOP = None  

class GasResource(resource.Resource):
    def __init__(self):
        super().__init__()

    async def render_put(self, request):
        try:
            encrypted_b64 = request.payload.decode("utf-8")
            data = decrypt_payload(encrypted_b64)  # usa sua função AES do backend
            print(f"[CoAP] Dados recebidos: {data}")

            # envia direto para WebSocket
            package = {"topic": "sensors/gas", "payload": data}
            if ASYNCIO_LOOP:
                asyncio.run_coroutine_threadsafe(broadcast(json.dumps(package)), ASYNCIO_LOOP)

            return Message(code=Code.CHANGED, payload=b"Dados recebidos com sucesso")
        except Exception as e:
            print(f"[CoAP] Erro ao processar PUT: {e}")
            return Message(code=Code.BAD_REQUEST, payload=b"Erro no payload")
        
# -------------------- Servidor COAP --------------------        
async def start_coap_server():
    root = resource.Site()
    root.add_resource(['gas_level'], GasResource())
    await Context.create_server_context(root, bind=('127.0.0.1', 5683))
    print("[CoAP] Servidor iniciado na porta 5683")
    await asyncio.get_running_loop().create_future()        

# -------------------- AES-GCM helpers --------------------
def decrypt_payload(encrypted_b64: str) -> dict:
    aesgcm = AESGCM(AES_KEY)
    raw = base64.b64decode(encrypted_b64)
    if len(raw) < 13:
        raise ValueError("Payload muito curto para nonce + ciphertext")
    nonce = raw[:12]
    ciphertext = raw[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))

# -------------------- MQTT callbacks --------------------
def connect(client, userdata, flags, rc):
    print(f"[MQTT] Conectado ao broker {MQTT_BROKER}:{MQTT_PORT} com código {rc}")
    for topic, qos in MQTT_TOPICS:
        client.subscribe(topic, qos=qos)
        print(f"[MQTT] Subscrevendo: {topic} (qos={qos})")

def message(client, userdata, msg):
    print("entrou no message")
    payload_bytes = msg.payload
    try:
        encrypted_b64 = payload_bytes.decode("utf-8")
    except Exception as e:
        print(f"[MQTT] erro ao decodificar payload de bytes para string: {e}")
        return

    try:
        data = decrypt_payload(encrypted_b64)
    except Exception as e:
        print(f"[MQTT] Falha ao descriptografar mensagem do tópico {msg.topic}: {e}")
        return

    package = {"topic": msg.topic, "payload": data}
    print("[MQTT] Enviando para WS:", json.dumps(package))

    if ASYNCIO_LOOP:
        asyncio.run_coroutine_threadsafe(broadcast(json.dumps(package)), ASYNCIO_LOOP)
    else:
        print("[MQTT] Loop asyncio não disponível; não foi possível enviar aos websockets.")

# -------------------- MQTT thread --------------------
def start_mqtt_client():
    mqttc = MqttClient(client_id="backend_aes_fastapi")
    mqttc.on_connect = connect
    mqttc.on_message = message
    print("[MQTT] Callback message atribuído")
    mqttc.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqttc.loop_forever()
    
@app.get("/token")
async def get_token(user: str = Query(..., description="Nome ou ID do usuário")):
    payload = {
        "sub": user,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    print(f"[JWT] Token gerado para {user}: {token}")
    return {"token": token}      
    

# -------------------- WebSocket / broadcast --------------------
async def broadcast(message: str):
    to_remove = []
    for ws in set(connected_websockets):
        try:
            await ws.send_text(message)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        connected_websockets.discard(ws)
        
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008, reason="Token ausente")
        print("[WS] Cliente tentou conectar sem token")
        return

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        await ws.close(code=1008, reason="Token expirado")
        print("[WS] Token expirado")
        return
    except jwt.InvalidTokenError:
        await ws.close(code=1008, reason="Token inválido")
        print("[WS] Token inválido")
        return

    # Conexão aceita
    await ws.accept()
    connected_websockets.add(ws)
    print(f"[WS] Cliente conectado. Total: {len(connected_websockets)} | Usuário: {payload.get('sub')}")

    try:
        while True:
            try:
                _ = await ws.receive_text()
            except Exception:
                break
    finally:
        connected_websockets.discard(ws)
        print(f"[WS] Cliente desconectado. Total: {len(connected_websockets)}")

# -------------------- Startup event --------------------
@app.on_event("startup")
async def startup_event():
    global ASYNCIO_LOOP
    ASYNCIO_LOOP = asyncio.get_running_loop()
    t = threading.Thread(target=start_mqtt_client, daemon=True)
    t.start()
    print("[APP] MQTT client iniciado em thread separada.")
    
    asyncio.create_task(start_coap_server())
    print("[COAP] Criando servidor coap.")

# -------------------- Run --------------------
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
