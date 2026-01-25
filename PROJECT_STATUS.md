# Project Status

This document outlines the current status of the project, detailing the implemented and unimplemented features based on the project's goals.

## Implemented Features

### Server (FastAPI)
- **Session Management**:
    - The `SessionManager` is implemented as a proper singleton, ensuring a single instance throughout the application's lifecycle.
    - Sessions are stored in memory and now generate **globally unique integer `session_id`s (using UUIDs)**, preventing collisions across server restarts and with on-chain data.
- **API Endpoints**:
    - `/prepare`: Creates a new session with a given threshold. This now includes **registering the session on the Ethereum smart contract** via the `prepare` function and returns the `session_id`, `server_address`, and `challenge`.
    - `/submit-share`: Allows participants to submit their shares for a given session. It correctly checks for active sessions and prevents duplicate submissions. This now includes **recording the `shareHash` on the Ethereum smart contract** via the `submitShare` function for each submitted share.
    - `/reconstruct`: Reconstructs the key from the collected shares using Shamir's Secret Sharing. **The reconstructed key is now encrypted with the requester's provided public RSA key** (PKCS1v15 padding) before being returned, significantly improving security over plaintext transmission.
    - `/submit-proof`: Submits a proof to the smart contract, including the `session_id` (as `bytes32`) and the **hashes of the shares**, not the shares themselves.
- **Configuration**:
    - `load_dotenv()` is called at the beginning of the application, ensuring that environment variables are loaded correctly.
- **Error Handling**:
    - The API endpoints include robust error handling for common issues suchs as session not found, session closed, threshold not reached, and now **correctly propagates `HTTPException`s** (e.g., `400 Bad Request` for submitting to a closed session) instead of generic `500 Internal Server Errors`.

### Smart Contract (Solidity)
- **Notarization**:
    - The smart contract acts as a public and verifiable registry.
    - It stores the server's public key, the session's threshold, and the hashes of the shares.
- **`prepare` Function**:
    - It now actively called by the server to register new sessions on-chain, ensuring the contract is aware of each `session_id`.
- **`submitShare` Function**:
    - Now actively called by the server to record the hash of each share on-chain as it is submitted.
- **`submitProof` Function**:
    - This function can only be called by the authorized server.
    - It verifies that the **number of recorded `shareHashes`** has reached the threshold (now correctly, as `shareHashes` are recorded on-chain) and marks the session as closed.
    - It emits a `KeyReconstructed` event upon successful execution.

### Testing
- **End-to-End Test (`test_ee.py`)**:
    - A comprehensive asynchronous `pytest` test now covers the full off-chain and on-chain flow:
        - Client generates an RSA key pair.
        - `/prepare` call and on-chain session registration.
        - Multiple `/submit-share` calls and on-chain share recording, correctly handling threshold logic and inactive sessions.
        - `/reconstruct` call, with the client sending its public key, receiving the **encrypted key**, and then **successfully decrypting it** to verify the secret.
        - `/submit-proof` call and successful on-chain proof submission.
    - The test environment now correctly uses `httpx.AsyncClient` for asynchronous requests.
    - Test setup addresses `secret-sharing` library's character set requirements.
    - The test output now includes **colored messages for improved readability**.

## Unimplemented Features & Potential Improvements

### Server (FastAPI)
- **Persistence**:
    - The sessions are currently stored in memory, which means they will be lost if the server restarts. A database or a persistent cache like Redis could be used to store the sessions for long-term state.
- **Scalability**:
    - The current in-memory session management and single-threaded nature might limit scalability. For a production environment, distributed session management and asynchronous processing would be crucial.
- **Security**:
    - While the reconstructed key is now encrypted, the communication between the client and the server is not encrypted (i.e., no HTTPS). Implementing HTTPS is critical for production.
    - Hardhat's default accounts are used, which are publicly known. In a real scenario, secure key management (e.g., hardware security modules, vault services) for the server's private key would be essential.
    - A full Zero-Knowledge Proof (ZKP) based approach for key handling would provide the highest level of trustlessness, eliminating the need for the server to ever see the key in cleartext, even for encryption. This is a significant architectural change.

### Smart Contract (Solidity)
- **Advanced Security**:
    - The current contract primarily serves as a notarization layer. Further decentralization or more complex cryptographic checks could be added on-chain (e.g., verifying ZKPs).

### Client
- **No Production Client Implemented**:
    - There is no complete client-side implementation for users to interact with the server's API beyond the `test_ee.py` script.

### General
- **`SessionManager` Reset for Testing**:
    - For repeated automated testing without a fresh Hardhat node, a mechanism to reset the `SessionManager`'s internal state (e.g., `sessions.clear()`) might be beneficial between test runs to prevent state leakage. This is a testing-specific improvement rather than a core system feature.