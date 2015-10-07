# pybitcoin
Ultra-lightweight bitcoin client and library

This library allows you to create a bitcoin client that connects directly to the p2p network. 
It handles the bare minimum network messages necessary to connect to the network, broadcast and download transactions.

## Installation

```
python setup.py install
```

## Usage

```python
from pybitcoin.client import BitcoinClient

# connect to your own node on localhost
BitcoinClient([("localhost", 8333)])
reactor.run()
```

```python
from pybitcoin.client import BitcoinClient, TESTNET3
from pybitcoin.discovery import dns_discovery

# Alternatively query the dns seeds for peers
# We will connect to the testnet in this example
client = BitcoinClient(dns_discovery(True), params=TESTNET3)
reactor.run()
```

```python
# broadcast a transaction
tx = "01000000014bbb4302d919ac7612d6c52093fa2f411e231869295064baa9d2bfc562a2a914000000008b483045022100f6b8fce5db5c3b8a9b92e1f74f45959df860068a056c2e8c9425cadb83c4e7cd022055aa3476fa2d915cf4efe6850bba5392b07e6f95241c6c10bd88a451aa2bf2cd014104cfc882f3e582f6698544545e4d52f4798ec7e96e2fbb9a6927361de22d383b7e071ccd3c0f12e904ac2214feb2002dd64af190161bb3e942a5920ce211986c46ffffffff0110270000000000001976a914e7c1345fc8f87c68170b3aa798a956c2fe6a9eff88ac00000000"
client.broadcast_tx(tx)
```

## TODO
This library is not finished. The following things still need to be implemented:

- Set the bloom filter so we can 'subscribe' to an address. `FILTERLOAD` is already implemented, but
the Murmur3 hash function needs to be ported from java.
- Set the filter on half the peers at broadcast, push the tx to the other half and listen for `INV` packets containing the tx.
- Download and store the chain of headers. Requires the `GETBLOCK` message to be implemented and forking logic.
- Parse and validate the merkle proofs when subscribed to an address.
