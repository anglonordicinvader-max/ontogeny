# Ontogeny

Ontogeny is a local-first cognitive architecture and research workstation. It coordinates goals, planning, knowledge acquisition, persistent memory, a live Knowledge Graph, reflection, recursive improvement through Maldoror, and embodiment through NeoCorpus.

The desktop application is an operational view into backend state. It does not invent thoughts, telemetry, or simulator output. Blender and MuJoCo retain independent renderer lifecycles while NeoCorpus supplies their shared cognitive boundary.

## Architecture

```text
Ontogeny Core
├── Goals and planning
├── Persistent memory
├── Knowledge Graph
├── Reflection and metacognition
├── Model routing
├── Maldoror recursive improvement
└── NeoCorpus
    ├── Embodiment transport ── Blender
    └── Embodiment transport ── MuJoCo
```

The live embodiment route is backend-authoritative:

```text
Planning → Goals → Memory → Reflection → Maldoror
         → NeoCorpus → Embodiment Transport → Blender | MuJoCo
```

Manual controls use the same allowlisted transport. High-frequency image frames travel directly from each simulator to its own Electron viewport, preventing renderer crossover and keeping frame traffic out of the cognitive channel.

## Current systems

- **Ontogeny Core** — autonomous cognitive cycles, goal management, planning, execution, learning, and status reporting.
- **Maldoror** — the existing recursive-improvement pipeline with evaluation and rollback safeguards.
- **Persistent Memory** — working, episodic, semantic, procedural, and identity-oriented memory systems.
- **Knowledge Graph** — genuine extracted concepts and relations, durable local storage, revisioned snapshots, and live Electron synchronization.
- **NeoCorpus** — a registry and adapter contract for Blender, MuJoCo, and future embodiments.
- **Blender** — genuine Blender-rendered frames plus a five-world workspace: Research Lab, Small House, Warehouse, Outdoor Test Area, and Procedural Sandbox.
- **MuJoCo** — genuine physics, telemetry, deterministic reset, immediate freeze, walking/turn commands, and a repeatable demo sequence.
- **Electron** — monochrome native-AI research workstation UI driven by backend WebSocket status and events.
- **Terminal CLI** — interactive, autonomous, and demonstration entry points with subsystem and embodiment status.
- **Demo Mode** — an explicitly controlled presentation session; fixture-derived demo state is isolated from live agent data.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- Windows x64 for the packaged desktop demonstration
- Blender 5.2, or a compatible executable selected with `BLENDER_EXE`
- MuJoCo dependencies from `backend/requirements-ui.txt`
- Licensed simulator model assets (not redistributed in Git)

Ollama, Docker, and GPU tooling are optional and enable their corresponding model, sandbox, and training paths.

## Install

```powershell
git clone https://github.com/anglonordicinvader-max/ontogeny.git
cd ontogeny
python -m pip install -e ".[dev]"
python -m pip install -r backend/requirements-ui.txt
cd desktop
npm ci
```

The simulator assets expected by the demonstration are documented in [PACKAGING.md](PACKAGING.md).

## Run

### Terminal

From the repository root:

```powershell
python -m crawler_agent.main
python -m crawler_agent.main --autonomous 10
python -m crawler_agent.main --demo
```

The `embodiment` interactive command reports NeoCorpus registration and live adapter state.

### Desktop development

```powershell
cd desktop
npm run dev
```

Electron starts the backend and simulator processes. Blender remains an external installation; MuJoCo is run from Python in development and from its packaged executable in a release build.

## Demonstration

Open **Demo** and choose **Start Demo** for the controlled cognitive walkthrough. Blender and MuJoCo panels expose live simulator state separately. MuJoCo’s **Demo** control runs a deterministic physical sequence while manual Stand, Walk, Freeze, Reset, speed, and turning controls remain available.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the operator sequence and truth boundaries.

## Packaging

From `desktop/`:

```powershell
npm run package:demo
```

This validates assets, vendors Blender’s Python WebSocket dependency, builds the backend and MuJoCo executables with PyInstaller, builds Electron, and produces a Windows portable artifact in `desktop/dist/`.

Blender itself is intentionally not redistributed. See [PACKAGING.md](PACKAGING.md) for prerequisites, limitations, and validation commands.

## Validation

```powershell
python -m pytest tests -q
python -m ruff check backend src tests
python -m ruff format --check backend src tests
cd desktop
npm run typecheck
npm run build
npm run lint
```

Simulator smoke checks:

```powershell
python scripts/smoke_blender_ws.py
python scripts/smoke_mujoco_ws.py
```

These checks require the respective simulator process and assets.

## Configuration

Copy `.env.example` to `.env` for local overrides. Notable runtime variables include:

- `BLENDER_EXE` — compatible Blender executable path.
- `ONTOGENY_BLENDER_PORT` — Blender WebSocket port; default `8766`.
- `ONTOGENY_MUJOCO_PORT` — MuJoCo WebSocket port; default `8767`.
- Model-routing and persistence settings defined in `src/crawler_agent/config/settings.py`.

Do not commit credentials or private model assets.

## Documentation

- [DEMO_GUIDE.md](DEMO_GUIDE.md) — demonstration operation and troubleshooting.
- [PACKAGING.md](PACKAGING.md) — reproducible Windows packaging.
- [NEOCORPUS.md](NEOCORPUS.md) — embodiment contracts, transport, and future API work.
- [DEMO_RECORDING_SCRIPT.md](DEMO_RECORDING_SCRIPT.md) — recording sequence.

## Known release boundaries

- Autonomous embodiment is a live transport capability, not a claim that every planner/model will independently produce safe movement commands. Commands execute only when genuine backend planning supplies an allowlisted embodiment action.
- Demo Mode uses labeled controlled fixtures for presentation reliability. It never substitutes fixture data for live simulator frames or telemetry.
- Blender must be installed separately and its executable must be discoverable.
- Simulator model assets remain external because of size and upstream licensing.
- Maldoror’s destructive self-modification paths remain guarded; demonstration proposals are dry-run unless the existing safety gates explicitly authorize execution.

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).
