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
from .world_selector import WorldSelector, SelectionCriteria
from .sensor_sim import SensorArray
from .failure_injection import FailureInjector
from .navigation import ObstacleAvoidance, PathPlanner, SLAMSimulation, WaypointFollower
from .weather import WeatherSystem
from .locomotion import LocomotionController
from .manipulation_tasks import ManipulationController
from .social_sim import SocialSimulator
from .self_reflection import SelfReflectionEngine
from .evo_architecture import EvoArchitecture
from .modification_memory import ModificationMemory
from .model_trainer import ModelTrainer
from .custom_model_manager import CustomModelManager
from .model_evaluation import ModelEvaluator, QualityGate, RollbackManager, ABTestRunner
from .production import PerformanceMonitor, RetrainingTrigger, CircuitBreaker, GracefulDegradation, MetricType
from .self_training import SelfTrainingSynthesizer
from .contrastive_trainer import ContrastiveTrainer
from .model_population import ModelPopulation
from .emergent_curriculum import EmergentCurriculum
from .adversarial_trainer import AdversarialTrainer
from .architecture_modifier import ArchitectureModifier
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

        # World selector for practical worlds
        self.world_selector: WorldSelector | None = None

        # Sensor simulation
        self.sensor_array: SensorArray | None = None

        # Failure injection
        self.failure_injector: FailureInjector | None = None

        # Navigation
        self.obstacle_avoidance: ObstacleAvoidance | None = None
        self.path_planner: PathPlanner | None = None
        self.slam: SLAMSimulation | None = None
        self.waypoint_follower: WaypointFollower | None = None

        # Weather
        self.weather: WeatherSystem | None = None

        # Locomotion
        self.locomotion: LocomotionController | None = None

        # Manipulation
        self.manipulation: ManipulationController | None = None

        # Social simulation
        self.social: SocialSimulator | None = None

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

        # Build four-tier hybrid backend: routine + code + reasoning + modifier
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

        # Modifier backend: uses maldoror when deployed, otherwise falls back to code
        modifier_backend = None

        self.logger.info(
            "four_tier_llm",
            routine=self.settings.llm.model,
            code=self.settings.code_llm.model if code_backend else "disabled",
            reasoning=self.settings.heavy_llm.model if reasoning_backend else "disabled",
            modifier="maldoror (on-demand)",
        )

        self.backend = HybridBackend(
            routine=routine_backend,
            code=code_backend,
            reasoning=reasoning_backend,
            modifier=modifier_backend,
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

        # Initialize world selector
        self.world_selector = WorldSelector()

        # Initialize simulation modules
        self.sensor_array = SensorArray()
        self.failure_injector = FailureInjector()
        self.obstacle_avoidance = ObstacleAvoidance()
        self.path_planner = PathPlanner()
        self.slam = SLAMSimulation()
        self.waypoint_follower = WaypointFollower()
        self.weather = WeatherSystem()
        self.locomotion = LocomotionController()
        self.manipulation = ManipulationController()
        self.social = SocialSimulator()

        # === Autonomy Modules for AGI Progression ===
        self.self_reflection = SelfReflectionEngine(backend=self.backend)
        self.evo_architecture = EvoArchitecture(backend=self.backend)
        # Note: uncertainty, curiosity, causal_reasoning, world_model, attention
        # are already initialized above; their new methods are accessed directly.

        # === Maldoror Custom Model Pipeline ===
        self.modification_memory = ModificationMemory()
        self.model_trainer = ModelTrainer(
            modification_memory=self.modification_memory,
        )
        self.custom_model_manager = CustomModelManager(
            model_trainer=self.model_trainer,
        )

        # === Phase 4: Evaluation & Rollback ===
        self.model_evaluator: ModelEvaluator | None = None
        self.quality_gate = QualityGate(min_score=0.5, max_latency_ms=10000)
        self.rollback_manager: RollbackManager | None = None
        self.ab_test_runner: ABTestRunner | None = None

        # === Phase 5: Production Readiness ===
        self.perf_monitor = PerformanceMonitor()
        self.retrain_trigger = RetrainingTrigger(monitor=self.perf_monitor)
        self.circuit_breaker = CircuitBreaker()
        self.graceful = GracefulDegradation(
            circuit_breaker=self.circuit_breaker,
            monitor=self.perf_monitor,
        )

        # Initialize evaluation components (needs backend)
        self.model_evaluator = ModelEvaluator(
            base_backend=routine_backend,
            output_dir="data/maldoror/eval",
        )
        self.rollback_manager = RollbackManager(
            custom_model_manager=self.custom_model_manager,
        )
        self.ab_test_runner = ABTestRunner(evaluator=self.model_evaluator)

        # === Self-Training Loop ===
        self.self_trainer = SelfTrainingSynthesizer(
            backend=self.backend,
            modification_memory=self.modification_memory,
        )
        self.contrastive_trainer = ContrastiveTrainer(
            backend=self.backend,
            modification_memory=self.modification_memory,
        )

        # === Population-Based Training ===
        self.model_population = ModelPopulation(
            model_trainer=self.model_trainer,
            modification_memory=self.modification_memory,
            evaluator=self.model_evaluator,
        )

        # === Emergent Curriculum & Adversarial Training ===
        self.emergent_curriculum = EmergentCurriculum(
            backend=self.backend,
            modification_memory=self.modification_memory,
        )
        self.adversarial_trainer = AdversarialTrainer(
            backend=self.backend,
            modification_memory=self.modification_memory,
        )

        # === Architecture Modifier (neural network structural modification) ===
        self.architecture_modifier = ArchitectureModifier(
            output_dir="data/maldoror/architecture",
        )

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

                        # === Self-Training Loop: synthesize training data from recursive mod ===
                        try:
                            from .modification_memory import ModificationRecord
                            synth_record = ModificationRecord(
                                id=recursive_mod.id,
                                timestamp=datetime.utcnow().isoformat(),
                                source_module="recursive_modify",
                                target_file=recursive_mod.file_path,
                                task_type="code_rewrite",
                                description=recursive_mod.description,
                                reasoning=recursive_mod.reasoning,
                                original_code=recursive_mod.original_code[:1500] if hasattr(recursive_mod, 'original_code') else "",
                                modified_code=recursive_mod.new_code[:3000] if hasattr(recursive_mod, 'new_code') else "",
                                success=True,
                            )
                            synthesized = await self.self_trainer.synthesize_from_success(synth_record)
                            if synthesized:
                                result["self_training"] = {
                                    "synthesized": len(synthesized),
                                    "types": [e.synth_type for e in synthesized],
                                }
                        except Exception as e:
                            self.logger.warning("self_training_synthesis_error", error=str(e))
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

                # 23. Auto-render snippet for significant events
                try:
                    await self._auto_render_significant_event(result)
                except Exception as e:
                    self.logger.warning("auto_render_error", error=str(e))

                # 24. Maldoror retraining check — smart trigger (Phase 5)
                if self.model_trainer and self.modification_memory:
                    trigger = self.retrain_trigger.should_retrain(
                        current_iteration=self.iteration,
                        training_data_ready=self.modification_memory.ready_for_training(min_examples=20),
                        current_model_version=self.model_trainer.current_version,
                    )
                    if trigger["retrain"]:
                        asyncio.create_task(self._maldoror_retrain(result))

                # 25. Population-based training every 20 iterations
                if self.iteration % 20 == 0 and self.model_population:
                    asyncio.create_task(self._population_compete(result))

                # 26. Emergent curriculum — generate targeted training tasks every 10 iterations
                if self.iteration % 10 == 0 and self.emergent_curriculum:
                    asyncio.create_task(self._emergent_curriculum_generate(result))

                # 27. Adversarial training — critique self-attempts every 15 iterations
                if self.iteration % 15 == 0 and self.adversarial_trainer:
                    asyncio.create_task(self._adversarial_train(result))

                # 28. Architecture modification — structural evolution every 50 iterations
                if self.iteration % 50 == 0 and self.architecture_modifier:
                    asyncio.create_task(self._architecture_modify(result))

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

    async def _maldoror_retrain(self, result: dict) -> None:
        """Background task: ingest, train, evaluate, deploy (with rollback on regression)."""
        try:
            ingested = self.modification_memory.ingest_from_training_logs()
            if ingested > 0:
                self.logger.info("training_logs_ingested", count=ingested)
            if not self.modification_memory.ready_for_training(min_examples=20):
                return
            self.logger.info("starting_maldoror_training", version=self.model_trainer.current_version)
            run = await self.model_trainer.train(max_steps=200)
            if not run.success:
                self.logger.warning("maldoror_training_failed", error=run.error)
                self.perf_monitor.record(MetricType.ERROR_RATE, 1.0, model_version=self.model_trainer.current_version)
                return

            # Record training metrics
            self.perf_monitor.record(MetricType.LATENCY, run.duration_seconds * 1000, model_version=run.version)

            # Deploy to Ollama
            deployed = await self.custom_model_manager.deploy(run)
            if not deployed:
                return

            # Phase 4: Evaluate before activating
            if self.model_evaluator and self.model_evaluator.maldoror is None:
                # Create maldoror backend for evaluation
                mal_backend = LLMBackend(
                    api_key=self.settings.llm.api_key or "ollama",
                    model=deployed.name,
                    api_base=self.settings.llm.api_base,
                )
                self.model_evaluator.maldoror = mal_backend

            if self.model_evaluator and self.model_evaluator.maldoror:
                report = await self.model_evaluator.compare()
                gate = await self.quality_gate.check(report)

                # Record evaluation metrics
                self.perf_monitor.record(MetricType.QUALITY_SCORE, report.maldoror_avg, model_version=run.version)
                self.perf_monitor.record(MetricType.SUCCESS_RATE, 1.0 if gate["passed"] else 0.0, model_version=run.version)

                result["evaluation"] = {
                    "verdict": report.verdict,
                    "improvement_pct": report.improvement_pct,
                    "base_avg": report.base_avg,
                    "maldoror_avg": report.maldoror_avg,
                    "gate_passed": gate["passed"],
                    "gate_checks": gate["checks"],
                }

                if not gate["passed"]:
                    self.logger.warning("quality_gate_failed", checks=gate["checks"])
                    if self.rollback_manager and await self.rollback_manager.should_rollback(gate):
                        await self.rollback_manager.rollback(reason=f"quality_gate_failed: {gate['checks']}")
                        result["rollback"] = True
                        return

            # Gates passed (or no evaluator) — activate maldoror
            await self.custom_model_manager.switch_to(deployed.version)
            modifier_llm = LLMBackend(
                api_key=self.settings.llm.api_key or "ollama",
                model=deployed.name,
                api_base=self.settings.llm.api_base,
            )
            self.backend.update_modifier(modifier_llm)
            self.model_evaluator.maldoror = modifier_llm if self.model_evaluator else None
            self.logger.info("maldoror_deployed_and_swapped", version=run.version)
            result["maldoror_training"] = {
                "version": run.version,
                "loss": run.loss,
                "deployed": True,
                "num_examples": run.num_examples,
            }
        except Exception as e:
            self.logger.warning("maldoror_retrain_error", error=str(e))

    async def _population_compete(self, result: dict) -> None:
        """Background task: run population competition to evolve better training strategies."""
        try:
            if not self.model_population:
                return
            if not self.modification_memory.ready_for_training(min_examples=10):
                return

            self.logger.info("starting_population_competition", generation=self.model_population.generation)
            best = await self.model_population.compete()

            if best and best.training_run and best.training_run.success:
                # Deploy the winner
                deployed = await self.custom_model_manager.deploy(best.training_run)
                if deployed:
                    await self.custom_model_manager.switch_to(best.training_run.version)
                    modifier_llm = LLMBackend(
                        api_key=self.settings.llm.api_key or "ollama",
                        model=deployed.name,
                        api_base=self.settings.llm.api_base,
                    )
                    self.backend.update_modifier(modifier_llm)
                    self.logger.info(
                        "population_winner_deployed",
                        strategy=best.config.name,
                        fitness=best.fitness,
                        generation=best.generation,
                    )
                    result["population_competition"] = {
                        "generation": best.generation,
                        "winner_strategy": best.config.name,
                        "winner_fitness": best.fitness,
                        "best_fitness": self.model_population.best_variant.fitness if self.model_population.best_variant else 0,
                    }
        except Exception as e:
            self.logger.warning("population_competition_error", error=str(e))

    async def _emergent_curriculum_generate(self, result: dict) -> None:
        """Background task: analyze weaknesses and generate targeted training tasks."""
        try:
            if not self.emergent_curriculum:
                return
            if not self.modification_memory.records:
                return

            self.logger.info("starting_emergent_curriculum")
            tasks = await self.emergent_curriculum.generate_curriculum()

            if tasks:
                result["emergent_curriculum"] = {
                    "tasks_generated": len(tasks),
                    "weaknesses_addressed": len(set(t.weakness_type for t in tasks)),
                }
        except Exception as e:
            self.logger.warning("emergent_curriculum_error", error=str(e))

    async def _adversarial_train(self, result: dict) -> None:
        """Background task: generate adversarial training data (attempt + critique + counter-example)."""
        try:
            if not self.adversarial_trainer:
                return
            if not self.modification_memory.records:
                return

            self.logger.info("starting_adversarial_training")
            examples = await self.adversarial_trainer.generate_adversarial_data()

            if examples:
                result["adversarial_training"] = {
                    "examples_generated": len(examples),
                    "flaw_categories": list(set(
                        cat for ex in examples for cat in ex.flaw_categories
                    )),
                }
        except Exception as e:
            self.logger.warning("adversarial_training_error", error=str(e))

    async def _architecture_modify(self, result: dict) -> None:
        """Background task: attempt structural modification of the model architecture."""
        try:
            if not self.architecture_modifier:
                return

            # Recommend a modification based on history
            modification = self.architecture_modifier.recommend_modification()
            if not modification:
                return

            self.logger.info(
                "starting_architecture_modification",
                mod_type=modification.mod_type.value,
                description=modification.description,
            )

            # Apply the modification
            mod_result = await self.architecture_modifier.apply_modification(modification)

            if mod_result.success:
                result["architecture_modification"] = {
                    "mod_type": modification.mod_type.value,
                    "description": modification.description,
                    "eval_score": mod_result.eval_score,
                    "duration": mod_result.duration_seconds,
                    "new_version": mod_result.after_state.version if mod_result.after_state else "unknown",
                }
            else:
                result["architecture_modification"] = {
                    "mod_type": modification.mod_type.value,
                    "success": False,
                    "error": mod_result.error,
                }

        except Exception as e:
            self.logger.warning("architecture_modification_error", error=str(e))

    async def _auto_render_significant_event(self, result: dict) -> None:
        """Auto-render MP4 snippet for significant events."""
        if not self.blender_sandbox:
            return

        # Check video budget
        if not self.blender_sandbox.video_budget.can_render(3.0):
            return

        # Determine if this cycle had a significant event
        significant = False
        event_type = "cycle"

        # Goal completed
        if result.get("goals_progress"):
            for progress in result["goals_progress"]:
                if progress.get("progress", 0) >= 1.0:
                    significant = True
                    event_type = "goal_complete"
                    break

        # Self-modification succeeded
        if result.get("self_improvement") or result.get("recursive_modification"):
            significant = True
            event_type = "self_modify"

        # High reward
        if result.get("rl_reward", 0) > 0.7:
            significant = True
            event_type = "high_reward"

        # Emotional state change
        if result.get("emotional_state") and result["emotional_state"] != "neutral":
            significant = True
            event_type = f"emotion_{result['emotional_state']}"

        if not significant:
            return

        # Create snippet render
        from .blender_sandbox import SimulationSpec, SimulationType
        spec = SimulationSpec(
            type=SimulationType.EMOTION,
            emotion_config={
                "mood": result.get("emotional_state", "neutral"),
                "valence": 0.5 if "happy" in event_type else -0.3 if "sad" in event_type or "fail" in event_type else 0.0,
                "arousal": 0.7 if "high_reward" in event_type or "goal" in event_type else 0.4,
            },
            emotion_visualizer=self.settings.emotion_visualizer,
            render=True,
            render_animation=True,
            snippet_mode=True,
            snippet_duration=3.0,
            frame_start=1,
            frame_end=90,  # 3 seconds at 30fps
            fps=30,
            render_resolution=(1280, 720),
            render_engine="BLENDER_EEVEE",  # Fast rendering
            render_samples=32,
            output_path=f"data/blender/snippets/{event_type}",
            video_output_path=f"data/blender/snippets/{event_type}/snippet_{self.iteration}.mp4",
        )

        try:
            render_result = await self.blender_sandbox.run_render(spec)
            if render_result.success and render_result.video_path:
                result["auto_render"] = {
                    "event": event_type,
                    "video_path": render_result.video_path,
                }
                self.logger.info("auto_render_complete", event=event_type, path=render_result.video_path)
        except Exception as e:
            self.logger.warning("auto_render_failed", error=str(e))

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

            # Check practical worlds first
            from crawler_agent.cognitive.practical_worlds import get_practical_world
            practical = get_practical_world(scenario_name)

            # If not in practical worlds, check survival worlds
            if not practical:
                from crawler_agent.cognitive.survival_worlds import get_survival_world
                survival = get_survival_world(scenario_name)
                if survival:
                    # Convert survival world to simulation spec
                    spec = SimulationSpec(
                        type=SimulationType.RIGID_BODY,
                        objects=[
                            ObjectSpec(
                                type=obj.get("type", "cube"),
                                position=tuple(obj.get("position", [0, 0, 0])),
                                scale=tuple(obj.get("scale", [1, 1, 1])),
                                mass=obj.get("mass", 1.0),
                                passive=obj.get("passive", False),
                            )
                            for obj in survival.objects
                        ],
                        duration=survival.time_limit if survival.time_limit > 0 else 10.0,
                        fps=60,
                        generate_buildings=False,
                    )
                    result = await self.sim_library.run_custom(spec, backend=backend_enum)
                    step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
                    step.result = f"Survival world '{scenario_name}' {'succeeded' if result.success else 'failed'}"
                    return {"success": result.success, "frames": len(result.frames), "stats": result.stats, "error": result.error}

            # Anatomy mode: use practical worlds by default
            if self.settings.emotion_visualizer in ("anatomy", "both") and practical:
                from crawler_agent.cognitive.practical_worlds import PRACTICAL_WORLDS, get_practical_world
                practical = get_practical_world(scenario_name)
                if practical:
                    # Convert practical world to simulation spec
                    spec = SimulationSpec(
                        type=SimulationType.RIGID_BODY,
                        objects=[
                            ObjectSpec(
                                type=obj.get("type", "cube"),
                                position=tuple(obj.get("position", [0, 0, 0])),
                                scale=tuple(obj.get("scale", [1, 1, 1])),
                                mass=obj.get("mass", 1.0),
                                passive=obj.get("passive", False),
                            )
                            for obj in practical.objects
                        ],
                        duration=10.0,
                        fps=60,
                        generate_buildings=False,
                    )
                    result = await self.sim_library.run_custom(spec, backend=backend_enum)
                    step.status = StepStatus.COMPLETED if result.success else StepStatus.FAILED
                    step.result = f"Practical world '{scenario_name}' {'succeeded' if result.success else 'failed'}"
                    return {"success": result.success, "frames": len(result.frames), "stats": result.stats, "error": result.error}

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

        elif action == "select_world":
            # Select practical or survival world based on skill needs
            if not self.world_selector:
                self.world_selector = WorldSelector()
            goal = step.parameters.get("goal", "")
            max_difficulty = step.parameters.get("max_difficulty", 1.0)
            weak_skills = step.parameters.get("weak_skills", [])
            tier = step.parameters.get("tier")  # Optional: force specific tier
            criteria = SelectionCriteria(
                weak_skills=weak_skills or self.world_selector.get_weak_skills(),
                goal_description=goal,
                max_difficulty=max_difficulty,
            )
            result = self.world_selector.select(criteria)
            world = result.world
            step.status = StepStatus.COMPLETED
            step.result = f"Selected world: {world.name} - {result.reason}"
            return {
                "success": True,
                "world": world.name,
                "description": world.description,
                "difficulty": world.difficulty if hasattr(world, 'difficulty') else world.tier / 4.0,
                "tags": world.tags if hasattr(world, 'tags') else [],
                "matched_skills": result.matched_skills,
                "reason": result.reason,
                "is_survival": hasattr(world, 'tier'),
                "tier": world.tier if hasattr(world, 'tier') else None,
                "hazards": [h.value for h in world.hazards] if hasattr(world, 'hazards') else [],
            }

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

        # ═══════════════════════════════════════════════════════════════
        # Simulation modules
        # ═══════════════════════════════════════════════════════════════

        elif action == "sensor_read":
            # Read sensor data
            if not self.sensor_array:
                self.sensor_array = SensorArray()
            robot_pos = step.parameters.get("robot_pos", [0, 0, 0])
            object_positions = step.parameters.get("object_positions", {})
            readings = self.sensor_array.read_all(object_positions, robot_pos)
            step.status = StepStatus.COMPLETED
            step.result = f"Sensor readings: {list(readings.keys())}"
            return {"success": True, "readings": {k: v.data for k, v in readings.items()}}

        elif action == "yolo_detect":
            # YOLO object detection
            if not self.sensor_array:
                self.sensor_array = SensorArray()
            image = step.parameters.get("image")
            depth_map = step.parameters.get("depth_map")
            model_size = step.parameters.get("model_size")
            if model_size:
                self.sensor_array.yolo.model_size = model_size
            result = self.sensor_array.yolo.detect(image, depth_map)
            persons = self.sensor_array.yolo.detect_persons(result)
            obstacles = self.sensor_array.yolo.get_navigation_obstacles(result)
            step.status = StepStatus.COMPLETED
            step.result = f"YOLO: {result.count} objects detected ({result.inference_time_ms:.1f}ms)"
            return {
                "success": True,
                "count": result.count,
                "objects": [o.to_dict() for o in result.objects],
                "persons": [o.to_dict() for o in persons],
                "obstacles": [o.to_dict() for o in obstacles],
                "inference_ms": result.inference_time_ms,
                "model": result.model_name,
            }

        elif action == "failure_inject":
            # Inject failure
            if not self.failure_injector:
                self.failure_injector = FailureInjector()
            failure_type = step.parameters.get("type", "battery_drain")
            if failure_type == "battery_drain":
                dt = step.parameters.get("dt", 1.0)
                level = self.failure_injector.drain_battery(dt)
                step.result = f"Battery: {level:.0%}"
            elif failure_type == "structural_damage":
                damage = step.parameters.get("damage", 0.1)
                loc = step.parameters.get("location", "unknown")
                integrity = self.failure_injector.apply_structural_damage(damage, loc)
                step.result = f"Structural integrity: {integrity:.0%}"
            elif failure_type == "sensor_noise":
                sensor = step.parameters.get("sensor", "depth")
                noise = step.parameters.get("noise", 0.3)
                self.failure_injector.inject_sensor_noise(sensor, noise)
                step.result = f"Injected noise into {sensor}"
            elif failure_type == "actuator_jam":
                actuator = step.parameters.get("actuator", "arm")
                self.failure_injector.jam_actuator(actuator)
                step.result = f"Jammed {actuator}"
            elif failure_type == "comm_loss":
                severity = step.parameters.get("severity", 0.5)
                self.failure_injector.simulate_communication_loss(severity=severity)
                step.result = f"Communication degraded to {severity:.0%}"
            step.status = StepStatus.COMPLETED
            return {"success": True, "state": self.failure_injector.get_status()}

        elif action == "navigate":
            # Path planning and obstacle avoidance
            if not self.path_planner:
                self.path_planner = PathPlanner()
            if not self.obstacle_avoidance:
                self.obstacle_avoidance = ObstacleAvoidance()
            start = step.parameters.get("start", [0, 0, 0])
            goal = step.parameters.get("goal", [10, 0, 0])
            obstacles = step.parameters.get("obstacles", {})
            algorithm = step.parameters.get("algorithm", "astar")

            if algorithm == "astar":
                path = self.path_planner.a_star(start, goal, obstacles)
            elif algorithm == "rrt":
                path = self.path_planner.rrt(start, goal, obstacles)
            else:
                path = self.path_planner.dijkstra(start, goal, obstacles)

            step.status = StepStatus.COMPLETED if path.valid else StepStatus.FAILED
            step.result = f"Path {algorithm}: {len(path.waypoints)} waypoints, cost={path.cost:.2f}"
            return {"success": path.valid, "waypoints": path.waypoints, "cost": path.cost,
                    "algorithm": algorithm}

        elif action == "weather_update":
            # Update weather
            if not self.weather:
                self.weather = WeatherSystem()
            wind_speed = step.parameters.get("wind_speed", 0)
            rain = step.parameters.get("rain", 0)
            fog = step.parameters.get("fog", 0)
            temp = step.parameters.get("temperature", 22)
            self.weather.set_weather(wind_speed, rain, fog, temp)
            state = self.weather.update(0.01)
            step.status = StepStatus.COMPLETED
            step.result = f"Weather: wind={wind_speed}m/s, rain={rain:.0%}, fog={fog:.0%}"
            return {"success": True, "state": state}

        elif action == "locomotion":
            # Update locomotion
            if not self.locomotion:
                self.locomotion = LocomotionController()
            mode = step.parameters.get("mode")
            if mode:
                self.locomotion.set_mode(mode)
            cmd = step.parameters.get("cmd", {})
            self.locomotion.set_cmd(**cmd)
            state = self.locomotion.update(0.01)
            step.status = StepStatus.COMPLETED
            step.result = f"Locomotion ({self.locomotion.mode}): pos={state.position}"
            return {"success": True, "position": state.position, "velocity": state.velocity}

        elif action == "manipulate":
            # Execute manipulation task
            if not self.manipulation:
                self.manipulation = ManipulationController()
            task_type = step.parameters.get("task_type", "assembly")
            self.manipulation.start_task(task_type, **step.parameters.get("setup", {}))
            result = self.manipulation.execute(**step.parameters.get("execute", {}))
            step.status = StepStatus.COMPLETED
            step.result = f"Manipulation ({task_type}): progress={result.progress:.0%}, success={result.success}"
            return {"success": result.success, "progress": result.progress, "step": result.step}

        elif action == "social_update":
            # Update social simulation
            if not self.social:
                self.social = SocialSimulator()
            robot_pos = step.parameters.get("robot_pos", [0, 0, 0])
            add_humans = step.parameters.get("add_humans", [])
            for h in add_humans:
                self.social.crowd.add_human(h.get("position", [0, 0]), h.get("target"))
            state = self.social.update(0.01, robot_pos)
            step.status = StepStatus.COMPLETED
            step.result = f"Social: {state['crowd']['total_humans']} humans"
            return {"success": True, "state": state}

        elif action == "crowd_panic":
            # Trigger crowd panic
            if not self.social:
                self.social = SocialSimulator()
            epicenter = step.parameters.get("epicenter", [0, 0, 0])
            radius = step.parameters.get("radius", 10.0)
            self.social.crowd.trigger_panic(epicenter, radius)
            step.status = StepStatus.COMPLETED
            step.result = f"Panic triggered at {epicenter}"
            return {"success": True}

        elif action == "gesture_detect":
            # Detect gesture from nearest human
            if not self.social:
                self.social = SocialSimulator()
            robot_pos = step.parameters.get("robot_pos", [0, 0, 0])
            nearest = self.social.crowd.get_nearest_human(robot_pos)
            if nearest:
                gesture = self.social.gesture.detect(nearest, robot_pos)
                step.status = StepStatus.COMPLETED
                step.result = f"Gesture: {gesture.type} ({gesture.confidence:.0%})"
                return {"success": True, "gesture": gesture.type, "confidence": gesture.confidence,
                        "meaning": self.social.gesture.get_meaning(gesture)}
            step.status = StepStatus.COMPLETED
            step.result = "No humans detected"
            return {"success": True, "gesture": "none"}

        # === Autonomy Module Actions ===

        elif action == "self_reflect":
            # Record and reflect on an action
            action_type = step.parameters.get("action_type", "unknown")
            description = step.parameters.get("description", "")
            intended = step.parameters.get("intended_outcome", "")
            actual = step.parameters.get("actual_outcome", "")
            success = step.parameters.get("success", True)

            record = await self.self_reflection.record_action(
                action_type=action_type,
                description=description,
                intended_outcome=intended,
            )
            reflection = await self.self_reflection.reflect_on_action(
                action=record,
                actual_outcome=actual,
                success=success,
            )
            step.status = StepStatus.COMPLETED
            step.result = f"Reflection: {reflection.lesson_learned[:100]}"
            return {"success": True, "reflection": reflection.lesson_learned,
                    "type": reflection.reflection_type.value}

        elif action == "self_reflect_review":
            # Pre-action review from self-reflection
            action_type = step.parameters.get("action_type", "unknown")
            review = await self.self_reflection.pre_action_review(action_type)
            step.status = StepStatus.COMPLETED
            step.result = f"Review: {len(review.get('warnings', []))} warnings"
            return {"success": True, **review}

        elif action == "uncertainty_track":
            # Track confidence for an action
            action_type = step.parameters.get("action_type", "unknown")
            guidance = await self.uncertainty.track_action_confidence(
                action_id=step.id,
                action_type=action_type,
            )
            step.status = StepStatus.COMPLETED
            step.result = f"Confidence: {guidance['confidence_level']}"
            return {"success": True, **guidance}

        elif action == "uncertainty_update":
            # Update confidence after action
            action_type = step.parameters.get("action_type", "unknown")
            outcome_success = step.parameters.get("success", True)
            surprise = step.parameters.get("surprise", 0.0)
            await self.uncertainty.update_action_confidence(
                action_id=step.id,
                action_type=action_type,
                outcome_success=outcome_success,
                outcome_surprise=surprise,
            )
            step.status = StepStatus.COMPLETED
            step.result = "Confidence updated"
            return {"success": True}

        elif action == "uncertainty_epistemic":
            # Deep epistemic uncertainty analysis
            domain = step.parameters.get("domain", "general")
            known = step.parameters.get("known", [])
            result = await self.uncertainty.identify_epistemic_gaps(domain, known)
            step.status = StepStatus.COMPLETED
            step.result = f"Epistemic analysis: {len(result.get('known', []))} known, {len(result.get('uncertain', []))} uncertain"
            return {"success": True, **result}

        elif action == "intrinsic_goals":
            # Generate intrinsic motivation goals
            capabilities = step.parameters.get("capabilities", {})
            weaknesses = step.parameters.get("weaknesses", [])
            goals = await self.curiosity.generate_intrinsic_goals(capabilities, weaknesses)
            step.status = StepStatus.COMPLETED
            step.result = f"Generated {len(goals)} intrinsic goals"
            return {"success": True, "goals": goals[:5]}

        elif action == "drive_state":
            # Evaluate motivational state
            state = await self.curiosity.evaluate_drive_state()
            step.status = StepStatus.COMPLETED
            step.result = f"Dominant drive: {state['dominant_drive']}"
            return {"success": True, **state}

        elif action == "competence_gaps":
            # Analyze competence gaps
            performance = step.parameters.get("performance", {})
            gaps = await self.curiosity.assess_competence_gaps(performance)
            step.status = StepStatus.COMPLETED
            step.result = f"Found {len(gaps)} competence gaps"
            return {"success": True, "gaps": gaps}

        elif action == "temporal_causality":
            # Discover temporal causal relationships
            events = step.parameters.get("events", [])
            discovered = await self.causal_reasoning.discover_temporal_causality(events)
            step.status = StepStatus.COMPLETED
            step.result = f"Discovered {len(discovered)} causal edges"
            return {"success": True, "edges": len(discovered)}

        elif action == "plan_interventions":
            # Plan causal interventions
            outcome = step.parameters.get("desired_outcome", "")
            state = step.parameters.get("current_state", {})
            constraints = step.parameters.get("constraints", [])
            plan = await self.causal_reasoning.plan_interventions(outcome, state, constraints)
            step.status = StepStatus.COMPLETED
            interventions = plan.get("intervention_plan", [])
            step.result = f"Planned {len(interventions)} interventions"
            return {"success": True, **plan}

        elif action == "predict_cascade":
            # Predict cascade effects
            change = step.parameters.get("change", {})
            depth = step.parameters.get("depth", 3)
            result = await self.causal_reasoning.predict_cascade(change, depth)
            step.status = StepStatus.COMPLETED
            step.result = f"Cascade: {result['variables_affected']} variables affected"
            return {"success": True, **result}

        elif action == "world_predict":
            # Make prediction with world model
            query = step.parameters.get("query", "")
            context = step.parameters.get("context", {})
            result = await self.world_model.predict_and_update(query, context)
            step.status = StepStatus.COMPLETED
            step.result = f"Prediction: {result['predicted_probability']:.2f}"
            return {"success": True, **result}

        elif action == "world_update":
            # Update world model from outcome
            pred_id = step.parameters.get("prediction_id", "")
            outcome = step.parameters.get("outcome", True)
            obs = step.parameters.get("observation", {})
            result = await self.world_model.update_from_outcome(pred_id, outcome, obs)
            step.status = StepStatus.COMPLETED
            step.result = f"Error: {result.get('prediction_error', 0):.2f}"
            return {"success": True, **result}

        elif action == "world_simulate":
            # Internal simulation before action
            action_name = step.parameters.get("action", "")
            context = step.parameters.get("context", {})
            result = await self.world_model.internal_simulation(action_name, context)
            step.status = StepStatus.COMPLETED
            step.result = f"Sim confidence: {result.get('simulation_confidence', 0):.2f}"
            return {"success": True, **result}

        elif action == "evo_evolve":
            # Evolve architecture
            tasks = step.parameters.get("tasks", ["general"])
            if not self.evo_architecture.variants:
                await self.evo_architecture.initialize_population()
            variants = await self.evo_architecture.evolve_generation(tasks)
            step.status = StepStatus.COMPLETED
            stats = self.evo_architecture.get_stats()
            step.result = f"Gen {stats['generation']}: best={stats['best_fitness']:.3f}"
            return {"success": True, **stats}

        elif action == "evo_evaluate":
            # Evaluate a specific variant
            variant_id = step.parameters.get("variant_id", "")
            tasks = step.parameters.get("tasks", ["general"])
            variant = self.evo_architecture.variants.get(variant_id)
            if variant:
                result = await self.evo_architecture.evaluate_variant(variant, tasks)
                step.status = StepStatus.COMPLETED
                step.result = f"Fitness: {result.overall_fitness:.3f}"
                return {"success": True, "fitness": result.overall_fitness}
            step.status = StepStatus.FAILED
            step.result = "Variant not found"
            return {"success": False, "error": "Variant not found"}

        elif action == "attention_allocate":
            # Allocate compute resources
            components = step.parameters.get("components", ["attention", "reasoning", "working_memory"])
            uncertainty = step.parameters.get("uncertainty", {})
            context = step.parameters.get("context", {})
            allocation = await self.attention.allocate_compute(
                available_components=components,
                task_context=context,
                uncertainty_data=uncertainty,
            )
            step.status = StepStatus.COMPLETED
            step.result = f"Allocated to {len(allocation)} components"
            return {"success": True, "allocation": allocation}

        elif action == "attention_adaptive":
            # Adaptive attention with uncertainty
            stimulus = step.parameters.get("stimulus", "")
            uncertainty = step.parameters.get("uncertainty", 0.5)
            relevance = step.parameters.get("relevance", 0.5)
            result = await self.attention.adaptive_attention(
                stimulus=stimulus,
                uncertainty=uncertainty,
                task_relevance=relevance,
            )
            step.status = StepStatus.COMPLETED
            step.result = f"Focus: {result['should_focus']}, Score: {result['attention_score']:.2f}"
            return {"success": True, **result}

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

                        # === Self-Training Loop: synthesize training data from success ===
                        try:
                            from .modification_memory import ModificationRecord
                            synth_record = ModificationRecord(
                                id=mod.id,
                                timestamp=datetime.utcnow().isoformat(),
                                source_module="self_modify",
                                target_file=mod.config.get("name", "unknown"),
                                task_type="skill_creation",
                                description=mod.description,
                                reasoning=mod.reasoning,
                                modified_code=mod.code,
                                success=True,
                            )
                            synthesized = await self.self_trainer.synthesize_from_success(synth_record)
                            if synthesized:
                                result["self_training"] = {
                                    "synthesized": len(synthesized),
                                    "types": [e.synth_type for e in synthesized],
                                }
                        except Exception as e:
                            self.logger.warning("self_training_synthesis_error", error=str(e))

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

                            # === Self-Training Loop: synthesize training data from success ===
                            if perf_delta >= 0:
                                try:
                                    from .modification_memory import ModificationRecord
                                    synth_record = ModificationRecord(
                                        id=mod.id,
                                        timestamp=datetime.utcnow().isoformat(),
                                        source_module="self_modify",
                                        target_file=skill.metadata.get("skill_name", "unknown"),
                                        task_type="optimization",
                                        description=mod.description,
                                        reasoning=mod.reasoning,
                                        modified_code=mod.code,
                                        success=True,
                                        performance_delta=perf_delta,
                                    )
                                    synthesized = await self.self_trainer.synthesize_from_success(synth_record)
                                    if synthesized:
                                        result["self_training"] = {
                                            "synthesized": len(synthesized),
                                            "types": [e.synth_type for e in synthesized],
                                        }
                                except Exception as e:
                                    self.logger.warning("self_training_synthesis_error", error=str(e))

                            # === Contrastive Training: record failure for contrastive learning ===
                            else:
                                try:
                                    from .modification_memory import ModificationRecord
                                    fail_record = ModificationRecord(
                                        id=f"{mod.id}_fail",
                                        timestamp=datetime.utcnow().isoformat(),
                                        source_module="self_modify",
                                        target_file=skill.metadata.get("skill_name", "unknown"),
                                        task_type="optimization",
                                        description=mod.description,
                                        reasoning=mod.reasoning,
                                        modified_code=mod.code,
                                        success=False,
                                        performance_delta=perf_delta,
                                    )
                                    self.modification_memory.record(fail_record)
                                    # Generate contrastive data from the failure
                                    contrastive = await self.contrastive_trainer.generate_contrastive_data()
                                    if contrastive:
                                        result["contrastive_training"] = {
                                            "generated": len(contrastive),
                                            "types": [e.example_type for e in contrastive],
                                        }
                                except Exception as e:
                                    self.logger.warning("contrastive_training_error", error=str(e))

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
            # World Selector
            "world_selector": self.world_selector.to_context() if self.world_selector else {},
            # Simulation modules
            "sensors": self.sensor_array.to_context() if self.sensor_array else {},
            "failure": self.failure_injector.to_context() if self.failure_injector else {},
            "navigation": self.path_planner.to_context() if self.path_planner else {},
            "weather": self.weather.to_context() if self.weather else {},
            "locomotion": self.locomotion.to_context() if self.locomotion else {},
            "manipulation": self.manipulation.to_context() if self.manipulation else {},
            "social": self.social.to_context() if self.social else {},
            # Autonomy Modules
            "self_reflection": self.self_reflection.to_context() if self.self_reflection else {},
            "evo_architecture": self.evo_architecture.to_context() if self.evo_architecture else {},
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
        if self.self_reflection:
            parts.append(f"Self-Reflection:\n{self.self_reflection.to_context()}")
        if self.evo_architecture:
            parts.append(f"Evo Architecture:\n{self.evo_architecture.to_context()}")
        if self.model_trainer:
            parts.append(f"Model Trainer:\n{self.model_trainer.to_context()}")
        if self.custom_model_manager:
            parts.append(f"Custom Models:\n{self.custom_model_manager.to_context()}")
        if self.self_trainer:
            parts.append(f"Self-Training:\n{self.self_trainer.to_context()}")
        if self.contrastive_trainer:
            parts.append(f"Contrastive Training:\n{self.contrastive_trainer.to_context()}")
        if self.model_population:
            parts.append(f"Model Population:\n{self.model_population.to_context()}")
        if self.emergent_curriculum:
            parts.append(f"Emergent Curriculum:\n{self.emergent_curriculum.to_context()}")
        if self.adversarial_trainer:
            parts.append(f"Adversarial Training:\n{self.adversarial_trainer.to_context()}")
        if self.architecture_modifier:
            parts.append(f"Architecture Modifier:\n{self.architecture_modifier.to_context()}")
        if self.rollback_manager:
            rb_stats = self.rollback_manager.get_stats()
            if rb_stats["total_rollbacks"] > 0:
                parts.append(f"Rollbacks: {rb_stats['total_rollbacks']} total")
        # Phase 5: Production monitoring
        if self.perf_monitor:
            monitor_summary = self.perf_monitor.get_summary()
            if monitor_summary:
                parts.append(f"Performance Monitor: {len(monitor_summary)} metrics tracked")
        if self.circuit_breaker:
            cb_state = self.circuit_breaker.get_state()
            if cb_state["state"] != "closed":
                parts.append(f"Circuit Breaker: {cb_state['state']} (failures: {cb_state['failure_count']})")
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
