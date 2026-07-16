# Ontogeny

**Proto-AGI cognitive agent with recursive self-improvement, 35 web crawlers, multi-layer persistent memory, grounded physics simulation, sensor simulation, YOLOv8 vision, Maldoror custom fine-tuned model, and Monte Carlo Tree Search planning.**

Runs on Ollama with **four-tier hybrid LLM routing**: llama3.2 (routine), deepseek-coder-v2:16b (code), qwen2.5:72b (reasoning), **maldoror 7B** (self-modification). CLI-only. No web UI.

---

## What It Does

Ontogeny is a self-improving cognitive agent that autonomously explores the internet, learns from what it finds, and builds increasingly complex understanding over time. It operates in continuous autonomous cycles — setting its own goals, planning actions, executing crawls across 35 data sources, reasoning about results, reflecting on its own performance, and **modifying its own code and behavior** based on what works.

It also trains in a Blender physics sandbox with **9 sensor types** (depth, LiDAR, IMU, force/torque, proximity, touch, thermal, night vision, YOLOv8), **5 locomotion modes** (wheeled, legged, tracked, flying, swimming), **4 manipulation tasks** (assembly, cutting, pouring, folding), **social simulation** with human crowd dynamics, and **41 world environments** (8 practical + 33 survival/critical).

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Cognitive Loop                              │
│                                                                   │
│  Goals → Planning → Execution → Reflection → Memory               │
│                         ↑                    │                    │
│                         └── Self-Modify ◄────┘                    │
│                              (recursive)                          │
│                                                                   │
│  ┌───────────┐  ┌───────────┐  ┌────────────────────────────┐   │
│  │ 35        │  │ Meta-     │  │ 24 Cognitive                │   │
│  │ Crawlers  │  │ Cognition │  │ Learning Modules            │   │
│  │ +Proxies  │  │           │  │                             │   │
│  └───────────┘  └───────────┘  └────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │          Four-Tier Hybrid LLM Backend                      │   │
│  │  routine (llama3.2) → code (deepseek-coder-v2)            │   │
│  │  → reasoning (qwen2.5:72b) → modifier (maldoror)          │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │                  Sensor & Simulation                       │   │
│  │  9 Sensors · 5 Locomotion · 4 Manipulation · Social       │   │
│  │  YOLOv8 Vision · Navigation · Weather · Failure Injection  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │           Persistent Memory Layers                          │   │
│  │  Working → Episodic → Semantic → Procedural                 │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │        Recursive Self-Improvement (Maldoror)               │   │
│  │  Proactive: creates new skills from experience              │   │
│  │  Reactive: optimizes failing skills                         │   │
│  │  Recursive: improves the improvement process itself         │   │
│  │  Persistent: survives restarts                              │   │
│  │  Self-Training: QLoRA fine-tuning on successful mods        │   │
│  │  6 Phases: self-train · contrastive · population ·          │   │
│  │           curriculum · adversarial · architecture            │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │        Production Readiness                                 │   │
│  │  Performance monitoring · Drift detection · Circuit breaker │   │
│  │  Smart retraining triggers · Quality gates · Rollback       │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Features

### 35 Web Crawlers
GitHub, GitLab, Bitbucket, Codeberg/Gitea, SourceForge, Launchpad, Savannah, Apache, Pagure, PyPI, npm, Crates.io, Maven, NuGet, Go.dev, RubyGems, ArXiv, Semantic Scholar, Stack Overflow, Reddit, Hacker News, Wikipedia, RSS, Discord, Slack, Notion, Jira, Pastebin, HuggingFace, Web Scraper, Internet Archive, GitHub Code Search, Papers With Code, HuggingFace Hub, GitHub Trending — all with automatic proxy rotation across 12 free proxy sources.

### Four-Tier Hybrid LLM Backend

| Tier | Model | Purpose |
|------|-------|---------|
| **Routine** | llama3.2 | Memory queries, goal generation, simple reasoning, classification |
| **Code** | deepseek-coder-v2:16b | Code generation, self-modification, optimization |
| **Reasoning** | qwen2.5:72b | Planning, causal reasoning, complex analysis |
| **Modifier** | maldoror (fine-tuned) | Recursive self-modification, architecture rewrites |

