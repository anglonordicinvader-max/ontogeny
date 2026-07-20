from types import SimpleNamespace

import pytest

from crawler_agent.main import interactive_mode


class _FakeAgent:
    proxy_pool = SimpleNamespace(get_stats=lambda: {"healthy": 0, "total": 0})

    async def get_status(self):
        return {
            "state": "idle",
            "iteration": 3,
            "uptime_seconds": 12.0,
            "goals": {"active": 1, "total": 2, "drives": {"curiosity": 0.5}},
            "plans": {"total": 1},
            "memory": {
                "working_memory_size": 4,
                "episodic_count": 3,
                "semantic_count": 2,
                "procedural_count": 1,
            },
            "knowledge_graph": {"concepts": 7},
            "self_reflection": {"reflections": 2},
            "maldoror": {"current_version": "v1"},
            "backend": {
                "routine_backend": "routine",
                "code_backend": "code",
                "reasoning_backend": "reasoning",
                "modifier_backend": "maldoror",
            },
            "embodiment": {"blender": True, "mujoco": True},
            "embodiment_details": {
                "blender": {"lifecycle": "ready"},
                "mujoco": {"lifecycle": "running"},
            },
            "crawlers": ["arxiv"],
            "current_plan": None,
        }


@pytest.mark.asyncio
async def test_status_reflects_current_architecture(monkeypatch, capsys):
    commands = iter(("status", "quit"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(commands))

    await interactive_mode(_FakeAgent(), SimpleNamespace())

    output = capsys.readouterr().out
    assert "1 active / 2 total" in output
    assert "NeoCorpus" in output
    assert "maldoror" in output
    assert "4 working / 3 episodic / 2 semantic / 1 procedural" in output


@pytest.mark.asyncio
async def test_embodiment_command_reports_registered_backends(monkeypatch, capsys):
    commands = iter(("embodiment", "quit"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(commands))

    await interactive_mode(_FakeAgent(), SimpleNamespace())

    output = capsys.readouterr().out
    assert "NeoCorpus Embodiment" in output
    assert "Blender" in output
    assert "Mujoco" in output
    assert output.count("available") >= 2
    assert "ready" in output
    assert "running" in output
