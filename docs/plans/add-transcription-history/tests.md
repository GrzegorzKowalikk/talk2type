# Test Plan: Transcription History

Runner: `uv run pytest`  
DB: in-memory SQLite (`:memory:`) — zero disk I/O in tests

---

## Fixture: in-memory engine

```python
# tests/db/conftest.py
import pytest
from sqlmodel import create_engine, SQLModel, Session
from talk2type.db.model import Transcription  # noqa: F401 — registers metadata

@pytest.fixture
def engine():
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    yield e
    SQLModel.metadata.drop_all(e)

@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
```

---

## 1. Model tests (`tests/db/test_model.py`)

| # | Case | Assertion |
|---|------|-----------|
| M1 | Create Transcription with all fields | `ts` auto-set, `id` is None before insert |
| M2 | Optional fields default to None | `app`, `stt_ms`, `llm_ms` are None when not passed |
| M3 | Insert + query back | `id` auto-assigned as integer after commit |

```python
def test_optional_fields_default_none():
    t = Transcription(raw="raw", cleaned="clean")
    assert t.app is None
    assert t.stt_ms is None
    assert t.llm_ms is None
    assert t.ts is not None  # default_factory fired

def test_insert_assigns_id(session):
    t = Transcription(raw="r", cleaned="c")
    session.add(t)
    session.commit()
    assert isinstance(t.id, int)
```

---

## 2. Repository tests (`tests/db/test_repository.py`)

| # | Case | Assertion |
|---|------|-----------|
| R1 | `insert()` persists row | query returns same raw/cleaned |
| R2 | `recent(limit=N)` returns N newest rows | ordered by ts desc |
| R3 | `recent()` with empty DB returns `[]` | no crash |
| R4 | `recent(limit=2)` with 5 rows returns 2 | limit respected |

```python
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
    import time
    repo = TranscriptionRepository(session)
    repo.insert(Transcription(raw="first", cleaned="first"))
    time.sleep(0.01)
    repo.insert(Transcription(raw="second", cleaned="second"))
    rows = repo.recent()
    assert rows[0].raw == "second"  # newest first
```

---

## 3. Service tests (`tests/db/test_service.py`)

Strategy: patch `get_session` to return in-memory session; patch `_get_active_app`.

| # | Case | Assertion |
|---|------|-----------|
| S1 | `save_transcription()` writes row to DB | verify via repo.recent() |
| S2 | `_get_active_app()` returns None on error | no crash when win32gui unavailable |
| S3 | `app` field set from `_get_active_app()` result | mocked value propagates to row |

```python
from unittest.mock import patch, MagicMock
from talk2type.db import service as svc

def test_save_writes_row(engine):
    with patch("talk2type.db.service.get_session") as mock_get_session, \
         patch("talk2type.db.service._get_active_app", return_value="notepad.exe"):
        with Session(engine) as s:
            mock_get_session.return_value.__enter__ = lambda _: s
            mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
            svc.save_transcription("raw text", "Clean text.", 400, 200)
        rows = s.exec(select(Transcription)).all()
    assert len(rows) == 1
    assert rows[0].app == "notepad.exe"
    assert rows[0].stt_ms == 400

def test_get_active_app_returns_none_on_exception():
    with patch.dict("sys.modules", {"win32gui": None, "win32process": None}):
        result = svc._get_active_app()
    assert result is None
```

---

## 4. Integration test (`tests/test_pipeline_history.py`)

Verify `_run_pipeline` in main.py calls `save_transcription` with correct args.

| # | Case | Assertion |
|---|------|-----------|
| I1 | Successful pipeline call → `save_transcription` called once | mock assert_called_once |
| I2 | `stt_ms` > 0, `llm_ms` > 0 | timing captured |
| I3 | STT returns empty string → `save_transcription` NOT called | guard respected |

```python
from unittest.mock import patch, MagicMock
# Import App from main.py — patch stt, llm, paste, save

def test_pipeline_calls_save_on_success():
    with patch("main.cleanup_text", return_value="Clean."), \
         patch("main.paste_text"), \
         patch("main.save_transcription") as mock_save:
        app = build_test_app()  # helper that creates App with mocked STT
        app.stt = MagicMock()
        app.stt.transcribe.return_value = "raw text"
        app._run_pipeline(audio=MagicMock(), lang="pl")
    mock_save.assert_called_once()
    _, kwargs = mock_save.call_args
    assert kwargs["stt_ms"] >= 0
    assert kwargs["llm_ms"] >= 0

def test_pipeline_no_save_on_empty_transcription():
    with patch("main.cleanup_text"), \
         patch("main.paste_text"), \
         patch("main.save_transcription") as mock_save:
        app = build_test_app()
        app.stt.transcribe.return_value = ""
        app._run_pipeline(audio=MagicMock(), lang="pl")
    mock_save.assert_not_called()
```

---

## 5. Smoke test (manual, after deploy)

```bash
# 1. Start app, press F9, dictate something
# 2. Query DB:
uv run python -c "
from talk2type.db.engine import get_engine
from sqlmodel import Session, select
from talk2type.db.model import Transcription
with Session(get_engine()) as s:
    rows = s.exec(select(Transcription)).all()
    for r in rows:
        print(r.ts, r.app, r.stt_ms, r.llm_ms)
        print('RAW:', r.raw[:60])
        print('CLEAN:', r.cleaned[:60])
"
```

Expected: row with non-null `ts`, `app` like `"Code.exe"`, positive `stt_ms`/`llm_ms`.

---

## Run order

```bash
uv run pytest tests/db/ -v          # unit tests (no app needed)
uv run pytest tests/ -v             # all including integration
```
