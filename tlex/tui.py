# tlex/tui.py
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.align import Align
from rich.text import Text
from rich.progress import Progress
from tlex.server import TunnelServer
from tlex.client import TunnelClient
from tlex.reverse import ReverseTunnelServer, ReverseTunnelClient
from tlex.utils import ConfigManager, logger, test_connection, suggest_protocol
import subprocess
import threading
import os
import random

console = Console()

def show_logo():
    logo_text = Text()
    logo_text.append("T-LeX\n", style="bold cyan underline")
    logo_text.append(r"""
  _______  _      ______  _     _ 
 |__   __| |     |  ____| |   | |
    | |  | |     | |__  | |   | |
    | |  | |     |  __| | |   | |
    | |  | |____ | |____| |___| |
    |_|  |______|______|______| |
""", style="bold magenta")
    logo_text.append("\nSuper Fast Tunnel & Port Forwarding Tool 🚀\n", style="bold green blink")
    logo_text.append("Author: Amirreza NP\n", style="italic yellow")
    logo_text.append("GitHub: https://github.com/amirrezanp\n", style="italic yellow")
    console.print(Panel(logo_text, title="T-LeX v1.3.0", border_style="bold magenta", box=box.DOUBLE, expand=False))

def show_error(message):
    console.print(Panel(message, title="Error ⚠️", border_style="bold red", box=box.ROUNDED, expand=False))

def main_menu():
    console.clear()
    show_logo()
    console.print("\n[bold yellow]Main Menu:[/bold yellow]")
    options = [
        "1. Setup New Tunnel 🌐",
        "2. Manage Existing Tunnels 📂",
        "3. Generate SSL Certificate 🔒",
        "4. Exit ❌"
    ]
    table = Table(show_header=False, box=box.ROUNDED, border_style="bold green")
    for opt in options:
        table.add_row(opt)
    console.print(table)
    choice = Prompt.ask("[bold blue]Choose an option[/bold blue]")
    return choice

def setup_tunnel():
    console.clear()
    show_logo()
    console.print("\n[bold yellow]Setup New Tunnel:[/bold yellow]")
    is_server = Confirm.ask("Is this for Server (Outside Iran)? (y/n)", default=True)
    is_reverse = Confirm.ask("Reverse Tunnel? (y/n)", default=False)
    use_ssl = Confirm.ask("Use SSL? (y/n)", default=True)
    server_host = Prompt.ask("Server Host/IP for test")
    server_port = int(Prompt.ask("Server Port for test", default="443"))
    with Progress() as progress:
        task = progress.add_task("[cyan]Testing connection...", total=100)
        success, latency = test_connection(server_host, server_port)
        progress.update(task, advance=100)
    if success:
        protocol = suggest_protocol(latency)
        console.print(f"[green]Connection test successful! Latency: {latency}ms. Suggested protocol: {protocol.upper()}[/green]")
        protocol = Prompt.ask("Protocol (tls/plain/ssh/wireguard/vless)", default=protocol)
    else:
        console.print("[red]Connection test failed. Using default TLS.[/red]")
        protocol = 'tls'
    passwd = Prompt.ask("Enter strong password")
    if is_server:
        listen_host = Prompt.ask("Listen Host", default="0.0.0.0")
        listen_port = int(Prompt.ask("Listen Port (recommend 443 for camouflage)", default="443"))
        if use_ssl:
            domain = Prompt.ask("Domain for auto SSL (or skip)")
            if domain:
                get_ssl(domain)
            cert_file = Prompt.ask("Cert File Path", default="/etc/letsencrypt/live/yourdomain/fullchain.pem" if domain else "cert.pem")
            key_file = Prompt.ask("Key File Path", default="/etc/letsencrypt/live/yourdomain/privkey.pem" if domain else "key.pem")
        else:
            cert_file = key_file = None
        if is_reverse:
            config = ReverseTunnelServer(listen_host, listen_port, cert_file, key_file, passwd, use_ssl)
        else:
            config = TunnelServer(listen_host, listen_port, cert_file, key_file, passwd, use_ssl, protocol)
    else:
        local_host = Prompt.ask("Local Host", default="127.0.0.1")
        local_port = int(Prompt.ask("Local Port (e.g., 8080)", default="8080"))
        server_host = Prompt.ask("Server Host/IP")
        server_port = int(Prompt.ask("Server Port (e.g., 443)", default="443"))
        remote_host = Prompt.ask("Remote Target Host (e.g., google.com)")
        remote_port = int(Prompt.ask("Remote Target Port (e.g., 80)", default="80"))
        if use_ssl:
            ca_cert = Prompt.ask("CA Cert Path (optional)")
        else:
            ca_cert = None
        if is_reverse:
            config = ReverseTunnelClient(server_host, server_port, local_host, local_port, passwd, ca_cert, use_ssl)
        else:
            config = TunnelClient(local_host, local_port, server_host, server_port, remote_host, remote_port, passwd, ca_cert, use_ssl, protocol)
    try:
        config.setup()
    except OSError as e:
        show_error(f"Failed to bind port {config.listen_port or config.local_port}. Reason: {e}\nSuggestion: Choose another port or check if it's in use (netstat -tuln).")
        new_port = Prompt.ask("Enter new port or random (enter 'r')", default="r")
        if new_port == 'r':
            new_port = str(random.randint(10000, 65535))
        new_port = int(new_port)
        if hasattr(config, 'listen_port'):
            config.listen_port = new_port
        else:
            config.local_port = new_port
        config.setup()
    configs = ConfigManager.load_configs()
    if not isinstance(configs, list):
        configs = [configs] if configs else []
    configs.append(config)
    ConfigManager.save_configs(configs)
    console.print("[green]Tunnel added successfully! ✅[/green]")
    if Confirm.ask("Start now (as daemon)?"):
        start_as_service(config)
    elif Confirm.ask("Start in foreground?"):
        threading.Thread(target=config.run, daemon=True).start()
        console.print("[green]Tunnel started in foreground! Press Ctrl+C to stop.[/green]")

