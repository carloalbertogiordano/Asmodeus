# Key Reconstruction System: Hybrid Off-chain / On-chain

This project implements a hybrid system for **threshold cryptography key reconstruction**, combining an off-chain centralized server with an on-chain Ethereum smart contract for public verification and notarization.

## Final Objective

The goal is to demonstrate a system where:
*   A **Smart Contract** acts as a public, verifiable registry, ensuring the integrity and state transitions of key reconstruction sessions without ever seeing the secret shares in clear text.
*   A **Centralized Server (FastAPI)** coordinates the session, collects secret shares off-chain, performs the key reconstruction, and commits only proof (hashes) to the blockchain.
*   Clients can interact with the server to initiate sessions, submit shares, and request key reconstruction.

This system is not trustless. Users trust the server, but the server's actions are verifiable and constrained by the on-chain smart contract.

## Core Components

| Component        | Responsibility                                                                    |
| :--------------- | :-------------------------------------------------------------------------------- |
| **Smart Contract** | Public state, events, threshold enforcement, auditability. **DOES NOT** reconstruct the key. |
| **Server**         | Business logic, off-chain share collection, key reconstruction, on-chain proof submission. |
| **Client**         | Initiates sessions, submits shares, requests reconstruction result.                |

## Features

*   **Secure Session Management**: Server manages unique reconstruction sessions using globally unique IDs.
*   **Threshold Cryptography**: Utilizes Shamir's Secret Sharing to reconstruct keys from a sufficient number of shares.
*   **Encrypted Key Delivery**: The reconstructed secret key is **encrypted with the requester's public RSA key** before being returned by the server, enhancing security.
*   **On-chain Notarization**: All critical session events (session creation, share submission, proof of reconstruction) are recorded and verified on the Ethereum blockchain.
*   **FastAPI Backend**: Provides a RESTful API for client interaction and server coordination.
*   **End-to-End Testing**: Comprehensive test suite ensuring correct functionality of off-chain and on-chain interactions, including key encryption/decryption.

## Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

*   Node.js & npm (for Hardhat)
*   Python 3.9+ & pip (for FastAPI server)
*   Git

### 1. Clone the Repository

```bash
git clone https://github.com/carloalbertogiordano/Asmodeus.git
cd Asmodeus
```

### 2. Hardhat (Ethereum Smart Contract) Setup

The Hardhat setup, including dependency installation, contract compilation, and starting a local Hardhat Network node, is now automated as part of the `demonstrate_execution.sh` script. You do not need to run these steps manually.

### 3. FastAPI Server Setup

The FastAPI server setup, including the creation and activation of a Python virtual environment, installation of dependencies, and configuration of environment variables, is now automated as part of the `demonstrate_execution.sh` script. You do not need to run these steps manually.

### 4. Run the FastAPI Server

Starting the FastAPI server is now automated as part of the `demonstrate_execution.sh` script. You do not need to run these steps manually.
The server will start on `http://0.0.0.0:8000`. You can access the API documentation at `http://localhost:8000/docs`.

## Running Tests

To set up the entire system (Hardhat node, contract deployment, FastAPI server) and run the end-to-end test suite, execute the `demonstrate_execution.sh` script from the project root:

```bash
./demonstrate_execution.sh
```

This script will:
*   Install Hardhat and Python dependencies.
*   Start a local Hardhat Network node.
*   Deploy the smart contracts.
*   Configure and start the FastAPI server.
*   Execute the `test_ee.py` end-to-end test.

All tests should pass, confirming the correct interaction between the client, server, and smart contract, including key encryption/decryption. The script will also provide colored output for better readability.

## Project Status

For a detailed overview of implemented features, unimplemented features, and potential improvements, please refer to [PROJECT_STATUS.md](PROJECT_STATUS.md).