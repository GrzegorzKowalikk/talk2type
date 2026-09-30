from datetime import datetime

from talk2type.db.model import Transcription
from talk2type.db.repository import TranscriptionRepository


def test_history_pages_search_all_records_with_literal_unicode_query(session):
    repo = TranscriptionRepository(session)
    for cleaned in ["ŻÓŁĆ 100%_", "new one", "new two"]:
        session.add(Transcription(raw="raw", cleaned=cleaned, ts=datetime(2026, 1, 1)))
    first = repo.history(limit=2)
    assert [r.cleaned for r in first] == ["new two", "new one"]
    assert [r.cleaned for r in repo.history(limit=2, before=(first[-1].ts, first[-1].id))] == ["ŻÓŁĆ 100%_"]
    assert [r.cleaned for r in repo.history(limit=2, query="ŻÓŁĆ 100%_")] == ["ŻÓŁĆ 100%_"]
    assert [r.cleaned for r in repo.history(query="NEW ONE")] == ["new one"]
    assert [(row_id, ts, cleaned) for row_id, ts, cleaned in first] == [(r.id, r.ts, r.cleaned) for r in first]


def test_statistics_preserve_whitespace_days_and_average_per_transcription(session):
    repo = TranscriptionRepository(session)
    assert repo.statistics() == (0, 0, 0)
    for cleaned, day, stt, llm in [
        (" one\t two\nthree four ", 1, 30000, 30000),
        ("five six", 1, None, 30000),
        ("seven", 2, 0, None),
        ("", 2, 60000, 0),
    ]:
        session.add(Transcription(raw="raw", cleaned=cleaned, ts=datetime(2026, 1, day), stt_ms=stt, llm_ms=llm))
    assert repo.statistics() == (7, 2, 2)
    newest = session.get(Transcription, repo.history(limit=1)[0].id)
    session.delete(newest)
    assert repo.statistics() == (7, 2, 4)


def test_history_search_folds_polish_case(session):
    session.add(Transcription(raw="x", cleaned="Żółć na stole"))
    session.commit()
    assert len(TranscriptionRepository(session).history(query="żółć")) == 1
