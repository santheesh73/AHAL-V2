from __future__ import annotations

from app.sessions.models import SessionType
from app.sessions.session_manager import SessionCreateResult, session_manager


class AnalysisRouter:
    def create_session(
        self,
        session_type: SessionType,
        source_name: str,
    ) -> SessionCreateResult | None:
        return session_manager.create_session_if_capacity(
            session_type=session_type,
            source_name=source_name,
        )


analysis_router = AnalysisRouter()
