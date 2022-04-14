import argparse
import socket
import struct
import sys
import requests
import re
import ping_message


def run(destination, hops, timeout):
    for hop in range(1, hops):
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        my_socket.settimeout(timeout / 1000)
        my_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, struct.pack("I", hop))
        is_success = get_route(destination, my_socket, hop)
        if is_success:
            print("success\n")
            exit(0)


def get_route(destination, my_socket, number):
    ping = ping_message.ping_request()
    my_socket.sendto(ping, (destination, 0))
    try:
        recv_packet, address = my_socket.recvfrom(1024)
    except socket.timeout:
        print("timeout\n\n")
        return False

    header = recv_packet[20]
    if header in [0, 3, 11]:
        res = get_as(address[0])
        inf = requests.get(f"http://ip-api.com/json/{address[0]}").json()
        int_prov = inf.get("isp")
        country = inf.get("country")
        print(f'{number} | IP Address: {address[0]} | AS: {res} | Provider: {int_prov} | Country: {country}\n')
    if header == 0:
        return True

    return False


def get_as(ip):
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.connect(("whois.arin.net", 43))
    my_socket.send((ip + "\r\n").encode())
    response = b""
    while True:
        d = my_socket.recv(4096)
        response += d
        if not d:
            break
    response = response.decode()

    as_pattern = re.compile(r'(OriginAS:.*?)(?=\n)')
    net_name_pattern = re.compile(r'(NetName:.*?)(?=\n)')
    AS = as_pattern.findall(response)[0].split(":")[1].replace(" ", "")
    name = net_name_pattern.findall(response)[0].split(":")[1].replace(" ", "")
    return f"{name} {AS}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination')

    parser.add_argument('-ttl', type=int, dest='ttl', default=40,
                        help='Время жизни пакета(количество прыжков между маршрутизаторами).')

    parser.add_argument('-timeout', type=float, dest='timeout', default=5000.0,
                        help='Время ожидания для получения ответа от маршрутизатора.')

    args = parser.parse_args()

    destination = args.destination
    try:
        host = socket.gethostbyname(destination)
    except Exception:
        print(f"{args} address not Found")
        sys.exit(-1)
    run(host, args.ttl, args.timeout)


if __name__ == "__main__":
    main()

