__author__ = 'chris'
import bitcoin
from random import shuffle
from protocol import PeerFactory
from twisted.internet import reactor
from discovery import dns_discovery
from message import message, inv

MAINNET = "d9b4bef9"
TESTNET3 = "0709110b"

class BitcoinClient(object):

    def __init__(self, addrs, params=MAINNET, user_agent="/pyBitcoin:0.1/", max_connections=10):
        self.addrs = addrs
        self.params = params
        self.user_agent = user_agent
        self.max_connections = max_connections
        self.peers = []
        self.inventory = {}

        self.connect_to_peers()

    def connect_to_peers(self):
        if len(self.peers) < self.max_connections:
            shuffle(self.addrs)
            for i in range(self.max_connections - len(self.peers)):
                if len(self.addrs) > 0:
                    addr = self.addrs.pop(0)
                    peer = PeerFactory(self.params, self.user_agent, self.inventory, self.on_peer_disconnected)
                    reactor.connectTCP(addr[0], addr[1], peer)
                    self.peers.append(peer)

    def on_peer_disconnected(self, peer):
        self.peers.remove(peer)
        self.connect_to_peers()

    def broadcast_tx(self, tx):
        self.inventory[bitcoin.txhash(tx)] = tx
        inv_packet = inv("TX", bitcoin.txhash(tx))
        for peer in self.peers:
            peer.protocol.send_message(message(inv_packet, self.params))


if __name__ == "__main__":
    # Connect to testnet
    BitcoinClient(dns_discovery(True), params=TESTNET3)
    reactor.run()
