import socket

# import dns_package as dnspm
import cache as dnscm

SERVER = "8.8.8.8"


class Package:
    def __init__(self, data):
        self._data = data

        self.ID = self._data[:2]

        self.QR = self._data[2] >> 7
        self.Opcode = (self._data[2] & 120) >> 3
        self.AA = (self._data[2] & 4) >> 2
        self.TC = (self._data[2] & 2) >> 1
        self.RD = self._data[2] & 1
        self.RA = self._data[3] >> 7
        self.Z = (self._data[3] & 112) >> 4
        self.RCODE = self._data[3] & 15

        self.QDCOUNT = int.from_bytes(self._data[4:6], 'big')
        self.ANCOUNT = int.from_bytes(self._data[6:8], 'big')
        self.NSCOUNT = int.from_bytes(self._data[8:10], 'big')
        self.ARCOUNT = int.from_bytes(self._data[10:12], 'big')

        i = 12
        self.questions = []
        for _ in range(self.QDCOUNT):
            name, i = self.parse_name(i)

            type_number = int.from_bytes(self._data[i: i + 2], 'big')
            qclass = int.from_bytes(self._data[i + 2: i + 4], 'big')

            self.questions.append((name, type_number, qclass))

            i += 4

        self.answers = []
        for _ in range(self.ANCOUNT):
            i = self.parse_resource_record(self.answers, i)

        self.auth = []
        for _ in range(self.NSCOUNT):
            i = self.parse_resource_record(self.auth, i)

        self.add_info = []
        for _ in range(self.ARCOUNT):
            i = self.parse_resource_record(self.add_info, i)

    def parse_name(self, i):
        name = ""
        if self._data[i] != 0:
            ty = self._data[i] >> 6
            if ty == 0:
                le = self._data[i] & 63
                next_part = self.parse_name(i + le + 1)
                name = self._data[i + 1:i + le + 1].decode('ascii') + '.' + \
                       next_part[0]
                i = next_part[1]
            elif ty == 3:
                j = int.from_bytes(
                    (self._data[i] & 63).to_bytes(1, byteorder="big") +
                    self._data[i + 1:i + 2], 'big')
                name = self.parse_name(j)[0]
                i += 2
            else:
                raise Exception
        else:
            i += 1
        return name, i

    def parse_resource_record(self, list, i):
        name, i = self.parse_name(i)

        type_number = int.from_bytes(self._data[i: i + 2], 'big')

        qclass = int.from_bytes(self._data[i + 2: i + 4], 'big')
        TTL = int.from_bytes(self._data[i + 4: i + 8], 'big')
        offset = int.from_bytes(self._data[i + 8: i + 10], 'big')

        i += 10

        if type_number == 1:
            RDATA = ""
            RDLENGTH = 4
            for shift in range(RDLENGTH):
                RDATA += str(self._data[i + shift]) + "."
            RDATA = RDATA[:-1]
        elif type_number == 28:
            RDATA = ""
            RDLENGTH = 16
            for shift in range(0, RDLENGTH, 2):
                RDATA += hex(self._data[i + shift])[2:].zfill(2) + hex(
                    self._data[i + shift + 1])[2:].zfill(2) + ":"
            RDATA = RDATA[:-1]
        elif type_number == 12 or type_number == 2:
            RDATA, _ = self.parse_name(i)
            RDLENGTH = len(RDATA) + 1
        else:
            RDLENGTH = offset
            RDATA = self._data[i: i + RDLENGTH]

        i += offset
        list.append((name, type_number, qclass, TTL, RDLENGTH, RDATA))
        return i

    def add_resource_record(self, name, type_number, qclass, TTL, RDLENGTH, RDATA):
        self._data += b''.join(
            [len(dom).to_bytes(1, byteorder="big") + dom.encode("ascii")
             for dom in name.split('.')])

        self._data += type_number.to_bytes(2, byteorder="big")
        self._data += qclass.to_bytes(2, byteorder="big")
        self._data += TTL.to_bytes(4, byteorder="big")
        self._data += RDLENGTH.to_bytes(2, byteorder="big")
        if type_number == 1:
            self._data += b''.join(map(lambda x: bytes(x), list(
                map(lambda x: int(x).to_bytes(1, byteorder="big"),
                    RDATA.split('.')))))
        elif type_number == 28:
            for i in RDATA.split(':'):
                self._data += int(i[:2], 16).to_bytes(1, byteorder="big")
                self._data += int(i[2:], 16).to_bytes(1, byteorder="big")
        elif type_number == 12 or type_number == 2:
            self._data += b''.join(
                [len(dom).to_bytes(1, byteorder="big") + dom.encode("ascii")
                 for dom in RDATA.split('.')])
        else:
            self._data += RDATA

    def add_answer(self, name, type_number, qclass, TTL, RDATA):
        self.QR = 1
        if type_number == 1:
            RDLENGTH = 4
        elif type_number == 28:
            RDLENGTH = 16
        elif type_number == 12 or type_number == 2:
            RDLENGTH = len(RDATA) + 1
        else:
            raise Exception("wrong answer")

        self.answers.append((name, type_number, qclass, TTL, RDLENGTH, RDATA))

    def get_data(self):
        self.update_data()
        return self._data

    def update_data(self):
        self._data = b''
        self._data += self.ID
        self._data += ((self.QR << 7) + (self.Opcode << 3) + (self.AA << 2) + (
                self.TC << 1) + self.RD).to_bytes(1, byteorder="big")
        self._data += ((self.RA << 7) + (self.Z << 4) + self.RCODE) \
            .to_bytes(1, byteorder="big")
        self._data += len(self.questions).to_bytes(2, byteorder="big")
        self._data += len(self.answers).to_bytes(2, byteorder="big")
        self._data += len(self.auth).to_bytes(2, byteorder="big")
        self._data += len(self.add_info).to_bytes(2, byteorder="big")

        for name, type_number, qclass in self.questions:
            self._data += b''.join(
                [len(dom).to_bytes(1, byteorder="big") + dom.encode("ascii")
                 for dom in name.split('.')])

            self._data += type_number.to_bytes(2, byteorder="big")
            self._data += qclass.to_bytes(2, byteorder="big")

        for name, type_number, qclass, TTL, RDLENGTH, RDATA in self.answers + self.auth + self.add_info:
            self.add_resource_record(name, type_number, qclass, TTL, RDLENGTH, RDATA)



