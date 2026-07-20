# Ontogeny Build Week packaging

The desktop demonstration uses three independent local processes:

- `ontogeny-backend.exe` — Ontogeny Core and the Electron bridge
- Blender 5.2 — genuine Blender scene rendering through `blender_simulation.py`
- `ontogeny-mujoco.exe` — genuine MuJoCo physics and telemetry

## Prerequisites

- Windows x64
- Python 3.11 or newer with `backend/requirements-ui.txt`
- Node.js and npm
- Blender 5.2 installed, or `BLENDER_EXE` set to a compatible Blender executable
- TOCABI meshes at `data/blender/models/tocabi/combined/meshes`
- Unitree G1 MJCF assets at `data/mujoco/models/unitree_g1`
- Official application assets under `desktop/renderer/public/branding`

The model assets are intentionally external to Git because of their size and upstream licensing.
The TOCABI source used by this workspace is <https://github.com/cadop/tocabi>.

## Reproducible demo build

From `desktop/`:

```powershell
npm ci
npm run package:demo
```

The command validates required assets, vendors the Blender WebSocket dependency, builds both
Python executables with PyInstaller, builds the renderer, and creates the portable Electron
artifact under `desktop/dist/`.

The packaging build uses the official Ontogeny PNG for Electron, executable, portable, and
installer branding. The renderer copies the supplied Ontogeny and Maldoror assets without
redrawing them.

## Validation

Before distributing an artifact, run from the repository root:

```powershell
python -m pytest tests -q
python -m ruff check backend src tests
python -m ruff format --check backend src tests
cd desktop
npm run verify
```

Then launch the portable artifact and confirm backend health, Blender world switching,
MuJoCo Walk/Freeze/Reset, live telemetry, and the application icon.

## Runtime limitation

Blender is not redistributed inside the Electron artifact. The packaged application discovers
the standard Blender 5.2 installation or uses `BLENDER_EXE`. This avoids silently repackaging
Blender and keeps its licensing and installation lifecycle explicit.

The TOCABI and Unitree assets are also not fetched automatically. Packaging fails early when
required resources are missing rather than producing an artifact with placeholder rendering.

If Electron Builder reports an error while reopening `Ontogeny.exe` for ASAR-integrity metadata,
check endpoint-security or antivirus policy. Do not commit `disableAsarIntegrity`; allow the build
tool to update the executable and retain the default integrity metadata for release artifacts.
