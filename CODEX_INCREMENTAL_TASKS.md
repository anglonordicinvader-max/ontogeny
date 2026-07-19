# CODEX_INCREMENTAL_TASKS.md

## Purpose

This file defines small, practical, low-risk tasks for Codex to implement in an isolated worktree. These tasks improve the demo experience and UI polish without touching critical architecture.

## Branch

`hackathon/codex-incremental`

## Worktree Path

`C:\Users\subur\Documents\New OpenCode Project\ontogeny-codex-worktree`

## Rules

1. **Work only inside the worktree** — never edit files outside this directory
2. **Inspect before modifying** — read the file, understand the context, then edit
3. **Obey the allowlist** — only touch files listed below
4. **Do not touch critical architecture** — see prohibited list
5. **Implement one task at a time** — complete, test, commit, then move to next
6. **Run tests after each task** — `python -m pytest tests/ -x -q` from worktree root
7. **Commit each task separately** — descriptive commit messages
8. **Stop if broader changes seem needed** — do not broaden scope
9. **Never merge or push** — unless explicitly instructed
10. **Summarize every changed file** — list files modified in commit message

## Allowed Files and Directories

```
desktop/renderer/src/components/DemoPanel.tsx
desktop/renderer/src/components/CrawlerPanel.tsx
desktop/renderer/src/components/StatusBar.tsx
desktop/renderer/src/components/ActivityTimeline.tsx
desktop/renderer/src/components/SettingsPanel.tsx
desktop/renderer/src/components/BlenderPanel.tsx
desktop/renderer/src/components/MuJoCoPanel.tsx
desktop/renderer/src/components/KnowledgeGraph.tsx
desktop/renderer/src/components/Panel.tsx
desktop/renderer/src/types/index.ts
desktop/renderer/src/index.css
desktop/renderer/src/hooks/useWebSocket.ts
backend/demo_fixtures.py
backend/main.py
DEMO_GUIDE.md
```

## Prohibited Files and Directories

```
src/crawler_agent/cognitive/          # Core cognitive architecture
src/crawler_agent/crawlers/           # Acquisition engines
src/crawler_agent/crawlers/acquisition/  # Knowledge Acquisition System
src/crawler_agent/main.py             # CLI entry point
src/crawler_agent/persistence.py      # State persistence
backend/agent_manager.py              # Agent lifecycle
backend/blender_simulation.py         # Blender integration
backend/mujoco_simulation.py          # MuJoCo integration
desktop/main/index.js                 # Electron main process
desktop/preload/                      # Electron preload
*.py                                  # Any Python file not in allowlist
pyproject.toml                        # Project config
package.json                          # Root package config
tests/                                # Test files (read-only for verification)
data/                                 # Data directory
.github/                              # CI/CD
```

## Selected Tasks

### Task 1: Demo Reset Keyboard Shortcut

**Goal:** Add `Ctrl/Cmd+Shift+R` as a keyboard shortcut to reset the demo from anywhere in the UI.

**Files to modify:**
- `desktop/renderer/src/App.tsx` — add keyboard event listener
- `DEMO_GUIDE.md` — document the shortcut

**Acceptance criteria:**
- Pressing `Ctrl/Cmd+Shift+R` triggers demo reset
- Works from any tab
- Does not conflict with browser refresh
- Reset button in DemoPanel still works

### Task 2: Evidence Copy-to-Clipboard

**Goal:** Add a copy button to each evidence card in the DemoPanel that copies the citation as formatted text.

**Files to modify:**
- `desktop/renderer/src/components/DemoPanel.tsx`

**Acceptance criteria:**
- Each evidence card has a small copy icon button
- Clicking copies: `"Title" — Author, Source (Confidence: XX%)`
- Button shows brief "Copied!" feedback
- Uses `navigator.clipboard.writeText()`

### Task 3: Export Demo Summary

**Goal:** Add an "Export Summary" button at the end of the demo that downloads a Markdown summary of the session.

**Files to modify:**
- `desktop/renderer/src/components/DemoPanel.tsx`

