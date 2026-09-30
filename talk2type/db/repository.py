from datetime import datetime

from sqlalchemy import func, and_, or_
from sqlmodel import Session, col, select

from talk2type.db.model import Transcription


class TranscriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def history(
        self, limit: int = 50, query: str = "",
        before: tuple[datetime, int] | None = None,
    ) -> list:
        """Newest history summaries, with a stable cursor and literal search."""
        statement = select(Transcription.id, Transcription.ts, Transcription.cleaned)
        if query:
            # ponytail: SQLite lower() is ASCII-only; override so "żółć" matches "Żółć"
            self.session.connection().connection.driver_connection.create_function("lower", 1, str.lower)
            statement = statement.where(col(Transcription.cleaned).ilike(f"%{query}%"))
        if before is not None:
            ts, row_id = before
            statement = statement.where(or_(
                Transcription.ts < ts,
                and_(Transcription.ts == ts, Transcription.id < row_id),
            ))
        return list(self.session.exec(statement.order_by(
            col(Transcription.ts).desc(), col(Transcription.id).desc()
        ).limit(limit)).all())

    def statistics(self) -> tuple[int, int, int]:
        """Aggregate existing word/day/WPM semantics without loading ORM rows."""
        connection = self.session.connection().connection.driver_connection
        connection.create_function("word_count", 1, lambda text: len(text.split()))
        words = func.word_count(Transcription.cleaned)
        duration = func.coalesce(Transcription.stt_ms, 0) + func.coalesce(Transcription.llm_ms, 0)
        total, days, wpm = self.session.exec(select(
            func.coalesce(func.sum(words), 0),
            func.count(func.distinct(func.date(Transcription.ts))),
            func.coalesce(func.avg(words / (func.nullif(duration, 0) / 60000.0)), 0),
        )).one()
        return int(total), int(days), int(wpm)
