# Ontogeny

**Proto-AGI cognitive agent with recursive self-improvement, 30 web crawlers, multi-layer persistent memory, grounded physics simulation, and Monte Carlo Tree Search planning.**

Runs on Ollama with three-tier hybrid LLM routing: llama3.2 (routine), deepseek-coder-v2:16b (code), qwen2.5:72b (reasoning). CLI-only. No web UI.

---

## What It Does

Ontogeny is a self-improving cognitive agent that autonomously explores the internet, learns from what it finds, and builds increasingly complex understanding over time. It operates in continuous autonomous cycles — setting its own goals, planning actions, executing crawls across 30 data sources, reasoning about results, reflecting on its own performance, and **modifying its own code and behavior** based on what works.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Cognitive Loop                          │
│                                                           │
│  Goals → Planning → Execution → Reflection → Memory       │
│                         ↑                    │            │
│                         └── Self-Modify ◄────┘            │
│                              (recursive)                  │
│                                                           │
│  ┌───────────┐  ┌───────────┐  ┌────────────────────┐   │
│  │ 33        │  │ Meta-     │  │ 10 Cognitive        │   │
│  │ Crawlers  │  │ Cognition │  │ Learning Modules    │   │
│  │ +Proxies  │  │           │  │                     │   │
│  └───────────┘  └───────────┘  └────────────────────┘   │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │           Persistent Memory Layers                  │   │
│  │  Working → Episodic → Semantic → Procedural         │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  ┌───────────────────────────────────────────────────┐   │
│  │        Recursive Self-Improvement                   │   │
│  │  Proactive: creates new skills from experience      │   │
│  │  Reactive: optimizes failing skills                 │   │
│  │  Recursive: improves the improvement process itself │   │
│  │  Persistent: survives restarts                      │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Features

### 30 Web Crawlers
GitHub, GitLab, Bitbucket, Codeberg/Gitea, SourceForge, Launchpad, Savannah, Apache, Pagure, PyPI, npm, Crates.io, Maven, NuGet, Go.dev, RubyGems, ArXiv, Semantic Scholar, Stack Overflow, Reddit, Hacker News, Wikipedia, RSS, Discord, Slack, Notion, Jira, Pastebin, HuggingFace, Web Scraper, Internet Archive (books, Wayback Machine, media) — all with automatic proxy rotation across 12 free proxy sources.

**New Specialized Crawlers:**
- **Papers With Code** — ML papers with linked implementations and repositories
- **GitHub Trending** — Trending repositories by language and time period

### Cognitive Systems
- **Goal Management** — intrinsic drives (curiosity, mastery, novelty) with automatic goal generation and decay
- **Multi-step Planning** — LLM-powered plan creation with dependency resolution
- **Meta-cognition** — evaluates own reasoning quality and confidence
- **Causal Reasoning** — builds cause-effect graphs from experience
- **Knowledge Graph** — extracts entities and relations from crawled data
- **Uncertainty Tracking** — tracks confidence intervals and evidence counts
- **Emotional Model** — mood state that shifts based on success/failure
- **Outcome Verification** — executable verification of code, planning, reasoning, and simulation outcomes (replaces LLM-as-judge with sandbox execution)
- **Blender Physics Grounding** — rigid/soft body, fluid, cloth simulation and rendering via Dockerized Blender for grounded reasoning
- **MCTS Planning** — Monte Carlo Tree Search with learned world model for long-horizon planning
- **Recursive Self-Modification** — analyzes performance, creates new skills, optimizes failing ones, and improves its own improvement process. **Reads and rewrites its own Python source code** (syntax validation → import safety → sandbox test → backup → apply with auto-rollback). History persists across restarts.


### 10 Learning Modules
Pattern learning, reinforcement learning, curiosity-driven exploration, world modeling, knowledge transfer, sleep consolidation, attention management, meta-learning, skill composition, and causal discovery.

### Memory System
- **Working Memory** — current context window
- **Episodic Memory** — timestamped event log with importance scoring
- **Semantic Memory** — knowledge graph with entities and relations
- **Procedural Memory** — learned skills and action sequences

### Multi-Agent Collaboration
10 specialized agents (Researcher, Coder, Analyst, Planner, Critic, DataCleaner, Summarizer, Optimizer, Explorer, Synthesizer) that can collaborate on complex tasks.

### Docker Sandbox
Isolated code execution in Docker containers with resource limits and automatic cleanup.

### Recursive Self-Improvement
- **Proactive**: creates new skills when capabilities are limited
- **Reactive**: optimizes existing skills when performance drops
- **Source-level**: reads its own Python source files, identifies bottlenecks, rewrites code
- **Recursive**: detects when the improvement process itself is failing and flags it
- **Persistent**: modification history survives restarts via `data/recursive_modifications.json`
- **Safe**: syntax validation → import safety check → sandbox test → backup → apply (auto-rollback on failure)
- **Integrated**: generated skills are injected into the planning pipeline for future use

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
# Build Blender Docker image (one-time)
docker build -f Dockerfile.blender -t ontogeny-blender .
```

The agent auto-detects the image and enables physics simulation + rendering actions.

**New Physics Capabilities:**
- **Rigid/Soft Body** — cubes, spheres, soft bodies with goal strength
- **Fluid/Cloth** — SPH fluid, cloth with bending stiffness/damping
- **Particles** — particle systems with forces
- **URDF Robotics** — import URDF, joint position/velocity/torque control
- **Sensors** — camera (RGB/depth), lidar (360° raycast), contact, IMU
- **Domain Randomization** — lighting, textures, physics params, object poses, camera
- **Procedural Generation** — terrain (displacement), buildings, clutter
- **Domain Randomization** — lighting, textures, physics params, poses
- **Scene Persistence** — load/modify existing `.blend` files
- **Real-time Stepping** — step physics with async callbacks
- **Multi-format Export** — USD, glTF, glb, OBJ, STL, PLY, Alembic
- **Procedural Generation** — terrain (displacement), buildings, clutter
- **Multi-format Export** — USD, glTF, OBJ, STL, PLY, Alembic

The agent auto-detects the image and enables `blender_simulate`, `blender_render`, `blender_step` actions.

### macOS Setup

```bash
# Clone and run automated installer
git clone https://github.com/anglonordicinvader-max/ontogeny.git
cd ontogeny
chmod +x setup_macos.sh
./setup_macos.sh

