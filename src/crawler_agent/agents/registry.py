"""Agent registry for managing multiple agents."""

from typing import Any

import structlog

from .base import Agent, AgentMessage, AgentRole, AgentTask


class AgentRegistry:
    """Registry for managing agents."""

    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.logger = structlog.get_logger()

    def register(self, agent: Agent) -> None:
        """Register an agent."""
        self.agents[agent.name] = agent
        self.logger.info("agent_registered", name=agent.name, role=agent.role.value)

    def unregister(self, name: str) -> None:
        """Unregister an agent."""
        self.agents.pop(name, None)

    def get(self, name: str) -> Agent | None:
        """Get an agent by name."""
        return self.agents.get(name)

    def get_by_role(self, role: AgentRole) -> list[Agent]:
        """Get all agents with a specific role."""
        return [a for a in self.agents.values() if a.role == role]

    def get_available(self) -> list[Agent]:
        """Get agents that are idle."""
        from .base import AgentState

        return [a for a in self.agents.values() if a.state == AgentState.IDLE]

    def get_with_capability(self, capability: str) -> list[Agent]:
        """Get agents with a specific capability."""
        return [a for a in self.agents.values() if capability in a.capabilities]

    async def broadcast(self, message: AgentMessage) -> None:
        """Broadcast a message to all agents except sender."""
        for agent in self.agents.values():
            if agent.name != message.sender:
                await agent.receive_message(message)

    async def route_message(self, message: AgentMessage) -> bool:
        """Route a message to a specific agent."""
        target = self.agents.get(message.recipient)
        if target:
            await target.receive_message(message)
            return True
        return False

    async def assign_task(self, task: AgentTask, agent_name: str | None = None) -> bool:
        """Assign a task to an agent."""
        if agent_name:
            agent = self.agents.get(agent_name)
            if agent:
                await agent.assign_task(task)
                return True
            return False

        # Auto-assign to best available agent
        available = self.get_available()
        if not available:
            return False

        # Simple heuristic: assign to agent with fewest pending tasks
        best = min(available, key=lambda a: len(a.pending_tasks))
        await best.assign_task(task)
        return True

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [agent.get_stats() for agent in self.agents.values()]

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        agents = list(self.agents.values())
        return {
            "total_agents": len(agents),
            "by_role": {
                role.value: len([a for a in agents if a.role == role]) for role in AgentRole
            },
            "idle": len([a for a in agents if a.state.value == "idle"]),
            "working": len([a for a in agents if a.state.value == "working"]),
            "agents": [a.get_stats() for a in agents],
        }
