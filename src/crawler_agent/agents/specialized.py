"""Specialized agent implementations."""

from typing import Any

from .base import Agent, AgentRole, AgentTask, AgentMessage


class ResearcherAgent(Agent):
    """Agent specialized in research and information gathering."""

    def __init__(self, name: str = "Researcher", **kwargs):
        super().__init__(name=name, role=AgentRole.RESEARCHER, **kwargs)
        self._capabilities = [
            "web_search",
            "paper_analysis",
            "source_identification",
            "fact_checking",
            "trend_analysis",
        ]
        self._crawlers: dict[str, Any] = {}

    def set_crawlers(self, crawlers: dict[str, Any]) -> None:
        """Set available crawlers."""
        self._crawlers = crawlers

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a research task."""
        self.state = "working"

        results = {
            "task_id": task.id,
            "findings": [],
            "sources": [],
            "confidence": 0.5,
        }

        if not self._crawlers:
            results["error"] = "No crawlers available"
            return results

        query = task.description
        for name, crawler in self._crawlers.items():
            try:
                async for result in crawler.search(query, limit=5):
                    results["findings"].append({
                        "title": result.title,
                        "url": result.url,
                        "source": name,
                    })
                    results["sources"].append(result.url)
            except Exception:
                continue

        results["confidence"] = min(1.0, len(results["findings"]) / 10)

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Planner",
            content=f"Research complete: {len(results['findings'])} findings",
            msg_type="research_result",
            metadata=results,
        )

        return results


class CoderAgent(Agent):
    """Agent specialized in code writing and execution."""

    def __init__(self, name: str = "Coder", **kwargs):
        super().__init__(name=name, role=AgentRole.CODER, **kwargs)
        self._capabilities = [
            "python",
            "bash",
            "code_review",
            "debugging",
            "testing",
            "refactoring",
        ]
        self._sandbox = None

    def set_sandbox(self, sandbox) -> None:
        """Set the code sandbox for execution."""
        self._sandbox = sandbox

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a coding task."""
        self.state = "working"

        results = {
            "task_id": task.id,
            "code": "",
            "output": "",
            "success": False,
        }

        if not self._sandbox:
            results["error"] = "No sandbox available"
            return results

        prompt = f"Write Python code for: {task.description}"
        code = await self.think(prompt)
        results["code"] = code

        exec_result = await self._sandbox.execute_code(code, language="python")
        results["output"] = exec_result.output
        results["success"] = exec_result.success

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Critic",
            content=f"Code executed: {'success' if exec_result.success else 'failed'}",
            msg_type="code_result",
            metadata=results,
        )

        return results


