# tlex/server.py
import socket
import ssl
import paramiko
import subprocess
import uuid
from tlex.utils import PipeHandler, BUFFER_SIZE, logger, generate_x25519_keys, generate_wireguard_keys

class TunnelServer:
    def __init__(self, listen_host='0.0.0.0', listen_port=443, cert_file=None, key_file=None, passwd='', use_ssl=True, protocol='tls'):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.cert_file = cert_file
        self.key_file = key_file
        self.passwd = passwd
        self.use_ssl = use_ssl
        self.protocol = protocol.lower()
        self.context = None
        self.ssh_host_key = paramiko.RSAKey.generate(2048) if protocol == 'ssh' else None
        if self.protocol == 'tls' and self.use_ssl:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
        self.listener = None
        self.is_reverse = False
        self.process = None

    def setup(self):
        try:
            if self.protocol in ['wireguard', 'vless']:
                self.setup_advanced()
            else:
                self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.listener.bind((self.listen_host, self.listen_port))
                self.listener.listen(5)
            logger.info(f"Server listening on {self.listen_host}:{self.listen_port} (Protocol: {self.protocol.upper()}, SSL: {self.use_ssl})")
        except OSError as e:
            logger.error(f"Bind error: {e}. Port may be in use or invalid host.")
            raise

    def setup_advanced(self):
        if self.protocol == 'wireguard':
            priv, pub = generate_wireguard_keys()
            conf = f"""
[Interface]
Address = 10.0.0.1/24
PrivateKey = {priv}
ListenPort = {self.listen_port}
"""
            with open('/etc/wireguard/wg0.conf', 'w') as f:
                f.write(conf)
            self.process = subprocess.Popen(["wg-quick", "up", "wg0"])
        elif self.protocol == 'vless':
            id_ = str(uuid.uuid4())
            priv_b64, pub_b64 = generate_x25519_keys()
            short_id = os.urandom(4).hex()
            dest = random.choice(['www.microsoft.com:443', 'www.apple.com:443', 'www.google.com:443'])
            conf = {
                "inbounds": [
                    {
                        "port": self.listen_port,
                        "protocol": "vless",
                        "settings": {
                            "clients": [
                                {
                                    "id": id_,
                                    "flow": "xtls-rprx-vision"
                                }
                            ],
                            "decryption": "none"
                        },
                        "streamSettings": {
                            "network": "tcp",
                            "security": "reality",
                            "realitySettings": {
                                "dest": dest,
                                "xver": 0,
                                "serverNames": [dest.split(':')[0]],
                                "privateKey": priv_b64,
                                "shortIds": [short_id]
                            }
                        }
                    }
                ],
                "outbounds": [
                    {
                        "protocol": "freedom"
                    }
                ]
            }
            with open('/tmp/xray_server.json', 'w') as f:
                json.dump(conf, f)
            self.process = subprocess.Popen(["xray", "-config", "/tmp/xray_server.json"])

    def run(self):
        if self.protocol in ['wireguard', 'vless']:
            logger.info(f"{self.protocol.upper()} tunnel active. Use client to connect.")
            while True:
                time.sleep(1)  # Keep running
        if not self.listener:
            self.setup()
        while True:
            try:
                client_sock_tmp, addr = self.listener.accept()
                logger.info(f"Accepted connection from {addr}")
                client_conn = client_sock_tmp
                if self.protocol == 'tls' and self.use_ssl:
                    client_conn = self.context.wrap_socket(client_sock_tmp, server_side=True)
                elif self.protocol == 'ssh':
                    transport = paramiko.Transport(client_sock_tmp)
                    transport.add_server_key(self.ssh_host_key)
                    transport.start_server(server=paramiko.ServerInterface())
                    client_conn = transport.accept(20)
                    if client_conn is None:
                        continue
                
                recv_pass = client_conn.recv(BUFFER_SIZE).decode('utf-8')
                if recv_pass != self.passwd:
                    logger.warning("Invalid password")
                    client_conn.close()
                    continue
                
                host_len_bytes = client_conn.recv(1)
                if len(host_len_bytes) == 0:
                    client_conn.close()
                    continue
                host_len = int.from_bytes(host_len_bytes, 'big')
                host_bytes = client_conn.recv(host_len)
                port_bytes = client_conn.recv(2)
                host = host_bytes.decode('utf-8')
                port = int.from_bytes(port_bytes, 'big')
                
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.connect((host, port))
                logger.info(f"Connected to remote {host}:{port}")
                
                client_conn.sendall(self.passwd.encode('utf-8'))
                
                PipeHandler.pipe_sockets(client_conn, remote_sock)
                
                remote_sock.close()
                client_conn.close()
            except Exception as e:
                logger.error(f"Error in server loop: {e}")

    def stop(self):
        if self.protocol in ['wireguard', 'vless']:
            if self.process:
                self.process.terminate()
        if self.listener:
            self.listener.close()
            logger.info("Server stopped")