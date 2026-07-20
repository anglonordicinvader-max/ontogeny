"""Main entry point for Ontogeny — the autonomous knowledge acquisition and reasoning agent."""

import asyncio
import sys
from pathlib import Path

import structlog

from .cli_colors import ONTOGENY_LOGO, RESET, blue, bold, bright_red, cyan, dim, green, red, yellow
from .cognitive.goals import GoalPriority, GoalSource
from .cognitive.orchestrator import CognitiveOrchestrator
from .persistence import AgentState, StatePersistence
from .utils.proxy import ProxyPool


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging."""
    # Enable ANSI colors on Windows
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def interactive_mode(agent: CognitiveOrchestrator, persistence: StatePersistence) -> None:
    """Interactive command loop."""
    print(f"\n{ONTOGENY_LOGO}")
    print(f"{bold(cyan('=== Ontogeny Cognitive Agent — Interactive Mode ==='))}\n")
    print(f"{dim('Commands:')}")
    print(f"  {yellow('ask')} <question>             - Ask the agent anything")
    print(f"  {yellow('crawl')} <source> <url>       - Crawl a URL")
    print(f"  {yellow('search')} <source> <query>    - Search a source")
    print(f"  {yellow('goal')} <description>         - Create a goal")
    print(f"  {yellow('goals')}                      - List active goals")
    print(f"  {yellow('status')}                     - Agent status")
    print(f"  {yellow('embodiment')}                 - NeoCorpus backend status")
    print(f"  {yellow('memory')}                     - View memory stats")
    print(f"  {yellow('drives')}                     - View intrinsic drives")
    print(f"  {yellow('skills')}                     - View learned skills")
    print(f"  {yellow('proxy')} list                 - List proxy status")
    print(f"  {yellow('proxy')} add <url>            - Add a proxy")
    print(f"  {yellow('proxy')} load <file>          - Load proxies from file")
    print(f"  {yellow('proxy')} refresh              - Force refresh proxies")
    print(f"  {yellow('intensity')} <light|moderate|heavy> - Set crawl intensity")
    print(f"  {yellow('learn')} <topic>              - Focused learning session")
    print(f"  {yellow('adapt')}                      - Auto-adapt intensity")
    print(f"  {yellow('autonomous')} <cycles>        - Run autonomous loop")
    print(f"  {yellow('save')}                       - Save agent state")
    print(f"  {yellow('load')}                       - Load saved state")
    print(f"  {yellow('backups')}                    - List saved backups")
    print(f"  {bright_red('--- Advanced Cognitive ---')}")
    print(f"  {yellow('dream')} <theme>              - Dream session (novel connections)")
    print(f"  {yellow('simulate')} <action> [type]   - Simulate an action")
    print(f"  {yellow('simulate-plan')} <step1;step2> - Simulate a full plan")
    print(f"  {yellow('causal')} <query>             - Query causal graph")
    print(f"  {yellow('intervene')} <var> <val> <q>  - Do-calculus intervention")
    print(f"  {yellow('counterfactual')} <out> <var> <val> - What-if reasoning")
    print(f"  {yellow('know')} <query>               - Query knowledge graph")
    print(f"  {yellow('analogy')} <a> <b> <c>        - Find analogy: A:B :: C:?")
    print(f"  {yellow('paths')} <src> <tgt>          - Find knowledge paths")
    print(f"  {yellow('uncertainty')} <claim>        - Check uncertainty")
    print(f"  {yellow('compose')} <goal>             - Discover skill compositions")
    print(f"  {yellow('context')}                    - Full cognitive context")
    print(f"  {bright_red('--- Code Execution ---')}")
    print(f"  {yellow('run')} <code>                 - Execute Python code in sandbox")
    print(f"  {yellow('run-file')} <path>            - Execute a Python file in sandbox")
    print(f"  {yellow('install')} <package>          - Install a package in sandbox")
    print(f"  {yellow('sandboxes')}                  - List active sandboxes")
    print(f"  {yellow('sandbox destroy')} <name>     - Destroy a sandbox")
    print(f"  {bright_red('--- Multi-Agent ---')}")
    print(f"  {yellow('agents')}                     - List all agents")
    print(f"  {yellow('task')} <description>         - Run a task (auto-assign agent)")
    print(f"  {yellow('task')} <agent> <description> - Run a task with specific agent")
    print(f"  {yellow('collaborate')} <problem>      - Agents collaborate on problem")
    print(f"  {yellow('pipeline')} <a1:t1;a2:t2>    - Run agent pipeline")
    print(f"  {red('quit')}                       - Exit\n")

    while True:
        try:
            line = input("agent> ").strip()
            if not line:
                continue

            parts = line.split(maxsplit=2)
            command = parts[0].lower()

            if command == "quit":
                break

            elif command == "ask" and len(parts) >= 2:
                question = " ".join(parts[1:])
                print(f"\n{cyan('Thinking...')}")
                response = await agent.handle_user_input(question)
                print(f"\n{green(response)}\n")

            elif command == "crawl" and len(parts) >= 3:
                source = parts[1]
                url = parts[2]
                crawler = agent.crawlers.get(source)
                if crawler:
                    print(f"{cyan('Crawling...')}")
                    count = 0
                    async for result in crawler.crawl(url):
                        await agent.db.store(result)
                        count += 1
                    print(f"{green(f'Crawled {count} items from {source}')}")
                else:
                    print(f"{red(f'Unknown source: {source}')}")

            elif command == "search" and len(parts) >= 3:
                source = parts[1]
                query = parts[2]
                crawler = agent.crawlers.get(source)
                if crawler:
                    print(f"{cyan('Searching...')}")
                    count = 0
                    async for result in crawler.search(query, limit=10):
                        await agent.db.store(result)
                        print(f"  {green('•')} {result.title}: {dim(result.url)}")
                        count += 1
                    print(f"{green(f'Found {count} results')}")
                else:
                    print(f"{red(f'Unknown source: {source}')}")

            elif command == "goal" and len(parts) >= 2:
                description = " ".join(parts[1:])
                goal = await agent.goals.create_goal(
                    description=description,
                    source=GoalSource.EXTRINSIC,
                    priority=GoalPriority.HIGH,
                )
                print(f"{green(f'Created goal: {goal.id}')}")

            elif command == "goals":
                goals = await agent.goals.get_active_goals()
                if goals:
                    print(f"\n{bold(cyan('Active goals:'))}")
                    for g in goals:
                        print(
                            f"  {yellow('[' + g.priority.value + ']')} {g.description} (progress: {green(f'{g.progress:.0%}')})"
                        )
                else:
                    print(f"{dim('No active goals')}")

            elif command == "status":
                status = await agent.get_status()
                print(f"\n{bold(cyan('Agent Status'))}")
                print(f"  State:       {green(status['state'])}")
                print(f"  Iteration:   {yellow(str(status['iteration']))}")
                uptime = f"{status['uptime_seconds']:.0f}s"
                print(f"  Uptime:      {yellow(uptime)}")
                goals = status.get("goals", {})
                memory = status.get("memory", {})
                print(
                    f"  Goals:       {goals.get('active', 0)} active / "
                    f"{goals.get('total', 0)} total"
                )
                print(f"  Planning:    {status.get('plans', {})}")
                print(
                    "  Memory:      "
                    f"{memory.get('working_memory_size', 0)} working / "
                    f"{memory.get('episodic_count', 0)} episodic / "
                    f"{memory.get('semantic_count', 0)} semantic / "
                    f"{memory.get('procedural_count', 0)} procedural"
                )
                print(f"  Knowledge:   {status.get('knowledge_graph', {})}")
                print(f"  Reflection:  {status.get('self_reflection', {})}")
                print(f"  Maldoror:    {status.get('maldoror', {})}")
                backend = status.get("backend", {})
                routes = ", ".join(
                    f"{tier}={backend.get(tier + '_backend', 'unavailable')}"
                    for tier in ("routine", "code", "reasoning", "modifier")
                )
                print(f"  Routing:     {routes}")
                print(f"  NeoCorpus:   {status.get('embodiment', {})}")
                print(f"  Crawlers:    {status.get('crawlers', [])}")
                proxy_stats = agent.proxy_pool.get_stats()
                healthy_color = green if proxy_stats["healthy"] > 0 else red
                healthy_count = proxy_stats["healthy"]
                total_count = proxy_stats["total"]
                print(f"  Proxies:     {healthy_color(f'{healthy_count}/{total_count} healthy')}")
                if status.get("current_plan"):
                    print(f"\n{bold('Current Plan:')}\n{status['current_plan']}")

            elif command == "embodiment":
                status = await agent.get_status()
                embodiments = status.get("embodiment", {})
                print(f"\n{bold(cyan('NeoCorpus Embodiment'))}")
                for name in ("blender", "mujoco"):
                    available = embodiments.get(name, False)
                    marker = green("available") if available else red("unavailable")
                    print(f"  {name.capitalize():8} {marker}")

            elif command == "memory":
                context = await agent.memory.get_context_window()
                print(f"\n{bold(cyan(f'Memory Context ({len(context)} chars):'))}")
                print(context[:2000] + "..." if len(context) > 2000 else context)

            elif command == "drives":
                drives = await agent.goals.get_drive_status()
                print(f"\n{bold(cyan('Intrinsic Drives:'))}")
                for name, level in drives.items():
                    filled = int(level * 20)
                    bar = green("█" * filled) + dim("░" * (20 - filled))
                    print(f"  {yellow(name)}: [{bar}] {level:.0%}")

            elif command == "skills":
                skills = agent.self_modifier.get_skills()
                if skills:
                    print(f"\n{bold(cyan(f'Learned Skills ({len(skills)}):'))}")
                    for name in skills:
                        print(f"  {green('•')} {name}")
                else:
                    print(f"{dim('No skills learned yet')}")

            elif command == "proxy" and len(parts) >= 2:
                proxy_cmd = parts[1].lower()
                if proxy_cmd == "list":
                    stats = agent.proxy_pool.get_stats()
                    h_count = stats["healthy"]
                    t_count = stats["total"]
                    print(f"\n{bold(cyan(f'Proxy Pool: {green(str(h_count))}/{t_count} healthy'))}")
                    for p in agent.proxy_pool._proxies:
                        status_icon = green("✓") if p.is_healthy else red("✗")
                        print(
                            f"  {status_icon} {p._host_port} {yellow('[' + p.status.value + ']')} "
                            f"(success: {p.success_count}, fail: {p.failure_count})"
                        )
                elif proxy_cmd == "add" and len(parts) >= 3:
                    proxy_url = parts[2]
                    agent.proxy_pool.add_proxy(proxy_url)
                    print(f"{green(f'Added proxy: {proxy_url}')}")
                elif proxy_cmd == "load" and len(parts) >= 3:
                    filepath = parts[2]
                    count = agent.proxy_pool.load_from_file(filepath)
                    print(f"{green(f'Loaded {count} proxies from {filepath}')}")
                elif proxy_cmd == "refresh":
                    print(f"{cyan('Refreshing proxy pool...')}")
                    count = await agent.proxy_manager.refresher.force_refresh()
                    print(f"{green(f'Added {count} new proxies')}")
                elif proxy_cmd == "fetch":
                    print(f"{cyan('Fetching free proxies...')}")
                    from ..utils.proxy_fetcher import FreeProxyFetcher

                    fetcher = FreeProxyFetcher()
                    proxies = await fetcher.fetch_all(limit=20)
                    for p in proxies:
                        agent.proxy_pool.add_proxy(p)
                    print(f"{green(f'Fetched {len(proxies)} free proxies')}")
                else:
                    print(f"{dim('Usage: proxy <list|add|load|refresh|fetch> [args]')}")

            elif command == "intensity" and len(parts) >= 2:
                from .cognitive.scheduler import CrawlIntensity

                intensity_map = {
                    "light": CrawlIntensity.LIGHT,
                    "moderate": CrawlIntensity.MODERATE,
                    "heavy": CrawlIntensity.HEAVY,
                }
                level = parts[1].lower()
                if level in intensity_map:
                    agent.crawl_orchestrator.scheduler.set_intensity(intensity_map[level])
                    print(f"{green(f'Intensity set to: {level}')}")
                    stats = agent.crawl_orchestrator.scheduler.get_stats()
                    print(f"  RPM:   {yellow(str(stats['requests_per_minute']))}")
                    print(
                        f"  Delay: {yellow(str(stats.get('min_delay', '?')))}-{yellow(str(stats.get('max_delay', '?')))}s"
                    )
                else:
                    print(f"{red('Options: light, moderate, heavy')}")

            elif command == "adapt":
                new_level = await agent.adapt_intensity()
                print(f"{green(f'Adapted intensity to: {new_level}')}")

            elif command == "learn" and len(parts) >= 2:
                topic = " ".join(parts[1:])
                print(f"{cyan(f'Starting focused learning on: {topic}...')}")
                result = await agent.learn_focused(topic, max_items=5)
                print(f"\n{bold(cyan('Learning complete:'))}")
                print(f"  Items processed: {yellow(str(result['items_learned']))}")
                knowledge_gained = result["knowledge_gained"]
                print(f"  Knowledge gained: {green(f'{knowledge_gained:.2f}')}")
                if result["insights"]:
                    print(f"  {bold('Insights:')}")
                    for insight in result["insights"][:3]:
                        print(f"    {green('•')} {insight}")

            elif command == "dream" and len(parts) >= 2:
                theme = " ".join(parts[1:])
                print(f"{cyan(f'Dreaming about: {theme}...')}")
                result = await agent.dream(theme)
                emotional_tone = result["emotional_tone"]
                print(f"\n{bold(magenta(f'Dream results ({emotional_tone}):'))}")
                if result["novel_connections"]:
                    print(f"  {bold('Novel connections:')}")
                    for c in result["novel_connections"][:5]:
                        print(f"    {green('•')} {c}")
                if result["insights"]:
                    print(f"  {bold('Insights:')}")
                    for i in result["insights"][:3]:
                        print(f"    {green('•')} {i}")
                if result["creative_ideas"]:
                    print(f"  {bold('Creative ideas:')}")
                    for i in result["creative_ideas"][:3]:
                        print(f"    {yellow('•')} {i}")

            elif command == "simulate" and len(parts) >= 2:
                action = parts[1]
                sim_type = parts[2] if len(parts) > 2 else "planning"
                print(f"{cyan(f'Simulating: {action} ({sim_type})...')}")
                result = await agent.simulate(action, sim_type)
                confidence = result["confidence"]
                conf_str = f"{confidence:.0%}"
                print(f"\n{bold(cyan(f'Simulation (confidence: {green(conf_str)}):'))}")
                print(f"  Outcomes: {result['outcomes']}")
                if result["steps"]:
                    print(f"  {bold('Steps:')}")
                    for s in result["steps"][:5]:
                        print(f"    {green('•')} {s}")

            elif command == "simulate-plan" and len(parts) >= 2:
                steps_str = " ".join(parts[1:])
                steps = [s.strip() for s in steps_str.split(";") if s.strip()]
                print(f"{cyan(f'Simulating plan with {len(steps)} steps...')}")
                result = await agent.simulate_plan(steps)
                confidence = result["confidence"]
                conf_str = f"{confidence:.0%}"
                print(
                    f"\n{bold(cyan(f'Plan simulation (confidence: {green(conf_str)}):'))}"
                )
                print(f"  Outcomes: {result['outcomes']}")
                for detail in result.get("step_details", [])[:5]:
                    print(f"    {green('•')} {detail.get('description', detail)}")

            elif command == "causal" and len(parts) >= 2:
                query = " ".join(parts[1:])
                result = await agent.causal_query(query)
                print(f"\n{bold(cyan(f'Causal query: {query}'))}")
                if result["causes"]:
                    print(f"  {bold('Causes:')}")
                    for c in result["causes"][:5]:
                        print(f"    {green('•')} {c}")
                if result["effects"]:
                    print(f"  {bold('Effects:')}")
                    for e in result["effects"][:5]:
                        print(f"    {yellow('•')} {e}")

            elif command == "intervene" and len(parts) >= 4:
                var = parts[1]
                value = parts[2]
                query = " ".join(parts[3:])
                result = await agent.causal_intervention(var, value, query)
                print(f"\n{bold(cyan(f'Intervention do({yellow(var)}={green(value)}):'))}")
                print(f"  {result}")

            elif command == "counterfactual" and len(parts) >= 4:
                outcome = parts[1]
                var = parts[2]
                value = " ".join(parts[3:])
                result = await agent.counterfactual(outcome, var, value)
                print(f"\n{bold(cyan(f'Counterfactual: if {yellow(var)}={green(value)}'))}")
                print(f"  Predicted: {result['predicted_outcome']}")
                confidence = result["confidence"]
                print(f"  Confidence: {green(f'{confidence:.0%}')}")

            elif command == "know" and len(parts) >= 2:
                query = " ".join(parts[1:])
                results = await agent.query_knowledge(query)
                print(f"\n{bold(cyan(f'Knowledge results for {yellow(query)}:'))}")
                for r in results[:10]:
                    print(
                        f"  {green('•')} {r.get('name', r.get('id', '?'))}: {dim(r.get('description', '')[:80])}"
                    )

            elif command == "analogy" and len(parts) >= 4:
                results = await agent.knowledge_analogy(parts[1], parts[2], parts[3])
                print(
                    f"\n{bold(cyan(f'{yellow(parts[1])} is to {yellow(parts[2])} as {yellow(parts[3])} is to:'))}"
                )
                for r in results[:5]:
                    print(f"  {green('•')} {r}")

            elif command == "paths" and len(parts) >= 3:
                results = await agent.knowledge_paths(parts[1], parts[2])
                print(f"\n{bold(cyan(f'Paths from {yellow(parts[1])} to {yellow(parts[2])}:'))}")
                for path in results[:5]:
                    print(f"  {green('→')} {' → '.join(path)}")

            elif command == "uncertainty" and len(parts) >= 2:
                claim = " ".join(parts[1:])
                result = await agent.uncertainty_check(claim)
                print(f"\n{bold(cyan(f'Uncertainty for: {yellow(claim)}'))}")
                confidence = result["confidence"]
                print(f"  Confidence: {green(f'{confidence:.0%}')}")
                print(f"  Type:       {yellow(result['type'])}")
                print(f"  Interval:   {result['interval']}")
                print(
                    f"  Evidence:   {result['evidence_count']} (contradicting: {red(str(result['contradicting']))})"
                )

            elif command == "compose" and len(parts) >= 2:
                goal = " ".join(parts[1:])
                result = await agent.compose_skill(goal)
                print(f"\n{bold(cyan(f'Skill composition for: {yellow(goal)}'))}")
                print(f"  Chain:        {green(result['chain_name'])}")
                print(f"  Steps:        {yellow(str(len(result['steps'])))}")
                success_rate = result["success_rate"]
                print(f"  Success rate: {green(f'{success_rate:.0%}')}")
                print(f"  Description:  {result['description']}")

            elif command == "context":
                ctx = agent.get_cognitive_context()
                print(f"\n{bold(cyan(f'Cognitive Context ({len(ctx)} chars):'))}")
                print(ctx[:3000] + "..." if len(ctx) > 3000 else ctx)

            elif command == "run" and len(parts) >= 2:
                code = " ".join(parts[1:])
                print(f"{cyan('Executing code in sandbox...')}")
                result = await agent.execute_code(code)
                if result.get("success"):
                    print(f"\n{green('Output:')}\n{result.get('output', '')}")
                else:
                    print(f"\n{red('Error:')} {result.get('error', 'Unknown error')}")
                duration_ms = result.get("duration_ms", 0)
                print(f"{dim(f'Duration: {duration_ms:.0f}ms')}")

            elif command == "run-file" and len(parts) >= 2:
                filepath = parts[1]
                try:
                    with open(filepath) as f:
                        code = f.read()
                    print(f"{cyan(f'Executing {filepath} in sandbox...')}")
                    result = await agent.execute_code(code)
                    if result.get("success"):
                        print(f"\n{green('Output:')}\n{result.get('output', '')}")
                    else:
                        print(f"\n{red('Error:')} {result.get('error', 'Unknown error')}")
                except FileNotFoundError:
                    print(f"{red(f'File not found: {filepath}')}")

            elif command == "install" and len(parts) >= 2:
                package = parts[1]
                print(f"{cyan(f'Installing {package} in sandbox...')}")
                if agent.code_sandbox:
                    sandbox_name = await agent.code_sandbox.create_sandbox()
                    result = await agent.code_sandbox.install_package(package, sandbox_name)
                    if result.success:
                        print(f"{green(f'Installed: {package}')}")
                    else:
                        print(f"{red(f'Error: {result.error}')}")
                else:
                    print(f"{red('Docker not available')}")

            elif command == "sandboxes":
                if agent.code_sandbox:
                    sandboxes = await agent.code_sandbox.list_sandboxes()
                    if sandboxes:
                        print(f"\n{bold(cyan('Active sandboxes:'))}")
                        for s in sandboxes:
                            print(f"  {green('•')} {s}")
                    else:
                        print(f"{dim('No active sandboxes')}")
                else:
                    print(f"{red('Docker not available')}")

            elif command == "sandbox" and len(parts) >= 3 and parts[1] == "destroy":
                sandbox_name = parts[2]
                if agent.code_sandbox:
                    await agent.code_sandbox.destroy_sandbox(sandbox_name)
                    print(f"{green(f'Destroyed sandbox: {sandbox_name}')}")
                else:
                    print(f"{red('Docker not available')}")

            elif command == "agents":
                if agent.multi_agent:
                    agents = agent.multi_agent.registry.list_agents()
                    print(f"\n{bold(cyan('Registered Agents:'))}")
                    for a in agents:
                        print(
                            f"  {yellow('[' + a['role'] + ']')} {a['name']} - {green(a['state'])}"
                        )
                        if a["capabilities"]:
                            print(f"    {dim(', '.join(a['capabilities'][:5]))}")
                else:
                    print(f"{red('Multi-agent system not available')}")

            elif command == "task" and len(parts) >= 2:
                if agent.multi_agent:
                    valid_agents = [
                        "Researcher",
                        "Coder",
                        "Analyst",
                        "Planner",
                        "Critic",
                        "DataCleaner",
                        "Summarizer",
                        "Optimizer",
                        "Explorer",
                        "Synthesizer",
                    ]
                    if len(parts) >= 3 and parts[1] in valid_agents:
                        agent_name = parts[1]
                        task_desc = " ".join(parts[2:])
                    else:
                        agent_name = None
                        task_desc = " ".join(parts[1:])

                    print(f"{cyan(f'Running task: {task_desc[:50]}...')}")
                    result = await agent.agent_task(task_desc, agent_name)
                    if "error" in result:
                        error = result["error"]
                        print(f"{red(f'Error: {error}')}")
                    else:
                        completed_agent = result.get("agent", "unknown")
                        print(f"\n{green(f'Task completed by: {completed_agent}')}")
                        res = result.get("result", {})
                        if isinstance(res, dict):
                            for k, v in res.items():
                                print(f"  {yellow(k)}: {str(v)[:100]}")
                        else:
                            print(f"  Result: {str(res)[:200]}")
                else:
                    print(f"{red('Multi-agent system not available')}")

            elif command == "collaborate" and len(parts) >= 2:
                problem = " ".join(parts[1:])
                print(f"{cyan(f'Agents collaborating on: {problem[:50]}...')}")
                result = await agent.agent_collaborate(problem)
                if "error" in result:
                    error = result["error"]
                    print(f"{red(f'Error: {error}')}")
                else:
                    participants = result.get("participants", [])
                    print(f"\n{bold(cyan(f'Collaboration ({len(participants)} agents):'))}")
                    for line in result.get("discussion", []):
                        print(f"  {dim(line[:150])}")

            elif command == "pipeline" and len(parts) >= 2:
                pipeline_str = " ".join(parts[1:])
                stages = []
                for stage_str in pipeline_str.split(";"):
                    if ":" in stage_str:
                        agent_name, task = stage_str.split(":", 1)
                        stages.append({"agent": agent_name.strip(), "task": task.strip()})

                if stages:
                    print(f"{cyan(f'Running pipeline with {len(stages)} stages...')}")
                    result = await agent.agent_pipeline(stages)
                    if "error" in result:
                        error = result["error"]
                        print(f"{red(f'Error: {error}')}")
                    else:
                        stages_count = result.get("stages", 0)
                        print(f"\n{green(f'Pipeline complete ({stages_count} stages)')}")
                        for i, r in enumerate(result.get("results", [])):
                            print(
                                f"  {yellow(f'Stage {i + 1}:')} {r.get('agent', '?')} - {dim(str(r.get('result', ''))[:80])}"
                            )
                else:
                    print(f"{red('Invalid pipeline format. Use: agent1:task1;agent2:task2')}")

            elif command == "autonomous":
                cycles = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                label = f"{cycles} cycles" if cycles else "infinite"
                print(f"{cyan(f'Running {label} autonomous cycles (Ctrl+C to stop)...')}")
                await agent.autonomous_loop(max_cycles=cycles)

            elif command == "save":
                state = AgentState(
                    iteration=agent._iteration if hasattr(agent, "_iteration") else 0,
                    start_time=agent._start_time.isoformat()
                    if hasattr(agent, "_start_time") and agent._start_time
                    else "",
                )
                if hasattr(agent, "goals"):
                    goals = await agent.goals.get_active_goals()
                    state.goals = [
                        {"id": g.id, "description": g.description, "progress": g.progress}
                        for g in goals
                    ]
                await persistence.save(state)
                await persistence.save_backup(state)
                print(f"{green('State saved successfully')}")

            elif command == "load":
                state = await persistence.load()
                if state:
                    print(f"{green(f'Loaded state from {persistence.state_file}')}")
                    print(f"  Iteration: {state.iteration}")
                    print(f"  Goals: {len(state.goals)}")
                    print(f"  Custom: {len(state.custom)} entries")
                else:
                    print(f"{yellow('No saved state found')}")

            elif command == "backups":
                backups = persistence.list_backups()
                if backups:
                    print(f"\n{bold(cyan('Available backups:'))}")
                    for b in backups:
                        print(f"  {green('•')} {b}")
                else:
                    print(f"{dim('No backups found')}")

            else:
                print(f"{dim('Unknown command. Type ')}{yellow('quit')}{dim(' to exit.')}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"{red(f'Error: {e}')}")


async def demo_mode(agent: CognitiveOrchestrator) -> None:
    """Run demo of cognitive capabilities."""
    print(f"\n{bold(cyan('=== Ontogeny Demo Mode ==='))}\n")

    # 1. Set identity
    print(f"{yellow('1.')} Setting identity...")
    await agent.memory.identity.set_value("name", "DemoAgent")
    await agent.memory.identity.set_value(
        "capabilities", ["crawling", "learning", "self-improvement"]
    )

    # 2. Create and pursue a goal
    print(f"{yellow('2.')} Creating learning goal...")
    goal = await agent.goals.create_goal(
        description="Learn about large language models",
        source=GoalSource.INTRINSIC,
        priority=GoalPriority.HIGH,
        metadata={"drive": "curiosity"},
    )

    # 3. Create a plan
    print(f"{yellow('3.')} Creating plan...")
    plan = await agent.planner.create_plan(
        goal_id=goal.id,
        goal_description=goal.description,
        available_actions=["arxiv", "semantic_scholar", "wikipedia", "think"],
    )
    print(f"   Plan has {green(str(len(plan.steps)))} steps")

    # 4. Execute one cycle
    print(f"{yellow('4.')} Running cognitive cycle...")
    result = await agent.run_cycle()
    print(f"   Actions:   {yellow(str(len(result['actions'])))}")
    confidence = result.get("confidence", 0)
    print(f"   Confidence: {green(f'{confidence:.0%}')}")

    # 5. Check drives
    print(f"{yellow('5.')} Checking drives...")
    drives = await agent.goals.get_drive_status()
    for name, level in drives.items():
        print(f"   {yellow(name)}: {green(f'{level:.0%}')}")

    # 6. Get status
    print(f"{yellow('6.')} Agent status...")
    status = await agent.get_status()
    print(f"   State:     {green(status['state'])}")
    print(f"   Iteration: {yellow(str(status['iteration']))}")

    print(f"\n{bold(green('=== Demo Complete ==='))}")


def main() -> None:
    """Main entry point."""
    setup_logging()
    structlog.get_logger()

    agent = CognitiveOrchestrator()
    persistence = StatePersistence()

    async def run():
        try:
            await agent.initialize()

            if len(sys.argv) > 1:
                if sys.argv[1] == "--demo":
                    await demo_mode(agent)
                elif sys.argv[1] == "--autonomous":
                    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else None
                    await agent.autonomous_loop(max_cycles=cycles)
                else:
                    print(f"{red(f'Unknown argument: {sys.argv[1]}')}")
            else:
                print(f"\n{ONTOGENY_LOGO}")
                print(f"{bold(cyan('Select mode:'))}\n")
                print(f"  {yellow('1')} - Interactive mode (type commands)")
                print(f"  {yellow('2')} - Autonomous mode (continuous cycles)")
                print(f"  {yellow('3')} - Demo mode (quick showcase)")
                print(f"  {red('q')} - Quit\n")
                choice = input("mode> ").strip().lower()
                if choice == "1":
                    await interactive_mode(agent, persistence)
                elif choice == "2":
                    raw = input("cycles (leave empty for infinite): ").strip()
                    cycles = int(raw) if raw.isdigit() else None
                    await agent.autonomous_loop(max_cycles=cycles)
                elif choice == "3":
                    await demo_mode(agent)
        finally:
            await agent.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
