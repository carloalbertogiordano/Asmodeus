pragma solidity ^0.8.28;

contract KeyReconstruction {

    // Pubkey del server autorizzato
    address public serverPubKey;

    // Threshold minimo per chiudere una sessione
    uint256 public threshold;

    struct Session {
        bool exists;
        address creator;
        address[] participants;
        bytes32[] shareHashes;
        bytes32[] ciphertextHashes;
        bool closed;
    }

    mapping(bytes32 => Session) public sessions;

    // Eventi
    event Prepare(bytes32 indexed keyID, address indexed creator);
    event ShareSubmitted(bytes32 indexed keyID, address indexed user, bytes32 shareHash);
    event KeyReconstructed(bytes32 indexed keyID);

    // --- Costruttore ---
    constructor(address _serverPubKey, uint256 _threshold) {
        require(_serverPubKey != address(0), "Invalid server public key");
        serverPubKey = _serverPubKey;
        threshold = _threshold;
    }

    // --- Funzioni ---

    // 1️Inizializza la sessione
    function prepare(bytes32 keyID) external {
        require(!sessions[keyID].exists, "Session already exists");

        Session storage s = sessions[keyID];
        s.exists = true;
        s.creator = msg.sender;
        s.closed = false;

        emit Prepare(keyID, msg.sender);
    }

    // 2️Registrazione hash share
    function submitShare(bytes32 keyID, bytes32 shareHash) external {
        Session storage s = sessions[keyID];
        require(s.exists, "Session does not exist");
        require(!s.closed, "Session is closed");

        // aggiungi partecipante se nuovo
        bool alreadyParticipant = false;
        for (uint i = 0; i < s.participants.length; i++) {
            if (s.participants[i] == msg.sender) {
                alreadyParticipant = true;
                break;
            }
        }
        if (!alreadyParticipant) {
            s.participants.push(msg.sender);
        }

        s.shareHashes.push(shareHash);
        emit ShareSubmitted(keyID, msg.sender, shareHash);
    }

    // 3️Registrazione proof e hash dei ciphertext (solo server)
    function submitProof(bytes32 keyID, bytes32[] calldata ciphertextHashes) external {
        require(msg.sender == serverPubKey, "Only server can submit proof");

        Session storage s = sessions[keyID];
        require(s.exists, "Session does not exist");
        require(!s.closed, "Session is closed");
        require(s.shareHashes.length >= threshold, "Threshold not reached");

        for (uint i = 0; i < ciphertextHashes.length; i++) {
            s.ciphertextHashes.push(ciphertextHashes[i]);
        }

        s.closed = true;
        emit KeyReconstructed(keyID);
    }

    // --- Getter helpers ---
    function getParticipants(bytes32 keyID) external view returns (address[] memory) {
        return sessions[keyID].participants;
    }

    function getShareHashes(bytes32 keyID) external view returns (bytes32[] memory) {
        return sessions[keyID].shareHashes;
    }

    function getCiphertextHashes(bytes32 keyID) external view returns (bytes32[] memory) {
        return sessions[keyID].ciphertextHashes;
    }
}
