# Dark-Themed Full Window UI — Implementation Plan

## Context

Build a dark-themed PySide6 QMainWindow with sidebar navigation for the WisprFlow voice dictation app. Triggered from tray icon. 5 pages: Home, History, Dictionary, Snippets, Notes.

## Documentation Sources

| Library | Source | Key APIs |
|---------|--------|----------|
| PySide6 | context7 / Qt for Python docs | QMainWindow, QStackedWidget, QWidget sidebar, QSS, QLineEdit, QTextEdit, QListWidget, QMenu, Signal/Slot |
| SQLModel | context7 / sqlmodel.tiangolo.com | `table=True`, `create_all` (idempotent), CRUD via Session context manager |

## Allowed APIs (from docs)

**PySide6 widgets:**
- `QMainWindow` — top-level window
- `QStackedWidget` — page switching via `setCurrentIndex(int)`
- `QWidget` + `QVBoxLayout` — custom sidebar (not QDockWidget — we want fixed)
- `QPushButton` — sidebar navigation buttons, connect to `setCurrentIndex`
- `QLabel` — text display
- `QLineEdit` — search input, `textEdited` signal for live filtering
- `QTextEdit` / `QPlainTextEdit` — notes editor, `toPlainText()`, `textChanged` signal
- `QListWidget` — simple list display (built-in model, no custom QAbstractItemModel needed)
- `QMenu`, `QAction` — context menus, tray menu items
- `Signal`, `Slot` — custom signals for cross-component communication

**QSS dark theme:**
- `background-color`, `color`, `border`, `border-radius`, `padding`, `font-size`
- Widget selectors: `QMainWindow`, `QPushButton`, `QListWidget::item:selected`, etc.
- State selectors: `:hover`, `:pressed`, `:selected`

**SQLModel:**
- `SQLModel.metadata.create_all(engine)` — idempotent, safe to add new tables
- `Session(engine)` context manager with auto commit/rollback
- `select(Model).where(...)` for queries
- `session.add()`, `session.delete()`, `session.get(Model, id)`

## Anti-Patterns (do NOT)

- ❌ QDockWidget for sidebar — we want fixed, not user-movable
- ❌ QML — project uses widgets
- ❌ Custom QAbstractItemModel — QListWidget/QTableWidget suffice for this scale
- ❌ Alembic — we're adding NEW tables, not modifying existing ones; `create_all` handles it
- ❌ Shared DB session across threads — each operation gets its own session via `get_session()`
- ❌ Direct widget manipulation from non-GUI thread — use `Signal(QueuedConnection)`
- ❌ Modifying overlay.py — it stays unchanged

---

## Phase 1: DB Schema — New Tables

**What:** Add 3 new SQLModel tables to existing `model.py`. Update `engine.py` imports to ensure `create_all` sees them.

**Files to modify:**
- `talk2type/db/model.py` — add Hotword, Snippet, Note models
- `talk2type/db/engine.py` — ensure new models are imported before `create_all`

**New models (from SQLModel docs):**

```python
class Hotword(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    word: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.now)

class Snippet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Note(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

**Verification:**
- [ ] App starts without error (tables created)
- [ ] `sqlite3 data/history.db ".tables"` shows `hotword`, `note`, `snippet`, `transcription`
- [ ] Existing `transcription` table untouched (same schema)

---

## Phase 2: Dark Theme QSS + Main Window Shell

**What:** Create dark QSS stylesheet, MainWindow with sidebar + QStackedWidget shell. No page content yet.

**New files:**
- `talk2type/ui/__init__.py`
- `talk2type/ui/theme.py` — dark QSS constants
- `talk2type/ui/main_window.py` — QMainWindow with sidebar + QStackedWidget
- `talk2type/ui/sidebar.py` — custom QWidget sidebar with navigation buttons

**Architecture:**

```
MainWindow (QMainWindow)
├── Sidebar (QWidget, fixed width ~200px)
│   ├── QPushButton "Home"
│   ├── QPushButton "History"
│   ├── QPushButton "Dictionary"
│   ├── QPushButton "Snippets"
│   └── QPushButton "Notes"
└── QStackedWidget (central widget)
    ├── HomePlaceholder
    ├── HistoryPlaceholder
    ├── DictionaryPlaceholder
    ├── SnippetsPlaceholder
    └── NotesPlaceholder