**Acceptance criteria:**
- "Export Summary" button appears in the Session Summary panel
- Downloads a `.md` file with: goal, evidence list, memory writes, knowledge graph stats, reflection, Maldoror proposal
- Filename: `ontogeny-demo-summary-YYYY-MM-DD.md`
- Uses `Blob` + `URL.createObjectURL` for download

### Task 4: Simulator-Offline Status Message

**Goal:** Show a clear status message in Blender and MuJoCo panels when the respective simulator is not connected.

**Files to modify:**
- `desktop/renderer/src/components/BlenderPanel.tsx`
- `desktop/renderer/src/components/MuJoCoPanel.tsx`

**Acceptance criteria:**
- If WebSocket is not connected, show a centered message: "Blender is not connected. Install Blender 5.2 and restart to enable physics simulation."
- Same pattern for MuJoCo: "MuJoCo is not connected. Run `pip install mujoco>=3.10` and restart to enable robotics simulation."
- Message is styled consistently with the rest of the UI
- Does not show when connected

## Test Commands

```bash
# From worktree root
python -m pytest tests/ -x -q                    # Quick test run
python -m pytest tests/test_acquisition.py -x -q  # Acquisition tests
cd desktop/renderer && npx tsc --noEmit           # TypeScript check
cd desktop/renderer && npx vite build             # Production build
```

## Build Commands

```bash
cd desktop/renderer && npm run build    # Build renderer
cd desktop && npm run package           # Package Electron app (Windows)
```

## Codex Prompt

```
You are working in the Ontogeny hackathon Codex worktree at:
C:\Users\subur\Documents\New OpenCode Project\ontogeny-codex-worktree

IMPORTANT RULES:
1. Work ONLY inside this worktree directory
2. Read CODEX_INCREMENTAL_TASKS.md first
3. Only touch files in the allowlist
4. Never touch files in the prohibited list
5. Implement ONE task at a time
6. Run tests after each task: python -m pytest tests/ -x -q
7. Commit each task separately with a descriptive message
8. Stop if you need to make broader architectural changes
9. Never merge branches or push to remote
10. List every changed file in your commit message

START: Read CODEX_INCREMENTAL_TASKS.md, then implement Task 1.
After completing Task 1, stop and report what you did.
```

## Acceptance Criteria

Each task must:
- Compile without TypeScript errors (if frontend)
- Pass existing tests (if backend)
- Be visually correct in the UI
- Have a descriptive commit message
- Not break any existing functionality
- Be narrow in scope (1-3 files modified)

## Integration Workflow

After Codex completes its work:

```bash
# 1. Review Codex commits
cd "C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent"
git log hackathon/codex-incremental --oneline

# 2. Inspect each diff
git diff master..hackathon/codex-incremental

# 3. Run tests in the worktree
cd "C:\Users\subur\Documents\New OpenCode Project\ontogeny-codex-worktree"
python -m pytest tests/ -x -q

# 4. Cherry-pick approved commits (one at a time)
git cherry-pick <commit-hash>

# 5. Run full test suite after merge
python -m pytest tests/ -v

# 6. Clean up worktree when done
cd "C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent"
git worktree remove "C:\Users\subur\Documents\New OpenCode Project\ontogeny-codex-worktree"
git branch -d hackathon/codex-incremental
```

## Source Attribution Record

| Task | Benefit | Commit | Files | Tests | Date | Status |
|------|---------|--------|-------|-------|------|--------|
| Task 1 | Keyboard shortcut for demo reset | (pending) | App.tsx, DEMO_GUIDE.md | (pending) | (pending) | Not started |
| Task 2 | Copy evidence citations | (pending) | DemoPanel.tsx | (pending) | (pending) | Not started |
| Task 3 | Export demo summary as Markdown | (pending) | DemoPanel.tsx | (pending) | (pending) | Not started |
| Task 4 | Simulator-offline status messages | (pending) | BlenderPanel.tsx, MuJoCoPanel.tsx | (pending) | (pending) | Not started |