# Launch
chmod +x run_macos.sh
./run_macos.sh
```

The installer handles Homebrew, Python, Ollama, and dependencies automatically. Requires macOS 11+ for full functionality (Ollama + Docker). macOS 10.15 Catalina runs with limited features — no local LLM or sandbox.

### Linux Setup

```bash
# Clone and run automated installer
git clone https://github.com/anglonordicinvader-max/ontogeny.git
cd ontogeny
chmod +x setup_linux.sh
./setup_linux.sh

# Launch
chmod +x run_linux.sh
./run_linux.sh
```

The installer detects your distro (Ubuntu, Fedora, Arch, CentOS) and installs Python, Ollama, and Docker automatically. Full support on all three platforms — Linux is the recommended environment.

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
```

## Project Structure

```
src/crawler_agent/
├── main.py                  # CLI entry point with mode selector
├── cli_colors.py            # ANSI color support
├── persistence.py           # Agent state persistence
├── config/
│   └── settings.py          # All settings (env-loaded)
├── cognitive/
│   ├── orchestrator.py      # Main cognitive loop
│   ├── backend.py           # Cognitive backend abstraction (hybrid LLM)
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
│   ├── scheduler.py         # Intelligent crawl scheduling
│   ├── pattern_learner.py   # Pattern recognition
│   ├── rl_agent.py          # Reinforcement learning
│   ├── curiosity.py         # Curiosity-driven exploration
│   ├── world_model.py       # Predictive modeling
│   ├── transfer.py          # Knowledge transfer
│   ├── sleep.py             # Memory consolidation
│   ├── attention.py         # Attention management
│   ├── meta_learner.py      # Learning-to-learn
│   ├── outcome_verifier.py  # Executable outcome verification (code/planning/reasoning/simulation)
│   ├── blender_sandbox.py   # Physics simulation & rendering via Dockerized Blender
│   ├── mcts_planner.py      # Monte Carlo Tree Search planning with learned world model
│   └── patch_verifier.py    # Test-driven patch verification
├── crawlers/
│   ├── base.py              # Base crawler (proxy-aware)
│   ├── github.py            # GitHub
│   ├── gitlab.py            # GitLab
│   ├── bitbucket.py         # Bitbucket
│   ├── codeberg.py          # Codeberg (Gitea)
│   ├── sourceforge.py       # SourceForge
│   ├── launchpad.py         # Launchpad
│   ├── savannah.py          # GNU Savannah
│   ├── apache.py            # Apache
│   ├── pagure.py            # Pagure
│   ├── pypi.py              # PyPI
│   ├── npm_registry.py      # npm
│   ├── crates.py            # Crates.io
│   ├── go_dev.py            # Go.dev
│   ├── maven.py             # Maven Central
│   ├── nuget.py             # NuGet
│   ├── rubygems.py          # RubyGems
│   ├── arxiv.py             # ArXiv
│   ├── academic.py          # Semantic Scholar
│   ├── stackoverflow.py     # Stack Overflow
│   ├── reddit.py            # Reddit
│   ├── hackernews.py        # Hacker News
│   ├── rss.py               # RSS/Atom feeds
│   ├── wikipedia.py         # Wikipedia
│   ├── discord.py           # Discord
│   ├── slack.py             # Slack
│   ├── notion.py            # Notion
│   ├── jira.py              # Jira
│   ├── pastebin.py          # Pastebin
│   ├── huggingface.py       # HuggingFace
│   ├── webscraper.py        # Generic web scraper
│   ├── internetarchive.py   # Archive.org + Wayback Machine
│   ├── github_code.py       # GitHub code & repo search
│   ├── papers_with_code.py  # ML papers with implementations
│   ├── huggingface_hub.py   # HF models, datasets, spaces
│   └── github_trending.py   # GitHub trending repos
├── agents/
│   ├── base.py              # Base agent class & protocol
│   ├── orchestrator.py      # Multi-agent coordination
│   ├── registry.py          # Agent registry
│   └── specialized.py       # 10 specialized agent implementations
├── processing/
│   ├── llm.py               # LLM processing pipeline
│   └── embeddings.py        # Embedding generation
├── storage/
│   ├── database.py          # SQL storage (SQLite/PostgreSQL)
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
4. **Step execution** — one step per cycle (crawl, search, think, execute)
5. **Meta-cognition** — evaluates reasoning quality
6. **Memory recording** — episodic + semantic memory updated
7. **Emotional update** — mood shifts based on outcomes
8. **Causal extraction** — builds cause-effect relationships
9. **Self-modification** — creates new skills, optimizes failing ones, or improves its own improvement process
10. **Repeat** — until Ctrl+C

## License

MIT
