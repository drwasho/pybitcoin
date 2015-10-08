__author__ = 'chris'
import bitcoin
import random
from random import shuffle
from protocol import PeerFactory
from twisted.internet import reactor, defer
from discovery import dns_discovery
from message import message, inv
from bloom import BloomFilter
from binascii import unhexlify

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
        self.pending_txs = {}
        self.subscriptions = {}
        self.bloom_filter = BloomFilter(3, 0.01, random.getrandbits(32), BloomFilter.UPDATE_NONE)
        self.connect_to_peers()

    def connect_to_peers(self):
        if len(self.peers) < self.max_connections:
            shuffle(self.addrs)
            for i in range(self.max_connections - len(self.peers)):
                if len(self.addrs) > 0:
                    addr = self.addrs.pop(0)
                    peer = PeerFactory(self.params, self.user_agent, self.inventory,
                                       self.bloom_filter, self.on_peer_disconnected)
                    reactor.connectTCP(addr[0], addr[1], peer)
                    self.peers.append(peer)

    def on_peer_disconnected(self, peer):
        self.peers.remove(peer)
        self.connect_to_peers()

    def broadcast_tx(self, tx):
        """
        Send the tx to half our peers, wait for half of the remainder to announce the tx before
        calling back True.
        """
        def on_peer_anncounce(txid):
            self.pending_txs[txid][0] += 1
            if self.pending_txs[txid][0] >= self.pending_txs[txid][1] / 2:
                if self.pending_txs[txid][3].active():
                    self.pending_txs[txid][3].cancel()
                    self.pending_txs[txid][2].callback(True)

        d = defer.Deferred()
        self.inventory[bitcoin.txhash(tx)] = tx
        inv_packet = inv("TX", bitcoin.txhash(tx))
        self.bloom_filter.insert(bitcoin.bin_txhash(tx))
        self.pending_txs[bitcoin.txhash(tx)] = [0, len(self.peers)/2, d, reactor.callLater(10, d.callback, False)]
        for peer in self.peers[len(self.peers)/2:]:
            peer.protocol.update_filter()
            peer.protocol.add_inv_callback(bitcoin.txhash(tx), on_peer_anncounce)
        for peer in self.peers[:len(self.peers)/2]:
            peer.protocol.send_message(message(inv_packet, self.params))
        return d

    def subscribe_address(self, address, callback):
        """
        Listen for transactions on an address. Since we can't validate the transaction, we will only
        callback if a majority of our peers relay it. If less than a majority relay it, we will have
        to wait for block inclusion to callback.
        """
        def on_peer_announce(tx):
            txhash = bitcoin.txhash(bitcoin.serialize(tx["tx"]))
            if txhash in self.subscriptions[address][0] and self.subscriptions[address][0][txhash][0] != "complete":
                self.subscriptions[address][0][txhash][0] += 1
                if self.subscriptions[address][0][txhash][0] >= self.subscriptions[address][0][txhash][1]:
                    self.subscriptions[address][0][txhash][0] = "complete"
                    self.subscriptions[address][1](tx["tx"])
            elif txhash not in self.subscriptions[address][0]:
                self.subscriptions[address][0][txhash] = [1, len(self.peers)/2]

        self.subscriptions[address] = [{}, callback]
        self.bloom_filter.insert(unhexlify(bitcoin.b58check_to_hex(address)))
        for peer in self.peers:
            peer.protocol.add_inv_callback(bitcoin.b58check_to_hex(address), on_peer_announce)
            peer.protocol.update_filter()

if __name__ == "__main__":
    # Connect to testnet
    BitcoinClient(dns_discovery(True), params=TESTNET3)
    reactor.run()
