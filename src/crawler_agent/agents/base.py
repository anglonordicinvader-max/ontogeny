"""Base agent class for multi-agent system."""

import asyncio
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from typing import Any

import structlog


class AgentRole(StrEnum):
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"
    PLANNER = "planner"
    CRITIC = "critic"
    COORDINATOR = "coordinator"


class AgentState(StrEnum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Message between agents."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    sender: str = ""
    recipient: str = ""
    content: str = ""
    msg_type: str = "info"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentTask:
    """Task assigned to an agent."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    assigned_to: str = ""
    status: str = "pending"
    result: Any = None
    dependencies: list[str] = field(default_factory=list)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


class Agent:
    """Base agent class."""

    def __init__(
        self,
        name: str,
        role: AgentRole,
        api_key: str = "",
        model: str = "gpt-4-turbo-preview",
        api_base: str | None = None,
    ):
        self.name = name
        self.role = role
        self.state = AgentState.IDLE
        self.logger = structlog.get_logger()

        self.api_key = api_key
        self.model = model
        self.api_base = api_base

        self._inbox: list[AgentMessage] = []
        self._outbox: list[AgentMessage] = []
        self._tasks: list[AgentTask] = []
        self._capabilities: list[str] = []
        self._memory: list[dict[str, Any]] = []

        self._on_message: Callable | None = None

    @property
    def capabilities(self) -> list[str]:
        return self._capabilities.copy()

    @property
    def inbox(self) -> list[AgentMessage]:
        return self._inbox.copy()

    @property
    def pending_tasks(self) -> list[AgentTask]:
        return [t for t in self._tasks if t.status == "pending"]

    async def receive_message(self, message: AgentMessage) -> None:
        """Receive a message from another agent."""
        self._inbox.append(message)
        self.logger.debug(
            "message_received",
            sender=message.sender,
            type=message.msg_type,
        )

    async def send_message(
        self,
        recipient: str,
        content: str,
        msg_type: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Create a message to send."""
        msg = AgentMessage(
            sender=self.name,
            recipient=recipient,
            content=content,
            msg_type=msg_type,
            metadata=metadata or {},
        )
        self._outbox.append(msg)
        return msg

    async def assign_task(self, task: AgentTask) -> None:
        """Assign a task to this agent."""
        task.assigned_to = self.name
        self._tasks.append(task)
        self.logger.info("task_assigned", task_id=task.id, desc=task.description[:50])

    async def think(self, prompt: str) -> str:
        """Use LLM to reason about something."""
        from ..processing.llm import LLMProcessor

        if not self.api_key and not self.api_base:
            return f"[{self.name}] No LLM configured - thinking about: {prompt[:100]}"

        llm = LLMProcessor(
            api_key=self.api_key or "ollama",
            model=self.model,
            api_base=self.api_base,
        )
        context = self._build_context()
        response = await llm.answer_query(prompt, context)
        return response

    def _build_context(self) -> str:
        """Build context from memory and recent messages."""
        parts = []

        if self._memory:
            parts.append("Recent memory:")
            for m in self._memory[-5:]:
                parts.append(f"  - {m.get('content', '')[:100]}")

        if self._inbox:
            parts.append("Recent messages:")
            for msg in self._inbox[-5:]:
                parts.append(f"  [{msg.sender}]: {msg.content[:100]}")

        return "\n".join(parts) if parts else "No context available."

    async def process_message(self, message: AgentMessage) -> AgentMessage | None:
        """Process an incoming message and optionally respond."""
        self._memory.append(
            {
                "type": "message",
                "sender": message.sender,
                "content": message.content[:200],
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return None

    async def execute_task(self, task: AgentTask) -> Any:
        """Execute a task. Override in subclasses."""
        task.status = "completed"
        task.result = f"{self.name} completed: {task.description}"
        return task.result

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "messages_received": len(self._inbox),
            "messages_sent": len(self._outbox),
            "tasks_total": len(self._tasks),
            "tasks_pending": len(self.pending_tasks),
            "memory_size": len(self._memory),
            "capabilities": self._capabilities,
        }
