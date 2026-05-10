# Dark UI — Test Plan

TDD approach — write tests before implementation.

## Fixtures

- **QApplication**: session-scoped singleton (`qt_app`), prevents duplicate QApplication
- **DB**: in-memory SQLite session with `create_all()`, defined in `tests/db/conftest.py`

---

## [x] Phase 1 — DB Models (Hotword, Snippet, Note)

**File**: `tests/db/test_new_models.py` (8 tests)

- [x] Hotword insert assigns id
- [x] Hotword fields (word)
- [x] Snippet insert assigns id
- [x] Snippet fields (name, body)
- [x] Note insert assigns id
- [x] Note fields (title, body)
- [x] `create_all()` idempotent — no raise on second call
- [x] Transcription table untouched by new models

---

## [x] Phase 2 — MainWindow + Sidebar + Dark Theme

**File**: `tests/test_main_window.py` (9 tests)

- [x] Window title is "Talk2Type"
- [x] Sidebar has 5 nav buttons
- [x] QStackedWidget has 5 pages
- [x] Sidebar width is 200px
- [x] Click nav button switches QStackedWidget page
- [x] Active button gets `active=true` property
- [x] Window stylesheet contains `#1e1e2e`
- [x] Sidebar stylesheet contains dark bg color
- [x] Window stylesheet contains `#cdd6f4` text color

---

## [x] Phase 3 — Tray Integration

**File**: `tests/test_tray.py` (4 tests)

- [x] Tray constructor accepts on_open callback
- [x] "Open" callback wired correctly
- [x] "Quit" callback still works (no regression)
- [x] Menu has both "Open" and "Quit" items

---

## [x] Phase 4 — Home Page (Stats)

**File**: `tests/test_home_page.py` (10 tests)

- [x] Word count displayed from transcription data
- [x] Days of usage displayed
- [x] WPM calculated
- [x] Empty DB shows zeros gracefully
- [x] Recent 20 transcriptions listed
- [x] Total words empty state
- [x] Days empty state
- [x] WPM empty state
- [x] WPM skips zero-duration rows
- [x] Recent ordered newest first

---

## [x] Phase 5 — History Page

**File**: `tests/test_history_page.py` (9 tests)

- [x] Full transcription list displayed
- [x] Transcription text visible in list items
- [x] Live search/filter by text
- [x] Search clear restores all items
- [x] Date grouping — "TODAY" header
- [x] Date grouping — "YESTERDAY" header
- [x] Date grouping — older date header
- [x] Context menu: Copy
- [x] Context menu: Delete

---

## [x] Phase 6 — Dictionary Page (Hotwords)

**File**: `tests/test_dictionary_page.py` (7 tests)

- [x] List hotwords from DB
- [x] Add hotword via UI
- [x] Ignore empty input
- [x] Ignore duplicates
- [x] Remove hotword via UI
- [x] Seed from WHISPER_HOTWORDS config on first launch
- [x] Skip seed when DB already has data

**Also modified**: `tests/test_stt.py` — patched DB for hotwords (5 tests, all pass)

---

## [x] Phase 7 — Snippets Page

**File**: `tests/test_snippets_page.py` (7 tests)

- [x] List snippets from DB
- [x] Shows name and body preview
- [x] Add snippet (name + body) via form
- [x] Form hidden after save
- [x] Delete snippet
- [x] Click to copy body to clipboard
- [x] Search by name

---

## [x] Phase 8 — Notes Page

**File**: `tests/test_notes_page.py` (16 tests)

- [x] Split panel has list and editor
- [x] Title editor exists
- [x] New note button exists
- [x] Delete button exists
- [x] Search input exists
- [x] Refresh populates list
- [x] List shows note titles
- [x] Select note loads body
- [x] Select note loads title
- [x] Create note adds to list
- [x] Create note default title
- [x] Delete note removes from list
- [x] Search filters by title
- [x] Search clear shows all
- [x] Auto-save persists body edits
- [x] Auto-save persists title edits

---

## [x] Phase 9 — Integration

**File**: `tests/test_integration.py` (5 tests)

- [x] Tray "Open" callback shows MainWindow
- [x] MainWindow has real page widgets (not placeholders)
- [x] Switch to page calls refresh_data
- [x] refresh_current_page delegates to active page
- [x] Window close and reopen works without crash

**Full suite**: 130 passed, 0 failed. mypy clean on 24 source files.

---

## Summary

| Phase | File | Tests | Status |
|-------|------|-------|--------|
| 1 — DB Models | `tests/db/test_new_models.py` | 8 | Done |
| 2 — MainWindow | `tests/test_main_window.py` | 9 | Done |
| 3 — Tray | `tests/test_tray.py` | 4 | Done |
| 4 — Home Page | `tests/test_home_page.py` | 10 | Done |
| 5 — History Page | `tests/test_history_page.py` | 9 | Done |
| 6 — Dictionary | `tests/test_dictionary_page.py` | 7 | Done |
| 7 — Snippets | `tests/test_snippets_page.py` | 7 | Done |
| 8 — Notes | `tests/test_notes_page.py` | 16 | Done |
| 9 — Integration | `tests/test_integration.py` | 5 | Done |
| **Total** | | **75** | **All done** |
