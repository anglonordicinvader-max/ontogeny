# NeoCorpus embodiment contracts

NeoCorpus is Ontogeny's internal embodiment boundary. It is not a second simulator implementation and is not presented as a standalone public API in this release.

## Route

```text
Ontogeny Core → NeoCorpus → Embodiment Transport → Blender | MuJoCo
```

`EmbodimentRegistry` owns adapter registration. Each adapter exposes its type, availability, lifecycle, snapshot, observation, action, reset, joints, and sensors. `SimulationEmbodimentAdapter` extends the existing batch simulation backends and optionally binds to the live backend transport.

## Live transport

`backend/embodiment_transport.py` maintains one asynchronous state-only WebSocket channel per live simulator. It provides:

- backend-authoritative, allowlisted commands;
- correlated request IDs and timeouts;
- reconnect and disconnect handling;
- genuine health, world, controller, and telemetry snapshots;
- independent Blender and MuJoCo channels.

Electron viewport sockets remain dedicated to high-frequency image frames. Their controls route through the backend transport. This split preserves renderer ownership, prevents MuJoCo output from entering Blender, and avoids copying frame traffic through Ontogeny Core.

Lifecycle values are `unavailable`, `ready`, `running`, and `error`. Snapshots are derived from actual adapter or simulator state; NeoCorpus does not synthesize telemetry.

## Autonomous embodiment

The planner can emit an `embodiment_command` step containing an embodiment and allowlisted command. Execution resolves the existing NeoCorpus adapter and awaits the backend transport result. Manual controls use the same path. No movement is generated merely to animate the interface.

## Future standalone API

A future public NeoCorpus API should version these contracts rather than replace them. Remaining work includes authentication, capability negotiation, structured action schemas beyond the current allowlist, cancellation, telemetry backpressure, remote transports, physical-device safety policy, and compatibility guarantees.
