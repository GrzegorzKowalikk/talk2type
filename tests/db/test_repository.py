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


def test_history_pages_search_all_records_with_literal_unicode_query(session):
    from datetime import datetime

    repo = TranscriptionRepository(session)
    for cleaned in ["ŻÓŁĆ 100%_", "new one", "new two"]:
        repo.insert(Transcription(raw="raw", cleaned=cleaned, ts=datetime(2026, 1, 1)))
    first = repo.history(limit=2)
    assert [r.cleaned for r in first] == ["new two", "new one"]
    assert [r.cleaned for r in repo.history(limit=2, before=(first[-1].ts, first[-1].id))] == ["ŻÓŁĆ 100%_"]
    assert [r.cleaned for r in repo.history(limit=2, query="żółć 100%_")] == ["ŻÓŁĆ 100%_"]


def test_statistics_preserve_whitespace_days_and_average_per_transcription(session):
    from datetime import datetime

    repo = TranscriptionRepository(session)
    assert repo.statistics() == (0, 0, 0)
    for cleaned, day, stt, llm in [
        (" one\t two\nthree\u00a0four ", 1, 30000, 30000),
        ("five six", 1, None, 30000),
        ("seven", 2, 0, None),
        ("", 2, 60000, 0),
    ]:
        repo.insert(Transcription(raw="raw", cleaned=cleaned, ts=datetime(2026, 1, day), stt_ms=stt, llm_ms=llm))
    assert repo.statistics() == (7, 2, 2)
    newest = session.get(Transcription, repo.history(limit=1)[0].id)
    session.delete(newest)
    assert repo.statistics() == (7, 2, 4)
