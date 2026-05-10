from datetime import datetime

from sqlmodel import Field, SQLModel


class Transcription(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.now)
    raw: str
    cleaned: str
    app: str | None = None
    stt_ms: int | None = None
    llm_ms: int | None = None