Routing is automatic based on task keywords. The modifier tier hot-swaps when a new maldoror version is deployed.

### Maldoror — Custom Fine-Tuned Model

Maldoror is a **metacognitive self-modification agent** — a QLoRA fine-tuned Qwen2.5-7B specialized in rewriting the agent's own source code. **Deployed to Ollama and wired as the modifier tier** in the four-tier hybrid backend.

**Pipeline:**
1. **Training data** — successful self-modifications logged from `recursive_modify` and `self_modify`
2. **Modification Memory** — aggregates, deduplicates, scores quality, exports in ChatML format
3. **Self-Training Synthesizer** — generates variations, inverses, reasoning chains from successes
4. **Contrastive Trainer** — generates attempt + critique + counter-example triples from failures
5. **Model Trainer** — QLoRA fine-tuning via Docker GPU (peft + trl + 4-bit quantization)
6. **Model Population** — evolutionary training with 5 strategies, variant competition
7. **Emergent Curriculum** — analyzes weaknesses, generates targeted training tasks
8. **Adversarial Trainer** — self-criticism via adversarial training data
9. **Architecture Modifier** — rewrites transformer structure (layers, heads, FFN, hidden dim)
10. **Custom Model Manager** — deploys to Ollama, manages versions, A/B testing
11. **Quality Gates** — evaluates maldoror vs base before activation
12. **Rollback** — auto-reverts if quality drops >15%
13. **Hot-swap** — runtime backend switch without restarting

```bash
# View maldoror pipeline status
python scripts/maldoror_dashboard.py

# Maldoror is now auto-loaded at startup if available in Ollama
# The orchestrator probes /api/tags and loads it as the modifier tier
```

### Cognitive Systems
- **Goal Management** — intrinsic drives (curiosity, mastery, novelty) with automatic goal generation and decay
- **Multi-step Planning** — LLM-powered plan creation with dependency resolution
- **Meta-cognition** — evaluates own reasoning quality and confidence
- **Self-Reflection** — post-action evaluator with blind spot detection and self-model
- **Evolutionary Architecture** — architecture search using real benchmarks
- **Causal Reasoning** — builds cause-effect graphs from experience, plans interventions
- **Knowledge Graph** — extracts entities and relations from crawled data
- **Uncertainty Tracking** — tracks confidence intervals, epistemic gaps, information value
- **Curiosity Engine** — intrinsic goals from knowledge gaps, novelty scoring
- **World Model** — Bayesian belief tracking, prediction-error minimization, internal simulation
- **Attention Mechanism** — relevance × uncertainty × urgency compute allocation
- **Emotional Model** — mood state that shifts based on success/failure
- **Outcome Verification** — executable verification of code, planning, reasoning, and simulation outcomes
- **Blender Physics Grounding** — rigid/soft body, fluid, cloth, particles, URDF robotics via Dockerized Blender
- **MCTS Planning** — Monte Carlo Tree Search with learned world model for long-horizon planning
- **Recursive Self-Modification** — reads and rewrites its own Python source code with auto-rollback
- **Persistent Identity** — core identity, emotional state, session context, and milestones across restarts
- **Self-Generated Curriculum** — auto-generates learning tasks from knowledge gaps
- **Cross-Domain Transfer** — maps skills between unrelated domains via analogy
- **Continual Learning** — experience replay with elastic weight consolidation
- **Scene Understanding** — video frame analysis, object detection, action recognition, OCR
- **Architecture-Aware Modification** — dependency graph analysis for safe self-modification
- **Rollback System** — version tracking with automatic rollback on failure

### Sensor Simulation (9 Types)
Depth camera, LiDAR (360° raycast), IMU (accelerometer + gyroscope), force/torque, proximity, touch, thermal (heat map), night vision (image intensification), YOLOv8 object detection (80 COCO classes with 3D positioning and frame-to-frame tracking).

### Robot Training Environment
- **5 Locomotion Modes** — wheeled (differential drive), legged (quadruped gait), tracked (tank), flying (drone), swimming (ROV)
- **4 Manipulation Tasks** — peg-in-hole assembly, cutting, pouring, folding
- **Social Simulation** — human crowd dynamics, gesture recognition (wave/point/stop/help/danger), verbal command zones
- **Navigation** — A*, RRT, Dijkstra, potential field obstacle avoidance, SLAM simulation
- **Weather System** — wind force, rain particles, day/night cycle, fog visibility
- **Failure Injection** — battery drain, structural damage, sensor noise, actuator jamming, communication loss