```

**Dark theme colors (QSS):**
- Background: `#1e1e2e` (main), `#181825` (sidebar)
- Text: `#cdd6f4`
- Accent: `#89b4fa` (blue), `#a6e3a1` (green for active)
- Input bg: `#313244`
- Hover: `#45475a`
- Selected: `#585b70`

**Verification:**
- [ ] Window shows with dark theme, sidebar on left, empty content area on right
- [ ] Clicking sidebar buttons switches placeholder pages
- [ ] Window title: "Talk2Type"

---

## Phase 3: Tray Integration

**What:** Add "Open" menu item to tray. Wire it to show/hide MainWindow.

**Files to modify:**
- `talk2type/tray.py` — add `on_open` callback parameter, add "Open" MenuItem before "Quit"
- `main.py` — pass `window.show` callback to Tray, create MainWindow

**Tray changes:**
```python
class Tray:
    def __init__(self, on_quit, on_open):  # add on_open
        self._icon = Icon(
            "Talk2Type",
            Image.open(_IMAGES_DIR / "icon.png"),
            "Talk2Type",
            Menu(
                MenuItem("Open", lambda i, _: on_open()),
                MenuItem("Quit", lambda i, _: (on_quit(), i.stop())),
            ),
        )
```

**Verification:**
- [ ] Right-click tray shows "Open" + "Quit"
- [ ] "Open" shows the MainWindow
- [ ] "Quit" still works as before

---

## Phase 4: Home Page

**What:** Welcome text + stats (total words, avg WPM, days of usage) + recent activity list (last 20 transcriptions).

**New files:**
- `talk2type/ui/pages/home.py`

**Data queries (from existing `transcriptions` table):**
- Total words: `SUM(words_count)` — but wait, existing model doesn't have `words_count` field. Let me check...

Actually from the codebase research, `Transcription` has: `id, ts, raw, cleaned, app, stt_ms, llm_ms`. No `words_count` or `duration_ms` field. So WPM calculation needs:
- Word count: `len(cleaned.split())` computed at query time
- Duration: `stt_ms + llm_ms` as proxy, or just count total transcriptions
- Days: `COUNT(DISTINCT DATE(ts))`

**Home page layout:**
```
┌─────────────────────────────────────────────┐
│ Welcome back!                                │
│                                              │
│ ┌──────┐ ┌──────┐ ┌──────┐                  │
│ │ 127  │ │ 45   │ │ 142  │                  │
│ │words │ │days  │ │ WPM  │                  │
│ └──────┘ └──────┘ └──────┘                  │
│                                              │
│ Recent activity                    TODAY     │
│ ─────────────────────────────────────────── │
│ 04:02 PM  "Transcribed text here..."         │
│ 04:01 PM  "Another transcription..."         │
│ 03:58 PM  "Yet another one..."               │
└─────────────────────────────────────────────┘
```

**Verification:**
- [ ] Stats show correct word count, days, WPM
- [ ] Recent activity shows last 20 transcriptions with timestamps
- [ ] Empty state handled (no transcriptions yet)

---

## Phase 5: History Page

**What:** Full searchable list of all transcriptions with date grouping (TODAY, YESTERDAY, older).

**New files:**
- `talk2type/ui/pages/history.py`

**Layout:**
```
┌─────────────────────────────────────────────┐
│ 🔍 Search...                    [Clear]     │
│                                              │
│ TODAY                                        │
│ ─────────────────────────────────────────── │
│ 04:02 PM  "Hmm, I'm not really sure..."      │
│ 04:01 PM  "I have a grocery list..."    ⋮   │
│                                              │
│ YESTERDAY                                    │
│ ─────────────────────────────────────────── │
│ 02:04 PM  "The transcription was..."         │
└─────────────────────────────────────────────┘
```

**Features:**
- QLineEdit search bar with `textEdited` signal → filter by `cleaned` text
- Group by day: TODAY, YESTERDAY, date headers for older
- Context menu (right-click): Copy text, Delete
- Click to expand/view full transcription text

