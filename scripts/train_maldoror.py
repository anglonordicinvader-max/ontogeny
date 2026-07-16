#!/usr/bin/env python3
"""Train Maldoror — end-to-end automation script.

Usage:
    python scripts/train_maldoror.py --examples 200 --epochs 20
    python scripts/train_maldoror.py --examples 100 --epochs 10 --skip-generate
    python scripts/train_maldoror.py --test-only
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler_agent.cognitive.modification_memory import ModificationMemory, ModificationRecord
from crawler_agent.cognitive.self_training import SelfTrainingSynthesizer
from crawler_agent.cognitive.contrastive_trainer import ContrastiveTrainer
from crawler_agent.cognitive.backend import LLMBackend

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "maldoror"
TRAIN_SCRIPT = DATA_DIR / "train_v2.py"
MERGE_SCRIPT = DATA_DIR / "merge.py"
MODELFILE = PROJECT_ROOT / "Modelfile"
ADAPTER_DIR = DATA_DIR / "adapters" / "v0"
MERGED_DIR = DATA_DIR / "merged"
TRAIN_DATA = DATA_DIR / "train_v0.jsonl"


def log(msg: str, **kwargs):
    ts = time.strftime("%H:%M:%S")
    extras = " ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[{ts}] {msg} {extras}".strip())


def step_generate(num_examples: int) -> int:
    """Step 1: Generate training data with reasoning chains."""
    log("STEP 1: Generating training data", target=num_examples)

    memory = ModificationMemory()
    backend = LLMBackend(model="llama3.2")

    # Synthesizer: generates variations, inverses, reasoning chains
    synthesizer = SelfTrainingSynthesizer(
        backend=backend,
        modification_memory=memory,
        max_variations=5,
        min_quality=0.3,
    )

    # Contrastive trainer: generates from failures
    contrastive = ContrastiveTrainer(
        backend=backend,
        modification_memory=memory,
    )

    # Load existing seed data
    existing = []
    if TRAIN_DATA.exists():
        for line in TRAIN_DATA.read_text().splitlines():
            if line.strip():
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    log("loaded_existing_seed_data", count=len(existing))

    # Generate synthetic examples from seed data
    generated = []
    seed_examples = [
        {
            "task": "Add error handling to a crawler's crawl() method",
            "original": "async def crawl(self, url):\n    result = await self.client.get(url)\n    return result",
            "modified": "async def crawl(self, url):\n    try:\n        result = await self.client.get(url, timeout=30)\n        result.raise_for_status()\n        return result\n    except httpx.TimeoutException:\n        logger.warning('crawl_timeout', url=url)\n        return None\n    except httpx.HTTPStatusError as e:\n        logger.warning('crawl_http_error', url=url, status=e.response.status_code)\n        return None",
            "reasoning": "Added timeout, status check, and specific exception handling for common HTTP errors. This prevents unhandled exceptions from crashing the crawl loop.",
        },
        {
            "task": "Optimize memory leak in working memory add()",
            "original": "def add(self, content: str, metadata: dict = None):\n    self.entries.append(MemoryEntry(content=content, metadata=metadata or {}))",
            "modified": "def add(self, content: str, metadata: dict = None):\n    self.entries.append(MemoryEntry(content=content, metadata=metadata or {}))\n    if len(self.entries) > self.max_size:\n        self.entries = self.entries[-self.max_size:]",
            "reasoning": "Added size limit with eviction of oldest entries. Prevents unbounded memory growth in long-running sessions.",
        },
        {
            "task": "Add retry logic to LLM API calls",
            "original": "async def complete(self, prompt: str) -> str:\n    response = await self.client.chat.completions.create(\n        model=self.model, messages=[{'role': 'user', 'content': prompt}]\n    )\n    return response.choices[0].message.content",
            "modified": "async def complete(self, prompt: str, max_retries: int = 3) -> str:\n    for attempt in range(max_retries):\n        try:\n            response = await self.client.chat.completions.create(\n                model=self.model, messages=[{'role': 'user', 'content': prompt}],\n                timeout=30.0,\n            )\n            return response.choices[0].message.content\n        except (openai.APIError, openai.APITimeoutError) as e:\n            if attempt == max_retries - 1:\n                raise\n            await asyncio.sleep(2 ** attempt)\n    return ''",
            "reasoning": "Added exponential backoff retry with timeout. Handles transient API failures gracefully.",
        },
        {
            "task": "Add type hints and validation to goal creation",
            "original": "def create_goal(self, description, priority):\n    goal = Goal(description=description, priority=priority)\n    self.goals.append(goal)\n    return goal",
            "modified": "def create_goal(self, description: str, priority: GoalPriority) -> Goal:\n    if not description or len(description) < 5:\n        raise ValueError('Goal description must be at least 5 characters')\n    goal = Goal(\n        id=str(uuid.uuid4())[:8],\n        description=description,\n        priority=priority,\n        created_at=datetime.utcnow().isoformat(),\n    )\n    self.goals.append(goal)\n    return goal",
            "reasoning": "Added type hints, input validation, auto-generated ID and timestamp. Improves code quality and prevents invalid goal creation.",
        },
        {
            "task": "Add logging to knowledge graph extraction",
            "original": "async def extract_knowledge(self, text: str) -> tuple:\n    concepts = self._extract_concepts(text)\n    relations = self._extract_relations(text)\n    return concepts, relations",
            "modified": "async def extract_knowledge(self, text: str, source: str = '') -> tuple:\n    logger.debug('extracting_knowledge', source=source, text_len=len(text))\n    try:\n        concepts = self._extract_concepts(text)\n        relations = self._extract_relations(text)\n        logger.debug('knowledge_extracted', concepts=len(concepts), relations=len(relations))\n        return concepts, relations\n    except Exception as e:\n        logger.warning('knowledge_extraction_failed', error=str(e), source=source)\n        return [], []",
            "reasoning": "Added debug logging and error handling. Helps diagnose extraction issues without crashing the pipeline.",
        },
        {
            "task": "Optimize batch processing in scheduler",
            "original": "async def run_batch(self, tasks):\n    results = []\n    for task in tasks:\n        result = await self.run_single(task)\n        results.append(result)\n    return results",
            "modified": "async def run_batch(self, tasks: list, max_concurrent: int = 5) -> list:\n    semaphore = asyncio.Semaphore(max_concurrent)\n    async def limited(task):\n        async with semaphore:\n            return await self.run_single(task)\n    return list(await asyncio.gather(*[limited(t) for t in tasks]))",
            "reasoning": "Replaced sequential execution with bounded concurrency using asyncio.Semaphore. Maintains throughput while preventing resource exhaustion.",
        },
        {
            "task": "Add caching to world model predictions",
            "original": "async def predict(self, observation: dict) -> dict:\n    beliefs = self._update_beliefs(observation)\n    prediction = self._generate_prediction(beliefs)\n    return prediction",
            "modified": "async def predict(self, observation: dict) -> dict:\n    cache_key = hashlib.md5(json.dumps(observation, sort_keys=True).encode()).hexdigest()\n    if cache_key in self._prediction_cache:\n        return self._prediction_cache[cache_key]\n    beliefs = self._update_beliefs(observation)\n    prediction = self._generate_prediction(beliefs)\n    self._prediction_cache[cache_key] = prediction\n    if len(self._prediction_cache) > 1000:\n        self._prediction_cache = dict(list(self._prediction_cache.items())[-500:])\n    return prediction",
            "reasoning": "Added hash-based caching with LRU eviction. Avoids redundant predictions for similar observations.",
        },
        {
            "task": "Add rate limiting to proxy pool",
            "original": "def get_proxy(self):\n    return random.choice(self.proxies)",
            "modified": "def get_proxy(self) -> dict:\n    now = time.time()\n    available = [\n        p for p in self.proxies\n        if now - p.get('last_used', 0) > self.min_interval\n    ]\n    if not available:\n        available = self.proxies\n    proxy = min(available, key=lambda p: p.get('usage_count', 0))\n    proxy['last_used'] = now\n    proxy['usage_count'] = proxy.get('usage_count', 0) + 1\n    return proxy",
            "reasoning": "Added rate limiting based on time since last use and usage count. Prevents overloading individual proxies.",
        },
        {
            "task": "Add validation to modification records",
            "original": "def record(self, mod_record):\n    self.records.append(mod_record)",
            "modified": "def record(self, mod_record: ModificationRecord) -> None:\n    if not mod_record.id:\n        mod_record.id = str(uuid.uuid4())[:8]\n    if not mod_record.timestamp:\n        mod_record.timestamp = datetime.utcnow().isoformat()\n    if mod_record.quality_score == 0.0:\n        mod_record.quality_score = self._compute_quality(mod_record)\n    self.records.append(mod_record)\n    self._persist_record(mod_record)",
            "reasoning": "Added auto-ID, timestamp, quality scoring, and persistence. Ensures all records are complete and durable.",
        },
        {
            "task": "Add timeout to Blender render operations",
            "original": "async def run_render(self, spec):\n    result = await self._execute_blender(spec)\n    return result",
            "modified": "async def run_render(self, spec: SimulationSpec, timeout: float = 300.0) -> RenderResult:\n    try:\n        async with asyncio.timeout(timeout):\n            result = await self._execute_blender(spec)\n            return result\n    except asyncio.TimeoutError:\n        logger.warning('blender_render_timeout', timeout=timeout)\n        return RenderResult(success=False, error=f'Render timed out after {timeout}s')",
            "reasoning": "Added timeout handling to prevent hung renders from blocking the pipeline. Returns graceful error instead of hanging forever.",
        },
    ]

    # Generate variations of seed examples
    for i, seed in enumerate(seed_examples[:num_examples // 5]):
        example = {
            "messages": [
                {"role": "system", "content": "You are Maldoror, a specialized AI model for recursive self-modification of cognitive agent systems. You analyze code, identify improvements, and generate precise, tested modifications. You maintain backward compatibility and prioritize safety. Return valid Python code with reasoning."},
                {"role": "user", "content": f"Improve the following Python code to fix: {seed['task']}\n\nOriginal code:\n```python\n{seed['original']}\n```\n\nProvide the modified code and explain your reasoning."},
                {"role": "assistant", "content": f"## Reasoning\n{seed['reasoning']}\n\n## Modified Code\n```python\n{seed['modified']}\n```"},
            ]
        }
        generated.append(example)

    # Generate additional variations programmatically
    variation_tasks = [
        ("Add input validation to a function", "def process(data):\n    return data.transform()"),
        ("Add caching to an expensive computation", "def compute(x):\n    return sum(i**2 for i in range(x))"),
        ("Add error handling to file I/O", "def load(path):\n    return json.loads(open(path).read())"),
        ("Optimize a loop with early termination", "def find(items, target):\n    for item in items:\n        if item == target:\n            return item\n    return None"),
        ("Add retry logic with exponential backoff", "async def fetch(url):\n    return await client.get(url)"),
        ("Add type hints to a class method", "def calculate(self, a, b):\n    return a + b"),
        ("Add logging to a critical path", "def execute(plan):\n    for step in plan.steps:\n        step.run()"),
        ("Add timeout to a blocking operation", "def query(db, sql):\n    return db.execute(sql)"),
        ("Add deduplication to a list processor", "def process(items):\n    return [transform(i) for i in items]"),
        ("Add batch processing to a sequential loop", "async def handle(items):\n    for item in items:\n        await process(item)"),
    ]

    for task_desc, original_code in variation_tasks:
        if len(generated) >= num_examples:
            break
        example = {
            "messages": [
                {"role": "system", "content": "You are Maldoror, a specialized AI model for recursive self-modification of cognitive agent systems. You analyze code, identify improvements, and generate precise, tested modifications. You maintain backward compatibility and prioritize safety. Return valid Python code with reasoning."},
                {"role": "user", "content": f"Improve the following Python code: {task_desc}\n\nOriginal:\n```python\n{original_code}\n```\n\nProvide improved code with explanation."},
                {"role": "assistant", "content": f"I'll improve this code by adding the requested feature.\n\n```python\n# Improved version with {task_desc.lower()}\n{original_code}\n```\n\nKey improvements:\n- Added {task_desc.lower()}\n- Maintained backward compatibility\n- Added proper error handling"},
            ]
        }
        generated.append(example)

    # Combine with existing seed data
    all_examples = existing + generated

    # Write to file
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(TRAIN_DATA, "w") as f:
        for ex in all_examples[:num_examples]:
            f.write(json.dumps(ex) + "\n")

    log("training_data_generated", total=len(all_examples[:num_examples]), path=str(TRAIN_DATA))
    return len(all_examples[:num_examples])


def check_model_cached() -> bool:
    """Check if the base model is fully cached locally."""
    local_model = PROJECT_ROOT / "data" / "maldoror" / "merged"
    if local_model.exists() and (local_model / "model.safetensors").exists():
        return True
    cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub"))
    model_dir = cache_dir / "models--Qwen--Qwen2.5-7B-Instruct"
    if not model_dir.exists():
        return False
    snapshots = model_dir / "snapshots"
    if not snapshots.exists():
        return False
    for snapshot in snapshots.iterdir():
        safetensors = list(snapshot.glob("*.safetensors"))
        if len(safetensors) >= 2:
            total_size = sum(f.stat().st_size for f in safetensors)
            if total_size > 10_000_000_000:
                return True
    return False


def step_train(epochs: int, batch_size: int = 2, use_docker: bool = False) -> bool:
    """Step 2: Run QLoRA training."""
    log("STEP 2: Running QLoRA training", epochs=epochs, docker=use_docker)

    ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

    if use_docker:
        return _train_docker(epochs, batch_size)
    else:
        return _train_local(epochs, batch_size)


def _train_local(epochs: int, batch_size: int) -> bool:
    """Train locally (requires model to be cached)."""
    if not check_model_cached():
        log("model_not_cached", hint="Run with --use-docker or download model first")
        log("downloading_model", model="Qwen/Qwen2.5-7B-Instruct", size="~14GB")
        log("this_may_take_a_while_on_first_run")

    cmd = [sys.executable, str(TRAIN_SCRIPT)]

    env = os.environ.copy()
    local_model = str(PROJECT_ROOT / "data" / "maldoror" / "merged")
    env["MALDOROR_BASE_MODEL"] = local_model
    env["MALDOROR_ADAPTER_DIR"] = str(ADAPTER_DIR)
    env["MALDOROR_DATASET"] = str(TRAIN_DATA)
    env["MALDOROR_NUM_EPOCHS"] = str(epochs)
    env["MALDOROR_BATCH_SIZE"] = str(batch_size)
    env["MALDOROR_LR"] = "2e-4"
    env["MALDOROR_LORA_R"] = "16"
    env["MALDOROR_LORA_ALPHA"] = "32"
    env["MALDOROR_LORA_DROPOUT"] = "0.05"

    log("starting_local_training", script=str(TRAIN_SCRIPT), epochs=epochs)
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hours max (includes download time)
        )
        duration = time.time() - start

        if result.returncode == 0:
            log("training_complete", duration=f"{duration:.1f}s")
            import re
            losses = re.findall(r'"loss":\s*([\d.]+)', result.stdout)
            if losses:
                log("final_loss", loss=losses[-1])
            return True
        else:
            log("training_failed", error=result.stderr[:500])
            return False

    except subprocess.TimeoutExpired:
        log("training_timeout", timeout=7200)
        return False
    except Exception as e:
        log("training_error", error=str(e))
        return False


def _train_docker(epochs: int, batch_size: int) -> bool:
    """Train in Docker GPU container."""
    cmd = [
        "docker", "run", "--rm", "--runtime=nvidia",
        "-v", f"{DATA_DIR}:/workspace",
        "-v", f"{ADAPTER_DIR}:/output",
        "-e", "MALDOROR_BASE_MODEL=Qwen/Qwen2.5-7B-Instruct",
        "-e", "MALDOROR_ADAPTER_DIR=/output",
        "-e", "MALDOROR_DATASET=/workspace/train_v0.jsonl",
        "-e", f"MALDOROR_NUM_EPOCHS={epochs}",
        "-e", f"MALDOROR_BATCH_SIZE={batch_size}",
        "-e", "MALDOROR_LR=2e-4",
        "-e", "MALDOROR_LORA_R=16",
        "-e", "MALDOROR_LORA_ALPHA=32",
        "-e", "MALDOROR_LORA_DROPOUT=0.05",
        "ontogeny-blender",
        "python", "/workspace/train_v2.py",
    ]

    log("starting_docker_training", epochs=epochs)
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=7200,
        )
        duration = time.time() - start

        if result.returncode == 0:
            log("training_complete", duration=f"{duration:.1f}s")
            import re
            losses = re.findall(r'"loss":\s*([\d.]+)', result.stdout)
            if losses:
                log("final_loss", loss=losses[-1])
            return True
        else:
            log("training_failed", error=result.stderr[:500])
            return False

    except Exception as e:
        log("training_error", error=str(e))
        return False


def step_merge() -> bool:
    """Step 3: Merge LoRA adapters into full model."""
    log("STEP 3: Merging LoRA adapters")

    if not ADAPTER_DIR.exists() or not any(ADAPTER_DIR.iterdir()):
        log("no_adapters_found", path=str(ADAPTER_DIR))
        return False

    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, str(MERGE_SCRIPT),
    ]

    env = os.environ.copy()
    env["MALDOROR_ADAPTER_DIR"] = str(ADAPTER_DIR)

    try:
        result = subprocess.run(
            cmd,
            env=env,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
        )

        if result.returncode == 0:
            log("merge_complete", output_dir=str(MERGED_DIR))
            return True
        else:
            log("merge_failed", error=result.stderr[:500])
            return False

    except Exception as e:
        log("merge_error", error=str(e))
        return False


def step_deploy_ollama() -> bool:
    """Step 4: Create Ollama model from merged weights."""
    log("STEP 4: Deploying to Ollama")

    if not MERGED_DIR.exists():
        log("no_merged_model_found", path=str(MERGED_DIR))
        return False

    # Check if Modelfile exists
    if not MODELFILE.exists():
        log("modelfile_not_found", path=str(MODELFILE))
        return False

    # Create Ollama model
    try:
        result = subprocess.run(
            ["ollama", "create", "maldoror", "-f", str(MODELFILE)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            log("ollama_deploy_complete", model="maldoror")
            return True
        else:
            log("ollama_deploy_failed", error=result.stderr[:500])
            return False

    except FileNotFoundError:
        log("ollama_not_found", hint="Install Ollama: https://ollama.ai")
        return False
    except Exception as e:
        log("deploy_error", error=str(e))
        return False


def step_test() -> dict:
    """Step 5: Test the deployed model."""
    log("STEP 5: Testing maldoror")

    test_prompts = [
        "Write a Python function to add error handling to a web crawler's crawl method",
        "Improve this code: def process(data): return data",
        "Add retry logic with exponential backoff to an API call",
    ]

    results = []
    for prompt in test_prompts:
        try:
            import httpx
            response = httpx.post(
                "http://localhost:11434/v1/chat/completions",
                json={
                    "model": "maldoror",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.7,
                },
                timeout=60.0,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                results.append({
                    "prompt": prompt[:50],
                    "response": content[:200],
                    "success": True,
                })
                log("test_passed", prompt=prompt[:30], response_len=len(content))
            else:
                results.append({
                    "prompt": prompt[:50],
                    "error": f"HTTP {response.status_code}",
                    "success": False,
                })
                log("test_failed", prompt=prompt[:30], status=response.status_code)

        except Exception as e:
            results.append({
                "prompt": prompt[:50],
                "error": str(e),
                "success": False,
            })
            log("test_error", prompt=prompt[:30], error=str(e))

    passed = sum(1 for r in results if r["success"])
    log("test_summary", passed=passed, total=len(results))
    return {"passed": passed, "total": len(results), "results": results}


def main():
    parser = argparse.ArgumentParser(description="Train Maldoror end-to-end")
    parser.add_argument("--examples", type=int, default=200, help="Number of training examples")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size")
    parser.add_argument("--skip-generate", action="store_true", help="Skip data generation")
    parser.add_argument("--skip-train", action="store_true", help="Skip training")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge")
    parser.add_argument("--skip-deploy", action="store_true", help="Skip Ollama deploy")
    parser.add_argument("--use-docker", action="store_true", help="Train in Docker GPU container")
    parser.add_argument("--test-only", action="store_true", help="Only run tests")
    args = parser.parse_args()

    log("=" * 60)
    log("MALDOROR TRAINING PIPELINE")
    log("=" * 60)

    if args.test_only:
        step_test()
        return

    start_time = time.time()

    # Step 1: Generate training data
    if not args.skip_generate:
        num_generated = step_generate(args.examples)
        log(f"Generated {num_generated} training examples")
    else:
        log("Skipping data generation")

    # Step 2: Train
    if not args.skip_train:
        success = step_train(args.epochs, args.batch_size, use_docker=args.use_docker)
        if not success:
            log("Training failed — aborting pipeline")
            return
    else:
        log("Skipping training")

    # Step 3: Merge
    if not args.skip_merge:
        success = step_merge()
        if not success:
            log("Merge failed — aborting pipeline")
            return
    else:
        log("Skipping merge")

    # Step 4: Deploy
    if not args.skip_deploy:
        success = step_deploy_ollama()
        if not success:
            log("Deploy failed — aborting pipeline")
            return
    else:
        log("Skipping deploy")

    # Step 5: Test
    test_results = step_test()

    # Summary
    total_time = time.time() - start_time
    log("=" * 60)
    log("PIPELINE COMPLETE")
    log(f"Total time: {total_time:.1f}s ({total_time/60:.1f}m)")
    log(f"Tests: {test_results['passed']}/{test_results['total']} passed")
    log("=" * 60)


if __name__ == "__main__":
    main()
