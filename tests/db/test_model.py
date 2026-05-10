from talk2type.db.model import Transcription


def test_optional_fields_default_none():
    t = Transcription(raw="raw", cleaned="clean")
    assert t.app is None
    assert t.stt_ms is None
    assert t.llm_ms is None
    assert t.ts is not None


def test_ts_auto_set():
    t = Transcription(raw="r", cleaned="c")
    assert t.ts is not None


def test_insert_assigns_id(session):
    t = Transcription(raw="r", cleaned="c")
    session.add(t)
    session.commit()
    session.refresh(t)
    assert isinstance(t.id, int)
