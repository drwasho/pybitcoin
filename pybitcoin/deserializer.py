__author__ = 'chris'
import struct
import socket
import bitcoin
from binascii import hexlify
from hashlib import sha256
from message import version


def var_int(bytes):
    if int(bytes[:1].encode("hex"), 16) < 253:
        return (struct.unpack('<B', bytes[:1])[0], 1)
    elif bytes[:1].encode("hex") == "fd":
        return (struct.unpack('<H', bytes[1:3])[0], 3)
    elif bytes[:1].encode("hex") == "fe":
        return (struct.unpack('<L', bytes[1:5])[0], 5)
    elif bytes[:1].encode("hex") == "ff":
        return (struct.unpack('<Q', bytes[1:9])[0], 9)


def deserialize(bytes, type="message"):
    try:
        if type == "message":
            obj = {
                "message": {
                    "magic": hex(struct.unpack('<L', bytes[:4])[0])[2:],
                    "command": hexlify(bytes[4:16]).decode("hex").replace("\x00", ""),
                    "length": struct.unpack('<L', bytes[16:20])[0],
                    "checksum": hex(struct.unpack('>L', bytes[20:24])[0])[2:],
                    "payload": bytes[24:24+struct.unpack('<L', bytes[16:20])[0]]
                }
            }
            while len(obj["message"]["checksum"]) < 8:
                obj["message"]["checksum"] = "0" + obj["message"]["checksum"]
            if sha256(sha256(obj["message"]["payload"]).digest()).digest().encode("hex")[:8] != \
                    obj["message"]["checksum"] and obj["message"]["command"] != "verack":
                raise Exception("Invalid Checksum")
            return obj

        elif type == "version":
            version_num = struct.unpack('<L', bytes[:4])[0]
            services = bytes[4:12].encode("hex")
            timestamp = struct.unpack('<Q', bytes[12:20])[0]
            addr_recv = {
                "services": hexlify(bytes[20:28]),
                "port": int(bytes[44:46].encode("hex"), 16)
            }
            if bytes[28:40].encode("hex") == "00000000000000000000ffff":
                addr_recv["ip"] = socket.inet_ntoa(bytes[40:44])
            else:
                addr_recv["ip"] = socket.inet_ntoa(bytes[28:44])
            addr_from = {
                "services": hexlify(bytes[46:54]),
                "port": int(bytes[70:72].encode("hex"), 16)
            }
            if bytes[54:66].encode("hex") == "00000000000000000000ffff":
                addr_from["ip"] = socket.inet_ntoa(bytes[66:70])
            else:
                addr_from["ip"] = socket.inet_ntoa(bytes[54:70])
            nonce = bytes[72:80].encode("hex")
            var_str = var_int(bytes[80:])
            user_agent = bytes[80+var_str[1]:80+var_str[1]+var_str[0]]
            start_height = struct.unpack('<L', bytes[80+var_str[1]+var_str[0]:80+var_str[1]+var_str[0]+4])[0]
            relay = struct.unpack('?', bytes[len(bytes)-1: len(bytes)])[0]
            return version(version_num, services, timestamp, addr_recv, addr_from, nonce, user_agent, start_height, relay)

        elif type == "inv" or type == "getdata":
            def get_type(i):
                i = struct.unpack("<L", i)[0]
                if i == 0:
                    return "ERROR"
                elif i == 1:
                    return "TX"
                elif i == 2:
                    return "BLOCK"
                elif i == 3:
                    return "MERKLEBLOCK"
            count = var_int(bytes)
            bytes = bytes[count[1]:]
            bytelist = []
            for i in range(len(bytes)):
                bytelist.append(bytes[i:i+1])
            inventory = []
            for i in range(count[0]):
                inv_type = ""
                for i in range(4):
                    inv_type += bytelist.pop(0)
                hash = ""
                for i in range(32):
                    hash += bytelist.pop(0)
                inventory.append((get_type(inv_type), ''.join(reversed(hash)).encode("hex")))
            return {type: inventory}

        elif type == "tx":
            return {"tx": bitcoin.deserialize(bytes.encode("hex"))}

    except Exception:
        return {"message": {"command": "error deserializing"}}
