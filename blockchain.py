import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
import requests

from flask import Flask, jsonify, request


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.new_block(previous_hash=1, proof=100)
        self.nodes = set()

    def register_node(self, address):
        """Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True or False if Valid
        """
        last_block = chain[0]
        while current_index := 1 < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self_hash(last_block):
                return False

            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """This is our Consensus Algorithm, it resolves conflicts by replacing our chain <-- longest one in the network.
        :return: <bool> True if our chain was replaced, False if not
        """
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_block(self, proof, previous_hash=None):
        """Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """Returns the last block in the chain"""
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """
        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


class FrontEndFlaskApp:
    """Front end for the flask app, maps a series of http endpoints to backend (Blockchain) functionality"""

    def __init__(self):
        self.app = Flask(__name__)
        self.node_identifier = str(uuid4()).replace('-', '')
        self.blockchain = Blockchain()

    def create_routes(self):
        """Create all the needed routes for the flask frontend to operate"""

        @self.app.route('/nodes/register', methods=['POST'])
        def register_nodes():
            """Register nodes to the blockchain"""

            values = request.get_json()
            nodes = values.get('nodes')
            if nodes is None:
                return "Error: Please supply a valid list of nodes", 400

            for node in nodes:
                self.blockchain.register_node(node)

            response = {
                'message': 'New nodes have been added',
                'total_nodes': [self.blockchain.nodes]
            }
            return jsonify(response), 201

        @self.app.route('/mine', methods=['GET'])
        def mine():
            """Mine a coin (forge a new block), payment of 1 coin is rewarded to the winning node for mining a block"""

            last_block = self.blockchain.last_block
            last_proof = last_block['proof']
            proof = self.blockchain.proof_of_work(last_proof)

            self.blockchain.new_transaction(
                sender="0",
                recipient=self.node_identifier,
                amount=1
            )
            previous_hash = self.blockchain.hash(last_block)
            block = self.blockchain.new_block(proof, previous_hash)

            response = {
                'message': "New Block Forged",
                'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
            }
            return jsonify(response), 200

        @self.app.route('/transactions/new', methods=['POST'])
        def new_transaction():
            """Endpoint for creating a new transaction on the current block,
            Allows a sender to send an amount of coins to a recipient"""

            values = request.get_json()
            print(values)
            required = ['sender', 'recipient', 'amount']
            if not all(k in values for k in required):
                return 'Missing values', 400

            sender, recipient, amount = values['sender'], values['recipient'], values['amount']
            index = self.blockchain.new_transaction(sender, recipient, amount)

            response = {'message': f'Transaction will be added to Block {index}'}
            return jsonify(response), 201

        @self.app.route('/chain', methods=['GET'])
        def full_chain():
            """Returns the full block chain represented a json dict"""

            resp = {
                'chain': self.blockchain.chain,
                'length': len(self.blockchain.chain)
            }
            return jsonify(resp)

        #after defining all routes, return self to allow method chaining --> instance.create_routes().run_<dev/prod>
        return self

    def run_dev(self):
        return self.app.run(host="0.0.0.0", port=5000)

    def run_prod(self):
        ...

if __name__ == '__main__':
    front_end = FrontEndFlaskApp()
    front_end.create_routes().run_dev()


