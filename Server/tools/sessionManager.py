import uuid
from web3 import Web3

class Session:
    def __init__(self, session_id: int, threshold: int):
        self.id = session_id
        self.threshold = threshold
        self.participants: list[str] = []
        self.shares: list[str] = []
        self.share_hashes: list[str] = []
        self.active = True

class SessionManager:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.sessions: dict[int, Session] = {}
            # self.session_counter: int = 0 # No longer needed for unique IDs
            self._initialized = True

    def add_session(self, threshold: int) -> int:
        # Generate a globally unique integer ID
        session_id = uuid.uuid4().int
        self.sessions[session_id] = Session(session_id, threshold)
        # self.session_counter += 1 # No longer needed for unique IDs
        return session_id

    def get_session(self, session_id: int) -> Session | None:
        return self.sessions.get(session_id)

    def add_share(self, session_id: int, user_address: str, share: str) -> bool:
        session = self.get_session(session_id)
        if session and session.active and user_address not in session.participants:
            session.participants.append(user_address)
            session.shares.append(share)
            share_hash = Web3.keccak(text=share).hex()
            session.share_hashes.append(share_hash)
            return True
        return False
