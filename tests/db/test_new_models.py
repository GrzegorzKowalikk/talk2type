from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

from talk2type.db.model import Transcription  # noqa: F401


# --- Hotword ---


def test_hotword_insert_assigns_id(session):
    from talk2type.db.model import Hotword

    h = Hotword(word="Claude")
    session.add(h)
    session.commit()
    session.refresh(h)
    assert isinstance(h.id, int)


def test_hotword_fields(session):
    from talk2type.db.model import Hotword

    h = Hotword(word="Anthropic")
    session.add(h)
    session.commit()
    session.refresh(h)
    assert h.word == "Anthropic"


# --- Snippet ---


def test_snippet_insert_assigns_id(session):
    from talk2type.db.model import Snippet

    s = Snippet(name="greeting", body="Hello, {name}!")
    session.add(s)
    session.commit()
    session.refresh(s)
    assert isinstance(s.id, int)


def test_snippet_fields(session):
    from talk2type.db.model import Snippet

    s = Snippet(name="sig", body="Best regards")
    session.add(s)
    session.commit()
    session.refresh(s)
    assert s.name == "sig"
    assert s.body == "Best regards"


# --- Note ---


def test_note_insert_assigns_id(session):
    from talk2type.db.model import Note

    n = Note(title="ideas", body="remember to refactor")
    session.add(n)
    session.commit()
    session.refresh(n)
    assert isinstance(n.id, int)


def test_note_fields(session):
    from talk2type.db.model import Note

    n = Note(title="scratch", body="some text")
    session.add(n)
    session.commit()
    session.refresh(n)
    assert n.title == "scratch"
    assert n.body == "some text"


# --- Idempotent create_all ---


def test_create_all_idempotent():
    """create_all twice must not raise — tables already exist."""
    from talk2type.db.model import Hotword, Snippet, Note  # noqa: F401

    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    SQLModel.metadata.create_all(e)  # second call must not raise

    with Session(e) as s:
        assert s.exec(text("SELECT count(*) FROM hotword")).one() == (0,)
        assert s.exec(text("SELECT count(*) FROM snippet")).one() == (0,)
        assert s.exec(text("SELECT count(*) FROM note")).one() == (0,)


def test_transcription_table_untouched():
    """Adding new tables must not break existing Transcription table."""
    from talk2type.db.model import Hotword, Snippet, Note  # noqa: F401

    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)

    with Session(e) as s:
        t = Transcription(raw="r", cleaned="c")
        s.add(t)
        s.commit()
        s.refresh(t)
        assert isinstance(t.id, int)
