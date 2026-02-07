# tlex/client.py
import socket
import ssl
import paramiko
import subprocess
import uuid
from tlex.utils import PipeHandler, BUFFER_SIZE, logger, generate_x25519_keys, generate_wireguard_keys

class TunnelClient:
    def __init__(self, local_host='127.0.0.1', local_port=8080, server_host='', server_port=443, remote_host='', remote_port=80, passwd='', ca_cert=None, use_ssl=True, protocol='tls'):
        self.local_host = local_host
        self.local_port = local_port
        self.server_host = server_host
        self.server_port = server_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.passwd = passwd
        self.ca_cert = ca_cert
        self.use_ssl = use_ssl
        self.protocol = protocol.lower()
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if protocol == 'tls' else None
        if self.protocol == 'tls' and self.use_ssl:
            if self.ca_cert:
                self.context.load_verify_locations(self.ca_cert)
                self.context.verify_mode = ssl.CERT_REQUIRED
            else:
                self.context.verify_mode = ssl.CERT_NONE
                self.context.check_hostname = False
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
                self.listener.bind((self.local_host, self.local_port))
                self.listener.listen(5)
            logger.info(f"Client listening locally on {self.local_host}:{self.local_port} forwarding to {self.remote_host}:{self.remote_port} via {self.server_host}:{self.server_port} (Protocol: {self.protocol.upper()}, SSL: {self.use_ssl})")
        except OSError as e:
            logger.error(f"Bind error: {e}. Port may be in use.")
            raise

    def setup_advanced(self):
        if self.protocol == 'wireguard':
            priv, pub = generate_wireguard_keys()
            conf = f"""
[Interface]
Address = 10.0.0.2/24
PrivateKey = {priv}
DNS = 8.8.8.8

[Peer]
PublicKey = <server_pub>  # User input or from config
Endpoint = {self.server_host}:{self.server_port}
AllowedIPs = 0.0.0.0/0
"""
            with open('/etc/wireguard/wg0.conf', 'w') as f:
                f.write(conf)
            self.process = subprocess.Popen(["wg-quick", "up", "wg0"])
        elif self.protocol == 'vless':
            id_ = str(uuid.uuid4())
            priv_b64, pub_b64 = generate_x25519_keys()
            short_id = os.urandom(4).hex()
            server_name = random.choice(['www.microsoft.com', 'www.apple.com', 'www.google.com'])
            conf = {
                "inbounds": [
                    {
                        "port": self.local_port,
                        "protocol": "socks",
                        "settings": {
                            "auth": "noauth",
                            "udp": true
                        }
                    }
                ],
                "outbounds": [
                    {
                        "protocol": "vless",
                        "settings": {
                            "vnext": [
                                {
                                    "address": self.server_host,
                                    "port": self.server_port,
                                    "users": [
                                        {
                                            "id": id_,
                                            "flow": "xtls-rprx-vision",
                                            "encryption": "none"
                                        }
                                    ]
                                }
                            ]
                        },
                        "streamSettings": {
                            "network": "tcp",
                            "security": "reality",
                            "realitySettings": {
                                "show": false,
                                "fingerprint": "chrome",
                                "serverName": server_name,
                                "publicKey": pub_b64,
                                "shortId": short_id,
                                "spiderX": "/"
                            }
                        }
                    }
                ]
            }
            with open('/tmp/xray_client.json', 'w') as f:
                json.dump(conf, f)
            self.process = subprocess.Popen(["xray", "-config", "/tmp/xray_client.json"])

    def run(self):
        if self.protocol in ['wireguard', 'vless']:
            logger.info(f"{self.protocol.upper()} tunnel active. Internet should be free.")
            while True:
                time.sleep(1)
        if not self.listener:
            self.setup()
        while True:
            try:
                local_conn, addr = self.listener.accept()
                logger.info(f"Accepted local connection from {addr}")
                
                server_sock_tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock_tmp.connect((self.server_host, self.server_port))
                server_conn = server_sock_tmp
                if self.protocol == 'tls' and self.use_ssl:
                    server_conn = self.context.wrap_socket(server_sock_tmp, server_hostname=self.server_host)
                elif self.protocol == 'ssh':
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(self.server_host, self.server_port, username='user', password=self.passwd)  # Assume SSH auth
                    server_conn = client.open_sftp()  # Or channel for tunnel
                
                server_conn.sendall(self.passwd.encode('utf-8'))
                
                host_bytes = self.remote_host.encode('utf-8')
                host_len = len(host_bytes).to_bytes(1, 'big')
                port_bytes = self.remote_port.to_bytes(2, 'big')
                server_conn.sendall(host_len + host_bytes + port_bytes)
                
                resp = server_conn.recv(BUFFER_SIZE).decode('utf-8')
                if resp != self.passwd:
                    logger.warning("Association failed")
                    local_conn.close()
                    server_conn.close()
                    continue
                
                PipeHandler.pipe_sockets(local_conn, server_conn)
                
                local_conn.close()
                server_conn.close()
            except Exception as e:
                logger.error(f"Error in client loop: {e}")

    def stop(self):
        if self.protocol in ['wireguard', 'vless']:
            if self.process:
                self.process.terminate()
        if self.listener:
            self.listener.close()
            logger.info("Client stopped")