from fastapi import HTTPException
from tools.sessionManager import SessionManager
from pydantic import BaseModel
from web3 import Web3
import os
import json # Added json import for contract ABI loading

from dotenv import load_dotenv
load_dotenv()

ETH_NODE_URL = os.getenv("ETH_NODE_URL")
SERVER_PRIVATE_KEY = os.getenv("SERVER_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

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

# Pydantic model per la richiesta
class SubmitShareRequest(BaseModel):
    session_id: int
    user_address: str
    share: str

# Access the singleton instance of SessionManager
session_manager = SessionManager()

async def submit_share_handler(data: SubmitShareRequest):
    session = session_manager.get_session(data.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.active:
        raise HTTPException(status_code=400, detail="Session is closed")

    if not session_manager.add_share(data.session_id, data.user_address, data.share):
        raise HTTPException(status_code=400, detail="Share already submitted by this user or session is inactive")
    
    # Refresh session after adding share, as it might have been updated
    session = session_manager.get_session(data.session_id)

    # Register share on-chain
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
    nonce = w3.eth.get_transaction_count(server_account.address)
    
    # Get the hash of the submitted share to send to the contract
    # We need the hash of the share as it was added to the session
    share_hash_to_submit = next((h for p, s, h in zip(session.participants, session.shares, session.share_hashes) if p == data.user_address and s == data.share), None)
    if not share_hash_to_submit:
        # This should ideally not happen if add_share was successful
        raise HTTPException(status_code=500, detail="Share hash not found after adding share.")

    tx = contract.functions.submitShare(
        data.session_id.to_bytes(32, 'big'), # Convert int session_id to bytes32 for the contract
        Web3.to_bytes(hexstr=share_hash_to_submit) # Convert hex string share_hash to bytes32 for the contract
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
        raise HTTPException(status_code=500, detail="On-chain share submission failed.")

    # If threshold is reached, we can close the session
    if len(session.shares) >= session.threshold:
        session.active = False

    return {
        "status": "ok",
        "session_id": data.session_id,
        "shares_count": len(session.shares),
        "threshold": session.threshold,
        "active": session.active,
        "tx_hash": tx_hash.hex() # Include transaction hash for transparency
    }
