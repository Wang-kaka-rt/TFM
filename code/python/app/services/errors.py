class SessionServiceError(Exception):
    """Base service error for session workflow failures."""


class SessionNotFoundError(SessionServiceError):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"session '{session_id}' not found")
        self.session_id = session_id


class SessionProcessingError(SessionServiceError):
    def __init__(self, session_id: str, message: str) -> None:
        super().__init__(f"session '{session_id}' failed: {message}")
        self.session_id = session_id
        self.message = message
