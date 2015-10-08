__author__ = 'chris'
import enum
import bitcoin
import sys
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from message import message, version, verack, filer_load, tx, filter_add, get_data
from serializer import serialize
from deserializer import deserialize

State = enum.Enum('State', ('CONNECTING', 'CONNECTED', 'SHUTDOWN'))

class BitcoinProtocol(Protocol):

    def __init__(self, params, user_agent, inventory, bloom_filter):
        self.params = params
        self.user_agent = user_agent
        self.inventory = inventory
        self.bloom_filter = bloom_filter
        self.timeouts = {}
        self.callbacks = {}
        self.state = State.CONNECTING

    def connectionMade(self):
        """
        Send the version message and start the handshake
        """
        self.timeouts["verack"] = reactor.callLater(5, self.response_timeout, "verack")
        self.timeouts["version"] = reactor.callLater(5, self.response_timeout, "version")
        self.transport.write(serialize(message(version(user_agent=self.user_agent), self.params)))

    def dataReceived(self, data):
        m = deserialize(data)

        if m["message"]["command"] == "verack":
            """Complete the handshake if we received both version and verack"""
            self.timeouts["verack"].cancel()
            del self.timeouts["verack"]
            if "version" not in self.timeouts:
                self.on_handshake_complete()

        elif m["message"]["command"] == "version":
            """Send the verack back"""
            # TODO: make sure this node uses NODE_NETWORK (and maybe NODE_BLOOM in the future)
            self.timeouts["version"].cancel()
            del self.timeouts["version"]
            self.transport.write(serialize(message(verack(), self.params)))
            if "verack" not in self.timeouts:
                self.on_handshake_complete()

        elif m["message"]["command"] == "inv":
            """Run through our callbacks to see if we are waiting on any of these inventory items"""
            inventory = deserialize(m["message"]["payload"], "inv")
            for item in inventory["inv"]:
                if item[1] in self.callbacks:
                    self.callbacks[item[1]](item[1])
                    del self.callbacks[item[1]]
                elif item[0] == "TX":
                    self.send_message(message(get_data(item[0], item[1]), self.params))
                print "Peer %s:%s announced new %s %s" % (self.transport.getPeer().host, self.transport.getPeer().port, item[0], item[1])

        elif m["message"]["command"] == "getdata":
            """Serve the data from inventory if we have it"""
            data_request = deserialize(m["message"]["payload"], "getdata")
            for item in data_request["getdata"]:
                if item[1] in self.inventory and item[0] == "TX":
                    transaction = tx(self.inventory[item[1]])
                    self.send_message(message(transaction, self.params))

        elif m["message"]["command"] == "tx":
            """Parse to check the script_pubkey data element against our subscriptions"""
            t = deserialize(m["message"]["payload"], "tx")
            for out in t['tx']['outs']:
                script = bitcoin.deserialize_script(out['script'])
                data_element = script[2] if len(script) == 5 else script[1]
                if data_element in self.callbacks:
                    self.callbacks[data_element](t)

        else:
            print "Received message %s from %s:%s" % (m["message"]["command"], self.transport.getPeer().host, self.transport.getPeer().port)

    def on_handshake_complete(self):
        print "Connected to peer %s:%s" % (self.transport.getPeer().host, self.transport.getPeer().port)
        self.state = State.CONNECTED
        self.send_message(message(filer_load(str(self.bloom_filter.vData).encode("hex"),
                                             self.bloom_filter.nHashFuncs,
                                             self.bloom_filter.nTweak,
                                             self.bloom_filter.nFlags), self.params))

    def response_timeout(self, id):
        del self.timeouts[id]
        for t in self.timeouts.values():
            t.cancel()
        if self.state != State.SHUTDOWN:
            print "Peer unresponsive, disconnecting..."
        self.transport.loseConnection()
        self.state = State.SHUTDOWN

    def send_message(self, message_obj):
        if self.state == State.CONNECTING:
            reactor.callLater(1, self.send_message, message_obj)
        else:
            self.transport.write(serialize(message_obj))

    def update_filter(self):
        self.send_message(message(filer_load(str(self.bloom_filter.vData).encode("hex"),
                                             self.bloom_filter.nHashFuncs,
                                             self.bloom_filter.nTweak,
                                             self.bloom_filter.nFlags), self.params))

    def add_inv_callback(self, key, cb):
        self.callbacks[key] = cb

    def connectionLost(self, reason):
        self.state = State.SHUTDOWN
        print "Connection to %s:%s closed" % (self.transport.getPeer().host, self.transport.getPeer().port)


class PeerFactory(ClientFactory):

    def __init__(self, params, user_agent, inventory, bloom_filter, disconnect_cb):
        self.params = params
        self.user_agent = user_agent
        self.inventory = inventory
        self.cb = disconnect_cb
        self.bloom_filter = bloom_filter
        self.protocol = None

    def buildProtocol(self, addr):
        self.protocol = BitcoinProtocol(self.params, self.user_agent, self.inventory, self.bloom_filter)
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed, will try a different node"
        self.cb(self)

    def clientConnectionLost(self, connector, reason):
        self.cb(self)
