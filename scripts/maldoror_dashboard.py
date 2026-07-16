#!/usr/bin/env python3
"""CLI dashboard for Maldoror custom model pipeline status.

Usage: python scripts/maldoror_dashboard.py
"""
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def divider(char="=", width=60):
    return char * width


def section(title):
    return f"\n{divider()}\n  {title}\n{divider()}"


def main():
    try:
        from src.crawler_agent.cognitive.modification_memory import ModificationMemory
        from src.crawler_agent.cognitive.model_trainer import ModelTrainer
        from src.crawler_agent.cognitive.custom_model_manager import CustomModelManager
        from src.crawler_agent.cognitive.model_evaluation import (
            ModelEvaluator, QualityGate, RollbackManager, ABTestRunner,
        )
        from src.crawler_agent.cognitive.production import (
            PerformanceMonitor, RetrainingTrigger, CircuitBreaker,
        )
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from the project root.")
        sys.exit(1)

    print(section("MALDOROR PIPELINE DASHBOARD"))

    # Modification Memory
    mm = ModificationMemory()
    mem_stats = mm.get_stats()
    print(section("1. Training Data (ModificationMemory)"))
    print(f"  Total Records:     {mem_stats['total_records']}")
    print(f"  Successful:        {mem_stats['successful']}")
    print(f"  Avg Quality:       {mem_stats['avg_quality']:.2f}")
    print(f"  Ready for Training: {'YES' if mem_stats['ready_for_training'] else 'NO'}")
    print(f"  Sources:")
    for src, count in mem_stats.get("sources", {}).items():
        print(f"    {src}: {count}")
    print(f"  Task Types:")
    for t, count in mem_stats.get("task_types", {}).items():
        print(f"    {t}: {count}")

    # Model Trainer
    trainer = ModelTrainer(modification_memory=mm, output_dir="data/maldoror")
    train_stats = trainer.get_stats()
    print(section("2. Training (ModelTrainer)"))
    print(f"  Current Version:   {train_stats['current_version']}")
    print(f"  Total Runs:        {train_stats['total_runs']}")
    print(f"  Successful:        {train_stats['successful']}")
    print(f"  Latest Adapter:    {train_stats['latest_adapter'] or 'None'}")
    if train_stats["avg_loss"] > 0:
        print(f"  Avg Loss:          {train_stats['avg_loss']:.4f}")
    if train_stats["avg_duration"] > 0:
        print(f"  Avg Duration:      {train_stats['avg_duration']:.0f}s")
    if train_stats["runs"]:
        print(f"  Recent Runs:")
        for r in train_stats["runs"]:
            status = "OK" if r["success"] else "FAIL"
            print(f"    {r['version']}: [{status}] loss={r['loss']:.4f}")

    # Custom Model Manager
    mgr = CustomModelManager(model_trainer=trainer)
    mgr_stats = mgr.get_stats()
    print(section("3. Deployed Models (CustomModelManager)"))
    print(f"  Deployed Models:   {mgr_stats['deployed_models']}")
    print(f"  Active Model:      {mgr_stats['active_model'] or 'None'}")
    if mgr_stats["versions"]:
        print(f"  Versions:          {', '.join(mgr_stats['versions'])}")

    # Check Ollama availability
    print(section("4. Ollama Status"))
    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            maldoror_models = [l for l in lines[1:] if "maldoror" in l.lower()]
            print(f"  Ollama:            Available")
            print(f"  Total Models:      {len(lines) - 1}")
            print(f"  Maldoror Models:   {len(maldoror_models)}")
            for m in maldoror_models:
                print(f"    {m}")
        else:
            print(f"  Ollama:            Not running or error")
    except FileNotFoundError:
        print(f"  Ollama:            Not installed")
    except Exception as e:
        print(f"  Ollama:            Error - {e}")

    # Docker GPU status
    print(section("5. Docker GPU Status"))
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "images", "ontogeny-blender", "--format", "{{.Repository}}:{{.Tag}} {{.Size}}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            print(f"  Image:             {result.stdout.strip()}")
        else:
            print(f"  Image:             Not found (build with Dockerfile.blender)")
    except FileNotFoundError:
        print(f"  Docker:            Not installed")
    except Exception as e:
        print(f"  Docker:            Error - {e}")

    # Backend routing
    print(section("6. Backend Routing (MODIFIER_TASKS)"))
    try:
        from src.crawler_agent.cognitive.backend import HybridBackend
        print(f"  Modifier Tasks:    {', '.join(sorted(HybridBackend.MODIFIER_TASKS))}")
        print(f"  Code Tasks:        {', '.join(sorted(HybridBackend.CODE_TASKS))}")
        print(f"  Reasoning Tasks:   {', '.join(sorted(HybridBackend.REASONING_TASKS))}")
    except Exception as e:
        print(f"  Error: {e}")

    # Pipeline readiness
    print(section("7. Pipeline Readiness"))
    checks = [
        ("Training data exists", mem_stats["total_records"] >= 10),
        ("Ready for training", mem_stats["ready_for_training"]),
        ("Trainer initialized", trainer is not None),
        ("Manager initialized", mgr is not None),
    ]

    # Phase 4: Evaluation & Rollback
    eval_dir = Path("data/maldoror/eval")
    eval_reports = list(eval_dir.glob("eval_*.json")) if eval_dir.exists() else []
    print(section("8. Evaluation (Phase 4)"))
    print(f"  Evaluation Reports:  {len(eval_reports)}")
    if eval_reports:
        latest = eval_reports[-1]
        try:
            data = json.loads(latest.read_text())
            report = data.get("report", {})
            print(f"  Latest Verdict:      {report.get('verdict', 'unknown')}")
            print(f"  Improvement:         {report.get('improvement_pct', 0):+.1f}%")
            print(f"  Base Avg Score:      {report.get('base_avg', 0):.2f}")
            print(f"  Maldoror Avg Score:  {report.get('maldoror_avg', 0):.2f}")
        except Exception:
            print(f"  (could not parse {latest.name})")

    # Rollback history
    rollback_path = Path("data/maldoror/rollback_history.json")
    rollbacks = []
    if rollback_path.exists():
        try:
            rollbacks = json.loads(rollback_path.read_text())
        except Exception:
            pass
    print(f"  Total Rollbacks:     {len(rollbacks)}")
    if rollbacks:
        for rb in rollbacks[-3:]:
            print(f"    {rb.get('timestamp', '?')[:16]}: {rb.get('from_version', '?')} -> {rb.get('to_version', '?')} ({rb.get('reason', 'unknown')})")

    # Quality gates
    print(f"  Quality Gate:        min_score=0.5, max_latency=10s")

    # Phase 5: Production Monitoring
    print(section("9. Production Monitoring (Phase 5)"))
    monitor = PerformanceMonitor()
    monitor_summary = monitor.get_summary()
    if monitor_summary:
        print(f"  Tracked Metrics:     {len(monitor_summary)}")
        for name, stats in monitor_summary.items():
            print(f"    {name}: avg={stats['avg']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}, n={stats['count']}")
    else:
        print(f"  Tracked Metrics:     0 (no data yet)")

    trigger = RetrainingTrigger(monitor=monitor)
    t_stats = trigger.get_stats()
    print(f"  Retraining Trigger:  min_gap={t_stats['min_iterations']}, quality<{t_stats['quality_threshold']}")

    cb = CircuitBreaker()
    cb_state = cb.get_state()
    print(f"  Circuit Breaker:     {cb_state['state']} (failures: {cb_state['failure_count']})")

    # Self-Training Loop
    print(section("10. Self-Training Loop"))
    try:
        from src.crawler_agent.cognitive.self_training import SelfTrainingSynthesizer
        from src.crawler_agent.cognitive.backend import LLMBackend
        # We can't fully initialize without a running LLM, but we can show the module exists
        print(f"  Module:              SelfTrainingSynthesizer")
        print(f"  Function:            Generates training data from successful self-modifications")
        print(f"  Types:               variation, inverse, reasoning, generalization")
        print(f"  Integration:         Wired into orchestrator._check_self_improvement()")
        synth_records = [r for r in mm.records if r.source_module == "self_training"]
        print(f"  Synthesized Records: {len(synth_records)}")
        if synth_records:
            by_type = {}
            for r in synth_records:
                t = r.metadata.get("synth_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
            print(f"  By Type:")
            for t, count in by_type.items():
                print(f"    {t}: {count}")
    except ImportError as e:
        print(f"  Error: {e}")

    # Contrastive Training
    print(section("11. Contrastive Training"))
    try:
        from src.crawler_agent.cognitive.contrastive_trainer import ContrastiveTrainer
        print(f"  Module:              ContrastiveTrainer")
        print(f"  Function:            Trains on both successful AND failed modifications")
        print(f"  Types:               prediction, diagnosis, comparison")
        print(f"  Integration:         Wired into orchestrator reactive optimization (failure path)")
        contrastive_records = [r for r in mm.records if r.source_module == "contrastive_training"]
        print(f"  Contrastive Records: {len(contrastive_records)}")
        if contrastive_records:
            by_type = {}
            for r in contrastive_records:
                t = r.metadata.get("example_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
            print(f"  By Type:")
            for t, count in by_type.items():
                print(f"    {t}: {count}")
        failed_records = [r for r in mm.records if not r.success]
        print(f"  Failed Records:      {len(failed_records)}")
    except ImportError as e:
        print(f"  Error: {e}")

    # Model Population
    print(section("12. Model Population (Evolutionary Training)"))
    try:
        from src.crawler_agent.cognitive.model_population import ModelPopulation
        pop_dir = Path("data/maldoror/population")
        state_path = pop_dir / "population_state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
            print(f"  Generation:          {state.get('generation', 0)}")
            print(f"  Best Fitness:        {state.get('best_variant', {}).get('fitness', 0) if state.get('best_variant') else 0:.3f}")
            best = state.get("best_variant")
            if best:
                print(f"  Best Strategy:       {best.get('config', {}).get('name', 'unknown')}")
            gens = state.get("generations", [])
            if gens:
                latest = gens[-1]
                print(f"  Latest Generation:   {latest.get('variants', 0)} variants, avg_fitness={latest.get('avg_fitness', 0):.3f}")
        else:
            print(f"  Status:              Not yet initialized")
            print(f"  Will run first competition when training data is available")
        print(f"  Function:            Evolutionary training — multiple variants compete, winners propagate")
        print(f"  Integration:         Runs every 20 iterations via orchestrator._population_compete()")
    except ImportError as e:
        print(f"  Error: {e}")

    # Emergent Curriculum
    print(section("13. Emergent Curriculum (Self-Directed Training)"))
    try:
        from src.crawler_agent.cognitive.emergent_curriculum import EmergentCurriculum
        print(f"  Module:              EmergentCurriculum")
        print(f"  Function:            Analyzes weaknesses, generates targeted training tasks")
        print(f"  Types:               error_pattern, task_type, remediation")
        print(f"  Integration:         Runs every 10 iterations via orchestrator._emergent_curriculum_generate()")
        curriculum_records = [r for r in mm.records if r.source_module == "emergent_curriculum"]
        print(f"  Curriculum Records:  {len(curriculum_records)}")
        if curriculum_records:
            by_type = {}
            for r in curriculum_records:
                t = r.metadata.get("weakness_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
            print(f"  By Type:")
            for t, count in by_type.items():
                print(f"    {t}: {count}")
    except ImportError as e:
        print(f"  Error: {e}")

    # Adversarial Training
    print(section("14. Adversarial Training (Self-Critique)"))
    try:
        from src.crawler_agent.cognitive.adversarial_trainer import AdversarialTrainer
        print(f"  Module:              AdversarialTrainer")
        print(f"  Function:            Generates attempt + critique + counter-example triples")
        print(f"  Integration:         Runs every 15 iterations via orchestrator._adversarial_train()")
        adversarial_records = [r for r in mm.records if r.source_module == "adversarial_training"]
        print(f"  Adversarial Records: {len(adversarial_records)}")
        if adversarial_records:
            all_cats = []
            for r in adversarial_records:
                all_cats.extend(r.metadata.get("flaw_categories", []))
            cat_counts = {}
            for c in all_cats:
                cat_counts[c] = cat_counts.get(c, 0) + 1
            if cat_counts:
                print(f"  Flaw Categories:")
                for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])[:5]:
                    print(f"    {cat}: {count}")
    except ImportError as e:
        print(f"  Error: {e}")

    # Architecture Modifier
    print(section("15. Architecture Modifier (Neural Network Structural Modification)"))
    try:
        from src.crawler_agent.cognitive.architecture_modifier import ArchitectureModifier
        arch_dir = Path("data/maldoror/architecture")
        state_path = arch_dir / "architecture_state.json"
        print(f"  Module:              ArchitectureModifier")
        print(f"  Function:            maldoror rewrites its own transformer structure")
        print(f"  Modifications:       add_layer, remove_layer, modify_heads, modify_ffn, expand_tokenizer")
        print(f"  Integration:         Runs every 50 iterations via orchestrator._architecture_modify()")
        if state_path.exists():
            state = json.loads(state_path.read_text())
            cs = state.get("current_state", {})
            print(f"  Current Version:     {cs.get('version', 'v0')}")
            print(f"  Total Params:        {cs.get('total_params', 0):,}")
            print(f"  Layers:              {cs.get('num_layers', 0)}")
            print(f"  Attention Heads:     {cs.get('num_attention_heads', 0)}")
            print(f"  FFN Dim:             {cs.get('ffn_dim', 0)}")
            print(f"  Vocab Size:          {cs.get('vocab_size', 0)}")
            history = state.get("history", [])
            successful = [h for h in history if h.get("success")]
            print(f"  Modifications:       {len(history)} ({len(successful)} success)")
        else:
            print(f"  Status:              Not yet initialized")
            print(f"  Will run first modification when triggered")
    except ImportError as e:
        print(f"  Error: {e}")

    # Pipeline readiness
    checks.append(("Evaluation reports exist", len(eval_reports) > 0))
    all_pass = True
    for label, passed in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {label}")

    print(f"\n{divider()}")
    if all_pass:
        print("  PIPELINE: READY")
    else:
        print("  PIPELINE: NOT READY (fix FAIL items above)")
    print(divider())


if __name__ == "__main__":
    main()
