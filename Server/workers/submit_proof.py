import os
import json
from fastapi import HTTPException
from pydantic import BaseModel
from web3 import Web3

# Use the singleton instance of the session manager
from tools.sessionManager import SessionManager

ETH_NODE_URL = os.getenv("ETH_NODE_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY")

# Load contract ABI
try:
    # Construct the absolute path to the contract ABI
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    contract_path = os.path.join(base_dir, "artifacts", "contracts", "KeyReconstruction.sol", "KeyReconstruction.json")
    with open(contract_path, "r") as f:
        contract_json = json.load(f)
    CONTRACT_ABI = contract_json["abi"]
except FileNotFoundError:
    raise RuntimeError("KeyReconstruction.json ABI file not found. Ensure the contract is compiled.")

w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))
server_account = w3.eth.account.from_key(SERVER_PRIVATE_KEY)

# Modello per la richiesta
class SubmitProofRequest(BaseModel):
    session_id: int
    # Removed ciphertext_hashes from request, as server derives them

# Access the singleton instance of SessionManager
session_manager = SessionManager()

async def submit_proof_handler(data: SubmitProofRequest):
    session = session_manager.get_session(data.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.active: # Should be inactive if reconstruction is complete
        raise HTTPException(status_code=400, detail="Session is still active. Key not reconstructed yet.")
    if len(session.share_hashes) < session.threshold: # Use share_hashes here
        raise HTTPException(status_code=400, detail="Threshold not reached")

    # Instantiate contract
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    # Convert share_hashes (hex strings) to bytes32 for the contract
    ciphertext_hashes_bytes32 = [Web3.to_bytes(hexstr=h) for h in session.share_hashes]

    # Build transaction
    nonce = w3.eth.get_transaction_count(server_account.address)
    tx = contract.functions.submitProof(
        data.session_id.to_bytes(32, 'big'),
        ciphertext_hashes_bytes32
    ).build_transaction({
        'chainId': w3.eth.chain_id,
        'gasPrice': w3.eth.gas_price,
        'from': server_account.address,
        'nonce': nonce,
    })

    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, SERVER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if tx_receipt.status == 0:
        raise HTTPException(status_code=500, detail="Transaction failed on blockchain.")

    # Update session status (already handled by contract, but mirror locally for consistency)
    session.active = False
    # This is not a valid attribute of session
    # session.ciphertext_hashes = [h.hex() for h in ciphertext_hashes_bytes32] # Store as hex strings

    return {
        "status": "ok",
        "session_id": data.session_id,
        "active": session.active,
        "tx_hash": tx_hash.hex()
    }
