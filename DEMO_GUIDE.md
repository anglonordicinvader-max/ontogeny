# Ontogeny Demo Guide

## Purpose

The Build Week demonstration presents Ontogeny as a live cognitive research workstation. It distinguishes controlled presentation data from live cognition and never substitutes placeholders for Blender or MuJoCo output.

## Before presenting

1. Install the Python and desktop dependencies from `README.md`.
2. Confirm Blender 5.2 is installed or set `BLENDER_EXE`.
3. Confirm the TOCABI and Unitree G1 assets described in `PACKAGING.md` are present.
4. From `desktop/`, run `npm run dev` for development or launch the packaged portable executable.
5. Wait for the status bar to report the backend connection.
6. Open Blender and MuJoCo once and confirm each panel reports its own live connection.

## Recommended sequence

1. Open **Demo** and select **Start Demo**.
2. Advance through the cognitive stages manually, or enable auto-play.
3. Open **Knowledge** to show backend-derived concepts and relations. Empty state means no live knowledge has been ingested; it is not filled artificially.
4. Open **Blender**, select a world, and show that only the embodiment reloads.
5. Open **MuJoCo**, press **Reset**, **Walk**, then **Freeze**. Freeze should stop physics immediately; Reset should restore the deterministic initial pose.
6. Use MuJoCo **Demo** for the repeatable walk, stop, turn, return, and reset sequence.
7. Open **Cognitive** or **Activity** to show genuine backend status/events.

## Demo Mode truth boundary

The cognitive walkthrough uses labeled controlled fixtures in an isolated demo session for repeatability. Live Blender frames, MuJoCo frames, physics telemetry, world changes, backend health, and autonomous embodiment results are never fixtures. Maldoror proposals shown in the controlled walkthrough are dry-run artifacts.

Autonomous embodiment occurs only when a genuine backend plan produces an allowlisted `embodiment_command`. The interface does not invent a plan or movement.

## Reset

- Demo panel: **Reset**.
- Command palette: `Ctrl/Cmd+K`, then **Reset Demo**.
- Global shortcut: `Ctrl/Cmd+Shift+R`.
- MuJoCo: **Reset** affects only the physics embodiment.
- Blender world changes affect only the Blender embodiment.

## Troubleshooting

| Symptom | Check |
|---|---|
| UI disconnected | Restart Electron and inspect the backend process output. |
| Blender disconnected | Verify `BLENDER_EXE`, Blender version, port 8766, and vendored `websockets`. |
| Blender has no image | Check the Blender render error in process output; no fallback image is used. |
| MuJoCo disconnected | Install `backend/requirements-ui.txt`, verify assets, and check port 8767. |
| Walk has no visible motion | Reset, select Walk, and verify telemetry controller mode is `walk`. |
| Freeze does not stop | Verify the command result and controller mode `freeze`; capture logs as a regression. |
| World switch remains loading | Verify the selected ID is in the live `world_catalog`. |
| Knowledge Graph is empty | Run live cognition/ingestion; the UI intentionally does not fabricate nodes. |

## Expected duration

- Controlled walkthrough: roughly 20 seconds in auto-play.
- Full narrated cognitive and embodiment demonstration: 3–5 minutes.