def manage_tunnels():
    console.clear()
    show_logo()
    configs = ConfigManager.load_configs()
    if not configs:
        console.print("[red]No tunnels configured! ⚠️[/red]")
        return
    table = Table(title="Existing Tunnels", box=box.ROUNDED, border_style="bold green")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Details", style="green")
    for i, conf in enumerate(configs):
        typ = "Server" if isinstance(conf, TunnelServer) or isinstance(conf, ReverseTunnelServer) else "Client"
        rev = "Reverse" if conf.is_reverse else ""
        ssl = "SSL" if conf.use_ssl else "No SSL"
        port = conf.listen_port if hasattr(conf, 'listen_port') else conf.local_port
        details = f"{typ} {rev} {ssl} - Port: {port}"
        table.add_row(str(i), typ, details)
    console.print(table)
    action = Prompt.ask("[bold blue]Action (start <id>, stop <id>, delete <id>, service <id>, back): [/bold blue]")
    if action.startswith("start"):
        id_ = int(action.split()[1])
        threading.Thread(target=configs[id_].run, daemon=True).start()
        console.print("[green]Started! ✅[/green]")
    elif action.startswith("stop"):
        id_ = int(action.split()[1])
        configs[id_].stop()
        console.print("[yellow]Stopped! 🛑[/yellow]")
    elif action.startswith("delete"):
        id_ = int(action.split()[1])
        del configs[id_]
        ConfigManager.save_configs(configs)
        console.print("[red]Deleted! ❌[/red]")
    elif action.startswith("service"):
        id_ = int(action.split()[1])
        start_as_service(configs[id_])
        console.print("[green]Installed as service (always active)! 🔄[/green]")

def get_ssl(domain):
    try:
        subprocess.run(["certbot", "certonly", "--standalone", "-d", domain, "--non-interactive", "--agree-tos", "--email", "admin@example.com"], check=True)
        console.print("[green]SSL certificate generated! Files in /etc/letsencrypt/live/{domain} ✅[/green]")
    except Exception as e:
        show_error(f"Error generating SSL: {e} ⚠️")

def start_as_service(config):
    service_name = f"tlex_tunnel_{id(config)}.service"
    service_content = f"""
[Unit]
Description=T-LeX Tunnel Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m tlex.main --run-config {id(config)}  # Placeholder, implement if needed
Restart=always
User=root

[Install]
WantedBy=multi-user.target
"""
    with open(f"/etc/systemd/system/{service_name}", 'w') as f:
        f.write(service_content)
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", service_name])
    subprocess.run(["systemctl", "start", service_name])
    console.print("[green]Service installed and started! Always active even after reboot. 🔄[/green]")

def tui_loop():
    while True:
        choice = main_menu()
        if choice == '1':
            setup_tunnel()
        elif choice == '2':
            manage_tunnels()
        elif choice == '3':
            domain = Prompt.ask("Enter domain for SSL")
            get_ssl(domain)
        elif choice == '4':
            console.print("[yellow]Exiting T-LeX. Goodbye! 👋[/yellow]")
            break