### 41 World Environments
- **8 Practical Worlds** — small house, office building, warehouse, construction site, parkour course, truck loading, stair climb, indoor maze
- **33 Survival Worlds** — 4 tiers (easy → expert): fire escape, flood escape, earthquake rubble, chemical zone, high wind, multi-hazard, damaged robot rescue, total system failure, and more

### 24+ Learning Modules
Pattern learning, reinforcement learning, curiosity-driven exploration, world modeling, knowledge transfer, sleep consolidation, attention management, meta-learning, skill composition, causal discovery, continual learning, cross-domain transfer, self-generated curriculum, persistent identity, physics experimentation, world memory, affordance learning, object permanence, scene understanding, benchmarks, architecture-aware modification, rollback, skill export, reliability, self-reflection, evolutionary architecture.

### Memory System
- **Working Memory** — current context window
- **Episodic Memory** — timestamped event log with importance scoring
- **Semantic Memory** — knowledge graph with entities and relations
- **Procedural Memory** — learned skills and action sequences
- **World Memory** — persistent object tracking, affordance learning, and experiment history

### Multi-Agent Collaboration
10 specialized agents (Researcher, Coder, Analyst, Planner, Critic, DataCleaner, Summarizer, Optimizer, Explorer, Synthesizer) with evolutionary selection and strategy propagation.

### Production Readiness (Phase 5)
- **Performance Monitoring** — tracks latency, quality scores, error rates, memory usage over time
- **Drift Detection** — compares model versions for performance regression
- **Smart Retraining Triggers** — quality-based, not just iteration count
- **Circuit Breaker** — prevents cascading failures (closed → open → half-open states)
- **Graceful Degradation** — fallback strategies when primary pipeline fails
- **Quality Gates** — pre-deployment checks (min score, latency, pattern matching)
- **Auto-Rollback** — reverts to previous model on regression >15%

### Maldoror Self-Improvement (6 Phases)

Maldoror doesn't just get trained — it trains itself through six interconnected phases that run autonomously during the cognitive loop:

| Phase | Module | Trigger | What It Does |
|-------|--------|---------|--------------|
| 1 | **Self-Training Synthesizer** | Every successful modification | Generates variations, inverses, reasoning chains, generalizations from what worked |
| 2 | **Contrastive Trainer** | Every failed modification | Generates attempt + diagnosis + counter-example triples — learns from mistakes |
| 3 | **Model Population** | Every 20 iterations | Evolutionary competition between 5 training strategies (standard, curriculum, adversarial, exploratory, ensemble), winner propagates |
| 4 | **Emergent Curriculum** | Every 10 iterations | Analyzes modification memory for weaknesses, generates targeted training tasks (error patterns, task types, remediation) |
| 5 | **Adversarial Trainer** | Every 15 iterations | Generates adversarial training data — self-critique of own modification attempts |
| 6 | **Architecture Modifier** | Every 50 iterations | Rewrites its own transformer structure — adds layers, changes attention heads, modifies FFN dims, expands tokenizer, with backup/rollback |

Each phase writes to `data/maldoror/` and the results feed back into the next training cycle, creating a continuous self-improvement loop.

### Docker Sandbox
Isolated code execution in Docker containers with resource limits and automatic cleanup. GPU-accelerated Blender rendering via NVIDIA CUDA.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop (for code execution sandbox + Blender sandbox + GPU training)
- Ollama with llama3.2, deepseek-coder-v2:16b, qwen2.5:72b, and maldoror
- NVIDIA Container Toolkit (optional, for GPU training)

```bash
# Install Ollama and pull models
ollama pull llama3.2
ollama pull deepseek-coder-v2:16b
ollama pull qwen2.5:72b
# maldoror is created from training output — see Maldoror Training section

# Build Blender sandbox image (one-time)
docker build -f Dockerfile.blender -t ontogeny-blender .

# Clone and install
git clone https://github.com/anglonordicinvader-max/ontogeny.git
cd ontogeny
pip install -e .
```

