# Integration of Asmodeus with TCFS: Analysis and Contextualization

This document provides an in-depth analysis of how the **Asmodeus** project integrates within the broader architecture of the **Transparent Cryptographic Filesystem (TCFS)**, as originally described in the bachelor's thesis. It highlights the specific functionalities covered by Asmodeus and elucidates its potential role within the comprehensive TCFS framework.

## 1. Scope of Asmodeus within TCFS

The Asmodeus project is meticulously designed to address a critical and highly specialized sub-component within the overarching TCFS architecture presented in the thesis: the **threshold sharing and key reconstruction mechanism** based on Shamir's Secret Sharing (SSS).

In the thesis, Section 2.3.4, titled "The TCFS REST server," conceptualized a server (then prototyped in Golang) intended for managing threshold sharing. However, the thesis acknowledged that this component was "partial" and "not completely implemented" (as further detailed in Section 2.5, "Open Challenges and Problems of TCFS," under "Implementation of threshold sharing"). Notably, a crucial mechanism for key recovery was absent from this preliminary design.

Asmodeus significantly advances this foundational concept of a "TCFS REST server" by transforming a nascent idea into a robust, secure, and verifiable system for distributed key management and secure key reconstruction. Specifically, Asmodeus encompasses the following core functionalities:

### 1.1 Internal Architecture and Operational Flow of Asmodeus

Asmodeus operates as a hybrid off-chain/on-chain system, orchestrating cryptographic operations and blockchain notarization to facilitate secure key reconstruction. The operational flow involves several distinct phases, each with specific interactions between the client, the FastAPI server, and the Ethereum Smart Contract.

#### 1.1.1 Detailed Workflow

1.  **Client Initialization:** The process begins with a client application, which may be part of a larger TCFS client. The client generates a temporary RSA key pair, where the public key will be used for encrypting the reconstructed secret. It then initiates communication with the Asmodeus FastAPI server.

2.  **Session Preparation (`/prepare` endpoint):**
    *   The client sends a request to the FastAPI server's `/prepare` endpoint, specifying the `threshold` (the minimum number of shares required for reconstruction).
    *   The FastAPI server generates a globally unique `session_id` to identify the reconstruction session.
    *   Critically, the FastAPI server then interacts with the deployed Ethereum Smart Contract, invoking its `prepare` function. This transaction registers the `session_id` and the specified `threshold` on-chain, establishing a public, immutable record of the session's parameters.
    *   The FastAPI server responds to the client with the newly generated `session_id`, its own network address (for subsequent interactions), and a cryptographic `challenge` (e.g., a nonce or session-specific data).

3.  **Share Submission (`/submit-share` endpoint):**
    *   Individual participants, each holding a secret share, send their respective `share` along with the `session_id` to the FastAPI server's `/submit-share` endpoint.
    *   The FastAPI server first verifies that the provided `session_id` corresponds to an active and open session.
    *   For each submitted share, the server computes a cryptographic hash (`shareHash`). This hash, *not the share itself*, is then sent in a transaction to the Smart Contract's `submitShare` function. This on-chain record notarizes the submission of each share, preventing duplicate submissions and providing an auditable trail without exposing the sensitive share data.
    *   The server manages the collection of shares off-chain, maintaining a count of submitted unique share hashes.

4.  **Key Reconstruction (`/reconstruct` endpoint):**
    *   Once the number of submitted valid shares (as noted by the on-chain `shareHash` count) reaches or exceeds the `threshold`, a client can request key reconstruction by calling the FastAPI server's `/reconstruct` endpoint. The client must include the `session_id` and its RSA public key in this request.
    *   The FastAPI server retrieves all collected shares for the specified `session_id`. It then applies Shamir's Secret Sharing algorithm to these shares to reconstruct the original secret key.
    *   A paramount security feature: the reconstructed secret key is *immediately encrypted* using the RSA public key provided by the requesting client. This encryption uses PKCS1v15 padding for robustness.
    *   The FastAPI server returns the encrypted secret key to the client.

5.  **Proof Submission (`/submit-proof` endpoint):**
    *   Following the successful reconstruction and encrypted delivery of the key, the FastAPI server calls the Smart Contract's `submitProof` function.
    *   The Smart Contract performs an on-chain verification: it checks if the count of recorded `shareHashes` for that `session_id` meets the `threshold`.
    *   If this condition is satisfied, the Smart Contract marks the `session_id` as closed, preventing any further share submissions or reconstruction attempts for that session.
    *   A `KeyReconstructed` event is emitted by the Smart Contract, publicly signaling the successful completion of the reconstruction process for that session.

