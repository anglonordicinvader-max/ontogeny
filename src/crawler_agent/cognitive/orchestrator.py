"""Cognitive orchestrator - the core agent loop with full cognitive architecture."""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from ..config.settings import load_settings
from ..crawlers import (
    # Code Hosting
    GitHubCrawler, GitLabCrawler, BitbucketCrawler,
    CodebergCrawler, GiteaDotComCrawler, SourceForgeCrawler,
    LaunchpadCrawler, SavannahCrawler, ApacheCrawler, PagureCrawler,
    # Additional
    GitHubCodeSearchCrawler, PapersWithCodeCrawler, HuggingFaceHubCrawler, GitHubTrendingCrawler,
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
    # Archives
    InternetArchiveCrawler,
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
from .recursive_modify import RecursiveSelfModifier, RecursiveModification
from .planning import Planner, Plan, PlanStep, PlanStatus, StepStatus
from .learning import FocusedLearner, LearningMode
from .scheduler import AdaptiveScheduler, CrawlOrchestrator, CrawlIntensity
from .knowledge_graph import KnowledgeGraph
from .causal_reasoning import CausalReasoner
from .skill_composition import SkillComposer
from .uncertainty import UncertaintyTracker
from .simulator import InternalSimulator, SimulationType
from .backend import CognitiveBackend, LLMBackend, HybridBackend, PatternBackend
from .pattern_learner import PatternLearner
from .rl_agent import RLAgent, State as RLState
from .curiosity import CuriosityEngine
from .world_model import BayesianWorldModel
from .meta_learner import MetaLearner
from .sleep import SleepConsolidator
from .attention import AttentionMechanism
from .emotional import EmotionalProcessor
from .transfer import TransferLearner
from .benchmark import BenchmarkHarness, create_benchmark_harness
from .patch_verifier import PatchVerifier, TestGenerator
from .skill_library import SkillLibrary, create_skill_library
from .distillation import KnowledgeDistiller, create_knowledge_distiller
from .ci_validator import GitHubActionsValidator, LocalCIValidator, CompositeValidator
from .outcome_verifier import CompositeOutcomeVerifier, create_outcome_verifier, VerificationSpec, VerificationStatus
from .blender_sandbox import BlenderSandbox, create_blender_sandbox, SimulationSpec, SimulationType
from .mcts_planner import MCTSPlanner, create_mcts_planner, MCTSConfig
from .tools import ToolManager, ToolResult
from .sim_library import SimulationLibrary, SimBackend
from .self_audit import SelfAuditor
from .multimodal import MultimodalProcessor
from .agent_variety import AgentPopulation
from .skill_export import SkillExporter
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

        # Tier 1: Core Learning
        self.backend: CognitiveBackend | None = None
        self.pattern_learner: PatternLearner | None = None
        self.rl_agent: RLAgent | None = None

        # Tier 2: Advanced Cognition
        self.curiosity: CuriosityEngine | None = None
        self.world_model: BayesianWorldModel | None = None
        self.transfer_learner: TransferLearner | None = None

        # Tier 3: Foundation
        self.meta_learner: MetaLearner | None = None
        self.sleep_consolidator: SleepConsolidator | None = None
        self.attention: AttentionMechanism | None = None
        self.emotional: EmotionalProcessor | None = None

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

        # New: Verification, Grounding & Planning
        self.outcome_verifier: CompositeOutcomeVerifier | None = None
        self.blender_sandbox: BlenderSandbox | None = None
        self.mcts_planner: MCTSPlanner | None = None

        # Tool integrations
        self.tool_manager: ToolManager | None = None

        # Simulation library
        self.sim_library: SimulationLibrary | None = None

        # Self-audit system
        self.self_auditor: SelfAuditor | None = None

        # Multimodal processing
        self.multimodal: MultimodalProcessor | None = None

        # Agent population with behavioral variation
        self.agent_population: AgentPopulation | None = None

        # Skill export system
        self.skill_exporter: SkillExporter | None = None

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

        # Build three-tier hybrid backend: routine + code + reasoning
        routine_backend = LLMBackend(
            api_key=self.settings.llm.api_key or "ollama",
            model=self.settings.llm.model,
            api_base=self.settings.llm.api_base,
        )
        code_backend = None
        if self.settings.code_llm.enabled:
            code_backend = LLMBackend(
                api_key=self.settings.code_llm.api_key or "ollama",
                model=self.settings.code_llm.model,
                api_base=self.settings.code_llm.api_base,
            )
        reasoning_backend = None
        if self.settings.heavy_llm.enabled:
            reasoning_backend = LLMBackend(
                api_key=self.settings.heavy_llm.api_key or "ollama",
                model=self.settings.heavy_llm.model,
                api_base=self.settings.heavy_llm.api_base,
            )
        self.logger.info(
            "three_tier_llm",
            routine=self.settings.llm.model,
            code=self.settings.code_llm.model if code_backend else "disabled",
            reasoning=self.settings.heavy_llm.model if reasoning_backend else "disabled",
        )

        self.backend = HybridBackend(
            routine=routine_backend,
            code=code_backend,
            reasoning=reasoning_backend,
        )

        self.metacognition = MetaCognition(backend=self.backend)

        self.goals = GoalManager()

        self.self_modifier = SelfModifier(backend=self.backend)

        self.recursive_modifier = RecursiveSelfModifier(
            backend=self.backend,
            base_path=Path("."),
        )

        self.planner = Planner(backend=self.backend)

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
        self.knowledge_graph = KnowledgeGraph(backend=self.backend)
        self.causal_reasoner = CausalReasoner(backend=self.backend)
        self.skill_composer = SkillComposer(backend=self.backend)
        self.uncertainty_tracker = UncertaintyTracker(backend=self.backend)
        self.simulator = InternalSimulator(backend=self.backend)

        # Tier 1: Core Learning
        self.pattern_learner = PatternLearner()
        self.rl_agent = RLAgent()
        self.rl_agent.register_default_actions()

        # Tier 2: Advanced Cognition
        self.curiosity = CuriosityEngine()
        self.world_model = BayesianWorldModel()
        self.transfer_learner = TransferLearner()

        # Tier 3: Foundation
        self.meta_learner = MetaLearner(
            persistence_dir=str(Path(self.settings.storage.chroma_path).parent / "meta_learner"),
        )
        self.sleep_consolidator = SleepConsolidator()
        self.attention = AttentionMechanism()
        self.emotional = EmotionalProcessor()

        # New: Verification & Learning Infrastructure
        self.benchmark_harness = await create_benchmark_harness(self.backend, self.code_sandbox)
        self.patch_verifier = PatchVerifier(
            backend=self.backend,
            sandbox=self.code_sandbox,
        )
        self.skill_library = await create_skill_library(self.backend)
        self.knowledge_distiller = KnowledgeDistiller(self.backend)
        self.ci_validator = CompositeValidator([
            LocalCIValidator(self.code_sandbox) if self.code_sandbox else None,
            GitHubActionsValidator(
                repo_owner=os.environ.get("GITHUB_OWNER", ""),
                repo_name=os.environ.get("GITHUB_REPO", ""),
                token=os.environ.get("GITHUB_TOKEN"),
            ) if os.environ.get("GITHUB_TOKEN") else None,
        ])

# New: Verification, Grounding & Planning
        self.outcome_verifier = await create_outcome_verifier(
            code_sandbox=self.code_sandbox,
            blender_sandbox=None,  # Will initialize after blender_sandbox
            backend=self.backend
        )
        try:
            self.blender_sandbox = await create_blender_sandbox()
            # Recreate outcome_verifier with blender_sandbox
            self.outcome_verifier = await create_outcome_verifier(
                code_sandbox=self.code_sandbox,
                blender_sandbox=self.blender_sandbox,
                backend=self.backend
            )
            self.logger.info("blender_sandbox_initialized")
        except Exception as e:
            self.logger.warning("blender_sandbox_unavailable", error=str(e))
            self.blender_sandbox = None
        self.mcts_planner = await create_mcts_planner(
            backend=self.backend,
            bayesian_model=self.world_model,
            available_actions=list(self.crawlers.keys()) + [
                "think", "search", "execute", "blender_simulate", "blender_render",
                "github_api", "arxiv_api", "ros2_publish", "ros2_subscribe",
            ],
        )

        # Initialize tool integrations
        self.tool_manager = ToolManager(settings=self.settings, proxy_pool=self.proxy_pool)
        await self.tool_manager.initialize()

        # Initialize simulation library
        self.sim_library = SimulationLibrary(blender_sandbox=self.blender_sandbox)

        # Initialize self-auditor
        self.self_auditor = SelfAuditor()

        # Initialize multimodal processor
        self.multimodal = MultimodalProcessor(settings=self.settings)
        await self.multimodal.initialize()

        # Initialize agent population
        self.agent_population = AgentPopulation()

        # Initialize skill exporter
        self.skill_exporter = SkillExporter()

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
            # Archives
            "internetarchive": lambda: InternetArchiveCrawler(config=config, proxy_pool=self.proxy_pool),
            # Additional
            "github_code": lambda: GitHubCodeSearchCrawler(
                name="github_code",
                token=self.settings.platform.github_token,
                config=config, proxy_pool=self.proxy_pool,
            ) if self.settings.platform.github_token else None,
            "papers_with_code": lambda: PapersWithCodeCrawler(
                name="papers_with_code",
                config=config, proxy_pool=self.proxy_pool,
            ),
            "hf_hub": lambda: HuggingFaceHubCrawler(
                name="hf_hub",
                token=self.settings.platform.huggingface_token,
                config=config, proxy_pool=self.proxy_pool,
            ) if self.settings.platform.huggingface_token else None,
            "github_trending": lambda: GitHubTrendingCrawler(
                name="github_trending",
                config=config, proxy_pool=self.proxy_pool,
            ),
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
                plan_done = self.current_plan and all(
                    s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
                    for s in self.current_plan.steps
                ) if self.current_plan and self.current_plan.steps else False
                if not self.current_plan or self.current_plan.goal_id != goal.id or plan_done:
                    context = await self.memory.get_context_window()
                    self.current_plan = await self.planner.create_plan(
                        goal_id=goal.id,
                        goal_description=goal.description,
                        context=context,
                        available_actions=list(self.crawlers.keys()) + ["think", "search", "execute"],
                    )

                    if self.current_plan.steps:
                        result["plan_created"] = len(self.current_plan.steps)
                        # Register plan as skill for composition
                        try:
                            skill = await self.skill_composer.refine_skill(
                                skill_id=f"plan_{goal.id[:8]}",
                                feedback=f"Goal: {goal.description}",
                                performance=0.5,
                            )
                            self.skill_composer.register_skill(skill)
                        except Exception:
                            pass
                    else:
                        # Fallback: search all crawlers, then think about results
                        search_step = PlanStep(
                            id="step_search",
                            description=f"Search for: {goal.description}",
                            action="search",
                            parameters={"query": goal.description, "limit": 10},
                        )
                        self.current_plan.steps.append(search_step)
                        think_step = PlanStep(
                            id="step_think",
                            description=f"Analyze search results for: {goal.description}",
                            action="think",
                            parameters={"question": goal.description},
                            dependencies=["step_search"],
                        )
                        self.current_plan.steps.append(think_step)
                        result["plan_created"] = len(self.current_plan.steps)
                        result["plan_fallback"] = True

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

                    # 13. Pattern learning from experience
                    experience = {
                        "action": step.action,
                        "success": step_result.get("success", False),
                        "quality": trace.confidence,
                        "events": [step.description],
                    }
                    new_patterns = await self.pattern_learner.learn_from_experience(experience)
                    result["patterns_learned"] = len(new_patterns)

                    # 14. RL learning from outcome (wired to crawl results + curiosity)
                    rl_state = RLState(context={"goal": goal.description})
                    rl_action = self.rl_agent.actions.get(step.action)
                    if rl_action:
                        # Calculate reward from success, quality, and novelty
                        novelty_bonus = 0.0
                        if step_result.get("success") and step_result.get("items"):
                            for item in step_result.get("items", [])[:2]:
                                novelty_signal = await self.curiosity.analyze_novelty(
                                    str(item)[:500],
                                    topic=goal.description[:50],
                                )
                                novelty_bonus += novelty_signal.novelty_score * 0.3
                        reward = self.rl_agent.get_reward(
                            success=step_result.get("success", False),
                            quality=trace.confidence,
                            novelty=min(1.0, novelty_bonus),
                        )
                        next_rl_state = RLState(context={"progress": progress})
                        await self.rl_agent.record_outcome(rl_state, rl_action, reward, next_rl_state)
                        result["rl_reward"] = reward

                    # 15. Curiosity and novelty detection
                    if step_result.get("success") and step_result.get("items"):
                        for item in step_result.get("items", [])[:2]:
                            novelty = await self.curiosity.analyze_novelty(
                                str(item)[:500],
                                topic=goal.description[:50],
                            )
                            result["novelty_detected"] = novelty.novelty_score

                    # 16. Update world model
                    observation = {
                        "action": step.action,
                        "success": step_result.get("success", False),
                        "context": goal.description[:100],
                    }
                    await self.world_model.observe(observation)

                    # 17. Emotional processing
                    event_type = "success" if step_result.get("success") else "failure"
                    await self.emotional.process_event(event_type, step.description)
                    result["emotional_state"] = self.emotional.state.mood

                    # 18. Attention update
                    target = await self.attention.evaluate_attention(
                        step.description,
                        context={"goals": [goal.description]},
                    )
                    await self.attention.decide_focus([target])

            # 19. Check for self-improvement opportunities
            if self.iteration % 5 == 0:
                self.state = AgentState.SELF_MODIFYING
                await self._check_self_improvement(result)

                # 19b. Recursive self-modification — reads and rewrites own source
                try:
                    recent_errors = [
                        {"module": e.get("module", "unknown"), "error": e.get("error", "")}
                        for e in self.execution_log[-20:] if not e.get("actions", [{}])[0].get("success", True)
                    ]
                    perf_metrics = {
                        "module_success_rates": {
                            "orchestrator": sum(1 for e in self.execution_log[-20:] if e.get("actions", [{}])[0].get("success", True)) / max(len(self.execution_log[-20:]), 1),
                        }
                    }
                    recursive_mod = await self.recursive_modifier.analyze_and_improve(
                        error_logs=recent_errors,
                        performance_metrics=perf_metrics,
                    )
                    if recursive_mod and recursive_mod.applied:
                        result["recursive_modification"] = {
                            "target": recursive_mod.target.value,
                            "file": recursive_mod.file_path,
                            "description": recursive_mod.description,
                            "applied": True,
                        }
                except Exception as e:
                    self.logger.warning("recursive_modification_error", error=str(e))

                # 20. Sleep consolidation every 10 cycles
                await self.sleep_consolidator.consolidate(self.memory, self.pattern_learner)
                result["consolidation"] = self.sleep_consolidator.get_stats()

                # 20b. Periodic self-audit every 10 cycles
                if self.self_auditor and self.self_auditor.should_run_audit():
                    try:
                        audit_report = await self.self_auditor.run_full_audit(self)
                        result["audit_report"] = {
                            "id": audit_report.id,
                            "healthy": audit_report.overall_healthy,
                            "checks": len(audit_report.checks),
                            "warnings": sum(1 for c in audit_report.checks if c.severity == "warning"),
                            "recommendations": audit_report.recommendations[:3],
                        }
                    except Exception as e:
                        self.logger.warning("audit_error", error=str(e))

                # 21. Generate exploration goal from curiosity (auto-feed into GoalManager)
                exploration_goal = await self.curiosity.generate_exploration_goal()
                if exploration_goal:
                    result["exploration_goal"] = exploration_goal
                    # Automatically create a goal from curiosity gap
                    from .goals import GoalSource
                    curiosity_goal = await self.goals.create_goal(
                        description=exploration_goal,
                        priority=GoalPriority.MEDIUM,
                        source=GoalSource.INTRINSIC,
                        metadata={"source": "curiosity_engine", "auto_generated": True},
                    )
                    if curiosity_goal:
                        result["curiosity_goal_created"] = curiosity_goal.description

                # 22. Meta-learning analysis
                suggestions = await self.meta_learner.suggest_improvements()
                result["meta_suggestions"] = suggestions
                # Persist meta-learner state
                self.meta_learner.save()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.logger.error("cycle_error", error=str(e), traceback=tb)
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
            # Search across all crawlers, trying multiple method names
            query = step.parameters.get("query", goal.description)
            limit = step.parameters.get("limit", 10)
            all_results = []
            search_methods = ["search", "search_repositories", "search_projects",
                              "search_packages", "search_artifacts", "search_gems",
                              "search_pastes", "search_models", "search_messages"]
            for name, crawler in self.crawlers.items():
                for method_name in search_methods:
                    method = getattr(crawler, method_name, None)
                    if method and callable(method):
                        try:
                            async for result in method(query, limit=limit):
                                all_results.append(result)
                                await self.db.store(result)
                                self.memory.working.add(
                                    f"Found: {result.title} from {result.source}",
                                    {"url": result.url, "type": result.content_type.value},
                                )
                        except Exception:
                            continue
                        break  # Found a working method for this crawler

            step.status = StepStatus.COMPLETED
            step.result = f"Found {len(all_results)} results"
            return {"success": True, "count": len(all_results), "items": [r.title for r in all_results[:10]]}

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

        elif action == "blender_simulate":
            # Run physics simulation in Blender
            if not self.blender_sandbox:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Blender sandbox not available"}

            spec = SimulationSpec(
                type=SimulationType(step.parameters.get("type", "rigid_body")),
                objects=step.parameters.get("objects", []),
                duration=step.parameters.get("duration", 5.0),
                fps=step.parameters.get("fps", 60),
                gravity=tuple(step.parameters.get("gravity", [0, 0, -9.81])),
                ground=step.parameters.get("ground", True),
                render=step.parameters.get("render", False),
                render_resolution=tuple(step.parameters.get("render_resolution", [1920, 1080])),
                render_engine=step.parameters.get("render_engine", "CYCLES"),
                render_samples=step.parameters.get("render_samples", 128),
                emotion_visualizer=self.settings.emotion_visualizer,
            )
            result = await self.blender_sandbox.run_simulation(spec)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Simulation {'succeeded' if result.success else 'failed'}: {result.output or result.error}"
            return {"success": result.success, "output": result.output, "frames": result.frames, "blend_path": result.blend_path, "error": result.error}

        elif action == "blender_render":
            # Render a scene in Blender
            if not self.blender_sandbox:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Blender sandbox not available"}

            spec = SimulationSpec(
                type=SimulationType.RENDER,
                objects=step.parameters.get("objects", []),
                render=True,
                render_resolution=tuple(step.parameters.get("render_resolution", [1920, 1080])),
                render_engine=step.parameters.get("render_engine", "CYCLES"),
                render_samples=step.parameters.get("render_samples", 128),
            )
            result = await self.blender_sandbox.run_render(spec)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Render {'succeeded' if result.success else 'failed'}: {result.output or result.error}"
            return {"success": result.success, "render_path": result.render_path, "blend_path": result.blend_path, "error": result.error}

        elif action == "github_api":
            # GitHub API operations
            if not self.tool_manager:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Tool manager not available"}
            operation = step.parameters.get("operation", "get_repo")
            params = {k: v for k, v in step.parameters.items() if k != "operation"}
            result = await self.tool_manager.invoke("github", operation, **params)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"GitHub {operation} {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "data": result.data, "error": result.error, "metadata": result.metadata}

        elif action == "arxiv_api":
            # arXiv API operations
            if not self.tool_manager:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Tool manager not available"}
            operation = step.parameters.get("operation", "search")
            params = {k: v for k, v in step.parameters.items() if k != "operation"}
            result = await self.tool_manager.invoke("arxiv", operation, **params)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"arXiv {operation} {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "data": result.data, "error": result.error, "metadata": result.metadata}

        elif action == "ros2_publish":
            # ROS2 publish
            if not self.tool_manager:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Tool manager not available"}
            topic = step.parameters.get("topic", "/ontogeny/default")
            message_type = step.parameters.get("message_type", "std_msgs/msg/String")
            data = step.parameters.get("data", {})
            result = await self.tool_manager.invoke("ros2", "publish", topic=topic, message_type=message_type, data=data)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"ROS2 publish {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "data": result.data, "error": result.error}

        elif action == "ros2_subscribe":
            # ROS2 subscribe
            if not self.tool_manager:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Tool manager not available"}
            topic = step.parameters.get("topic", "/ontogeny/default")
            message_type = step.parameters.get("message_type", "std_msgs/msg/String")
            timeout = step.parameters.get("timeout", 5.0)
            result = await self.tool_manager.invoke("ros2", "subscribe", topic=topic, message_type=message_type, callback=lambda x: x, timeout=timeout)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"ROS2 subscribe {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "data": result.data, "error": result.error}

        elif action == "sim_scenario":
            # Run a pre-built simulation scenario
            if not self.sim_library:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Simulation library not available"}
            scenario_name = step.parameters.get("scenario", "pendulum")
            backend = step.parameters.get("backend")
            modifications = step.parameters.get("modifications")
            backend_enum = SimBackend(backend) if backend else None
            result = await self.sim_library.run_scenario(scenario_name, backend=backend_enum, modifications=modifications)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Scenario '{scenario_name}' {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "frames": len(result.frames), "stats": result.stats, "error": result.error}

        elif action == "sim_custom":
            # Run a custom simulation
            if not self.sim_library:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Simulation library not available"}
            backend = step.parameters.get("backend", "blender")
            spec_params = step.parameters.get("spec", {})
            spec = SimulationSpec(**spec_params)
            backend_enum = SimBackend(backend)
            result = await self.sim_library.run_custom(spec, backend=backend_enum)
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Custom simulation {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "frames": len(result.frames), "stats": result.stats, "error": result.error}

        elif action == "vision_analyze":
            # Analyze an image
            if not self.multimodal:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Multimodal processor not available"}
            image_path = step.parameters.get("image_path")
            image_url = step.parameters.get("image_url")
            prompt = step.parameters.get("prompt", "Describe this image in detail.")
            result = await self.multimodal.process_image(
                image_path=image_path, image_url=image_url, prompt=prompt
            )
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Vision analysis {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "description": result.description, "objects": result.objects, "error": result.error}

        elif action == "audio_transcribe":
            # Transcribe audio
            if not self.multimodal:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Multimodal processor not available"}
            audio_path = step.parameters.get("audio_path")
            language = step.parameters.get("language", "en")
            result = await self.multimodal.process_audio(
                audio_path=audio_path, language=language, analyze=False
            )
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Audio transcription {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "transcript": result.transcript, "language": result.language, "error": result.error}

        elif action == "audio_analyze":
            # Analyze audio content
            if not self.multimodal:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Multimodal processor not available"}
            audio_path = step.parameters.get("audio_path")
            prompt = step.parameters.get("prompt", "What is being discussed?")
            result = await self.multimodal.process_audio(
                audio_path=audio_path, analyze=True, prompt=prompt
            )
            step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
            step.result = f"Audio analysis {'succeeded' if result.success else 'failed'}"
            return {"success": result.success, "transcript": result.transcript, "metadata": result.metadata, "error": result.error}

        elif action == "agent_create":
            # Create a new agent instance with behavioral variation
            if not self.agent_population:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Agent population not available"}
            name = step.parameters.get("name", "")
            parent_id = step.parameters.get("parent_id")
            agent = self.agent_population.create_agent(name=name, parent_id=parent_id)
            step.status = StepStatus.COMPLETED
            step.result = f"Created agent '{agent.name}' (gen {agent.generation})"
            return {"success": True, "agent_id": agent.id, "name": agent.name, "generation": agent.generation}

        elif action == "agent_reproduce":
            # Create offspring from best performers
            if not self.agent_population:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Agent population not available"}
            num_offspring = step.parameters.get("num_offspring", 2)
            offspring = []
            for _ in range(num_offspring):
                child = self.agent_population.reproduce()
                offspring.append(child)
            step.status = StepStatus.COMPLETED
            step.result = f"Created {len(offspring)} offspring"
            return {"success": True, "offspring": [{"id": a.id, "name": a.name} for a in offspring]}

        elif action == "agent_propagate":
            # Propagate strategies from a successful agent
            if not self.agent_population:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Agent population not available"}
            agent_id = step.parameters.get("agent_id")
            num_offspring = step.parameters.get("num_offspring", 2)
            propagated = self.agent_population.propagate_successful_strategies(
                agent_id, num_offspring=num_offspring
            )
            step.status = StepStatus.COMPLETED
            step.result = f"Propagated {len(propagated)} agents from {agent_id}"
            return {"success": True, "propagated": [{"id": a.id, "name": a.name} for a in propagated]}

        elif action == "agent_best":
            # Get best agents
            if not self.agent_population:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Agent population not available"}
            n = step.parameters.get("n", 5)
            best = self.agent_population.get_best(n)
            step.status = StepStatus.COMPLETED
            step.result = f"Top {len(best)} agents"
            return {"success": True, "agents": [a.to_dict() for a in best]}

        elif action == "agent_diverse":
            # Get diverse sample of agents
            if not self.agent_population:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Agent population not available"}
            n = step.parameters.get("n", 5)
            diverse = self.agent_population.get_diverse_sample(n)
            step.status = StepStatus.COMPLETED
            step.result = f"Diverse sample of {len(diverse)} agents"
            return {"success": True, "agents": [a.to_dict() for a in diverse]}

        elif action == "skill_export":
            # Export a skill as portable module
            if not self.skill_exporter or not self.skill_library:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Skill exporter or library not available"}
            skill_id = step.parameters.get("skill_id")
            if skill_id:
                portable = self.skill_exporter.export_from_library(self.skill_library, skill_id)
                if portable:
                    step.status = StepStatus.COMPLETED
                    step.result = f"Exported skill '{portable.manifest.name}'"
                    return {"success": True, "name": portable.manifest.name, "version": portable.manifest.version}
                else:
                    step.status = StepStatus.FAILED
                    return {"success": False, "error": f"Skill '{skill_id}' not found"}
            else:
                # Create new skill from parameters
                name = step.parameters.get("name", "new_skill")
                description = step.parameters.get("description", "")
                code = step.parameters.get("code", "")
                category = step.parameters.get("category", "general")
                portable = self.skill_exporter.export_skill(
                    skill_id="new",
                    name=name,
                    description=description,
                    code=code,
                    category=category,
                )
                step.status = StepStatus.COMPLETED
                step.result = f"Created and exported skill '{name}'"
                return {"success": True, "name": name, "version": portable.manifest.version}

        elif action == "skill_import":
            # Import a portable skill
            if not self.skill_exporter or not self.skill_library:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Skill exporter or library not available"}
            skill_path = step.parameters.get("path")
            if not skill_path:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "No skill path provided"}
            skill_id = self.skill_exporter.import_to_library(self.skill_library, skill_path)
            if skill_id:
                step.status = StepStatus.COMPLETED
                step.result = f"Imported skill as '{skill_id}'"
                return {"success": True, "skill_id": skill_id}
            else:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Failed to import skill"}

        elif action == "skill_list_exported":
            # List exported skills
            if not self.skill_exporter:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Skill exporter not available"}
            skills = self.skill_exporter.list_exported()
            step.status = StepStatus.COMPLETED
            step.result = f"{len(skills)} exported skills"
            return {"success": True, "skills": skills}

        elif action == "skill_template":
            # Create a skill template
            if not self.skill_exporter:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Skill exporter not available"}
            name = step.parameters.get("name", "new_skill")
            description = step.parameters.get("description", "")
            category = step.parameters.get("category", "general")
            template = self.skill_exporter.create_skill_template(name, description, category)
            step.status = StepStatus.COMPLETED
            step.result = f"Created template for '{name}'"
            return {"success": True, "code": template.code, "tests": template.tests}

        elif action == "verify_outcome":
            # Verify the outcome of a previous action
            if not self.outcome_verifier:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "Outcome verifier not available"}

            spec = VerificationSpec(
                task_type=step.parameters.get("task_type", "code"),
                success_criteria=step.parameters.get("success_criteria", {}),
                test_cases=step.parameters.get("test_cases", []),
                expected_output=step.parameters.get("expected_output"),
                timeout_seconds=step.parameters.get("timeout_seconds", 60.0),
            )
            actual_output = step.parameters.get("actual_output", step.result)
            context = step.parameters.get("context", {})
            result = await self.outcome_verifier.verify(step.parameters.get("task_type", "code"), spec, actual_output, context)
            step.status = StepStatus.COMPLETED if result.status == VerificationStatus.PASSED else StepStatus.FAILED
            step.result = f"Verification {'passed' if result.status == VerificationStatus.PASSED else 'failed'}: score={result.score:.2f}"
            return {"success": result.status == VerificationStatus.PASSED, "score": result.score, "details": result.details, "errors": result.errors, "evidence": result.evidence}

        elif action == "mcts_plan":
            # Run MCTS planning
            if not self.mcts_planner:
                step.status = StepStatus.FAILED
                return {"success": False, "error": "MCTS planner not available"}

            initial_state = step.parameters.get("initial_state", {})
            goal = step.parameters.get("goal", goal.description)
            max_time_ms = step.parameters.get("max_time_ms", 30000)

            plan = await self.mcts_planner.plan(initial_state, goal, max_time_ms)
            step.status = StepStatus.COMPLETED
            step.result = f"MCTS plan created with {len(plan.steps)} steps"
            return {"success": True, "plan_id": plan.id, "steps": len(plan.steps), "plan": plan}

    async def _check_self_improvement(self, result: dict) -> None:
        """Check if agent should improve itself. Measures before/after and auto-rollbacks."""
        # Analyze recent performance
        recent = self.execution_log[-10:] if self.execution_log else []
        success_rate = sum(
            1 for log in recent
            if all(a.get("success", False) for a in log.get("actions", []))
        ) / max(len(recent), 1)

        # Record pre-modification performance baseline
        pre_success_rate = success_rate
        pre_avg_reward = 0.0
        if recent:
            rewards = [log.get("rl_reward", 0.0) for log in recent if log.get("rl_reward") is not None]
            pre_avg_reward = sum(rewards) / max(len(rewards), 1)

        # === PROACTIVE: Create new skills when performance is decent but capabilities are limited ===
        existing_skills = await self.memory.procedural.list_skills()
        if len(existing_skills) < 5 and success_rate >= 0.5:
            # Agent has few skills — proactively create one based on what it learned
            recent_learnings = [
                log.get("actions", [{}])[0].get("step", "")
                for log in recent[-3:]
                if log.get("actions")
            ]
            if recent_learnings:
                mod = await self.self_modifier.propose_skill(
                    name=f"learned_skill_{self.iteration}",
                    description=f"Skill learned from cycle {self.iteration}: {recent_learnings[0][:100]}",
                    context=f"Recent actions: {'; '.join(recent_learnings)}",
                )
                if mod and mod.code:
                    applied = await self.self_modifier.apply_modification(mod.id)
                    if applied:
                        # Register as usable skill for future planning
                        self.planner.available_skills[mod.config.get("name", mod.id)] = mod.code
                        result["self_improvement"] = {
                            "type": "proactive_creation",
                            "skill": mod.config.get("name"),
                            "description": mod.description,
                            "applied": True,
                        }

        # === REACTIVE: Optimize existing skills when performance is low ===
        elif success_rate < 0.6:
            for skill in existing_skills:
                if skill.metadata.get("success_rate", 1.0) < 0.7:
                    mod = await self.self_modifier.propose_optimization(
                        skill_name=skill.metadata.get("skill_name", "unknown"),
                        current_code=skill.content,
                        issue="Low success rate",
                    )
                    if mod:
                        applied = await self.self_modifier.apply_modification(mod.id)
                        if applied:
                            # Actually re-measure after modification
                            post_result = await self.run_cycle()
                            post_actions = post_result.get("actions", [])
                            post_success = all(a.get("success", False) for a in post_actions) if post_actions else False
                            post_reward = post_result.get("rl_reward", 0.0)

                            perf_delta = (1.0 if post_success else 0.0 - pre_success_rate) * 0.5 + \
                                        (post_reward - pre_avg_reward) * 0.5

                            await self.self_modifier.learn_from_outcome(
                                mod.id,
                                success=perf_delta >= 0,
                                performance_delta=perf_delta,
                            )

                            result["self_improvement"] = {
                                "type": "reactive_optimization",
                                "skill": skill.metadata.get("skill_name"),
                                "pre_success_rate": pre_success_rate,
                                "post_success": post_success,
                                "performance_delta": perf_delta,
                                "applied": True,
                            }
                            break

        # === RECURSIVE: Improve the improvement process itself ===
        mod_stats = self.self_modifier.get_stats()
        if mod_stats["total_modifications"] >= 5 and mod_stats["rolled_back"] > mod_stats["applied"]:
            # More rollbacks than successes — the improvement process itself needs fixing
            mod = await self.self_modifier.propose_optimization(
                skill_name="self_modification_strategy",
                current_code=f"# Current strategy: optimize on low success, create on high\n# Success rate: {success_rate}\n# Mods applied: {mod_stats['applied']}, rolled back: {mod_stats['rolled_back']}",
                issue=f"High rollback rate: {mod_stats['rolled_back']}/{mod_stats['total_modifications']} modifications failed",
            )
            if mod:
                result["self_improvement"] = {
                    "type": "recursive_improvement",
                    "issue": "Improvement process itself is underperforming",
                    "rollback_rate": mod_stats["rolled_back"] / max(mod_stats["total_modifications"], 1),
                }

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
        """Get comprehensive agent status with memory, mood, health, and recent activity."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Memory usage
        memory_stats = {}
        if self.memory:
            memory_stats = {
                "working_memory_size": len(self.memory.working.items) if hasattr(self.memory.working, 'items') else 0,
                "episodic_count": await self.memory.episodic.count() if hasattr(self.memory.episodic, 'count') else 0,
                "semantic_count": await self.memory.semantic.count() if hasattr(self.memory.semantic, 'count') else 0,
                "procedural_count": len(await self.memory.procedural.list_skills()) if hasattr(self.memory.procedural, 'list_skills') else 0,
            }

        # Current goals
        goals_stats = {}
        if self.goals:
            active_goals = [g for g in self.goals.goals if g.status.value in ("active", "pending")]
            goals_stats = {
                "active": len(active_goals),
                "completed": sum(1 for g in self.goals.goals if g.status.value == "completed"),
                "total": len(self.goals.goals),
                "drives": await self.goals.get_drive_status(),
            }

        # Recent modifications
        recent_mods = []
        if self.self_modifier:
            history = self.self_modifier.modification_history if hasattr(self.self_modifier, 'modification_history') else []
            recent_mods = [
                {"id": m.id, "description": m.description[:100], "applied": m.applied}
                for m in history[-5:]
            ]

        # Mood/state
        mood = {}
        if self.emotional:
            mood = self.emotional.get_stats()

        # System health
        health = {}
        try:
            from .reliability import get_reliability_manager
            reliability = get_reliability_manager()
            health = {
                "circuit_breakers": reliability.get_circuit_breaker_report(),
                "component_health": reliability.get_health_report(),
            }
        except Exception:
            pass

        # Simulation library
        sim_status = {}
        if self.sim_library:
            sim_status = self.sim_library.get_backend_status()

        return {
            "state": self.state.value,
            "iteration": self.iteration,
            "uptime_seconds": uptime,
            # Memory
            "memory": memory_stats,
            # Goals & Tasks
            "goals": goals_stats,
            "plans": self.planner.get_stats() if self.planner else {},
            "current_plan": self.current_plan.to_context() if self.current_plan else None,
            # Mood & Attention
            "mood": mood,
            "attention": self.attention.get_focus_stats() if self.attention else {},
            # Recent modifications
            "recent_modifications": recent_mods,
            "self_modification": self.self_modifier.get_stats() if self.self_modifier else {},
            "recursive_modification": self.recursive_modifier.get_stats() if self.recursive_modifier else {},
            # Crawlers & Infrastructure
            "crawlers": list(self.crawlers.keys()),
            "proxy_pool": self.proxy_pool.get_stats(),
            "scheduler": self.crawl_orchestrator.scheduler.get_stats() if self.crawl_orchestrator else {},
            # Tools & Simulation
            "tools": list(self.tool_manager.tools.keys()) if self.tool_manager else [],
            "simulation": sim_status,
            # Learning
            "learning": self.learner.get_stats() if self.learner else {},
            "knowledge_graph": self.knowledge_graph.get_stats() if self.knowledge_graph else {},
            "causal_reasoning": self.causal_reasoner.get_stats() if self.causal_reasoner else {},
            "skill_composition": self.skill_composer.get_stats() if self.skill_composer else {},
            "uncertainty": self.uncertainty_tracker.get_stats() if self.uncertainty_tracker else {},
            "simulator": self.simulator.get_stats() if self.simulator else {},
            # Tier 1: Core Learning
            "pattern_learner": self.pattern_learner.get_stats() if self.pattern_learner else {},
            "rl_agent": self.rl_agent.get_stats() if self.rl_agent else {},
            # Tier 2: Advanced Cognition
            "curiosity": self.curiosity.get_stats() if self.curiosity else {},
            "world_model": self.world_model.get_stats() if self.world_model else {},
            "transfer_learner": self.transfer_learner.get_stats() if self.transfer_learner else {},
            # Tier 3: Foundation
            "meta_learner": self.meta_learner.get_stats() if self.meta_learner else {},
            "sleep_consolidator": self.sleep_consolidator.get_stats() if self.sleep_consolidator else {},
            # System Health
            "health": health,
        }

    async def autonomous_loop(self, max_cycles: int | None = None) -> None:
        """Run autonomous cognitive loop. None = infinite until Ctrl+C."""
        self.logger.info("starting_autonomous_loop", max_cycles=max_cycles or "infinite")

        i = 0
        try:
            while True:
                if max_cycles is not None and i >= max_cycles:
                    break
                result = await self.run_cycle()
                stats = self.backend.get_stats() if hasattr(self.backend, "get_stats") else {}
                self.logger.info(
                    "cycle_complete",
                    iteration=result["iteration"],
                    actions=len(result["actions"]),
                    state=result["state"],
                    **stats,
                )
                i += 1
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("autonomous_loop_stopped", cycles_completed=i)

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
            parts.append(f"Simulator:\n{self.simulator.to_context()}")
        if self.pattern_learner:
            parts.append(f"Patterns:\n{self.pattern_learner.to_context()}")
        if self.rl_agent:
            parts.append(f"RL Agent:\n{self.rl_agent.to_context()}")
        if self.curiosity:
            parts.append(f"Curiosity:\n{self.curiosity.to_context()}")
        if self.world_model:
            parts.append(f"World Model:\n{self.world_model.to_context()}")
        if self.transfer_learner:
            parts.append(f"Transfer Learning:\n{self.transfer_learner.to_context()}")
        if self.meta_learner:
            parts.append(f"Meta-Learning:\n{self.meta_learner.to_context()}")
        if self.sleep_consolidator:
            parts.append(f"Sleep/Consolidation:\n{self.sleep_consolidator.to_context()}")
        if self.attention:
            parts.append(f"Attention:\n{self.attention.to_context()}")
        if self.emotional:
            parts.append(f"Emotional State:\n{self.emotional.to_context()}")
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

        if self.tool_manager:
            await self.tool_manager.close()

        if self.workspace:
            await self.workspace.cleanup()

        self.logger.info(
            "cognitive_agent_closed",
            proxy_stats=self.proxy_pool.get_stats(),
        )
