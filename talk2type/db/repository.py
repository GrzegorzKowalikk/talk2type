from datetime import datetime
from typing import NamedTuple

from sqlalchemy import func, and_, or_
from sqlmodel import Session, col, select

from talk2type.db.model import Transcription


class HistoryEntry(NamedTuple):
    id: int
    ts: datetime
    cleaned: str


class TranscriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def insert(self, record: Transcription) -> None:
        self.session.add(record)

    def recent(self, limit: int = 50) -> list[Transcription]:
        return list(
            self.session.exec(
                select(Transcription).order_by(col(Transcription.ts).desc()).limit(limit)
            ).all()
        )

    def history(
        self, limit: int = 50, query: str = "",
        before: tuple[datetime, int] | None = None,
    ) -> list[HistoryEntry]:
        """Newest history summaries, with a stable cursor and literal search."""
        statement = select(Transcription.id, Transcription.ts, Transcription.cleaned)
        if query:
            connection = self.session.connection().connection.driver_connection
            connection.create_function(
                "history_matches", 3,
                lambda ts, cleaned, needle: needle.lower() in
                f'{datetime.fromisoformat(ts):%I:%M %p}  "{cleaned}"'.lower(),
            )
            statement = statement.where(func.history_matches(Transcription.ts, Transcription.cleaned, query))
        if before is not None:
            ts, row_id = before
            statement = statement.where(or_(
                Transcription.ts < ts,
                and_(Transcription.ts == ts, Transcription.id < row_id),
            ))
        rows = self.session.exec(statement.order_by(
            col(Transcription.ts).desc(), col(Transcription.id).desc()
        ).limit(limit)).all()
        return [HistoryEntry(*row) for row in rows]

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
