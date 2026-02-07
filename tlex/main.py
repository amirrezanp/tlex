# tlex/main.py
import argparse
import sys
from tlex.tui import tui_loop, console

def main():
    parser = argparse.ArgumentParser(description="T-LeX: Professional Tunnel Tool")
    parser.add_argument("command", choices=['run'], nargs='?', default=None, help="Command: 'run' to launch TUI")
    parser.add_argument("--interactive", action="store_true", help="Run interactive TUI")
    args = parser.parse_args()
    if args.command == 'run' or args.interactive or len(sys.argv) == 1:
        tui_loop()
    else:
        console.print("[yellow]Use 'tlex run' for TUI or --interactive.[/yellow]")

if __name__ == "__main__":
    main()