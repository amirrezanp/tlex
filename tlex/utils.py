# tlex/utils.py
import socket
import ssl
import threading
import json
import jsonpickle
import os
import logging
import asyncio
import time
import random
import subprocess
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
import base64

BUFFER_SIZE = 4096

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipeHandler:
    @staticmethod
    async def async_pipe(src, dst):
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.sock_recv(src, BUFFER_SIZE)
                if len(data) == 0:
                    break
                await loop.sock_sendall(dst, data)
            except Exception as e:
                logger.error(f"Pipe error: {e}")
                break

    @staticmethod
    def pipe_sockets(sock1, sock2):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.gather(
            PipeHandler.async_pipe(sock1, sock2),
            PipeHandler.async_pipe(sock2, sock1)
        ))
        loop.close()

class ConfigManager:
    CONFIG_FILE = os.path.expanduser('~/tlex_configs.json')

    @staticmethod
    def load_configs():
        if os.path.exists(ConfigManager.CONFIG_FILE):
            with open(ConfigManager.CONFIG_FILE, 'r') as f:
                try:
                    json_data = json.load(f)
                    configs = jsonpickle.decode(json.dumps(json_data))
                    if not isinstance(configs, list):
                        configs = [configs]
                    return configs
                except Exception as e:
                    logger.error(f"Config load error: {e}")
                    return []
        return []

    @staticmethod
    def save_configs(configs):
        with open(ConfigManager.CONFIG_FILE, 'w') as f:
            json.dump(jsonpickle.encode(configs), f, indent=4)

def test_connection(host, port, protocol='tcp'):
    start = time.time()
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((host, port))
        s.close()
        latency = (time.time() - start) * 1000
        return True, latency
    except Exception as e:
        return False, 0

def suggest_protocol(latency):
    if latency < 50:
        return 'wireguard'  # Fast for low latency
    elif latency < 100:
        return 'vless'
    elif latency < 150:
        return 'tls'
    else:
        return 'ssh'  # Reliable for high latency

def generate_x25519_keys():
    private_key = x25519.X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption())
    private_b64 = base64.b64encode(private_bytes).decode()

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    public_b64 = base64.b64encode(public_bytes).decode()

    return private_b64, public_b64

def generate_wireguard_keys():
    priv = subprocess.check_output("wg genkey", shell=True).decode().strip()
    pub = subprocess.check_output(f"echo '{priv}' | wg pubkey", shell=True).decode().strip()
    return priv, pub