### Run

```bash
# Menu mode (interactive / autonomous / demo)
python -m crawler_agent.main

# Autonomous mode (infinite, Ctrl+C to stop)
python -m crawler_agent.main --autonomous

# Autonomous with cycle limit
python -m crawler_agent.main --autonomous 50

# Demo mode
python -m crawler_agent.main --demo

# Maldoror pipeline dashboard
python scripts/maldoror_dashboard.py
```

### Blender Physics Sandbox (Optional)

```bash
# Build Blender Docker image (one-time, GPU-accelerated)
docker build -f Dockerfile.blender -t ontogeny-blender .

# Run with GPU (requires NVIDIA Container Toolkit)
docker run --runtime=nvidia ontogeny-blender
```

**Physics Capabilities:**
- Rigid/soft body, fluid (SPH), cloth, particle systems
- URDF robotics import with joint position/velocity/torque control
- Procedural generation — terrain (displacement), buildings, clutter
- Domain randomization — lighting, textures, physics params, object poses, camera
- Scene persistence — load/modify existing `.blend` files
- Multi-format export — USD, glTF, glb, OBJ, STL, PLY, Alembic
- Auto-render MP4 video snippets for significant events

**Emotion Visualization Modes:**
- **Sphere (default)** — Abstract proto-AGI internal state (glowing sphere with pulse animation)
- **Anatomy** — TOCABI humanoid robot with 38 STL meshes, metallic materials, facial emotion pipeline, breathing, hand tremors
- **Both** — Both visualizations simultaneously

```env
EMOTION_VISUALIZER=anatomy  # or "sphere" (default) | "both"
```

**MP4 Video Rendering:**
```python
from crawler_agent.cognitive.blender_sandbox import SimulationSpec, BlenderSandbox

spec = SimulationSpec(
    render_animation=True,
    frame_start=1,
    frame_end=250,
    video_format="FFMPEG",
    video_codec="H264",
    video_bitrate=8000,
    video_output_path="/workspace/output/animation.mp4"
)

sandbox = BlenderSandbox()
result = await sandbox.run_render(spec)
print(f"Video saved to: {result.video_path}")
```

The agent auto-renders MP4 snippets for significant events (goal completion, self-modification, high reward, emotion change) with a 60s rolling budget.

### Maldoror Training (GPU)

Maldoror fine-tuning runs automatically in Docker GPU when enough training data accumulates. The pipeline:

1. Self-modifications logged to `data/modification_training_log.jsonl`
2. Modification Memory aggregates and scores quality
3. Self-Training Synthesizer generates variations from successes
4. Contrastive Trainer generates triples from failures
5. When 20+ examples exist, training triggers automatically
6. QLoRA fine-tuning runs in Docker GPU container (~2 hours for 3 epochs)
7. LoRA adapters merged into full model (`data/maldoror/merge.py`)
8. Deployed to Ollama, evaluated against base model
9. Quality gates checked, auto-rollback on regression

**First training completed:** 3 epochs, 26 seconds on RTX 3090, loss 2.945. Model deployed to Ollama as `maldoror`.