#### 1.1.2 Operational Flow Diagram

The interaction between the components can be visualized as follows:

```
+--------+                    +-----------------+                    +---------------+
| Client |                    | FastAPI Server  |                    | Smart Contract|
+--------+                    +-----------------+                    +---------------+
    |                           |          ^                         |               |
    | 1. Request Session        |          |                         |               |
    | (threshold, RSA_pub_key)  |          |                         |               |
    |-------------------------->|          |                         |               |
    |                           | 2. Generate Session ID,            |               |
    |                           |    Call prepare()                  |               |
    |                           |------------------------------------>|               |
    |                           | 3. Event: SessionPrepared(ID, Th.) |               |
    |<--------------------------|          |                         |<--------------|
    | (session_id, challenge)   |          |                         |               |
    |                           |          |                         |               |
    | 4. Submit Share (share_i) |          |                         |               |
    |-------------------------->|          |                         |               |
    | (x_i, y_i, session_id)    | 5. Hash(share_i), Call submitShare()|               |
    |                           |------------------------------------>|               |
    |                           | 6. Event: ShareSubmitted(ID, H(share_i))|            |
    |                           |          |                         |<--------------|
    |                           |          |                         |               |
    |      ... (repeat for t shares) ...   |                         |               |
    |                           |          |                         |               |
    | 7. Request Reconstruction |          |                         |               |
    | (session_id, RSA_pub_key) |          |                         |               |
    |-------------------------->|          |                         |               |
    |                           | 8. Reconstruct Key (off-chain)     |               |
    |                           |    Encrypt with RSA_pub_key        |               |
    |                           |<---------|                         |               |
    |                           |          |                         |               |
    |                           | 9. Call submitProof()              |               |
    |--------------------------------------------------------------->|               |
    |                           | 10. Verify shares >= threshold,    |               |
    |                           |     Mark session closed            |               |
    |                           |          |                         |<--------------|
    |                           | 11. Event: KeyReconstructed(ID)    |               |
    |                           |          |                         |               |
    |                           |          |                         |               |
    | Decrypt with RSA_priv_key |          |                         |               |
    +--------+                    +-----------------+                    +---------------+
```

#### 1.1.3 Cryptographic Primitives Employed

*   **Shamir's Secret Sharing (SSS):** This information-theoretic secret sharing scheme is fundamental to Asmodeus. It enables a secret to be divided into multiple `n` shares, such that any `t` (threshold) or more shares can reconstruct the original secret, but any `t-1` or fewer shares yield no information about it. Asmodeus implements the polynomial interpolation over a finite field to achieve this.
*   **RSA Encryption:** For the secure delivery of the reconstructed secret key, Asmodeus utilizes the RSA asymmetric encryption algorithm. The client's dynamically generated RSA public key is used by the server to encrypt the secret, ensuring that only the client, possessing the corresponding private key, can decrypt it. This prevents eavesdropping on the reconstructed key in transit.
*   **Cryptographic Hashing:** Asmodeus employs a secure hashing algorithm (e.g., SHA-256) to generate immutable fingerprints of the submitted shares. These `shareHash` values are recorded on the blockchain, serving as a verifiable proof of share submission without revealing the share content itself.



In essence, while Asmodeus does not constitute a complete transparent filesystem or handle the on-the-fly encryption/decryption of files and filenames (which are primary objectives of a full TCFS implementation), it critically focuses on the **secure, verifiable, and distributed management of cryptographic keys**. This focus addresses a fundamental requirement for the security, resilience, and operational integrity of a robust TCFS system.

## 2. Contextualization and Theoretical Integration of Asmodeus within the TCFS Framework

Asmodeus positions itself within the bachelor's thesis as an **advanced, standalone realization and significant evolution** of the threshold sharing and key recovery component of TCFS, a crucial module that was conceptualized but not fully implemented in the original work.

One can conceptualize Asmodeus as an **external, robust key recovery and share management service** that a fully-fledged TCFS implementation could invoke to enhance its key lifecycle management capabilities. The following points detail its contextualization:

