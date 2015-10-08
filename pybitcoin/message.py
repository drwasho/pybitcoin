__author__ = 'chris'
import time
import random
from hashlib import sha256
from serializer import serialize

MAINNET = "d9b4bef9"
TESTNET3 = "0709110b"
USER_AGENT = "/pyBitcoin:0.1/"
SERVICES = "0000000000000000"
PROTOCOL_VERSION = 70002
PORT = 8333


def message(payload, params=MAINNET):
    command = payload.keys()[0]
    payload = serialize(payload)
    m = {
        "message": {
            "magic": params,
            "command": command,
            "length": len(payload),
            "checksum": sha256(sha256(payload).digest()).digest().encode("hex")[:8],
            "payload": payload
        }
    }
    return m


def version(protocol_version=None, services=None, timestamp=None, addr_recv=None,
            addr_from=None, nonce=None, user_agent=None, start_height=0, relay=False):
    ADDR_RECV = {
        "services": SERVICES,
        "ip": "127.0.0.1",
        "port": PORT
    }

    ADDR_FROM = {
        "services": SERVICES,
        "ip": "127.0.0.1",
        "port": PORT
    }

    ver = {
        "version": {
            "version": PROTOCOL_VERSION if not protocol_version else protocol_version,
            "services": SERVICES if not services else services,
            "timestamp": int(time.time()) if not timestamp else timestamp,
            "addr_recv": ADDR_RECV if not addr_recv else addr_recv,
            "addr_from": ADDR_FROM if not addr_from else addr_from,
            "nonce": sha256(str(random.getrandbits(255))).digest().encode("hex")[:16] if not nonce else nonce,
            "user_agent": USER_AGENT if not user_agent else user_agent,
            "start_height": start_height,
            "relay": relay
        }
    }
    return ver


def verack():
    return {"verack": {}}


def filer_load(filter=None, n_hash_functions=None, n_tweak=None, n_flags=None):
    fload = {
        "filterload":
            {
                "filter": filter if filter else "00",
                "nHashFunctions": n_hash_functions if n_hash_functions else 1,
                "nTweak": n_tweak if n_tweak else random.getrandbits(32),
                "nFlags": n_flags if n_flags else 0
            }
    }
    return fload


def filter_add(data):
    fadd = {
        "filteradd":
            {
                "data": data
            }
    }
    return fadd


def filter_clear():
    return {"filterclear": {}}


def inv(type, hash):
    inventory = {
        "inv": [(type, hash)]
    }
    return inventory


def get_data(type, hash):
    data = {
        "getdata": [(type, hash)]
    }
    return data


def tx(tx):
    transaction = {
        "tx": tx
    }
    return transaction