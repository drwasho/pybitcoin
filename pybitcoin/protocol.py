__author__ = 'chris'
import enum
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
from message import message, version, verack, filer_load, tx
from serializer import serialize
from deserializer import deserialize

State = enum.Enum('State', ('CONNECTING', 'CONNECTED', 'SHUTDOWN'))


class BitcoinProtocol(Protocol):

    def __init__(self, params, user_agent, inventory):
        self.params = params
        self.user_agent = user_agent
        self.inventory = inventory
        self.timeouts = {}
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
            self.timeouts["verack"].cancel()
            del self.timeouts["verack"]
            if "version" not in self.timeouts:
                self.on_handshake_complete()
        elif m["message"]["command"] == "version":
            self.timeouts["version"].cancel()
            del self.timeouts["version"]
            self.transport.write(serialize(message(verack(), self.params)))
            if "verack" not in self.timeouts:
                self.on_handshake_complete()
        elif m["message"]["command"] == "inv":
            inventory = deserialize(m["message"]["payload"], "inv")
            for item in inventory["inv"]:
                print "Peer %s:%s announced new %s %s" % (self.transport.getPeer().host, self.transport.getPeer().port, item[0], item[1])
        elif m["message"]["command"] == "getdata":
            print "Received an GETDATA message from %s:%s" % (self.transport.getPeer().host, self.transport.getPeer().port)
            data_request = deserialize(m["message"]["payload"], "getdata")
            for item in data_request["getdata"]:
                if item[1] in self.inventory and item[0] == "TX":
                    transaction = tx(self.inventory[item[1]])
                    self.send_message(message(transaction, self.params))
        else:
            print "Received message %s from %s:%s" % (m["message"]["command"], self.transport.getPeer().host, self.transport.getPeer().port)

    def on_handshake_complete(self):
        print "Connected to peer %s:%s" % (self.transport.getPeer().host, self.transport.getPeer().port)
        self.state = State.CONNECTED
        self.send_message(message(filer_load(), self.params))

    def response_timeout(self, id):
        del self.timeouts[id]
        for t in self.timeouts.values():
            t.cancel()
        print "Peer unresponsive, disconnecting..."
        self.transport.loseConnection()
        self.state = State.SHUTDOWN

    def send_message(self, message_obj):
        if self.state == State.CONNECTING:
            reactor.callLater(1, self.send_message, message_obj)
        else:
            self.transport.write(serialize(message_obj))

    def connectionLost(self, reason):
        print "Connection to %s:%s closed" % (self.transport.getPeer().host, self.transport.getPeer().port)


class PeerFactory(ClientFactory):

    def __init__(self, params, user_agent, inventory, disconnect_cb):
        self.params = params
        self.user_agent = user_agent
        self.inventory = inventory
        self.cb = disconnect_cb
        self.protocol = None

    def buildProtocol(self, addr):
        self.protocol = BitcoinProtocol(self.params, self.user_agent, self.inventory)
        return self.protocol

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed, will try a different node"
        self.cb(self)

    def clientConnectionLost(self, connector, reason):
        self.cb(self)
