# Ontogeny

**Proto-AGI cognitive agent with recursive self-improvement, 35 web crawlers, multi-layer persistent memory, grounded physics simulation, sensor simulation, YOLOv8 vision, and Monte Carlo Tree Search planning.**

Runs on Ollama with three-tier hybrid LLM routing: llama3.2 (routine), deepseek-coder-v2:16b (code), qwen2.5:72b (reasoning). CLI-only. No web UI.

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
│  │        Recursive Self-Improvement                           │   │
│  │  Proactive: creates new skills from experience              │   │
│  │  Reactive: optimizes failing skills                         │   │
│  │  Recursive: improves the improvement process itself         │   │
│  │  Persistent: survives restarts                              │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## Features

### 35 Web Crawlers
GitHub, GitLab, Bitbucket, Codeberg/Gitea, SourceForge, Launchpad, Savannah, Apache, Pagure, PyPI, npm, Crates.io, Maven, NuGet, Go.dev, RubyGems, ArXiv, Semantic Scholar, Stack Overflow, Reddit, Hacker News, Wikipedia, RSS, Discord, Slack, Notion, Jira, Pastebin, HuggingFace, Web Scraper, Internet Archive, GitHub Code Search, Papers With Code, HuggingFace Hub, GitHub Trending — all with automatic proxy rotation across 12 free proxy sources.

### Cognitive Systems
- **Goal Management** — intrinsic drives (curiosity, mastery, novelty) with automatic goal generation and decay
- **Multi-step Planning** — LLM-powered plan creation with dependency resolution
- **Meta-cognition** — evaluates own reasoning quality and confidence
- **Causal Reasoning** — builds cause-effect graphs from experience
- **Knowledge Graph** — extracts entities and relations from crawled data
- **Uncertainty Tracking** — tracks confidence intervals and evidence counts
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

### 24 Learning Modules
Pattern learning, reinforcement learning, curiosity-driven exploration, world modeling, knowledge transfer, sleep consolidation, attention management, meta-learning, skill composition, causal discovery, continual learning, cross-domain transfer, self-generated curriculum, persistent identity, physics experimentation, world memory, affordance learning, object permanence, scene understanding, benchmarks, architecture-aware modification, rollback, skill export, and reliability.

### Memory System
- **Working Memory** — current context window
- **Episodic Memory** — timestamped event log with importance scoring
- **Semantic Memory** — knowledge graph with entities and relations
- **Procedural Memory** — learned skills and action sequences
- **World Memory** — persistent object tracking, affordance learning, and experiment history

### Multi-Agent Collaboration
10 specialized agents (Researcher, Coder, Analyst, Planner, Critic, DataCleaner, Summarizer, Optimizer, Explorer, Synthesizer) with evolutionary selection and strategy propagation.

### Docker Sandbox
Isolated code execution in Docker containers with resource limits and automatic cleanup. GPU-accelerated Blender rendering via NVIDIA CUDA.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker Desktop (for code execution sandbox + Blender sandbox)
- Ollama with llama3.2, deepseek-coder-v2:16b, and qwen2.5:72b

```bash
# Install Ollama and pull models
ollama pull llama3.2
ollama pull deepseek-coder-v2:16b
ollama pull qwen2.5:72b

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
- **Anatomy** — Humanoid robot body with 7-DOF IK, muscle simulation, and grasp planning for real robot training
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
│   ├── orchestrator.py      # Main cognitive loop
│   ├── backend.py           # Hybrid LLM backend
│   ├── planning.py          # Plan creation & execution
│   ├── goals.py             # Goal & drive management
│   ├── metacognition.py     # Self-evaluation
│   ├── causal_reasoning.py  # Cause-effect graphs
│   ├── knowledge_graph.py   # Entity-relation extraction
│   ├── uncertainty.py       # Confidence tracking
│   ├── emotional.py         # Mood model
│   ├── self_modify.py       # Skill creation & optimization
│   ├── recursive_modify.py  # Source-level code rewriting
│   ├── skill_composition.py # Skill chaining
│   ├── simulator.py         # Action simulation
│   ├── memory.py            # Multi-layer persistent memory
│   ├── learning.py          # Focused learning mode
│   ├── scheduler.py         # Crawl scheduling
│   ├── pattern_learner.py   # Pattern recognition
│   ├── rl_agent.py          # Reinforcement learning
│   ├── curiosity.py         # Curiosity-driven exploration
│   ├── world_model.py       # Predictive modeling
│   ├── transfer.py          # Knowledge transfer
│   ├── sleep.py             # Memory consolidation
│   ├── attention.py         # Attention management
│   ├── meta_learner.py      # Learning-to-learn
│   ├── outcome_verifier.py  # Outcome verification
│   ├── blender_sandbox.py   # Blender physics sandbox
│   ├── mcts_planner.py      # MCTS planning
│   ├── patch_verifier.py    # Patch verification
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
│   ├── anatomy_mode.py      # 7-DOF IK, muscle simulation
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
```

## How Autonomous Mode Works

Each cycle:

1. **Drive decay** — curiosity/mastery/novelty satisfaction drops 1%/cycle
2. **Goal generation** — new goals created when drives fall below 50%
3. **Plan creation** — LLM generates multi-step plan (or fallback: search + analyze)
4. **Step execution** — one step per cycle (crawl, search, think, execute, navigate, manipulate)
5. **Meta-cognition** — evaluates reasoning quality
6. **Memory recording** — episodic + semantic memory updated
7. **Emotional update** — mood shifts based on outcomes
8. **Causal extraction** — builds cause-effect relationships
9. **Self-modification** — creates new skills, optimizes failing ones, or improves its own improvement process
10. **Repeat** — until Ctrl+C

## License

MIT
