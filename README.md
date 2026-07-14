# Ontogeny

**Proto-AGI cognitive agent with recursive self-improvement, 28 web crawlers, and multi-layer persistent memory.**

Runs entirely on Ollama llama3.2 locally. CLI-only. No web UI.

---

## What It Does

Ontogeny is a self-improving cognitive agent that autonomously explores the internet, learns from what it finds, and builds increasingly complex understanding over time. It operates in continuous autonomous cycles — setting its own goals, planning actions, executing crawls across 28 data sources, reasoning about results, reflecting on its own performance, and **modifying its own code and behavior** based on what works.

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
│  │ 28        │  │ Meta-     │  │ 10 Cognitive        │   │
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

### 28 Web Crawlers
GitHub, GitLab, PyPI, npm, Crates.io, Maven, NuGet, Go.dev, RubyGems, ArXiv, Semantic Scholar, Stack Overflow, Reddit, Hacker News, Wikipedia, RSS, Discord, Slack, Notion, Jira, Pastebin, HuggingFace, Web Scraper, Internet Archive (books, Wayback Machine, media) — all with automatic proxy rotation across 12 free proxy sources.

### Cognitive Systems
- **Goal Management** — intrinsic drives (curiosity, mastery, novelty) with automatic goal generation and decay
- **Multi-step Planning** — LLM-powered plan creation with dependency resolution
- **Meta-cognition** — evaluates own reasoning quality and confidence
- **Causal Reasoning** — builds cause-effect graphs from experience
- **Knowledge Graph** — extracts entities and relations from crawled data
- **Uncertainty Tracking** — tracks confidence intervals and evidence counts
- **Emotional Model** — mood state that shifts based on success/failure
- **Recursive Self-Modification** — analyzes performance, creates new skills, optimizes failing ones, and improves its own improvement process. History persists across restarts.

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
- Docker Desktop (for code execution sandbox)
- Ollama with llama3.2

```bash
# Install Ollama and pull model
ollama pull llama3.2

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
| `quit` | Exit |

## Configuration

Edit `.env`:

```env
# LLM (Ollama)
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434/v1

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
├── config/
│   └── settings.py          # All settings (env-loaded)
├── cognitive/
│   ├── orchestrator.py      # Main cognitive loop
│   ├── backend.py           # LLM backend (Ollama)
│   ├── planning.py          # Plan creation & execution
│   ├── goals.py             # Goal & drive management
│   ├── metacognition.py     # Self-evaluation
│   ├── causal_reasoning.py  # Cause-effect graphs
│   ├── knowledge_graph.py   # Entity-relation extraction
│   ├── uncertainty.py       # Confidence tracking
│   ├── emotional.py         # Mood model
│   ├── self_modify.py       # Recursive self-improvement engine
│   ├── skill_composition.py # Skill chaining
│   ├── simulator.py         # Action simulation
│   ├── pattern_learner.py   # Pattern recognition
│   ├── rl_agent.py          # Reinforcement learning
│   ├── curiosity.py         # Curiosity-driven exploration
│   ├── world_model.py       # Predictive modeling
│   ├── transfer.py          # Knowledge transfer
│   ├── sleep.py             # Memory consolidation
│   ├── attention.py         # Attention management
│   └── meta_learner.py      # Learning-to-learn
├── crawlers/
│   ├── base.py              # Base crawler (proxy-aware)
│   ├── github.py
│   ├── gitlab.py
│   ├── pypi.py
│   ├── npm.py
│   ├── arxiv.py
│   ├── stackoverflow.py
│   ├── reddit.py
│   ├── hackernews.py
│   ├── wikipedia.py
│   ├── internetarchive.py   # Archive.org + Wayback Machine
│   └── ... (28 total)
├── multi_agent/
│   ├── registry.py          # Agent registry
│   └── collaboration.py     # Inter-agent communication
├── processing/
│   ├── llm.py               # Raw LLM interface
│   └── embeddings.py        # Embedding generation
├── persistence/
│   ├── database.py          # SQLite storage
│   └── state.py             # State persistence
├── docker_manager.py        # Docker sandbox
└── utils/
    ├── proxy.py             # Proxy pool & rotation
    └── proxy_fetcher.py     # 12 free proxy sources
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
