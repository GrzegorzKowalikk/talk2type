from sqlmodel import Session, col, select

from talk2type.db.model import Transcription


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