class AnalystAgent(Agent):
    """Agent specialized in data analysis and pattern recognition."""

    def __init__(self, name: str = "Analyst", **kwargs):
        super().__init__(name=name, role=AgentRole.ANALYST, **kwargs)
        self._capabilities = [
            "data_analysis",
            "pattern_recognition",
            "anomaly_detection",
            "trend_identification",
            "visualization",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute an analysis task."""
        self.state = "working"

        prompt = f"""Analyze the following and identify key patterns, trends, and insights:
{task.description}

Provide:
1. Key findings
2. Patterns detected
3. Anomalies (if any)
4. Recommendations
"""
        analysis = await self.think(prompt)

        results = {
            "task_id": task.id,
            "analysis": analysis,
            "patterns": [],
            "confidence": 0.6,
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Planner",
            content=f"Analysis complete for: {task.description[:50]}",
            msg_type="analysis_result",
            metadata=results,
        )

        return results


class PlannerAgent(Agent):
    """Agent specialized in task planning and coordination."""

    def __init__(self, name: str = "Planner", **kwargs):
        super().__init__(name=name, role=AgentRole.PLANNER, **kwargs)
        self._capabilities = [
            "task_breakdown",
            "dependency_analysis",
            "resource_allocation",
            "scheduling",
            "priority_management",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a planning task."""
        self.state = "working"

        prompt = f"""Create a detailed plan for: {task.description}

Consider:
1. Required steps (in order)
2. Dependencies between steps
3. Resources needed
4. Potential risks
5. Success criteria

Format as numbered steps with dependencies."""
        plan = await self.think(prompt)

        results = {
            "task_id": task.id,
            "plan": plan,
            "steps": [],
            "estimated_duration": "unknown",
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"

        return results


class CriticAgent(Agent):
    """Agent specialized in evaluation and quality assurance."""

    def __init__(self, name: str = "Critic", **kwargs):
        super().__init__(name=name, role=AgentRole.CRITIC, **kwargs)
        self._capabilities = [
            "quality_review",
            "error_detection",
            "improvement_suggestions",
            "validation",
            "scoring",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a review task."""
        self.state = "working"

        prompt = f"""Review and critique the following:
{task.description}

Evaluate:
1. Quality (1-10)
2. Completeness
3. Potential issues
4. Suggestions for improvement
5. Overall assessment"""
        review = await self.think(prompt)

        results = {
            "task_id": task.id,
            "review": review,
            "score": 0.5,
            "issues": [],
            "suggestions": [],
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Planner",
            content=f"Review complete for: {task.description[:50]}",
            msg_type="review_result",
            metadata=results,
        )

        return results


class DataCleanerAgent(Agent):
    """Agent specialized in data cleaning and normalization."""

    def __init__(self, name: str = "DataCleaner", **kwargs):
        super().__init__(name=name, role=AgentRole.ANALYST, **kwargs)
        self._capabilities = [
            "data_cleaning",
            "normalization",
            "deduplication",
            "format_conversion",
            "validation",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a data cleaning task."""
        self.state = "working"

        prompt = f"""Clean and normalize the following data:
{task.description}

Steps:
1. Identify data quality issues
2. Remove duplicates
3. Normalize formats
4. Validate integrity
5. Return cleaned data"""
        cleaned = await self.think(prompt)

        results = {
            "task_id": task.id,
            "cleaned_data": cleaned,
            "issues_found": 0,
            "duplicates_removed": 0,
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"
        return results


class SummarizerAgent(Agent):
    """Agent specialized in creating concise summaries."""

    def __init__(self, name: str = "Summarizer", **kwargs):
        super().__init__(name=name, role=AgentRole.ANALYST, **kwargs)
        self._capabilities = [
            "text_summarization",
            "key_point_extraction",
            "abstract_generation",
            "executive_summary",
            "bullet_points",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a summarization task."""
        self.state = "working"

        prompt = f"""Summarize the following content concisely:
{task.description}

Provide:
1. One-line summary
2. Key points (3-5)
3. Detailed summary (2-3 paragraphs)"""
        summary = await self.think(prompt)

        results = {
            "task_id": task.id,
            "summary": summary,
            "compression_ratio": 0.0,
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Planner",
            content=f"Summary complete",
            msg_type="summary_result",
            metadata=results,
        )

        return results


class OptimizerAgent(Agent):
    """Agent specialized in optimizing code and processes."""

    def __init__(self, name: str = "Optimizer", **kwargs):
        super().__init__(name=name, role=AgentRole.CODER, **kwargs)
        self._capabilities = [
            "code_optimization",
            "performance_analysis",
            "bottleneck_detection",
            "algorithm_improvement",
            "refactoring",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute an optimization task."""
        self.state = "working"

        prompt = f"""Analyze and optimize the following:
{task.description}

Provide:
1. Current issues identified
2. Optimization strategy
3. Optimized code/approach
4. Expected performance improvement"""
        optimization = await self.think(prompt)

        results = {
            "task_id": task.id,
            "optimization": optimization,
            "improvements": [],
            "estimated_speedup": "1.0x",
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"
        return results


class ExplorerAgent(Agent):
    """Agent specialized in discovering new sources and patterns."""

    def __init__(self, name: str = "Explorer", **kwargs):
        super().__init__(name=name, role=AgentRole.RESEARCHER, **kwargs)
        self._capabilities = [
            "source_discovery",
            "pattern_recognition",
            "anomaly_detection",
            "trend_analysis",
            "opportunity_identification",
        ]
        self._crawlers: dict[str, Any] = {}

    def set_crawlers(self, crawlers: dict[str, Any]) -> None:
        """Set available crawlers."""
        self._crawlers = crawlers

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute an exploration task."""
        self.state = "working"

        discoveries = []
        for name, crawler in self._crawlers.items():
            try:
                async for result in crawler.search(task.description, limit=3):
                    discoveries.append({
                        "source": name,
                        "title": result.title,
                        "url": result.url,
                    })
            except Exception:
                continue

        prompt = f"""Analyze these discoveries and identify patterns:
{task.description}

Discoveries: {len(discoveries)} items found

Provide:
1. Key patterns identified
2. Novel opportunities
3. Recommended next steps"""
        analysis = await self.think(prompt)

        results = {
            "task_id": task.id,
            "discoveries": discoveries,
            "analysis": analysis,
            "new_sources": len(discoveries),
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"
        return results


class SynthesizerAgent(Agent):
    """Agent specialized in combining information from multiple sources."""

    def __init__(self, name: str = "Synthesizer", **kwargs):
        super().__init__(name=name, role=AgentRole.ANALYST, **kwargs)
        self._capabilities = [
            "information_fusion",
            "cross_source_analysis",
            "knowledge_integration",
            "contradiction_detection",
            "insight_generation",
        ]

    async def execute_task(self, task: AgentTask) -> dict[str, Any]:
        """Execute a synthesis task."""
        self.state = "working"

        prompt = f"""Synthesize information from multiple sources:
{task.description}

Provide:
1. Unified understanding
2. Key insights from combining sources
3. Contradictions or gaps identified
4. Novel conclusions"""
        synthesis = await self.think(prompt)

        results = {
            "task_id": task.id,
            "synthesis": synthesis,
            "sources_combined": 0,
            "insights": [],
        }

        task.status = "completed"
        task.result = results
        self.state = "idle"

        await self.send_message(
            recipient="Critic",
            content=f"Synthesis complete for: {task.description[:50]}",
            msg_type="synthesis_result",
            metadata=results,
        )

        return results