*   **Extension of the "TCFS REST Server" (Thesis Section 2.3.4):** Asmodeus directly concretizes and significantly evolves the "TCFS REST server" described in the thesis. Where the thesis identified the necessity of such a server for the *threshold sharing* of file encryption keys (acknowledging it was not strictly essential for rudimentary TCFS operation), Asmodeus delivers precisely this functionality with substantial architectural and security enhancements, particularly through its hybrid on-chain/off-chain design.
*   **Resolution of "Open Challenges and Problems of TCFS" (Thesis Section 2.5):** The thesis explicitly highlighted the partial implementation of threshold sharing as an open challenge. Asmodeus directly addresses this by providing a comprehensive and functional system for key reconstruction, thereby resolving a significant gap in the original TCFS design. While Asmodeus is not a filesystem mounting program, it offers a foundational service that a future TCFS could integrate to securely manage its own cryptographic keys, enabling more resilient key recovery strategies.
*   **Enhancement of Key Management Practices:** The thesis discussed the "hierarchy and key generation in TCFS" (Section 4.3.1) and the utilization of `Keyutils` for storing keys within the kernel's keyring. Asmodeus does not supplant this operating system-level key management. Instead, it provides a robust methodology for the **reconstruction of a master key or a session-specific key**. This reconstructed key could then be securely inserted into the kernel's keyring (via `key_utils`) or directly employed by the TCFS userspace module for transparent encryption/decryption operations, offering a resilient backup or recovery mechanism for critical keys.
*   **Introduction of Verifiability and Enhanced Security:** The incorporation of an Ethereum Smart Contract within Asmodeus introduces an unparalleled layer of public verifiability and transparency to the key recovery process, an aspect largely absent from the thesis's original "TCFS REST server" concept. This directly addresses the concerns regarding trust and security in remote server data handling, as outlined in the thesis. By notarizing critical events on an immutable blockchain, Asmodeus provides an auditable trail, mitigating risks associated with server compromise and increasing overall system trustworthiness.

### 2.1 Proposed Integration Patterns and Theoretical Implementations

Asmodeus, by providing a robust and auditable key recovery mechanism, can be theoretically integrated into a comprehensive TCFS framework in several impactful ways, extending the capabilities outlined in the original thesis.

#### 2.1.1 Scenario 1: Master Key Recovery for TCFS

In a typical TCFS setup, a master key (or volume key) is often used to derive or encrypt other file-specific keys. The secure management and recovery of this master key are paramount. Asmodeus can serve as the critical infrastructure for the resilient recovery of such a master key.

