# Ontogeny Demo Guide

## What Is Ontogeny?

Ontogeny is a proto-AGI cognitive agent that autonomously acquires knowledge, reasons about evidence, and recursively improves its own capabilities. It operates in continuous cognitive cycles: setting goals, planning actions, acquiring evidence from external sources, writing to persistent memory, reflecting on outcomes, and proposing safe self-improvements.

## What Makes It Distinct

- **Integrated cognitive loop**: Goal → Planning → Knowledge Acquisition → Evidence → Memory → Reasoning → Reflection → Self-Improvement — all wired together in a single autonomous cycle
- **Knowledge Acquisition System**: 30 specialized engines with source scoring, evidence validation, claim tracking, and provenance — not just web scraping
- **Maldoror**: A QLoRA fine-tuned model specialized in recursive self-modification, with 6-phase training pipeline, quality gates, and rollback safety
- **MuJoCo robotics**: Real-time physics simulation with TOCABI (33-DOF) and Unitree G1 (29-DOF) humanoids
- **Four-tier hybrid LLM routing**: Automatic task-based routing between routine, code, reasoning, and self-modification models

## Architecture Overview

```
Goal → Planning → Knowledge Acquisition → Evidence → Memory → Reasoning → Reflection → Self-Improvement
```

Each component is a real, tested subsystem:
- **30 Acquisition Engines** — GitHub, ArXiv, Semantic Scholar, HuggingFace, etc.
- **10-module Knowledge Acquisition System** — evidence store, source scorer, claim validator, revalidation
- **5-layer Memory** — working, episodic, semantic, procedural, identity
- **6-phase Maldoror Pipeline** — self-training, contrastive, population, curriculum, adversarial, architecture
- **MuJoCo Physics** — TOCABI + Unitree G1 with standing/walking controllers
- **307 tests** — all passing

## How to Install

```bash
# Clone and install
git clone https://github.com/anglonordicinvader-max/ontogeny.git
cd ontogeny
pip install -e .

# Install desktop UI dependencies
cd desktop/renderer && npm install && cd ../..
```

## How to Launch

### Desktop UI (recommended)
```bash
cd desktop && npx electron .
```

### Demo Mode
```bash
cd desktop && npx electron . --dev
# In the UI, click the "Demo" tab in the sidebar, then click "Start Demo"
```

### CLI
```bash
python -m crawler_agent.main --demo
```

## How to Enter Demo Mode

1. Launch the desktop UI
2. Click the **Demo** tab in the sidebar (first tab, play icon)
3. Click **Start Demo**
4. Watch the guided walkthrough, or click **Next Step** to advance manually
5. Use **Auto-play** to advance automatically every 2 seconds

## How to Reset Demo Mode

Click the **Reset** button in the Demo panel, or use the command palette:
- Press `Ctrl/Cmd+K`
- Type "reset demo"

Demo mode uses a separate session namespace. Resetting clears demo state without affecting normal agent data.

## Expected Demo Duration

- **Auto-play**: ~16 seconds (8 steps × 2 seconds)
- **Manual**: 2-5 minutes depending on narration
- **Recorded demo**: 3-5 minutes with script

## Optional Dependencies

| Dependency | Required? | What it enables |
|------------|-----------|-----------------|
| Python 3.11+ | Yes | Backend, cognitive systems |
| Ollama | No (fixtures used) | Live LLM routing |
| MuJoCo 3.10+ | No | Robotics simulation |
| Blender 5.2 | No | Physics sandbox |
| Docker | No | Code execution sandbox |
| Node.js 18+ | Yes | Desktop UI |

## Known Limitations

- Demo mode uses **controlled demonstration fixtures**, not live autonomous execution
- MuJoCo and Blender panels show status but may not connect without the respective software installed
- The Knowledge Acquisition System is fully implemented but currently decoupled from the orchestrator — demo shows fixture-based evidence
- Maldoror proposals are **dry-run only** — no actual source code is modified during demo
- WebSocket connection requires the Python backend to be running (started automatically by Electron)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "UI Disconnected" in status bar | Backend not running. Restart the app. |
| Demo tab shows nothing | Ensure backend is running. Check `http://127.0.0.1:<port>/api/health` |
| MuJoCo panel shows disconnected | MuJoCo not installed. Run `pip install mujoco>=3.10` |
| Blender panel shows placeholder | Blender not installed or not at expected path |
| Build fails | Run `cd desktop/renderer && npm install` |

## Which Portions Were Implemented Using Codex

See `CODEX_INCREMENTAL_TASKS.md` for the list of practical features implemented by Codex in the isolated worktree. Codex contributions are limited to UI improvements and small functional additions — the core architecture, cognitive systems, and Knowledge Acquisition System were implemented by the primary developer.
