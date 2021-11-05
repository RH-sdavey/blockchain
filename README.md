# blockchain

A very simple and naive implementation of a blockchain.

To run:

 - pip install -r requirements.txt
 - python3 blockchain.py
 
 This will start a flask instance for DEV purposes, on localhost:5000
 Text will appear in console with link to browser to see your flask app
 
 Valid endpoints
 
 - /nodes/register = """Register all neighbouring nodes to the blockchain"""
 
 - /mine = """Mine a coin (forge a new block), payment of 1 coin is rewarded to the winning node for mining a block"""
 
 - /transactions/new = """creating a new transaction on the current block, Allows a sender to send an amount of coins to a recipient"""
 
 - /chain = """Returns the full block chain represented a json dict"""
