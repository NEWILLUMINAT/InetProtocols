from concurrent.futures import ThreadPoolExecutor
from struct import pack
import socket
import argparse
import sys

PACKET = b'\x13' + b'\x00' * 39 + b'\x6f\x89\xe9\x1a\xb6\xd5\x3b\xd3'


def is_dns(packet):
    transaction_id = PACKET[:2]
    return transaction_id in packet


def is_sntp(packet):
    transmit_timestamp = PACKET[-8:]
    origin_timestamp = packet[24:32]
    is_packet_from_server = 7 & packet[0] == 4
    return len(packet) >= 48 and is_packet_from_server and origin_timestamp == transmit_timestamp


def is_pop3(packet):
    return packet.startswith(b'+')


def is_http(packet):
    return b'HTTP' in packet


def is_smtp(packet):
    return packet[:3].isdigit()


class Scanner:
    _PROTOCOL_DEFINER = {
        'SMTP': lambda packet: is_smtp(packet),
        'DNS': lambda packet: is_dns(packet),
        'POP3': lambda packet: is_pop3(packet),
        'HTTP': lambda packet: is_http(packet),
        'SNTP': lambda packet: is_sntp(packet)
    }

    def __init__(self, host):
        self._host = host

    def tcp(self, port):
        socket.setdefaulttimeout(0.5)
        result = ''
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as scanner:
            try:
                scanner.connect((self._host, port))
                result = f'TCP {port} - Open.'
            except (socket.timeout, TimeoutError, OSError):
                pass
            try:
                scanner.send(pack('!H', len(PACKET)) + PACKET)
                data = scanner.recv(1024)
                result += f' {self._check(data)}'
            except socket.error:
                pass
        return result

    def udp(self, port):
        socket.setdefaulttimeout(3)
        result = ''
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as scanner:
            try:
                scanner.sendto(PACKET, (self._host, port))
                data, _ = scanner.recvfrom(1024)
            except socket.error:
                result = f'UDP {port} - Open.'
        return result

    def _check(self, data, is_tcp=True):
        for protocol, checker in self._PROTOCOL_DEFINER.items():
            if checker(data):
                return protocol
        return ''


def main(host, start, end, tcp, udp):
    scanner = Scanner(host)
    with ThreadPoolExecutor(max_workers=300) as pool:
        for port in range(start, end + 1):
            pool.submit(execute, scanner, port, tcp, udp)


def execute(scanner: Scanner, port, tcp, udp):
    if tcp:
        show(scanner.tcp(port))
    if udp:
        show(scanner.udp(port))


def show(result):
    if result:
        print(result)


def parse_args():
    parser = argparse.ArgumentParser(
        description='TCP and UDP port scanner')
    parser.add_argument('--host', metavar='host', required=True,
                        default='localhost', help='host to scan')
    parser.add_argument('-p', '--ports', metavar='ports', required=True,
                        help='range of ports: 0-65535')
    parser.add_argument('-t', action='store_true',
                        help='To scan TCP ports')
    parser.add_argument('-u', action='store_true',
                        help='To scan UDP ports')
    args = parser.parse_args()
    max = 65535
    try:
        if '-' in args.ports:
            start, end = args.ports.split('-')
            start, end = int(start), int(end)
        else:
            start, end = int(args.ports), int(args.ports)
    except ValueError:
        print('Port number must be integer')
        sys.exit()
    if end > max:
        print('Port numbers must be less than 65535')
        sys.exit()
    if start > end:
        print('Invalid arguments')
        sys.exit()
    try:
        socket.gethostbyname(args.host)
    except socket.gaierror:
        print(f'Invalid host {args.host}')
        sys.exit()
    return args.host, start, end, args.t, args.u


if __name__ == "__main__":
    host, start, end, tcp, udp = parse_args()
    main(host, start, end, tcp, udp)