**Verification:**
- [ ] Search filters transcriptions in real-time
- [ ] Date grouping works correctly
- [ ] Copy text works
- [ ] Delete removes from DB and updates list

---

## Phase 6: Dictionary Page

**What:** CRUD for Whisper hotwords. Replace hardcoded `WHISPER_HOTWORDS` list with DB-backed storage.

**New files:**
- `talk2type/ui/pages/dictionary.py`

**Files to modify:**
- `talk2type/stt.py` — load hotwords from DB instead of config.py
- `talk2type/config.py` — remove `WHISPER_HOTWORDS` constant (or keep as fallback)

**Layout:**
```
┌─────────────────────────────────────────────┐
│ Dictionary                                   │
│ Words Whisper often mishears.                │
│                                              │
│ ┌─────────────────────────────────────────┐ │
│ │ + Add word...                           │ │
│ └─────────────────────────────────────────┘ │
│                                              │
│ Claude                              ✕       │
│ Claude Code                         ✕       │
│ Anthropic                           ✕       │
└─────────────────────────────────────────────┘
```

**Migration plan:**
1. On first launch, seed `hotword` table from `WHISPER_HOTWORDS` if table is empty
2. `stt.py` loads hotwords from DB via `get_session()`
3. Remove hardcoded list from config.py

**Verification:**
- [ ] Hotwords from config.py seeded into DB on first launch
- [ ] Add/remove hotwords via UI
- [ ] STT uses DB hotwords as `initial_prompt`
- [ ] Existing transcriptions unaffected

---

## Phase 7: Snippets Page

**What:** CRUD for text templates. Click to copy to clipboard.

**New files:**
- `talk2type/ui/pages/snippets.py`

**Layout:**
```
┌─────────────────────────────────────────────┐
│ Snippets                    [+ New Snippet]  │
│                                              │
│ ┌──────────────────────────────────────────┐│
│ │ Greeting                                  ││
│ │ Hello, I wanted to reach out about...     ││
│ └──────────────────────────────────────────┘│
│ ┌──────────────────────────────────────────┐│
│ │ Bug Report                                ││
│ │ Steps to reproduce: 1. ...                ││
│ └──────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**Features:**
- Add/Edit/Delete snippets
- Click snippet to copy content to clipboard
- Search by name

**Verification:**
- [ ] CRUD operations work
- [ ] Click copies to clipboard
- [ ] Search filters by name

---

## Phase 8: Notes Page

**What:** Free-form notes with title + content editor.

**New files:**
- `talk2type/ui/pages/notes.py`

**Layout:**
```
┌──────────────────────┬──────────────────────┐
│ Notes                │                      │
│ [+ New Note]         │  Note Title          │
│                      │  ─────────────────── │
│ > Meeting notes      │  Note content goes   │
│   Todo list          │  here. Edit freely.  │
│   Ideas              │                      │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

**Split-panel:** QListWidget (left) + QPlainTextEdit (right)

**Features:**
- Select note from list → loads into editor
- Auto-save on edit (debounced via QTimer, 500ms)
- Create/delete notes
- Search by title

**Verification:**
- [ ] Create new note
- [ ] Edit saves automatically
- [ ] Delete works
- [ ] Switching between notes preserves content

---

## Phase 9: Final Wiring + Integration

**What:** Wire MainWindow into `main.py` App lifecycle. Handle window show/hide from tray. Ensure DB tables created before UI loads.

**Files to modify:**
- `main.py` — create MainWindow, pass to Tray as `on_open` callback

**Key wiring:**
```python
# main.py App.__init__
self._window = MainWindow()  # new
self.tray = Tray(on_quit=self.shutdown, on_open=self._window.show)

# Ensure DB tables exist before UI
from talk2type.db import model  # triggers imports
get_engine()  # triggers create_all
```

**Verification:**
- [ ] Full app lifecycle works: start → record → transcribe → see in history
- [ ] Tray "Open" shows window, window close hides (not quits)
- [ ] All 5 pages functional
- [ ] No regressions in overlay, hotkeys, transcription pipeline
- [ ] mypy passes
- [ ] Full test suite passes
