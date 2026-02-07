from sshtunnel import SSHTunnelForwarder
from tlex.utils import logger

class ReverseTunnel:
    def __init__(self, server, port, username, remote_port):
        self.server = server
        self.port = port
        self.username = username
        self.remote_port = remote_port
        self.tunnel = None

    def start(self):
        self.tunnel = SSHTunnelForwarder(
            (self.server, self.port),
            ssh_username=self.username,
            remote_bind_address=("0.0.0.0", self.remote_port),
            local_bind_address=("127.0.0.1", self.remote_port)
        )
        self.tunnel.start()
        logger.info(f"Reverse tunnel exposed on {self.remote_port}!")

    def stop(self):
        if self.tunnel:
            self.tunnel.stop()
            logger.info("Reverse tunnel stopped!")
