"""Cognitive orchestrator - the core agent loop with full cognitive architecture."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from ..config.settings import load_settings
from ..crawlers import (
    # Code Hosting
    GitHubCrawler, GitLabCrawler, BitbucketCrawler,
    CodebergCrawler, GiteaDotComCrawler, SourceForgeCrawler,
    LaunchpadCrawler, SavannahCrawler, ApacheCrawler, PagureCrawler,
    # AI/ML
    HuggingFaceCrawler, PastebinCrawler,
    # Academic
    ArxivCrawler, SemanticScholarCrawler,
    # Q&A/Community
    StackOverflowCrawler, RedditCrawler, HackerNewsCrawler,
    # Documentation
    RSSCrawler, WikipediaCrawler,
    # Messaging
    DiscordCrawler, SlackCrawler,
    # Productivity
    NotionCrawler, JiraCrawler,
    # Web
    WebScraperCrawler,
    # Package Registries
    PyPICrawler, NpmCrawler, CratesCrawler,
    GoDevCrawler, MavenCrawler, NugetCrawler, RubyGemsCrawler,
    # Base
    CrawlResult, CrawlerConfig,
)
from ..storage import Database, VectorStore, DockerManager, CrawlerWorkspace, CodeSandbox
from ..processing import LLMProcessor, EmbeddingGenerator
from ..utils import ProxyPool, RotatingProxyManager
from .memory import MemorySystem
from .metacognition import MetaCognition, ReasoningTrace
from .goals import GoalManager, Goal, GoalSource, GoalPriority
from .self_modify import SelfModifier, Modification
from .planning import Planner, Plan, PlanStep, PlanStatus, StepStatus
from .learning import FocusedLearner, LearningMode
from .scheduler import AdaptiveScheduler, CrawlOrchestrator, CrawlIntensity
from .knowledge_graph import KnowledgeGraph
from .causal_reasoning import CausalReasoner
from .skill_composition import SkillComposer
from .uncertainty import UncertaintyTracker
from .simulator import InternalSimulator, SimulationType
from ..agents import MultiAgentOrchestrator


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    LEARNING = "learning"
    SELF_MODIFYING = "self_modifying"
    WAITING = "waiting"


class CognitiveOrchestrator:
    """Full cognitive architecture orchestrator."""

    def __init__(self):
        self.settings = load_settings()
        self.logger = structlog.get_logger()

        # State
        self.state = AgentState.IDLE
        self.iteration = 0
        self.start_time = datetime.utcnow()

        # Core systems
        self.memory: MemorySystem | None = None
        self.metacognition: MetaCognition | None = None
        self.goals: GoalManager | None = None
        self.self_modifier: SelfModifier | None = None
        self.planner: Planner | None = None

        # Infrastructure
        self.db: Database | None = None
        self.vector_store: VectorStore | None = None
        self.docker: DockerManager | None = None
        self.workspace: CrawlerWorkspace | None = None
        self.code_sandbox: CodeSandbox | None = None
        self.llm: LLMProcessor | None = None
        self.embedder: EmbeddingGenerator | None = None

        # Multi-agent system
        self.multi_agent: MultiAgentOrchestrator | None = None

        # Crawlers
        self.crawlers: dict[str, Any] = {}
        
        # Initialize proxy management with auto-refresh
        proxy_settings = self.settings.proxy
        providers = [
            {
                "provider": p.name,
                "api_key": p.api_key,
                "host": p.host,
                "port": p.port,
                "username": p.username,
                "password": p.password,
            }
            for p in proxy_settings.providers
            if p.name and p.api_key
        ]
        
        self.proxy_manager = RotatingProxyManager(
            proxies=proxy_settings.proxies,
            proxy_file=proxy_settings.proxy_file or None,
            auto_refresh=proxy_settings.auto_refresh,
            min_proxies=proxy_settings.min_proxies,
            providers=providers,
        )
        self.proxy_pool = self.proxy_manager.pool

        # Learning system
        self.learner: FocusedLearner | None = None
        self.crawl_orchestrator: CrawlOrchestrator | None = None

        # Advanced cognitive modules
        self.knowledge_graph: KnowledgeGraph | None = None
        self.causal_reasoner: CausalReasoner | None = None
        self.skill_composer: SkillComposer | None = None
        self.uncertainty_tracker: UncertaintyTracker | None = None
        self.simulator: InternalSimulator | None = None

        # Current plan
        self.current_plan: Plan | None = None
        self.execution_log: list[dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize all cognitive and infrastructure systems."""
        self.logger.info("initializing_cognitive_agent")

        # Infrastructure
        self.db = Database(self.settings.storage.database_url)
        await self.db.initialize()

        self.vector_store = VectorStore(self.settings.storage.chroma_path)

        # Cognitive systems
        self.memory = MemorySystem(self.settings.storage.database_url)
        await self.memory.initialize()

        self.metacognition = MetaCognition(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )

        self.goals = GoalManager()

        self.self_modifier = SelfModifier(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )

        self.planner = Planner(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )

        # LLM and embeddings
        self.llm = LLMProcessor(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )
        self.embedder = EmbeddingGenerator(
            provider="openai",
            model_name=self.settings.llm.embedding_model,
            api_key=self.settings.llm.api_key,
        )

        # Docker workspace
        try:
            self.docker = DockerManager()
            self.workspace = CrawlerWorkspace(self.docker)
            await self.workspace.setup()
            self.code_sandbox = CodeSandbox(self.docker)
            await self.code_sandbox.ensure_image()
        except Exception as e:
            self.logger.warning("docker_unavailable", error=str(e))

        # Initialize crawlers
        await self._init_crawlers()

        # Initialize multi-agent system
        self.multi_agent = MultiAgentOrchestrator(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )
        self.multi_agent.set_crawlers(self.crawlers)
        if self.code_sandbox:
            self.multi_agent.set_sandbox(self.code_sandbox)
        
        # Initialize learning system
        self.learner = FocusedLearner(
            llm=self.llm,
            memory=self.memory,
            embedder=self.embedder,
        )

        # Initialize advanced cognitive modules
        llm_kwargs = {
            "api_key": self.settings.llm.api_key or "ollama",
            "model": self.settings.llm.model,
            "api_base": self.settings.llm.api_base,
        }
        self.knowledge_graph = KnowledgeGraph(**llm_kwargs)
        self.causal_reasoner = CausalReasoner(**llm_kwargs)
        self.skill_composer = SkillComposer(**llm_kwargs)
        self.uncertainty_tracker = UncertaintyTracker(**llm_kwargs)
        self.simulator = InternalSimulator(**llm_kwargs)

        # Initialize crawl orchestrator with light intensity by default
        self.crawl_orchestrator = CrawlOrchestrator(
            proxy_manager=self.proxy_manager,
            intensity=CrawlIntensity.LIGHT,
        )

        # Start proxy auto-refresh
        if self.settings.proxy.auto_refresh:
            await self.proxy_manager.start()
        
        # Verify proxy availability
        if self.settings.proxy.required and not self.proxy_pool._proxies:
            self.logger.warning("no_proxies_initial, attempting_fetch")
            # Try to fetch some free proxies
            if self.settings.proxy.fetch_free_proxies:
                from ..utils.proxy_fetcher import FreeProxyFetcher
                fetcher = FreeProxyFetcher()
                try:
                    proxies = await fetcher.fetch_all(limit=20)
                    for p in proxies:
                        self.proxy_pool.add_proxy(p)
                    self.logger.info("free_proxies_fetched", count=len(proxies))
                except Exception as e:
                    self.logger.error("initial_proxy_fetch_failed", error=str(e))
            
            if self.settings.proxy.required and not self.proxy_pool._proxies:
                self.logger.error("no_proxies_configured")
                raise RuntimeError(
                    "Proxy required but none available. "
                    "Set PROXY_PROXIES, proxy.proxy_file, or configure a paid provider."
                )

        # Set identity
        await self.memory.identity.set_value("name", "CognitiveAgent")
        await self.memory.identity.set_value("version", "1.0")
        await self.memory.identity.set_value("created_at", self.start_time.isoformat())

        self.logger.info("cognitive_agent_initialized")

    async def _init_crawlers(self) -> None:
        """Initialize all crawlers with proxy support."""
        config = CrawlerConfig(
            requests_per_second=self.settings.crawler.requests_per_second,
            burst_size=self.settings.crawler.burst_size,
            user_agents=self.settings.crawler.user_agents,
            randomize_delay=self.settings.crawler.randomize_delay,
            min_delay=self.settings.crawler.min_delay,
            max_delay=self.settings.crawler.max_delay,
        )

        crawler_map = {
            # Code Hosting
            "github": lambda: GitHubCrawler(
                token=self.settings.platform.github_token,
                config=config, proxy_pool=self.proxy_pool,
            ) if self.settings.platform.github_token else None,
            "gitlab": lambda: GitLabCrawler(
                token=self.settings.platform.github_token,
                config=config, proxy_pool=self.proxy_pool,
            ),
            "bitbucket": lambda: BitbucketCrawler(config=config, proxy_pool=self.proxy_pool),
            "codeberg": lambda: CodebergCrawler(config=config, proxy_pool=self.proxy_pool),
            "gitea": lambda: GiteaDotComCrawler(config=config, proxy_pool=self.proxy_pool),
            "sourceforge": lambda: SourceForgeCrawler(config=config, proxy_pool=self.proxy_pool),
            "launchpad": lambda: LaunchpadCrawler(config=config, proxy_pool=self.proxy_pool),
            "savannah": lambda: SavannahCrawler(config=config, proxy_pool=self.proxy_pool),
            "apache": lambda: ApacheCrawler(config=config, proxy_pool=self.proxy_pool),
            "pagure": lambda: PagureCrawler(config=config, proxy_pool=self.proxy_pool),
            
            # AI/ML
            "huggingface": lambda: HuggingFaceCrawler(
                token=self.settings.platform.huggingface_token,
                config=config, proxy_pool=self.proxy_pool,
            ) if self.settings.platform.huggingface_token else None,
            "pastebin": lambda: PastebinCrawler(
                api_key=self.settings.platform.pastebin_api_key,
                config=config, proxy_pool=self.proxy_pool,
            ),
            
            # Academic
            "arxiv": lambda: ArxivCrawler(config=config, proxy_pool=self.proxy_pool),
            "semantic_scholar": lambda: SemanticScholarCrawler(
                api_key=self.settings.platform.semantic_scholar_api_key,
                config=config, proxy_pool=self.proxy_pool,
            ) if self.settings.platform.semantic_scholar_api_key else None,
            
            # Q&A/Community
            "stackoverflow": lambda: StackOverflowCrawler(config=config, proxy_pool=self.proxy_pool),
            "reddit": lambda: RedditCrawler(config=config, proxy_pool=self.proxy_pool),
            "hackernews": lambda: HackerNewsCrawler(config=config, proxy_pool=self.proxy_pool),
            
            # Documentation
            "rss": lambda: RSSCrawler(config=config, proxy_pool=self.proxy_pool),
            "wikipedia": lambda: WikipediaCrawler(config=config, proxy_pool=self.proxy_pool),
            
            # Messaging
            "discord": lambda: DiscordCrawler(config=config, proxy_pool=self.proxy_pool),
            "slack": lambda: SlackCrawler(config=config, proxy_pool=self.proxy_pool),
            
            # Productivity
            "notion": lambda: NotionCrawler(config=config, proxy_pool=self.proxy_pool),
            "jira": lambda: JiraCrawler(base_url="https://your-domain.atlassian.net", config=config, proxy_pool=self.proxy_pool),
            
            # Web
            "webscraper": lambda: WebScraperCrawler(config=config, proxy_pool=self.proxy_pool),
            
            # Package Registries
            "pypi": lambda: PyPICrawler(config=config, proxy_pool=self.proxy_pool),
            "npm": lambda: NpmCrawler(config=config, proxy_pool=self.proxy_pool),
            "crates": lambda: CratesCrawler(config=config, proxy_pool=self.proxy_pool),
            "go": lambda: GoDevCrawler(config=config, proxy_pool=self.proxy_pool),
            "maven": lambda: MavenCrawler(config=config, proxy_pool=self.proxy_pool),
            "nuget": lambda: NugetCrawler(config=config, proxy_pool=self.proxy_pool),
            "rubygems": lambda: RubyGemsCrawler(config=config, proxy_pool=self.proxy_pool),
        }

        for name, factory in crawler_map.items():
            try:
                crawler = factory()
                if crawler:
                    await crawler.initialize()
                    self.crawlers[name] = crawler
            except Exception as e:
                self.logger.warning("crawler_init_failed", name=name, error=str(e))

        self.logger.info("crawlers_initialized", count=len(self.crawlers))

    async def run_cycle(self) -> dict[str, Any]:
        """Run one cognitive cycle."""
        self.iteration += 1
        cycle_start = datetime.utcnow()
        self.logger.info("cycle_start", iteration=self.iteration)

        result = {
            "iteration": self.iteration,
            "state": self.state.value,
            "actions": [],
            "learnings": [],
            "goals_progress": [],
        }

        try:
            # 1. Update drive states
            drive_status = await self.goals.get_drive_status()
            result["drives"] = drive_status

            # 2. Generate intrinsic goals if needed
            new_goals = await self.goals.generate_intrinsic_goals()
            if new_goals:
                result["new_goals"] = [g.description for g in new_goals]

            # 3. Select next goal
            self.state = AgentState.THINKING
            goal = await self.goals.select_next_goal()

            if goal:
                result["selected_goal"] = goal.description

                # 4. Create or continue plan
                self.state = AgentState.PLANNING
                if not self.current_plan or self.current_plan.goal_id != goal.id:
                    context = await self.memory.get_context_window()
                    self.current_plan = await self.planner.create_plan(
                        goal_id=goal.id,
                        goal_description=goal.description,
                        context=context,
                        available_actions=list(self.crawlers.keys()) + ["think", "search", "execute"],
                    )
                    result["plan_created"] = len(self.current_plan.steps)

                    # Register plan as skill for composition
                    skill = await self.skill_composer.refine_skill(
                        skill_id=f"plan_{goal.id[:8]}",
                        feedback=f"Goal: {goal.description}",
                        performance=0.5,
                    )
                    self.skill_composer.register_skill(skill)

                # 5. Execute next step
                self.state = AgentState.EXECUTING
                step = self.current_plan.get_next_step()

                if step:
                    step.status = StepStatus.EXECUTING
                    step_result = await self._execute_step(step, goal)
                    result["actions"].append({
                        "step": step.description,
                        "action": step.action,
                        "success": step_result.get("success", False),
                    })

                    # 6. Meta-cognitive evaluation
                    self.state = AgentState.THINKING
                    trace = await self.metacognition.evaluate_reasoning(
                        query=goal.description,
                        reasoning=f"Step: {step.description}\nResult: {step_result}",
                    )
                    result["reasoning_quality"] = trace.reasoning_quality
                    result["confidence"] = trace.confidence

                    # 7. Uncertainty tracking
                    uncertainty = await self.uncertainty_tracker.estimate_uncertainty(
                        claim=f"Goal '{goal.description}' can be achieved",
                        evidence=[f"Step result: {step_result.get('success', False)}"],
                    )
                    result["uncertainty"] = {
                        "confidence": uncertainty.mean_confidence,
                        "type": uncertainty.uncertainty_type.value,
                    }

                    # 8. Record experience
                    self.state = AgentState.LEARNING
                    await self.memory.record_experience(
                        event=f"Executed: {step.description}",
                        outcome=str(step_result)[:500],
                        importance=trace.confidence,
                    )

                    # 9. Extract knowledge from crawl results
                    if step_result.get("success") and "items" in step_result:
                        for item_text in step_result.get("items", [])[:3]:
                            try:
                                concepts, relations = await self.knowledge_graph.extract_knowledge(
                                    str(item_text),
                                    source=step.action,
                                )
                                for c in concepts:
                                    self.knowledge_graph.add_concept(c)
                                for r in relations:
                                    self.knowledge_graph.add_relation(r)
                            except Exception:
                                pass

                    # 10. Extract causal structures from reasoning
                    if step_result.get("response") or step_result.get("output"):
                        text = step_result.get("response") or step_result.get("output", "")
                        if len(text) > 100:
                            try:
                                vars, edges = await self.causal_reasoner.extract_causal_structure(
                                    text[:2000],
                                    context=goal.description,
                                )
                                for v in vars:
                                    self.causal_reasoner.add_variable(v)
                                for e in edges:
                                    self.causal_reasoner.add_edge(e)
                            except Exception:
                                pass

                    # 11. Update progress
                    completed = sum(1 for s in self.current_plan.steps if s.status == StepStatus.COMPLETED)
                    progress = completed / len(self.current_plan.steps) if self.current_plan.steps else 0
                    await self.goals.update_progress(goal.id, progress)

                    result["goals_progress"].append({
                        "goal": goal.description,
                        "progress": progress,
                    })

                    # 12. Check if plan needs replanning
                    if not step_result.get("success") and self.current_plan:
                        self.current_plan = await self.planner.replan(
                            self.current_plan,
                            step,
                            str(step_result.get("error", "Unknown error")),
                        )
                        result["replanned"] = True

            # 10. Check for self-improvement opportunities
            if self.iteration % 10 == 0:
                self.state = AgentState.SELF_MODIFYING
                await self._check_self_improvement(result)

        except Exception as e:
            self.logger.error("cycle_error", error=str(e))
            result["error"] = str(e)

        finally:
            self.state = AgentState.IDLE
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            result["duration_seconds"] = cycle_duration

            self.execution_log.append(result)

        return result

    async def _execute_step(
        self,
        step: PlanStep,
        goal: Goal,
    ) -> dict[str, Any]:
        """Execute a plan step."""
        action = step.action

        # Map action to crawler
        if action in self.crawlers:
            crawler = self.crawlers[action]
            results = []
            async for result in crawler.crawl(step.parameters.get("url", ""), **step.parameters):
                results.append(result)
                # Store in memory
                await self.db.store(result)

                # Add to working memory
                self.memory.working.add(
                    f"Crawled: {result.title} from {result.source}",
                    {"url": result.url, "type": result.content_type.value},
                )

            step.status = StepStatus.COMPLETED
            step.result = f"Crawled {len(results)} items"
            return {"success": True, "count": len(results), "items": [r.title for r in results[:5]]}

        elif action == "search":
            # Search across all crawlers
            query = step.parameters.get("query", goal.description)
            all_results = []
            for name, crawler in self.crawlers.items():
                try:
                    async for result in crawler.search(query, limit=10):
                        all_results.append(result)
                        await self.db.store(result)
                except Exception:
                    continue

            step.status = StepStatus.COMPLETED
            step.result = f"Found {len(all_results)} results"
            return {"success": True, "count": len(all_results)}

        elif action == "think":
            # Use LLM to reason
            response = await self.llm.answer_query(
                step.parameters.get("question", step.description),
                await self.memory.get_context_window(),
            )
            step.status = StepStatus.COMPLETED
            step.result = response
            return {"success": True, "response": response[:500]}

        elif action == "execute":
            # Execute Docker command or code
            if self.docker:
                command = step.parameters.get("command", "ls")
                containers = await self.docker.list_containers()
                if containers:
                    output = await self.docker.exec_in_container(containers[0].id, command)
                    step.status = StepStatus.COMPLETED
                    step.result = output
                    return {"success": True, "output": output}

            step.status = StepStatus.FAILED
            return {"success": False, "error": "No execution environment"}

        else:
            # Unknown action - try to learn or use LLM
            response = await self.llm.answer_query(
                f"How to execute: {action}",
                f"Goal: {goal.description}\nStep: {step.description}",
            )
            step.status = StepStatus.COMPLETED
            step.result = response
            return {"success": True, "response": response[:500]}

    async def _check_self_improvement(self, result: dict) -> None:
        """Check if agent should improve itself."""
        # Analyze recent performance
        recent = self.execution_log[-10:] if self.execution_log else []
        success_rate = sum(
            1 for log in recent
            if all(a.get("success", False) for a in log.get("actions", []))
        ) / max(len(recent), 1)

        # If success rate is low, try to improve
        if success_rate < 0.6:
            # Get a skill that needs improvement
            skills = await self.memory.procedural.list_skills()
            for skill in skills:
                if skill.metadata.get("success_rate", 1.0) < 0.7:
                    # Try to optimize
                    mod = await self.self_modifier.propose_optimization(
                        skill_name=skill.metadata.get("skill_name", "unknown"),
                        current_code=skill.content,
                        issue="Low success rate",
                    )
                    if mod:
                        applied = await self.self_modifier.apply_modification(mod.id)
                        if applied:
                            result["self_improvement"] = f"Optimized skill: {skill.metadata.get('skill_name')}"
                            break

    async def handle_user_input(self, user_input: str) -> str:
        """Handle user input and respond."""
        # Add to working memory
        self.memory.working.add(f"User: {user_input}", {"role": "user"})

        # Recall relevant memories
        relevant = await self.memory.recall_relevant(user_input)

        # Get context
        context = await self.memory.get_context_window()

        # Process with LLM
        response = await self.llm.answer_query(user_input, context)

        # Add response to working memory
        self.memory.working.add(f"Agent: {response}", {"role": "assistant"})

        # Record interaction
        await self.memory.record_experience(
            event=f"User interaction: {user_input[:100]}",
            outcome=response[:200],
            importance=0.5,
        )

        return response

    async def get_status(self) -> dict[str, Any]:
        """Get comprehensive agent status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            "state": self.state.value,
            "iteration": self.iteration,
            "uptime_seconds": uptime,
            "goals": self.goals.get_stats() if self.goals else {},
            "plans": self.planner.get_stats() if self.planner else {},
            "self_modification": self.self_modifier.get_stats() if self.self_modifier else {},
            "crawlers": list(self.crawlers.keys()),
            "drives": await self.goals.get_drive_status() if self.goals else {},
            "working_memory_size": len(self.memory.working.items) if self.memory else 0,
            "current_plan": self.current_plan.to_context() if self.current_plan else None,
            "proxy_pool": self.proxy_pool.get_stats(),
            "scheduler": self.crawl_orchestrator.scheduler.get_stats() if self.crawl_orchestrator else {},
            "learning": self.learner.get_stats() if self.learner else {},
            "knowledge_graph": self.knowledge_graph.get_stats() if self.knowledge_graph else {},
            "causal_reasoning": self.causal_reasoner.get_stats() if self.causal_reasoner else {},
            "skill_composition": self.skill_composer.get_stats() if self.skill_composer else {},
            "uncertainty": self.uncertainty_tracker.get_stats() if self.uncertainty_tracker else {},
            "simulator": self.simulator.get_stats() if self.simulator else {},
        }

    async def autonomous_loop(self, max_cycles: int = 100) -> None:
        """Run autonomous cognitive loop."""
        self.logger.info("starting_autonomous_loop", max_cycles=max_cycles)

        for i in range(max_cycles):
            result = await self.run_cycle()
            self.logger.info(
                "cycle_complete",
                iteration=result["iteration"],
                actions=len(result["actions"]),
                state=result["state"],
            )

            # Brief pause between cycles
            await asyncio.sleep(1)

    async def learn_focused(
        self,
        topic: str,
        max_items: int = 10,
        mode: LearningMode = LearningMode.FOCUSED,
    ) -> dict[str, Any]:
        """Run focused learning session."""
        session = await self.learner.start_session(topic, mode, max_items)

        # Get priority sources
        sources = await self.learner.get_priority_sources(limit=3)

        results = []
        for source in sources:
            if session.items_processed >= max_items:
                break

            # Find appropriate crawler
            crawler = self.crawlers.get(source.tags[0] if source.tags else "webscraper")
            if not crawler:
                continue

            # Crawl with quality filter
            try:
                async for result in crawler.crawl(source.url):
                    learning = await self.learner.learn_from_source(result, deep_process=True)
                    if learning["quality"] > 0.6:
                        results.append(learning)
            except Exception as e:
                self.logger.warning("focused_crawl_failed", source=source.name, error=str(e))

        return {
            "session_id": session.id,
            "topic": topic,
            "mode": mode.value,
            "items_learned": len(results),
            "insights": session.insights,
            "knowledge_gained": session.knowledge_gained,
        }

    async def adapt_intensity(self) -> str:
        """Adapt crawling intensity based on conditions."""
        new_intensity = await self.crawl_orchestrator.scheduler.adapt_intensity()
        return new_intensity.value

    async def dream(self, theme: str) -> dict[str, Any]:
        """Run a dream session to generate novel connections and insights."""
        self.state = AgentState.LEARNING
        context = await self.memory.get_context_window()
        dream_result = await self.simulator.dream(theme, knowledge_context=context)
        self.state = AgentState.IDLE

        # Store insights in knowledge graph
        for insight in dream_result.insights:
            concepts, relations = await self.knowledge_graph.extract_knowledge(
                insight, source="dream",
            )
            for c in concepts:
                self.knowledge_graph.add_concept(c)
            for r in relations:
                self.knowledge_graph.add_relation(r)

        # Store in memory
        await self.memory.record_experience(
            event=f"Dream session: {theme}",
            outcome="\n".join(dream_result.insights),
            importance=0.7,
        )

        return {
            "theme": theme,
            "associations": dream_result.associations,
            "novel_connections": dream_result.novel_connections,
            "insights": dream_result.insights,
            "creative_ideas": dream_result.creative_ideas,
            "emotional_tone": dream_result.emotional_tone,
        }

    async def simulate(self, action: str, sim_type: str = "planning") -> dict[str, Any]:
        """Simulate an action before executing."""
        state = {}
        if self.memory.working.items:
            state["working_memory"] = [i.content for i in self.memory.working.items[-5:]]

        type_map = {
            "planning": SimulationType.PLANNING,
            "reflection": SimulationType.REFLECTION,
            "counterfactual": SimulationType.COUNTERFACTUAL,
            "prediction": SimulationType.PREDICTION,
            "dream": SimulationType.DREAM,
        }
        simulation = await self.simulator.simulate_action(
            action=action,
            current_state=state,
            simulation_type=type_map.get(sim_type, SimulationType.PLANNING),
        )

        return {
            "action": action,
            "type": sim_type,
            "steps": [s.get("description", "") for s in simulation.steps],
            "outcomes": simulation.outcomes,
            "confidence": simulation.confidence,
        }

    async def simulate_plan(self, plan_steps: list[str]) -> dict[str, Any]:
        """Simulate an entire plan before execution."""
        state = {}
        if self.memory.working.items:
            state["working_memory"] = [i.content for i in self.memory.working.items[-5:]]

        simulation = await self.simulator.simulate_plan(plan_steps, state)

        return {
            "steps_simulated": len(plan_steps),
            "outcomes": simulation.outcomes,
            "confidence": simulation.confidence,
            "step_details": simulation.steps,
        }

    async def causal_query(self, query: str) -> dict[str, Any]:
        """Query the causal reasoning engine."""
        causes = await self.causal_reasoner.get_causes(query)
        effects = await self.causal_reasoner.get_effects(query)
        return {
            "query": query,
            "causes": causes,
            "effects": effects,
            "context": self.causal_reasoner.to_context()[:1000],
        }

    async def causal_intervention(self, variable: str, value: Any, query: str) -> dict[str, Any]:
        """Perform a causal do-calculus intervention."""
        from .causal_reasoning import Intervention
        intervention = Intervention(variable=variable, value=value)
        result = await self.causal_reasoner.do_calculus(query, intervention)
        return result

    async def counterfactual(self, outcome: str, variable: str, value: Any) -> dict[str, Any]:
        """Run counterfactual reasoning."""
        from .causal_reasoning import Intervention
        intervention = Intervention(variable=variable, value=value)
        cf = await self.causal_reasoner.counterfactual_reasoning(outcome, intervention)
        return {
            "description": cf.description,
            "predicted_outcome": cf.predicted_outcome,
            "confidence": cf.confidence,
        }

    async def query_knowledge(self, query: str) -> list[dict[str, Any]]:
        """Query the knowledge graph."""
        return self.knowledge_graph.query(query)

    async def knowledge_analogy(self, a: str, b: str, c: str) -> list[str]:
        """Find analogies: A is to B as C is to ?"""
        return self.knowledge_graph.find_analogies(a, b, c)

    async def knowledge_paths(self, source: str, target: str) -> list[list[str]]:
        """Find paths between two concepts in the knowledge graph."""
        return self.knowledge_graph.find_paths(source, target)

    async def uncertainty_check(self, claim: str) -> dict[str, Any]:
        """Check uncertainty around a claim."""
        estimate = await self.uncertainty_tracker.estimate_uncertainty(claim)
        return {
            "claim": claim,
            "confidence": estimate.mean_confidence,
            "type": estimate.uncertainty_type.value,
            "interval": estimate.confidence_interval,
            "evidence_count": estimate.evidence_count,
            "contradicting": estimate.contradicting_evidence,
        }

    async def should_act(self, threshold: float = 0.6) -> tuple[bool, str]:
        """Check if agent should act based on uncertainty."""
        return await self.uncertainty_tracker.should_act(threshold)

    async def compose_skill(self, goal: str) -> dict[str, Any]:
        """Discover skill compositions for a goal."""
        chain = await self.skill_composer.auto_compose(goal)
        return {
            "goal": goal,
            "chain_name": chain.name,
            "steps": chain.steps,
            "success_rate": chain.success_rate,
            "description": chain.description,
        }

    def get_cognitive_context(self) -> str:
        """Get combined context from all cognitive modules."""
        parts = []
        if self.knowledge_graph:
            parts.append(f"Knowledge Graph:\n{self.knowledge_graph.to_context()}")
        if self.causal_reasoner:
            parts.append(f"Causal Models:\n{self.causal_reasoner.to_context()}")
        if self.skill_composer:
            parts.append(f"Skills:\n{self.skill_composer.to_context()}")
        if self.simulator:
            parts.append(f"World Model:\n{self.simulator.to_context()}")
        return "\n\n".join(parts)

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute code in a Docker sandbox."""
        if not self.code_sandbox:
            return {"error": "Docker not available"}

        result = await self.code_sandbox.execute_code(
            code, language=language, timeout=timeout,
        )
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
        }

    async def agent_task(
        self,
        description: str,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Run a task using the multi-agent system."""
        if not self.multi_agent:
            return {"error": "Multi-agent system not available"}

        return await self.multi_agent.run_task(description, agent_name)

    async def agent_collaborate(
        self,
        problem: str,
        agents: list[str] | None = None,
    ) -> dict[str, Any]:
        """Have multiple agents collaborate on a problem."""
        if not self.multi_agent:
            return {"error": "Multi-agent system not available"}

        return await self.multi_agent.collaborative_solve(problem, agents)

    async def agent_pipeline(
        self,
        stages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run a multi-agent pipeline."""
        if not self.multi_agent:
            return {"error": "Multi-agent system not available"}

        return await self.multi_agent.run_pipeline(stages)

    async def close(self) -> None:
        """Cleanup all resources."""
        # Stop proxy refresh
        await self.proxy_manager.stop()
        
        for crawler in self.crawlers.values():
            await crawler.cleanup()

        if self.db:
            await self.db.close()

        if self.memory:
            await self.memory.close()

        if self.workspace:
            await self.workspace.cleanup()

        self.logger.info(
            "cognitive_agent_closed",
            proxy_stats=self.proxy_pool.get_stats(),
        )
