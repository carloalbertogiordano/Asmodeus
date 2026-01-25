import httpx
import pytest
from secretsharing import SecretSharer
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.backends import default_backend
import base64
import asyncio
from eth_account import Account
from cryptography.hazmat.primitives.asymmetric import rsa

# ANSI escape codes for colors
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_END = "\033[0m"

# The base URL of your FastAPI server
BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_end_to_end_flow():
    await asyncio.sleep(2)
    async with httpx.AsyncClient() as client:
        # Use a private key from the hardhat node
        private_key_hex = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        
        # Generate an RSA key pair for encryption/decryption
        rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        rsa_public_key = rsa_private_key.public_key()

        # Serialize RSA public key to PEM format and base64 encode it
        pem_public_key = rsa_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        b64_public_key = base64.b64encode(pem_public_key).decode('utf-8')

        # STEP 1: /prepare
        print(f"\n{COLOR_YELLOW}--- Testing /prepare ---{COLOR_END}")
        threshold = 2
        prepare_response = await client.post(f"{BASE_URL}/prepare?threshold={threshold}")
        assert prepare_response.status_code == 200
        prepare_data = prepare_response.json()
        session_id = prepare_data["session_id"]
        server_address = prepare_data["server_address"]
        challenge = prepare_data["challenge"]
        print(f"{COLOR_GREEN}Prepare successful:{COLOR_END} Session ID {session_id}, Server Address {server_address}, Challenge {challenge}")
        print(f"{COLOR_YELLOW}Prepare Data:{COLOR_END} {prepare_data}")


        # STEP 2: /submit-share
        print(f"\n{COLOR_YELLOW}--- Testing /submit-share ---{COLOR_END}")
        # Generate valid Shamir's shares
        secret = "this-is-a-very-secret-key".encode().hex()
        shares = SecretSharer.split_secret(secret, threshold, 3)
        user_addresses = ["Alice", "Bob", "Charlie"]
    
        # Submit first share
        print(f"{COLOR_YELLOW}Submitting share for Alice...{COLOR_END}")
        submit_response_alice = await client.post(f"{BASE_URL}/submit-share", json={
            "session_id": session_id,
            "user_address": user_addresses[0],
            "share": shares[0]
        })
        assert submit_response_alice.status_code == 200
        submit_data_alice = submit_response_alice.json()
        print(f"{COLOR_GREEN}Alice's submission successful:{COLOR_END} {submit_data_alice}")
        assert submit_data_alice["shares_count"] == 1
        assert submit_data_alice["active"] is True # Session should still be active

        # Submit second share (reaching threshold)
        print(f"{COLOR_YELLOW}Submitting share for Bob...{COLOR_END}")
        submit_response_bob = await client.post(f"{BASE_URL}/submit-share", json={
            "session_id": session_id,
            "user_address": user_addresses[1],
            "share": shares[1]
        })
        assert submit_response_bob.status_code == 200
        submit_data_bob = submit_response_bob.json()
        print(f"{COLOR_GREEN}Bob's submission successful:{COLOR_END} {submit_data_bob}")
        assert submit_data_bob["shares_count"] == 2
        assert submit_data_bob["active"] is False # Session should now be inactive


        # Try to submit a third share (should be rejected as session is inactive)
        print(f"{COLOR_YELLOW}Attempting to submit share for Charlie (should be rejected)...{COLOR_END}")
        submit_response_charlie = await client.post(f"{BASE_URL}/submit-share", json={
            "session_id": session_id,
            "user_address": user_addresses[2],
            "share": shares[2]
        })
        assert submit_response_charlie.status_code == 400
        print(f"{COLOR_RED}Charlie's submission rejected (expected):{COLOR_END} {submit_response_charlie.json()}")
        assert "Session is closed" in submit_response_charlie.json()["detail"]


        # STEP 3: /reconstruct
        print(f"\n{COLOR_YELLOW}--- Testing /reconstruct ---{COLOR_END}")
        reconstruct_response = await client.post(f"{BASE_URL}/reconstruct", json={
            "session_id": session_id,
            "requester_public_key": b64_public_key # Send public key for encryption
        })
        assert reconstruct_response.status_code == 200
        reconstruct_data = reconstruct_response.json()
        print(f"{COLOR_GREEN}Reconstruct successful:{COLOR_END} {reconstruct_data}")
        assert "encrypted_key" in reconstruct_data
        
        # Decrypt the key using the client's RSA private key
        encrypted_key_bytes = base64.b64decode(reconstruct_data["encrypted_key"])
        decrypted_key_bytes = rsa_private_key.decrypt(
            encrypted_key_bytes,
            padding.PKCS1v15()
        )
        decrypted_key = decrypted_key_bytes.decode('utf-8')

        print(f"{COLOR_GREEN}Decrypted Key:{COLOR_END} {decrypted_key}")
        assert decrypted_key == secret # Verify it matches the original secret


        # STEP 4: /submit-proof (ON-CHAIN interaction)
        print(f"\n{COLOR_YELLOW}--- Testing /submit-proof ---{COLOR_END}")
        submit_proof_response = await client.post(f"{BASE_URL}/submit-proof", json={"session_id": session_id})
        assert submit_proof_response.status_code == 200
        submit_proof_data = submit_proof_response.json()
        print(f"{COLOR_GREEN}Submit Proof successful:{COLOR_END} {submit_proof_data}")
        assert submit_proof_data["status"] == "ok"
        assert submit_proof_data["session_id"] == session_id
        assert submit_proof_data["active"] is False
        assert "tx_hash" in submit_proof_data

        # Optionally, test error cases for reconstruct
        print(f"\n{COLOR_YELLOW}--- Testing /reconstruct error cases ---{COLOR_END}")
        # Try to reconstruct an non-existent session
        non_existent_session_id = 999
        reconstruct_non_existent = await client.post(f"{BASE_URL}/reconstruct", json={
            "session_id": non_existent_session_id,
            "requester_public_key": b64_public_key
        })
        assert reconstruct_non_existent.status_code == 404
        print(f"{COLOR_GREEN}Non-existent session reconstruction rejected (expected):{COLOR_END} {reconstruct_non_existent.json()}")
        assert "Session not found" in reconstruct_non_existent.json()["detail"]

        # Try to reconstruct a session that hasn't reached threshold (not easily testable here after successful flow)
        # A new session would be needed, but this test focuses on a complete flow.

        print(f"\n{COLOR_GREEN}--- End-to-end test completed successfully ---{COLOR_END}")
