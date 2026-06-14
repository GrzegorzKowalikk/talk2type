# Project Instructions

---

## Project Context

- **Stack:** Python 3.12, Windows 11, PySide6 overlay UI, Ollama (local LLM)
- **Purpose:** Push-to-talk voice dictation — hotkey → Whisper transcription → LLM cleanup → paste into active window
- **Package manager:** uv
- **Key libraries:** faster-whisper ≥1.0.3, ollama ≥0.3.0, pyside6 ≥6.5, pynput ≥1.7.7, pystray ≥0.19.5

---

## 🔴 Behavioral Guidelines

Bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you wrote 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- Remove imports/variables/functions that YOUR changes made unused. Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the request.

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

Strong success criteria let you loop independently. Weak criteria ("make it work") force me to keep clarifying.

---

## 🔴 Core Rule: Documentation-First

**Before planning or using ANY external library, fetch current docs.** Knowledge cutoff is stale — libraries ship breaking changes often. Assume nothing.

**Mandatory flow for library work:**
1. `context7 resolve-library-id` → find the library
2. `context7 query-docs` → fetch current API surface
3. Only then plan/implement

**Do NOT:**
- Invent methods that "should exist"
- Use parameters not found in current docs
- Trust memory about library APIs from training data
- Skip docs check because "I know this library"

If a method is not verifiable in current docs → stop and tell me.

---

## Workflow Phases

### Phase 0 — Understand (before any code)

Trigger skills:
- `brainstorming` — Socratic questions for anything non-trivial or ambiguous
- `claude-mem:mem-search` — check if this was solved in prior sessions
- `find-skills` — discover relevant skills I may not know exist

Output: clear statement of WHAT and WHY. Do not proceed without it.

### Phase 1 — Plan (docs-first)

**Use `claude-mem:make-plan`** (not `plan-writing`) whenever the task touches external libraries or takes >30 min of work. It has a mandatory Phase 0 Documentation Discovery.

Supporting skills by task type:
- API work → `api-patterns`
- DB work → `database-design`
- Architecture decision → `architecture`
- Claude/Anthropic SDK → `claude-api`
- MCP server → `mcp-builder`
- PDF → `pdf`

Plan must include:
- Cited doc sources (URLs/files + sections)
- "Allowed APIs" list from current docs
- Verification steps per phase
- Anti-pattern guards (known bad patterns to grep)

Skip `make-plan` only for: simple refactors inside own code, trivial bug fixes, one-file edits with no library concerns → use `plan-writing` instead.

#### Where plans live

**Always save plans under `docs/plans/` in the project root.** If `docs/` or `docs/plans/` does not exist, create them first.

Structure per task — one folder per task, slug = kebab-case of the goal:

```
docs/plans/
  {task-slug}/
    plan.md      # phased implementation plan (what to build, in what order)
    tests.md     # test plan (cases to cover, fixtures needed, edge cases)
```

Example: `docs/plans/add-stripe-webhook/plan.md` + `docs/plans/add-stripe-webhook/tests.md`.

Rules:
- Never save plans to project root, `.claude/`, or ad-hoc temp folders.
- `plan.md` is the output of `make-plan` / `plan-writing`.
- `tests.md` is written BEFORE implementation (test plan drives TDD).
- Keep plan files updated as work progresses — mark `[x]` on done items.
- When the task is shipped, leave the folder in place (serves as history).

### Phase 2 — Test First (TDD)

Always: `tdd-workflow` (RED → GREEN → REFACTOR).

For Python: `python-testing-patterns` (pytest, fixtures, mocking, parameterization).

**Write the failing test before the implementation.** Test based on behavior described in docs, not guesses.

### Phase 3 — Implement

- `claude-mem:do` — execute phased plan via subagents (fresh context per task, keeps main context clean)
- `python-patterns` — Python idioms, type hints, async patterns
- `clean-code` — no over-engineering, no unnecessary abstractions, no premature optimization
- `fastapi-templates` — if FastAPI scaffolding needed

**While coding:** re-query `context7` anytime a library detail is uncertain. Cheaper to check than to debug invented APIs.

### Phase 4 — Quality Gate

After every non-trivial modification:
- `lint-and-validate` — automatic checks
- `simplify` — review for reuse, remove duplication
- `systematic-debugging` — if something breaks (4-phase root cause analysis)
- `code-review-checklist` — final pass before commit

### Phase 5 — Ship

- `git-commit-helper` — commit message from diff
- `claude-mem` auto-captures the session

---

## Skill Routing Cheat Sheet

| I need to... | Skill |
|---|---|
| Understand what user wants | `brainstorming` |
| Check prior work | `claude-mem:mem-search` |
| Plan with docs verification | `claude-mem:make-plan` |
| Plan simple refactor | `plan-writing` |
| Execute phased plan | `claude-mem:do` |
| Write Python tests | `python-testing-patterns` + `tdd-workflow` |
| Design API | `api-patterns` |
| Design DB schema / pick DB | `database-design` |
| Pick architectural pattern | `architecture` |
| Build Claude/Anthropic app | `claude-api` |
| Build MCP server | `mcp-builder` |
| Work with PDF | `pdf` |
| Refactor/cleanup | `simplify` + `clean-code` |
| Debug something broken | `systematic-debugging` |
| Lint after changes | `lint-and-validate` |
| Commit message | `git-commit-helper` |
| Search codebase structurally | `claude-mem:smart-explore` |

---

## MCP Tools Priority

For library docs — this order:
1. **`context7`** — first choice for any library/framework/SDK/CLI docs
2. **`docs-langchain`** — for LangChain specifically
3. **`llama-index-docs`** — for LlamaIndex specifically
4. `WebFetch` — fallback for docs not in above MCPs

Use `context7` **even for libraries I "know well"** — APIs drift.

---

## Anti-Patterns (do not do)

- ❌ Coding before reading current docs
- ❌ Using `plan-writing` when the task touches external libraries (use `make-plan`)
- ❌ Writing implementation before writing the test
- ❌ Skipping `lint-and-validate` after changes
- ❌ Inventing APIs because "it should work this way"
- ❌ Over-engineering: adding abstractions, error handling, or fallbacks for cases that can't happen
- ❌ Adding comments that describe WHAT the code does (identifiers should do that)
- ❌ Creating docs files (.md) unless I explicitly ask
- ❌ Committing without my explicit request

---

## Communication Style

- Concise. No trailing summaries after diffs.
- State what you're doing in one sentence before tool calls.
- If blocked, say so — don't invent workarounds.
- Match response length to task: simple question → direct answer, no headers.
- Polish or English both fine; match the language I used.

---

## Project-Specific Overrides

> Add anything specific to THIS project below. The rules above are defaults.

- [e.g. "Never touch `legacy/` folder — frozen for compliance"]
- [e.g. "All DB changes must go through Alembic migrations"]
- [e.g. "Use `uv run pytest` not `pytest` directly"]

---

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues (`GrzegorzKowalikk/talk2type`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical label vocabulary, defaults unchanged (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