```bash
# Manual training (if needed)
python -c "
from src.crawler_agent.cognitive.modification_memory import ModificationMemory
from src.crawler_agent.cognitive.model_trainer import ModelTrainer
mm = ModificationMemory()
mm.ingest_from_training_logs()
t = ModelTrainer(modification_memory=mm)
import asyncio
asyncio.run(t.train())
"

# Merge LoRA adapters into full model for Ollama
python data/maldoror/merge.py

# Create Ollama model from merged weights
ollama create maldoror -f Modelfile
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `ask <question>` | Ask the agent anything |
| `search <source> <query>` | Search a specific crawler |
| `crawl <source> <url>` | Crawl a URL |
| `goal <description>` | Create a goal |
| `goals` | List active goals |
| `autonomous` | Start autonomous loop |
| `dream <theme>` | Dream session (novel connections) |
| `simulate <action>` | Simulate an action |
| `causal <query>` | Query causal graph |
| `know <query>` | Query knowledge graph |
| `run <code>` | Execute Python in sandbox |
| `agents` | List all agents |
| `task <description>` | Run a task |
| `status` | Agent status |
| `drives` | View intrinsic drives |
| `blender_sim <spec>` | Run physics simulation |
| `blender_render <spec>` | Render scene |
| `blender_step <blend> <steps>` | Step physics in existing .blend |
| `verify <task_type> <output>` | Verify outcome (code/plan/reason/sim) |
| `mcts_plan <goal> <state>` | MCTS planning |
| `skill_create <name> <code>` | Create new skill |
| `skill_list` | List available skills |
| `sensor_read <type>` | Read sensor (depth/lidar/imu/force/proximity/touch/thermal/night_vision) |
| `yolo_detect <image>` | Detect objects with YOLOv8 |
| `navigate <goal>` | Plan path (A*/RRT/Dijkstra) |
| `weather_update` | Update weather simulation |
| `locomotion <mode>` | Set locomotion mode (wheeled/legged/tracked/flying/swimming) |
| `manipulate <task>` | Run manipulation task (assembly/cutting/pouring/folding) |
| `social_update` | Update crowd simulation |
| `failure_inject <type>` | Inject failure (battery/structural/sensor/actuator/comm) |
| `maldoror_status` | View maldoror pipeline status |
| `maldoror_train` | Trigger manual training |
| `maldoror_evaluate` | Run evaluation benchmark |

## Configuration

Edit `.env`:

```env
# LLM (Ollama - routine tasks)
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434/v1

# Code LLM (deepseek-coder-v2:16b - code generation & self-modification)
CODE_LLM_ENABLED=true
CODE_LLM_MODEL=deepseek-coder-v2:16b
CODE_LLM_API_KEY=ollama
CODE_LLM_API_BASE=http://localhost:11434/v1

# Reasoning LLM (qwen2.5:72b - complex reasoning & planning)
HEAVY_LLM_ENABLED=true
HEAVY_LLM_MODEL=qwen2.5:72b
HEAVY_LLM_API_KEY=ollama
HEAVY_LLM_API_BASE=http://localhost:11434/v1

# Proxy (auto-fetches free proxies)
PROXY_ENABLED=true
PROXY_REQUIRED=true
PROXY_AUTO_REFRESH=true
PROXY_FETCH_FREE_PROXIES=true

# Storage
STORAGE_DATABASE_URL=sqlite+aiosqlite:///./crawler.db

# Crawler rates
CRAWLER_REQUESTS_PER_SECOND=5.0
CRAWLER_MIN_DELAY=1.0
CRAWLER_MAX_DELAY=3.0

# Blender Emotion Visualization (sphere | anatomy | both)
EMOTION_VISUALIZER=anatomy

