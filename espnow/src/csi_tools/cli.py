"""Command line tools for the three-board ESP-NOW pilot."""
import argparse
import json
from pathlib import Path

from .processing import align_recording
from .protocol import load_json
from .recording import capture
from .simulate import simulate


def main():
    parser = argparse.ArgumentParser(description='Three-board ESP-NOW CSI pilot')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('capture', 'simulate'):
        command = commands.add_parser(name)
        command.add_argument('--config', required=True, type=Path)
        command.add_argument('--metadata', required=True, type=Path)
        command.add_argument('--output', required=True, type=Path)
        command.add_argument('--seconds', type=float, default=12)
    command = commands.add_parser('qc')
    command.add_argument('recording', type=Path)
    commands.add_parser('ports')
    args = parser.parse_args()

    if args.command == 'ports':
        from serial.tools import list_ports

        for port in list_ports.comports():
            print(port.device, port.description, port.serial_number)
    elif args.command == 'qc':
        report = align_recording(args.recording, allow_empty=True)[-1]
        print(json.dumps(report, indent=2))
        if not report['shared_packets']:
            parser.exit(1, 'No unambiguous shared TX packets across both receivers.\n')
    else:
        operation = capture if args.command == 'capture' else simulate
        print(operation(args.output, load_json(args.config), load_json(args.metadata), args.seconds))
