__author__ = 'chris'
import bitcoin
import struct
import socket
from binascii import unhexlify


def serialize(obj):
    if "message" in obj:
        message = obj["message"]
        ser = []
        ser.append(struct.pack('<L', long(message["magic"], 16)))
        command = message["command"].encode("hex")
        while len(command) < 24:
            command += "0"
        ser.append(unhexlify(command))
        ser.append(struct.pack('<L', message["length"]))
        ser.append(struct.pack('>L', long(message["checksum"], 16)))
        ser.append(message["payload"])
        return "".join(ser)

    elif "version" in obj:
        version = obj["version"]
        ser = []
        ser.append(struct.pack('<L', version["version"]))
        ser.append(unhexlify(version["services"]))
        ser.append(struct.pack('<Q', version["timestamp"]))
        ser.append(unhexlify(version["addr_recv"]["services"]))
        ser.append(unhexlify("00000000000000000000FFFF"))
        ser.append(socket.inet_aton(version["addr_recv"]["ip"]))
        ser.append(struct.pack('>L', version["addr_recv"]["port"])[2:])
        ser.append(unhexlify(version["addr_from"]["services"]))
        ser.append(unhexlify("00000000000000000000FFFF"))
        ser.append(socket.inet_aton(version["addr_from"]["ip"]))
        ser.append(struct.pack('>L', version["addr_from"]["port"])[2:])
        ser.append(unhexlify(version["nonce"]))
        ser.append(bitcoin.num_to_var_int(len(unhexlify(version["user_agent"].encode("hex")))))
        ser.append(unhexlify(version["user_agent"].encode("hex")))
        ser.append(struct.pack('<L', version["start_height"]))
        ser.append(struct.pack('?', version["relay"]))
        return "".join(ser)

    elif "verack" in obj:
        return ""

    elif "filterload" in obj:
        fload = obj["filterload"]
        ser = []
        ser.append(bitcoin.num_to_var_int(len(unhexlify(fload["filter"]))))
        ser.append(unhexlify(fload["filter"]))
        ser.append(struct.pack('<L', fload["nHashFunctions"]))
        ser.append(struct.pack('<L', fload["nTweak"]))
        ser.append(struct.pack('B', fload["nFlags"]))
        return "".join(ser)

    elif "filteradd" in obj:
        fadd = obj["filteradd"]
        ser = []
        ser.append(bitcoin.num_to_var_int(len(unhexlify(fadd["data"]))))
        ser.append(''.join(reversed(unhexlify(fadd["data"]))))
        return "".join(ser)

    elif "inv" in obj or "getdata" in obj:
        def encode_type(type):
            if type == "ERROR":
                return struct.pack('<L', 0)
            elif type == "TX":
                return struct.pack('<L', 1)
            elif type == "BLOCK":
                return struct.pack('<L', 2)
            elif type == "MERKLEBLOCK":
                return struct.pack('<L', 3)
        dict = obj["inv"] if "inv" in obj else obj["getdata"]
        ser = []
        ser.append(bitcoin.num_to_var_int(len(dict)))
        for item in dict:
            ser.append(encode_type(item[0]))
            ser.append(''.join(reversed(unhexlify(item[1]))))
        return "".join(ser)

    elif "tx" in obj:
        return unhexlify(obj["tx"])
