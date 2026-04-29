from datetime import datetime, timezone

from app.models.session import SessionInfo, SessionState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionInfo] = {}
        self._active_session_id: str | None = None

    def start(self, session_id: str, paths: dict[str, str]) -> SessionInfo:
        now = utc_now()
        session = self._sessions.get(session_id)
        updates = {
            "state": SessionState.recording,
            "updated_at": now,
            "workspace_dir": paths["workspace_dir"],
            "raw_dir": paths["raw_dir"],
            "words_dir": paths["words_dir"],
            "phrases_dir": paths["phrases_dir"],
            "sentences_dir": paths["sentences_dir"],
            "metadata_path": paths["metadata_path"],
            "samples_path": paths["samples_path"],
            "strudel_script_path": paths["strudel_script_path"],
            "last_error": None,
        }

        if session is None:
            session = SessionInfo(
                session_id=session_id,
                created_at=now,
                last_event="started",
                **updates,
            )
        else:
            session = session.model_copy(
                update={
                    **updates,
                    "last_event": "restarted" if session.state == SessionState.stopped else "started",
                    "chunk_count": 0,
                    "word_count": 0,
                    "phrase_count": 0,
                    "sentence_count": 0,
                }
            )

        self._sessions[session_id] = session
        self._active_session_id = session_id
        return session

    def set_processing(self, session_id: str, event: str = "processing") -> SessionInfo:
        session = self.require(session_id)
        updated = session.model_copy(
            update={
                "state": SessionState.processing,
                "updated_at": utc_now(),
                "last_event": event,
            }
        )
        self._sessions[session_id] = updated
        return updated

    def stop(self, session_id: str) -> SessionInfo:
        session = self.require(session_id)
        updated = session.model_copy(
            update={
                "state": SessionState.stopped,
                "updated_at": utc_now(),
                "last_event": "stopped",
            }
        )
        self._sessions[session_id] = updated
        if self._active_session_id == session_id:
            self._active_session_id = None
        return updated

    def fail(self, session_id: str, error_message: str) -> SessionInfo:
        session = self.require(session_id)
        updated = session.model_copy(
            update={
                "state": SessionState.failed,
                "updated_at": utc_now(),
                "last_event": "failed",
                "last_error": error_message,
            }
        )
        self._sessions[session_id] = updated
        if self._active_session_id == session_id:
            self._active_session_id = None
        return updated

    def reload(self, session_id: str) -> SessionInfo:
        session = self.require(session_id)
        updated = session.model_copy(
            update={
                "updated_at": utc_now(),
                "last_event": "reloaded",
            }
        )
        self._sessions[session_id] = updated
        return updated

    def update_counts(
        self,
        session_id: str,
        *,
        chunk_count: int,
        word_count: int,
        phrase_count: int,
        sentence_count: int,
    ) -> SessionInfo:
        session = self.require(session_id)
        updated = session.model_copy(
            update={
                "updated_at": utc_now(),
                "chunk_count": chunk_count,
                "word_count": word_count,
                "phrase_count": phrase_count,
                "sentence_count": sentence_count,
            }
        )
        self._sessions[session_id] = updated
        return updated

    def require(self, session_id: str) -> SessionInfo:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def get(self, session_id: str) -> SessionInfo | None:
        return self._sessions.get(session_id)

    def active(self) -> SessionInfo | None:
        if self._active_session_id is None:
            return None
        return self._sessions.get(self._active_session_id)

    def all(self) -> list[SessionInfo]:
        return sorted(self._sessions.values(), key=lambda item: item.updated_at, reverse=True)
