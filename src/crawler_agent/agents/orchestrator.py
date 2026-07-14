"""Multi-agent orchestrator for coordinating multiple agents."""

import asyncio
from typing import Any

import structlog

from .base import Agent, AgentRole, AgentState, AgentMessage, AgentTask
from .registry import AgentRegistry
from .specialized import (
    ResearcherAgent,
    CoderAgent,
    AnalystAgent,
    PlannerAgent,
    CriticAgent,
    DataCleanerAgent,
    SummarizerAgent,
    OptimizerAgent,
    ExplorerAgent,
    SynthesizerAgent,
)


class MultiAgentOrchestrator:
    """Orchestrates multiple specialized agents."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4-turbo-preview",
        api_base: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self.registry = AgentRegistry()
        self.logger = structlog.get_logger()

        self._task_counter = 0
        self._message_log: list[AgentMessage] = []
        self._results: dict[str, Any] = {}

        self._init_default_agents()

    def _init_default_agents(self) -> None:
        """Initialize default set of agents."""
        kwargs = {
            "api_key": self.api_key,
            "model": self.model,
            "api_base": self.api_base,
        }

        self.registry.register(ResearcherAgent(name="Researcher", **kwargs))
        self.registry.register(CoderAgent(name="Coder", **kwargs))
        self.registry.register(AnalystAgent(name="Analyst", **kwargs))
        self.registry.register(PlannerAgent(name="Planner", **kwargs))
        self.registry.register(CriticAgent(name="Critic", **kwargs))
        self.registry.register(DataCleanerAgent(name="DataCleaner", **kwargs))
        self.registry.register(SummarizerAgent(name="Summarizer", **kwargs))
        self.registry.register(OptimizerAgent(name="Optimizer", **kwargs))
        self.registry.register(ExplorerAgent(name="Explorer", **kwargs))
        self.registry.register(SynthesizerAgent(name="Synthesizer", **kwargs))

        self.logger.info("default_agents_initialized", count=10)

    def set_crawlers(self, crawlers: dict[str, Any]) -> None:
        """Set crawlers for the researcher agent."""
        researcher = self.registry.get("Researcher")
        if researcher and isinstance(researcher, ResearcherAgent):
            researcher.set_crawlers(crawlers)

    def set_sandbox(self, sandbox) -> None:
        """Set code sandbox for the coder agent."""
        coder = self.registry.get("Coder")
        if coder and isinstance(coder, CoderAgent):
            coder.set_sandbox(sandbox)

    async def run_task(
        self,
        description: str,
        agent_name: str | None = None,
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a task, optionally assigning to a specific agent."""
        self._task_counter += 1
        task = AgentTask(
            id=f"task_{self._task_counter}",
            description=description,
            dependencies=dependencies or [],
        )

        if agent_name:
            assigned = await self.registry.assign_task(task, agent_name)
            if not assigned:
                return {"error": f"Agent '{agent_name}' not found or busy"}
        else:
            assigned = await self.registry.assign_task(task)
            if not assigned:
                return {"error": "No available agents"}

        agent = self.registry.get(task.assigned_to)
        if not agent:
            return {"error": f"Agent {task.assigned_to} not found"}

        self.logger.info(
            "task_started",
            task_id=task.id,
            agent=task.assigned_to,
            desc=description[:50],
        )

        try:
            result = await agent.execute_task(task)
            self._results[task.id] = result

            # Process outbox messages
            while agent._outbox:
                msg = agent._outbox.pop(0)
                await self.registry.route_message(msg)
                self._message_log.append(msg)

            return {
                "task_id": task.id,
                "agent": task.assigned_to,
                "result": result,
            }

        except Exception as e:
            self.logger.error("task_failed", task_id=task.id, error=str(e))
            return {"error": str(e), "task_id": task.id}

    async def run_pipeline(
        self,
        stages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run a multi-stage pipeline with different agents.

        stages: [{"agent": "Researcher", "task": "..."}, ...]
        """
        results = []
        context = ""

        for i, stage in enumerate(stages):
            agent_name = stage.get("agent")
            task_desc = stage.get("task", "")

            if context:
                task_desc = f"{task_desc}\n\nContext from previous stages:\n{context}"

            self.logger.info("pipeline_stage", stage=i + 1, agent=agent_name)

            result = await self.run_task(task_desc, agent_name)
            results.append(result)

            # Build context for next stage
            if "result" in result:
                result_str = str(result["result"])[:500]
                context += f"\nStage {i + 1} ({agent_name}): {result_str}"

        return {
            "stages": len(stages),
            "results": results,
            "final_context": context,
        }

    async def collaborative_solve(
        self,
        problem: str,
        agents: list[str] | None = None,
    ) -> dict[str, Any]:
        """Have multiple agents collaborate on a problem."""
        if not agents:
            agents = ["Researcher", "Analyst", "Coder", "Critic"]

        results = {}
        discussion = [f"Problem: {problem}"]

        for agent_name in agents:
            agent = self.registry.get(agent_name)
            if not agent:
                continue

            context = "\n".join(discussion[-5:])
            task = AgentTask(
                id=f"collab_{self._task_counter}",
                description=f"{problem}\n\nDiscussion so far:\n{context}",
            )
            await agent.assign_task(task)

            result = await agent.execute_task(task)
            results[agent_name] = result

            response = str(result)[:300] if result else "No response"
            discussion.append(f"[{agent_name}]: {response}")

            # Process outbox
            while agent._outbox:
                msg = agent._outbox.pop(0)
                await self.registry.route_message(msg)
                self._message_log.append(msg)

        # Get critic's final assessment
        critic = self.registry.get("Critic")
        if critic:
            final_task = AgentTask(
                id=f"final_{self._task_counter}",
                description=f"Final assessment of collaborative solution to: {problem}\n\nDiscussion:\n" + "\n".join(discussion),
            )
            await critic.assign_task(final_task)
            final_result = await critic.execute_task(final_task)
            results["final_assessment"] = final_result

        return {
            "problem": problem,
            "participants": agents,
            "results": results,
            "discussion": discussion,
        }

    def get_status(self) -> dict[str, Any]:
        """Get orchestrator status."""
        return {
            "agents": self.registry.list_agents(),
            "total_tasks": self._task_counter,
            "messages_logged": len(self._message_log),
            "results_stored": len(self._results),
            "registry": self.registry.get_stats(),
        }