def process_resource_record(record):
    print("New RR: " + str(record))
    name, type, qclass, TTL, RDLENGTH, RDATA = record
    if type == 1:
        ch.add_ipv4_address(name, RDATA, TTL)
    elif type == 12:
        name = name[:-13]
        name = ".".join(reversed(name.split('.')))[1:]
        ch.add_name(name, RDATA, TTL)
    elif type == 28:
        ch.add_ipv6_address(name, RDATA, TTL)
    elif type == 2:
        ch.add_nsname(name, RDATA, TTL)
    else:
        print("not remembered")


def work_loop(cache):
    global sock

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("localhost", 53))

        data, addr = sock.recvfrom(2048)

        print("\n\n")
        print("QUERY")
        try:
            package = Package(data)  # dnspm.parse_package(data)

            print("\n")
            print("(QNAME, QTYPE, QCLASS)")
            print("package.questions: " + str(package.questions))
            for name, type_number, qclass in package.questions:
                if qclass == 1:
                    if type_number == 1:
                        answers = cache.try_find_ipv4(name)
                    elif type_number == 12:
                        ip = name[:-13]  # remove ".in-addr.arpa"
                        ip = ".".join(reversed(ip.split('.')))[1:]
                        answers = cache.try_find_name(ip)
                    elif type_number == 28:
                        answers = cache.try_find_ipv6(name)
                    elif type_number == 2:
                        answers = cache.try_find_nsname(name)
                    else:
                        raise Exception(f"error in type {type_number}")

                    if answers:
                        print("Answers in cache")
                        for answer, TTL in answers:
                            package.add_answer(name, type_number, qclass, TTL, answer)
                        print("(NAME, TYPE, CLASS, TTL, RDLENGTH, RDATA)")
                        print("package.answers: " + str(package.answers))
                    else:
                        print("There was no answer in the cache")
                        sock.sendto(package.get_data(), (SERVER, 53))
                        data, _ = sock.recvfrom(2048)

                        package = Package(data)  # dnspm.parse_package(data)
                        print("(NAME, TYPE, CLASS, TTL, RDLENGTH, RDATA)")
                        for RR in package.answers + package.auth + package.add_info:
                            process_resource_record(RR)
                else:
                    raise Exception(f"error in class {qclass}")

            sock.sendto(package.get_data(), addr)
        except Exception as e:
            sock.sendto(data, (SERVER, 53))
            data, _ = sock.recvfrom(2048)
            sock.sendto(data, addr)
            print(f"error in package:\n {e}")
        print("\n")
        sock.close()
        dnscm.save_cache(cache)


if __name__ == "__main__":
    print('start:')

    global ch
    ch = dnscm.load_cache()
    work_loop(ch)