*   **Initial Setup:** The TCFS master key is initially generated and then securely split into `n` shares using Shamir's Secret Sharing. These shares are then distributed to multiple key custodians (e.g., system administrators, trusted third parties).
*   **Recovery Process:** In the event of a master key loss, compromise, or for scheduled key rotation, a sufficient number of custodians (`t` or more) submit their shares to Asmodeus via the defined protocol.
*   **Integration:** Once Asmodeus successfully reconstructs the master key (encrypted with the requester's public key), this key can then be securely injected back into the TCFS system. This could involve direct programmatic insertion into the kernel's keyring (leveraging `Keyutils` as discussed in Thesis Section 4.3.1) or into the memory space of the TCFS userspace module, enabling the entire filesystem to resume or begin operations.

```
+------------+        +-----------------+        +---------------------+        +-----------+
| Custodians |  -- Shares --> | FastAPI Server  | -- Reconstructed --> | TCFS Key Management | -- OS Keyring --> | TCFS      |
|  (t out of n)|        |   (Asmodeus)    |    Encrypted Key     |  (e.g., Keyutils)   |     Module|
+------------+        +-----------------+        +---------------------+        +-----------+
      ^                                      |                                    ^
      |                                      |                                    |
      |                                      | (Secure Injection)                 |
      |                                      |                                    |
      +--------------------------------------|------------------------------------+
                                             |
                                          (Blockchain Notarization)
                                             |
                                             v
                                   +-------------------+
                                   | Ethereum Contract |
                                   +-------------------+
```

#### 2.1.2 Scenario 2: Dynamic Per-File/Per-Directory Key Management

Beyond a single master key, Asmodeus could facilitate more granular key management within TCFS, especially in multi-user or collaborative environments.

*   **Granular Keys:** Each file or directory encrypted by TCFS could possess its own unique encryption key. These keys, or access policies to them, could be managed by Asmodeus.
*   **On-Demand Access:** When a TCFS FUSE module (as described in Thesis Section 2.3.2) attempts to access an encrypted file or directory, if its key is not locally available or expired, it could dynamically request the key from Asmodeus. The key would then be reconstructed (if needed) and delivered securely.
*   **Flexible Sharing:** This approach would enable more flexible key sharing policies, where access to specific files or directories can be granted or revoked by managing their respective shares through Asmodeus's verifiable process.

#### 2.1.3 Scenario 3: Secure Configuration/Seed Recovery

Asmodeus's utility extends to the secure recovery of any sensitive data critical for TCFS operation, not just encryption keys. This could include:

*   **Configuration Parameters:** Recovery of critical TCFS configuration settings (e.g., server addresses, cryptographic parameters) that are too sensitive to store in plaintext.
*   **Cryptographic Seeds:** Reconstruction of cryptographic seeds used for pseudorandom number generation or key derivation functions within TCFS, ensuring system integrity and randomness.

In these scenarios, Asmodeus acts as a trusted, verifiable oracle for critical data recovery, significantly enhancing the fault tolerance and resilience of the overall TCFS system.

### 2.2 Limitations and Future Considerations

While Asmodeus presents a robust solution for verifiable key reconstruction, it is essential to acknowledge its current limitations and consider avenues for future development:

#### 2.2.1 Limitations of the Current Asmodeus Implementation

*   **Trust Model:** Despite its on-chain notarization, the current implementation of Asmodeus is not entirely trustless. The FastAPI server remains a central point of trust for the actual off-chain key reconstruction process. While its actions are verifiable, a malicious server could theoretically reconstruct the key and then not submit proof on-chain, or misuse the key before encryption, though this risk is mitigated by encrypting the reconstructed key immediately with the requester's public key. Fully trustless reconstruction would necessitate more advanced cryptographic techniques, such as Multi-Party Computation (MPC) or Zero-Knowledge Proofs (ZKP) applied directly to the secret reconstruction computation, eliminating the server's cleartext access to the key.
*   **Performance Overhead:** The hybrid on-chain/off-chain model inherently introduces performance overhead. Interactions with the Ethereum blockchain, particularly for `prepare`, `submitShare`, and `submitProof` transactions, incur network latency and transaction finality delays, impacting the overall speed of session setup and share notarization compared to a purely off-chain system.
*   **Scalability Concerns:** The FastAPI server, in its current state, primarily manages sessions in memory. This design choice presents a scalability bottleneck for high-throughput environments or large numbers of concurrent key reconstruction requests. Implementing persistent session storage (e.g., using a database like PostgreSQL or a distributed cache like Redis) would be crucial for production-grade deployments.
*   **Blockchain Transaction Costs (Gas Fees):** Operations on the Ethereum mainnet incur gas fees. For frequent key management operations or a large volume of share submissions, these transaction costs could become prohibitive, necessitating a careful cost-benefit analysis or consideration of alternative, lower-cost blockchain solutions.
*   **Key Distribution Assumption:** Asmodeus currently assumes that secret shares are already securely generated and distributed to participants. It does not provide a mechanism for the initial secure generation and distribution of these shares, which is a critical aspect of any secure secret sharing scheme.
*   **Single Authority for Reconstruction Proof:** The `submitProof` function in the Smart Contract is designed to be called exclusively by the authorized FastAPI server. While this ensures that only the designated entity can finalize the session, it centralizes the responsibility for proof submission, which could be further decentralized in future iterations.

#### 2.2.2 Future Research Directions and Improvements

*   **Advanced Trustless Reconstruction:** Integrating MPC or ZKP protocols into the key reconstruction process would allow the secret to be reconstructed without any single entity (including the Asmodeus server) ever holding the secret in cleartext. This would significantly enhance the trustlessness and security posture.
*   **Decentralized Share Storage:** Exploring decentralized storage solutions (e.g., IPFS, Filecoin, Swarm) for the encrypted shares could further reduce reliance on centralized servers and enhance data availability and censorship resistance.
*   **Alternative Blockchain Integration:** Investigating integration with Layer 2 scaling solutions (e.g., Optimism, Arbitrum) or alternative EVM-compatible blockchains (e.g., Polygon, Binance Smart Chain) could mitigate the issue of high gas fees and improve transaction throughput.
*   **Enhanced Client-Side Tooling:** Developing a more comprehensive client-side application for TCFS users to manage their shares, initiate reconstruction, and interact with Asmodeus would improve user experience and reduce reliance on manual API calls.
*   **Server-Side Key Generation and Splitting:** Implementing secure mechanisms within the Asmodeus server itself for generating the original secret and splitting it into shares, followed by secure distribution channels, would provide a more complete key lifecycle management solution.
*   **Integration with Identity Management Systems:** Tying share management and reconstruction requests to decentralized identity systems could enhance security and user management within a TCFS context.

In conclusion, Asmodeus is not merely a component of TCFS; it is a **highly specialized, critical, and independently robust system** that resolves one of the key open and incomplete challenges identified in the thesis. It is poised to function as a **secure and auditable external key management service** for a future, complete TCFS implementation, providing the necessary cryptographic keys in a manner that ensures data confidentiality, integrity, and availability within the transparent filesystem.
