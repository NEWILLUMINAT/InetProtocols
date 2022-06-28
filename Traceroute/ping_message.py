import socket
import struct


def calculate_checksum(source_string):
    str = bytearray(source_string)
    checksum = 0
    count = (len(str) // 2) * 2

    for count in range(0, count, 2):
        this_val = str[count + 1] * 256 + str[count]
        checksum = checksum + this_val
        checksum = checksum & 0xffffffff

    if count < len(str):
        checksum = checksum + str[-1]
        checksum = checksum & 0xffffffff

    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum = checksum + (checksum >> 16)
    result = ~checksum
    result = result & 0xffff
    result = result >> 8 | (result << 8 & 0xff00)
    return result


def ping_request():
    icmp_echo = 8
    icmp_code = 0
    checksum = 0
    headers = struct.pack("bbHH", icmp_echo, icmp_code, checksum, 1)
    data = struct.pack('qqqqqqqq', 0, 0, 0, 0, 0, 0, 0, 0)
    checksum = socket.htons(calculate_checksum(headers + data))
    headers = struct.pack("bbHH", icmp_echo, icmp_code, checksum, 1)
    return headers + data


