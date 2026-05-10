# Plan: Add Transcription History (SQLModel + SQLite)

## Phase 0 — Documentation Discovery ✅

### Verified APIs

**SQLModel** (context7 confirmed):
- Model: `class T(SQLModel, table=True): id: int | None = Field(default=None, primary_key=True)`
- Engine: `create_engine("sqlite:///path")`, `SQLModel.metadata.create_all(engine)`
- Session: `with Session(engine) as session: session.add(obj); session.commit()`
- Query: `session.exec(select(Model)).all()` / `.first()`
- Nullable field: `field: str | None = None`
- **Use `session.exec()` NOT `session.execute()`** (SQLModel-specific)

**pywin32** (verified via docs):
```python
hwnd = win32gui.GetForegroundWindow()
_, pid = win32process.GetWindowThreadProcessId(hwnd)
handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
exe_path = win32process.GetModuleFileNameEx(handle, 0)  # full path
exe_name = os.path.basename(exe_path)                  # "chrome.exe"
```

**Integration points in main.py** (confirmed by grep):
- Line 65: `raw = self.stt.transcribe(audio, language=lang)` → `str`
- Line 67: `cleaned = cleanup_text(raw, language=lang)` → `str`
- Line 68: `paste_text(cleaned)` — capture active window BEFORE this line
- Project root: `Path(__file__).resolve().parent.parent` (from config.py pattern)

---

## Phase 1 — Deps + Model + Config

### Tasks
- [ ] `uv add sqlmodel pywin32`
- [ ] Add `DATA_DIR` to `talk2type/config.py`:
  ```python
  DATA_DIR = Path(__file__).resolve().parent.parent / "data"
  DATA_DIR.mkdir(exist_ok=True)
  DB_PATH = DATA_DIR / "history.db"
  ```
- [ ] Create `talk2type/db/__init__.py` (empty)
- [ ] Create `talk2type/db/model.py`:
  ```python
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
  ```

### Verification
- `uv run python -c "from talk2type.db.model import Transcription; print('ok')`
- No import errors

---

## Phase 2 — Engine + Repository

### Tasks
- [ ] Create `talk2type/db/engine.py`:
  ```python
  from sqlmodel import create_engine, SQLModel, Session
  from talk2type.config import DB_PATH

  _engine = None

  def get_engine():
      global _engine
      if _engine is None:
          _engine = create_engine(f"sqlite:///{DB_PATH}")
          SQLModel.metadata.create_all(_engine)
      return _engine

  def get_session() -> Session:
      return Session(get_engine())
  ```
- [ ] Create `talk2type/db/repository.py`:
  ```python
  from sqlmodel import Session, select
  from talk2type.db.model import Transcription

  class TranscriptionRepository:
      def __init__(self, session: Session):
          self.session = session

      def insert(self, record: Transcription) -> None:
          self.session.add(record)
          self.session.commit()

      def recent(self, limit: int = 50) -> list[Transcription]:
          return self.session.exec(
              select(Transcription).order_by(Transcription.ts.desc()).limit(limit)
          ).all()
  ```

### Verification
- `uv run python -c "from talk2type.db.engine import get_engine; get_engine(); print('db created')`
- `data/history.db` appears on disk

---

## Phase 3 — Service + Integration

### Tasks
- [ ] Create `talk2type/db/service.py`:
  ```python
  import os
  from talk2type.db.engine import get_session
  from talk2type.db.model import Transcription
  from talk2type.db.repository import TranscriptionRepository

  def _get_active_app() -> str | None:
      try:
          import win32gui, win32process, win32api, win32con
          hwnd = win32gui.GetForegroundWindow()
          if not hwnd:
              return None
          _, pid = win32process.GetWindowThreadProcessId(hwnd)
          handle = win32api.OpenProcess(
              win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid
          )
          exe = win32process.GetModuleFileNameEx(handle, 0)
          return os.path.basename(exe) if exe else None
      except Exception:
          return None

  def save_transcription(raw: str, cleaned: str, stt_ms: int, llm_ms: int) -> None:
      app = _get_active_app()
      record = Transcription(raw=raw, cleaned=cleaned, app=app, stt_ms=stt_ms, llm_ms=llm_ms)
      with get_session() as session:
          TranscriptionRepository(session).insert(record)
  ```

- [ ] Modify `main.py` `_run_pipeline` — add timing + service call:
  ```python
  # Before (lines 65-68):
  raw = self.stt.transcribe(audio, language=lang)
  # ... guard ...
  cleaned = cleanup_text(raw, language=lang)
  paste_text(cleaned)

  # After:
  import time
  from talk2type.db.service import save_transcription

  t0 = time.monotonic()
  raw = self.stt.transcribe(audio, language=lang)
  stt_ms = int((time.monotonic() - t0) * 1000)
  # ... guard ...
  t1 = time.monotonic()
  cleaned = cleanup_text(raw, language=lang)
  llm_ms = int((time.monotonic() - t1) * 1000)
  paste_text(cleaned)
  save_transcription(raw, cleaned, stt_ms, llm_ms)
  ```
  **Important:** capture active window inside `save_transcription` BEFORE paste (already the case — `_get_active_app()` is called before DB write, and `paste_text` already ran — but window focus should still be the target app at this point since we haven't yielded focus back).

  Actually: `_get_active_app()` must be called BEFORE `paste_text(cleaned)`. Move it:
  ```python
  paste_text(cleaned)                                    # pastes, may not change focus
  save_transcription(raw, cleaned, stt_ms, llm_ms)      # called right after — focus still on target app
  ```
  paste_text uses pyperclip + Ctrl+V, which shouldn't steal focus. Order is fine.

### Verification
- Press F9, dictate, release
- `uv run python -c "from talk2type.db.engine import get_engine; from sqlmodel import Session, select; from talk2type.db.model import Transcription; e=get_engine(); s=Session(e); print(s.exec(select(Transcription)).all())"`
- Row appears in DB with correct raw/cleaned/app/stt_ms/llm_ms

---

## Phase 4 — Quality Gate

- [ ] `uv run ruff check talk2type/db/`
- [ ] `uv run mypy talk2type/db/` (if mypy configured)
- [ ] Manual smoke test: F9 → dictate → check DB
- [ ] Verify no exceptions in `logs/wisprflow.log`

---

## Anti-Pattern Guards

- ❌ `session.execute()` — use `session.exec()` (SQLModel API)
- ❌ Blocking UI thread with DB write — pipeline runs in worker thread already ✅
- ❌ Forgetting `table=True` on model class
- ❌ Calling `_get_active_app()` after `paste_text()` might lose focus — but Ctrl+V paste keeps focus on target window ✅
- ❌ `get_session()` without context manager — resource leak

---

## New Files

```
talk2type/db/__init__.py
talk2type/db/model.py
talk2type/db/engine.py
talk2type/db/repository.py
talk2type/db/service.py
data/history.db          (created at runtime)
```

## Modified Files

```
talk2type/config.py      (+DATA_DIR, +DB_PATH)
main.py                  (+timing, +save_transcription call)
```