# Maldoror Training (via Docker GPU)
MALDOROR_BASE_MODEL=Qwen/Qwen2.5-7B-Instruct
MALDOROR_LORA_R=16
MALDOROR_LORA_ALPHA=32
MALDOROR_LORA_DROPOUT=0.05
MALDOROR_LR=2e-4
MALDOROR_BATCH_SIZE=2
MALDOROR_NUM_EPOCHS=3
MALDOROR_WARMUP=10
```

## Project Structure

```
src/crawler_agent/
├── main.py                  # CLI entry point
├── cli_colors.py            # ANSI color support
├── persistence.py           # Agent state persistence
├── config/
│   └── settings.py          # All settings (env-loaded)
├── cognitive/
│   ├── orchestrator.py      # Main cognitive loop (all phases integrated)
│   ├── backend.py           # Four-tier hybrid LLM backend
│   ├── planning.py          # Plan creation & execution
│   ├── goals.py             # Goal & drive management
│   ├── metacognition.py     # Self-evaluation
│   ├── self_reflection.py   # Post-action evaluator, blind spot detection
│   ├── evo_architecture.py  # Evolutionary architecture search
│   ├── causal_reasoning.py  # Cause-effect graphs
│   ├── knowledge_graph.py   # Entity-relation extraction
│   ├── uncertainty.py       # Confidence tracking, epistemic gaps
│   ├── curiosity.py         # Intrinsic goals, novelty scoring
│   ├── world_model.py       # Bayesian beliefs, prediction-error
│   ├── attention.py         # Relevance × uncertainty × urgency
│   ├── emotional.py         # Mood model
│   ├── self_modify.py       # Skill creation & optimization
│   ├── recursive_modify.py  # Source-level code rewriting
│   ├── modification_memory.py # Training data aggregation
│   ├── model_trainer.py     # QLoRA training orchestration
│   ├── custom_model_manager.py # Ollama model lifecycle
│   ├── model_evaluation.py  # Benchmark, A/B test, quality gates, rollback
│   ├── production.py        # Monitoring, triggers, circuit breaker
│   ├── self_training.py     # Self-training synthesizer (Phase 1)
│   ├── contrastive_trainer.py # Contrastive trainer (Phase 2)
│   ├── model_population.py  # Population-based training (Phase 3)
│   ├── emergent_curriculum.py # Emergent curriculum (Phase 4)
│   ├── adversarial_trainer.py # Adversarial trainer (Phase 5)
│   ├── architecture_modifier.py # Architecture modifier (Phase 6)
│   ├── skill_composition.py # Skill chaining
│   ├── simulator.py         # Action simulation
│   ├── memory.py            # Multi-layer persistent memory
│   ├── learning.py          # Focused learning mode
│   ├── scheduler.py         # Crawl scheduling
│   ├── pattern_learner.py   # Pattern recognition
│   ├── rl_agent.py          # Reinforcement learning
│   ├── meta_learner.py      # Learning-to-learn
│   ├── transfer.py          # Knowledge transfer
│   ├── sleep.py             # Memory consolidation
│   ├── outcome_verifier.py  # Outcome verification
│   ├── blender_sandbox.py   # Blender physics sandbox
│   ├── mcts_planner.py      # MCTS planning
│   ├── patch_verifier.py    # Patch verification
│   ├── benchmark_runner.py  # Real performance benchmarks
│   ├── sensor_sim.py        # 9-sensor array
│   ├── yolo_detector.py     # YOLOv8 object detection
│   ├── failure_injection.py # Failure injection
│   ├── navigation.py        # A*, RRT, Dijkstra, SLAM
│   ├── weather.py           # Wind, rain, day/night, fog
│   ├── locomotion.py        # 5 locomotion modes
│   ├── manipulation_tasks.py# Assembly, cutting, pouring, folding
│   ├── social_sim.py        # Human crowd simulation
│   ├── practical_worlds.py  # 8 practical environments
│   ├── survival_worlds.py   # 33 survival worlds
│   ├── world_selector.py    # Skill-based world selection
│   ├── world_memory.py      # Persistent world memory
│   ├── anatomy_mode.py      # TOCABI humanoid, 38 STL meshes
│   ├── sphere_viz.py        # Planning/knowledge visualizations
│   ├── benchmarks.py        # 18-task benchmark suite
│   ├── persistent_identity.py# Identity & session context
│   ├── curriculum.py        # Self-generated learning tasks
│   ├── physics_exp.py       # Hypothesis testing
│   ├── object_permanence.py # Hidden object tracking
│   ├── continual_learning.py# Experience replay, EWC
│   ├── cross_domain.py      # Cross-domain transfer
│   ├── scene_understanding.py # Video/OCR analysis
│   ├── architecture_modify.py # Safe self-modification zones
│   ├── rollback.py          # Version tracking & rollback
│   ├── skill_export.py      # Portable skill export
│   ├── multimodal.py        # Vision & audio processing
│   ├── self_audit.py        # Periodic self-audits
│   ├── reliability.py       # Circuit breaker, retry logic
│   ├── distillation.py      # Knowledge distillation, LoRA training
│   └── tools.py             # GitHub/arXiv/ROS2 APIs
├── crawlers/                # 35 data source crawlers
├── agents/                  # Multi-agent collaboration
├── processing/
│   ├── llm.py               # LLM pipeline
│   └── embeddings.py        # Embedding generation
├── storage/
│   ├── database.py          # SQL storage
│   ├── docker_manager.py    # Docker sandbox
│   └── vector.py            # ChromaDB vector store
└── utils/
    ├── proxy.py             # Proxy pool & rotation
    ├── proxy_fetcher.py     # 12 free proxy sources
    └── rate_limiter.py      # Request rate limiting

