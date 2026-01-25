import os
import secrets
import json
from fastapi import HTTPException
from pydantic import BaseModel
from web3 import Web3

# Use the singleton instance of the session manager
from tools.sessionManager import SessionManager

from dotenv import load_dotenv
load_dotenv()

ETH_NODE_URL = os.getenv("ETH_NODE_URL")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS") # Added CONTRACT_ADDRESS

w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))
server_account = w3.eth.account.from_key(SERVER_PRIVATE_KEY)

# Load contract ABI for KeyReconstruction.sol
try:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    contract_path = os.path.join(base_dir, "artifacts", "contracts", "KeyReconstruction.sol", "KeyReconstruction.json")
    with open(contract_path, "r") as f:
        contract_json = json.load(f)
    CONTRACT_ABI = contract_json["abi"]
except FileNotFoundError:
    raise RuntimeError("KeyReconstruction.json ABI file not found. Ensure the contract is compiled.")

# Access the singleton instance of SessionManager
session_manager = SessionManager()

async def prepare_handler(threshold: int):
    challenge = secrets.token_hex(32)  # challenge casuale

    # salva sessione con threshold off-chain
    session_id = session_manager.add_session(threshold)

    # Register session on-chain
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
    nonce = w3.eth.get_transaction_count(server_account.address)

    tx = contract.functions.prepare(
        session_id.to_bytes(32, 'big') # Convert int session_id to bytes32 for the contract
    ).build_transaction({
        'chainId': w3.eth.chain_id,
        'gasPrice': w3.eth.gas_price,
        'from': server_account.address,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, SERVER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if tx_receipt.status == 0:
        raise HTTPException(status_code=500, detail="On-chain session preparation failed.")

    return {
        "session_id": session_id,
        "challenge": challenge,
        "server_address": server_account.address,
        "threshold": threshold,
        "tx_hash": tx_hash.hex() # Include transaction hash for transparency
    }
