from fastapi import HTTPException
from pydantic import BaseModel
from tools.sessionManager import SessionManager
from secretsharing import SecretSharer
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64


class ReconstructRequest(BaseModel):
    session_id: int
    requester_public_key: str # Public key in PEM format (base64 encoded)

# Access the singleton instance of SessionManager
session_manager = SessionManager()

async def reconstruct_handler(request: ReconstructRequest):
    session = session_manager.get_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.active:
        raise HTTPException(status_code=400, detail="Session is still active. Cannot reconstruct yet.")

    # Verifica che la soglia sia stata raggiunta
    if len(session.shares) < session.threshold:
        raise HTTPException(status_code=400, detail="Threshold not reached for reconstruction.")

    # Ricostruzione reale della chiave
    try:
        reconstructed_key = SecretSharer.recover_secret(session.shares[:session.threshold])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reconstruct key: {str(e)}")

    # Encrypt the reconstructed key with the requester's public key
    try:
        # Decode the base64 public key
        pem_public_key_bytes = base64.b64decode(request.requester_public_key.encode('utf-8'))
        public_key = serialization.load_pem_public_key(
            pem_public_key_bytes,
            backend=default_backend()
        )

        encrypted_key = public_key.encrypt(
            reconstructed_key.encode('utf-8'),
            padding.PKCS1v15() # A common padding scheme for RSA encryption
        )
        encrypted_key_b64 = base64.b64encode(encrypted_key).decode('utf-8')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to encrypt key with requester's public key: {str(e)}")


    return {
        "session_id": request.session_id,
        "encrypted_key": encrypted_key_b64 # Return the encrypted key
    }