data/
├── maldoror/
│   ├── train_v0.jsonl       # Training data (ChatML format, 21KB)
│   ├── train_v2.py          # QLoRA training script (fixed: BitsAndBytesConfig, bf16)
│   ├── merge.py             # Merges LoRA adapters into full model for Ollama
│   ├── models.json          # Deployed model registry
│   ├── runs.json            # Training run history
│   ├── rollback_history.json # Rollback log
│   ├── adapters/            # LoRA adapter weights from training
│   │   └── v0/              # First training run adapters
│   ├── merged/              # Full merged model (14GB) for Ollama deployment
│   ├── architecture/        # Architecture modification history & backups
│   ├── eval/                # Evaluation reports & detailed results
│   └── monitoring/          # Performance metrics & snapshots
├── modification_memory/
│   └── memory.jsonl         # Aggregated training data
├── modification_training_log.jsonl # Raw self-modification logs
└── maldoror/eval/           # Evaluation reports

scripts/
├── maldoror_dashboard.py    # CLI dashboard for pipeline status
└── ...                      # Other utility scripts

Modelfile                   # Ollama model definition for maldoror
Modelfile.maldoror          # Alternative maldoror model definition

tests/
├── test_smoke.py            # 77 module import/instantiation/operation tests
├── test_maldoror_e2e.py     # 20 maldoror pipeline E2E tests
├── test_evaluation.py       # 15 evaluation/gate/rollback/A/B tests
├── test_production.py       # 28 monitoring/trigger/circuit breaker tests
├── test_self_training.py    # 13 self-training synthesizer tests
├── test_contrastive.py      # 14 contrastive trainer tests
├── test_population.py       # 16 population-based training tests
├── test_emergent_curriculum.py # 6 emergent curriculum tests
├── test_adversarial_trainer.py # 5 adversarial trainer tests
└── test_architecture_modifier.py # 15 architecture modifier tests

Modelfile.maldoror           # Ollama model definition for maldoror
```

## How Autonomous Mode Works

Each cycle:

1. **Drive decay** — curiosity/mastery/novelty satisfaction drops 1%/cycle
2. **Goal generation** — new goals created when drives fall below 50%
3. **Plan creation** — LLM generates multi-step plan (or fallback: search + analyze)
4. **Step execution** — one step per cycle (crawl, search, think, execute, navigate, manipulate)
5. **Meta-cognition** — evaluates reasoning quality
6. **Self-reflection** — post-action review with blind spot detection
7. **Memory recording** — episodic + semantic memory updated
8. **Emotional update** — mood shifts based on outcomes
9. **Causal extraction** — builds cause-effect relationships
10. **Self-modification** — creates new skills, optimizes failing ones, or improves its own improvement process
11. **Self-training synthesis** — generates training variations from successful modifications (every 10 iterations)
12. **Contrastive training** — generates critique triples from failed modifications (every 15 iterations)
13. **Population competition** — evolutionary training strategy selection (every 20 iterations)
14. **Emergent curriculum** — weakness-targeted task generation (every 10 iterations)
15. **Adversarial training** — self-critique data generation (every 15 iterations)
16. **Architecture modification** — transformer structure evolution (every 50 iterations)
17. **Smart retraining** — triggers maldoror fine-tuning when quality degrades
18. **Monitoring** — records performance metrics, checks for drift
19. **Repeat** — until Ctrl+C

## Testing

```bash
# Run all tests (205 tests)
python -m pytest tests/ -v

# Run specific suites
python -m pytest tests/test_smoke.py -v                    # 77 smoke tests
python -m pytest tests/test_maldoror_e2e.py -v             # 20 E2E pipeline tests
python -m pytest tests/test_evaluation.py -v               # 15 evaluation tests
python -m pytest tests/test_production.py -v               # 28 production tests
python -m pytest tests/test_self_training.py -v            # 13 self-training tests
python -m pytest tests/test_contrastive.py -v              # 14 contrastive tests
python -m pytest tests/test_population.py -v               # 16 population tests
python -m pytest tests/test_emergent_curriculum.py -v      # 6 curriculum tests
python -m pytest tests/test_adversarial_trainer.py -v      # 5 adversarial tests
python -m pytest tests/test_architecture_modifier.py -v    # 15 architecture tests
```

## License

AGPL-3.0
