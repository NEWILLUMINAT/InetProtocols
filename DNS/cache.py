import pickle
from datetime import datetime, timedelta


def load_cache():
    try:
        with open('cache.data', 'rb') as f:
            cache = pickle.load(f)
        print('Cache loaded')
    except FileNotFoundError:
        print('Cache not found')
        return DNSCache()
    return cache


def save_cache(cache):
    try:
        with open('cache.data', 'wb') as f:
            pickle.dump(cache, f)
        print('Cache saved')
    except FileNotFoundError:
        print('Error saving the cache')


def inspect_cache_list(cache_list, time):
    for key in list(cache_list.keys()):
        cache_list[key] = [x for x in cache_list[key] if x[1] > time]
        if not len(cache_list[key]):
            cache_list.pop(key)


class DNSCache:
    def __init__(self):
        self.ipv4_addresses = {}
        self.ipv6_addresses = {}
        self.names = {}
        self.nsnames = {}

    def add_name(self, address, name, TTL):
        self.names[address] = (name, datetime.now() + timedelta(seconds=TTL))

    def add_nsname(self, name, nsname, TTL):
        if name not in self.nsnames:
            self.nsnames[name] = []
        self.nsnames[name].append(
            (nsname, datetime.now() + timedelta(seconds=TTL)))

    def add_ipv4_address(self, name, address, TTL):
        if name not in self.ipv4_addresses:
            self.ipv4_addresses[name] = []
        self.ipv4_addresses[name].append(
            (address, datetime.now() + timedelta(seconds=TTL)))

    def add_ipv6_address(self, name, address, TTL):
        if name not in self.ipv6_addresses:
            self.ipv6_addresses[name] = []
        self.ipv6_addresses[name].append(
            (address, datetime.now() + timedelta(seconds=TTL)))

    def inspect_cache(self, time):
        inspect_cache_list(self.ipv4_addresses, time)
        inspect_cache_list(self.ipv6_addresses, time)
        inspect_cache_list(self.nsnames, time)
        for key in list(self.names.keys()):
            if self.names[key][1] < time:
                self.names.pop(key)

    def try_find_ipv4(self, name):
        time = datetime.now()
        self.inspect_cache(time)
        if name in self.ipv4_addresses:
            answer = []
            for i in range(len(self.ipv4_addresses[name])):
                answer.append((self.ipv4_addresses[name][i][0], (
                        self.ipv4_addresses[name][i][1] - time).seconds))
            return answer
        else:
            return None

    def try_find_ipv6(self, name):
        time = datetime.now()
        self.inspect_cache(time)
        if name in self.ipv6_addresses:
            answer = []
            for i in range(len(self.ipv6_addresses[name])):
                answer.append((self.ipv6_addresses[name][i][0], (
                        self.ipv6_addresses[name][i][1] - time).seconds))
            return answer
        else:
            return None

    def try_find_name(self, ip):
        time = datetime.now()
        self.inspect_cache(time)
        if ip in self.names:
            return [(self.names[ip][0], (self.names[ip][1] - time).seconds)]
        else:
            return None

    def try_find_nsname(self, name):
        time = datetime.now()
        self.inspect_cache(time)
        if name in self.nsnames:
            answers = []
            for i in range(len(self.nsnames[name])):
                answers.append((self.nsnames[name][i][0],
                                (self.nsnames[name][i][1] - time).seconds))
            return answers
        else:
            return None


