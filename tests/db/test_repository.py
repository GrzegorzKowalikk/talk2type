import time

from talk2type.db.model import Transcription
from talk2type.db.repository import TranscriptionRepository


def test_insert_persists(session):
    repo = TranscriptionRepository(session)
    repo.insert(Transcription(raw="hello", cleaned="Hello."))
    rows = repo.recent()
    assert len(rows) == 1
    assert rows[0].raw == "hello"


def test_recent_empty_db(session):
    repo = TranscriptionRepository(session)
    assert repo.recent() == []


def test_recent_respects_limit(session):
    repo = TranscriptionRepository(session)
    for i in range(5):
        repo.insert(Transcription(raw=f"r{i}", cleaned=f"c{i}"))
    assert len(repo.recent(limit=2)) == 2


def test_recent_ordered_desc(session):
    repo = TranscriptionRepository(session)
    repo.insert(Transcription(raw="first", cleaned="first"))
    time.sleep(0.01)
    repo.insert(Transcription(raw="second", cleaned="second"))
    rows = repo.recent()
    assert rows[0].raw == "second"
