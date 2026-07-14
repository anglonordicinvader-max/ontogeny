"""Recursive self-modification — reads and rewrites the agent's own source code."""

import ast
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from .backend import CognitiveBackend


class ModificationTarget(str, Enum):
    ORCHESTRATOR = "orchestrator"      # Main cognitive loop
    PLANNER = "planner"                # Planning logic
    GOALS = "goals"                    # Goal generation
    SELF_MODIFY = "self_modify"        # Self-modification engine
    LEARNING = "learning"              # Learning modules
    KNOWLEDGE = "knowledge"            # Knowledge graph
    METACOGNITION = "metacognition"    # Self-evaluation
    CAUSAL = "causal"                  # Causal reasoning
    EMOTIONAL = "emotional"            # Emotional model
    UNCERTAINTY = "uncertainty"        # Uncertainty tracking


@dataclass
class SourceFile:
    """Represents a source file the agent can modify."""
    path: Path
    module: str
    content: str
    line_count: int
    complexity: float  # 0-1
    last_modified: datetime | None = None


@dataclass
class RecursiveModification:
    """A modification to the agent's own source code."""
    id: str
    target: ModificationTarget
    file_path: str
    description: str
    original_code: str
    new_code: str
    diff: str
    reasoning: str
    expected_benefit: str
    risks: list[str] = field(default_factory=list)
    syntax_valid: bool = False
    import_safe: bool = False
    sandbox_passed: bool = False
    applied: bool = False
    rolled_back: bool = False
    performance_delta: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SourceAnalyzer:
    """Reads and analyzes the agent's own source code."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.cognitive_path = base_path / "src" / "crawler_agent" / "cognitive"
        self.logger = structlog.get_logger()

    def scan_source_files(self) -> dict[ModificationTarget, SourceFile]:
        """Scan all modifiable source files."""
        files = {}
        target_map = {
            "orchestrator.py": ModificationTarget.ORCHESTRATOR,
            "planning.py": ModificationTarget.PLANNER,
            "goals.py": ModificationTarget.GOALS,
            "self_modify.py": ModificationTarget.SELF_MODIFY,
            "learning.py": ModificationTarget.LEARNING,
            "knowledge_graph.py": ModificationTarget.KNOWLEDGE,
            "metacognition.py": ModificationTarget.METACOGNITION,
            "causal_reasoning.py": ModificationTarget.CAUSAL,
            "emotional.py": ModificationTarget.EMOTIONAL,
            "uncertainty.py": ModificationTarget.UNCERTAINTY,
        }

        for filename, target in target_map.items():
            filepath = self.cognitive_path / filename
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                lines = content.split("\n")
                complexity = self._estimate_complexity(content)
                files[target] = SourceFile(
                    path=filepath,
                    module=filename.replace(".py", ""),
                    content=content,
                    line_count=len(lines),
                    complexity=complexity,
                )

        return files

    def _estimate_complexity(self, code: str) -> float:
        """Estimate code complexity 0-1."""
        try:
            tree = ast.parse(code)
            lines = len(code.split("\n"))
            functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
            classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            # Higher score = more complex = more room for improvement
            return min(1.0, (lines * 0.005 + functions * 0.08 + classes * 0.15))
        except SyntaxError:
            return 1.0

    def find_bottlenecks(
        self,
        error_logs: list[dict],
        performance_metrics: dict,
    ) -> list[dict[str, Any]]:
        """Identify code bottlenecks from errors and performance data."""
        bottlenecks = []

        # Count errors per module
        error_counts: dict[str, int] = {}
        for entry in error_logs[-50:]:
            module = entry.get("module", "unknown")
            error_counts[module] = error_counts.get(module, 0) + 1

        # High error count = bottleneck
        for module, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            if count >= 3:
                bottlenecks.append({
                    "module": module,
                    "issue": "high_error_rate",
                    "severity": min(1.0, count / 10),
                    "details": f"{count} errors in recent cycles",
                })

        # Low success rate per module
        for module, rate in performance_metrics.get("module_success_rates", {}).items():
            if rate < 0.7:
                bottlenecks.append({
                    "module": module,
                    "issue": "low_success_rate",
                    "severity": 1.0 - rate,
                    "details": f"Success rate: {rate:.0%}",
                })

        # Complex code with high error rate
        files = self.scan_source_files()
        target_to_module = {
            ModificationTarget.ORCHESTRATOR: "orchestrator",
            ModificationTarget.PLANNER: "planner",
            ModificationTarget.GOALS: "goals",
            ModificationTarget.LEARNING: "learning",
        }
        for target, source in files.items():
            module_name = target_to_module.get(target, "")
            if module_name in error_counts and source.complexity > 0.6:
                bottlenecks.append({
                    "module": module_name,
                    "issue": "complex_and_error_prone",
                    "severity": source.complexity * (error_counts.get(module_name, 0) / 10),
                    "details": f"Complexity: {source.complexity:.0%}, errors: {error_counts.get(module_name, 0)}",
                })

        return sorted(bottlenecks, key=lambda x: -x["severity"])


class RecursiveSelfModifier:
    """Agent reads its own source, identifies issues, rewrites code, tests, and applies."""

    def __init__(
        self,
        backend: CognitiveBackend,
        base_path: Path | None = None,
    ):
        self.backend = backend
        self.base_path = base_path or Path(".")
        self.analyzer = SourceAnalyzer(self.base_path)
        self.modifications: list[RecursiveModification] = []
        self.history_file = Path("./data/recursive_modifications.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = Path("./data/code_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger()
        self._load_history()

    def _load_history(self) -> None:
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                for entry in data.get("modifications", []):
                    mod = RecursiveModification(
                        id=entry["id"],
                        target=ModificationTarget(entry["target"]),
                        file_path=entry["file_path"],
                        description=entry.get("description", ""),
                        original_code=entry.get("original_code", ""),
                        new_code=entry.get("new_code", ""),
                        diff=entry.get("diff", ""),
                        reasoning=entry.get("reasoning", ""),
                        expected_benefit=entry.get("expected_benefit", ""),
                        risks=entry.get("risks", []),
                        syntax_valid=entry.get("syntax_valid", False),
                        import_safe=entry.get("import_safe", False),
                        sandbox_passed=entry.get("sandbox_passed", False),
                        applied=entry.get("applied", False),
                        rolled_back=entry.get("rolled_back", False),
                        performance_delta=entry.get("performance_delta", 0.0),
                    )
                    self.modifications.append(mod)
                self.logger.info("recursive_history_loaded", count=len(self.modifications))
            except Exception as e:
                self.logger.warning("recursive_history_load_failed", error=str(e))

    def _save_history(self) -> None:
        data = {
            "modifications": [
                {
                    "id": m.id,
                    "target": m.target.value,
                    "file_path": m.file_path,
                    "description": m.description,
                    "original_code": m.original_code[:2000],  # Truncate for storage
                    "new_code": m.new_code[:2000],
                    "diff": m.diff[:2000],
                    "reasoning": m.reasoning,
                    "expected_benefit": m.expected_benefit,
                    "risks": m.risks,
                    "syntax_valid": m.syntax_valid,
                    "import_safe": m.import_safe,
                    "sandbox_passed": m.sandbox_passed,
                    "applied": m.applied,
                    "rolled_back": m.rolled_back,
                    "performance_delta": m.performance_delta,
                }
                for m in self.modifications
            ]
        }
        self.history_file.write_text(json.dumps(data, indent=2))

    async def analyze_and_improve(
        self,
        error_logs: list[dict] | None = None,
        performance_metrics: dict | None = None,
    ) -> RecursiveModification | None:
        """Full recursive loop: analyze → identify → generate → test → apply."""
        error_logs = error_logs or []
        performance_metrics = performance_metrics or {}

        # 1. Scan source
        files = self.analyzer.scan_source_files()
        if not files:
            return None

        # 2. Find bottlenecks
        bottlenecks = self.analyzer.find_bottlenecks(error_logs, performance_metrics)
        if not bottlenecks:
            # No bottlenecks — try to improve complexity
            most_complex = max(files.values(), key=lambda f: f.complexity)
            if most_complex.complexity > 0.5:
                bottlenecks = [{
                    "module": most_complex.module,
                    "issue": "high_complexity",
                    "severity": most_complex.complexity,
                    "details": f"Complexity: {most_complex.complexity:.0%}",
                }]
            else:
                return None  # Code is clean and simple — no improvement needed

        # 3. Pick highest severity bottleneck
        target_bottleneck = bottlenecks[0]
        target_file = self._find_file_for_module(files, target_bottleneck["module"])

        if not target_file:
            return None

        # 4. Generate improvement via LLM
        mod = await self._generate_code_modification(target_file, target_bottleneck)
        if not mod:
            return None

        # 5. Validate syntax
        mod.syntax_valid, syntax_err = self._validate_syntax(mod.new_code)
        if not mod.syntax_valid:
            mod.risks.append(f"Syntax error: {syntax_err}")
            self.modifications.append(mod)
            self._save_history()
            return mod

        # 6. Check imports are safe
        mod.import_safe = self._check_import_safety(mod.new_code)

        # 7. Test in sandbox (import the module)
        mod.sandbox_passed = await self._test_module_import(mod.new_code, target_file.module)

        # 8. Apply if safe
        if mod.syntax_valid and mod.import_safe and mod.sandbox_passed:
            applied = await self._apply_source_modification(mod)
            if applied:
                self.logger.info(
                    "recursive_modification_applied",
                    target=mod.target.value,
                    file=mod.file_path,
                    description=mod.description,
                )
            else:
                self.logger.warning(
                    "recursive_modification_failed",
                    target=mod.target.value,
                )
        else:
            self.logger.info(
                "recursive_modification_rejected",
                target=mod.target.value,
                syntax_valid=mod.syntax_valid,
                import_safe=mod.import_safe,
                sandbox_passed=mod.sandbox_passed,
            )

        self.modifications.append(mod)
        self._save_history()
        return mod

    def _find_file_for_module(
        self, files: dict[ModificationTarget, SourceFile], module: str
    ) -> SourceFile | None:
        """Find source file matching module name."""
        for target, source in files.items():
            if source.module == module:
                return source
        # Fuzzy match
        for target, source in files.items():
            if module.lower() in source.module.lower():
                return source
        return None

    async def _generate_code_modification(
        self, source: SourceFile, bottleneck: dict
    ) -> RecursiveModification | None:
        """Use LLM to generate improved version of source code."""
        # Read only a portion to avoid token limits (key functions)
        content_lines = source.content.split("\n")
        # Focus on first 200 lines (imports + main class + key methods)
        focused_content = "\n".join(content_lines[:200])

        system_prompt = """You are improving a Python module in a cognitive agent framework.

Analyze the code and generate an improved version that:
1. Fixes the identified issue
2. Maintains all existing functionality (class names, method signatures, imports)
3. Adds better error handling where needed
4. Improves the specific bottleneck identified
5. Keeps the same module structure

Return JSON with: improved_code, description of changes, reasoning, expected_benefit"""

        user_prompt = f"""Module: {source.module}.py
Lines of code: {source.line_count}
Complexity: {source.complexity:.0%}

Identified issue: {bottleneck['issue']}
Severity: {bottleneck['severity']:.0%}
Details: {bottleneck['details']}

Current code (first 200 lines):
```python
{focused_content}
```

Generate improved code:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=4000,
            temperature=0.2,
        )

        try:
            result = response.parsed_json
            new_code = result.get("improved_code", "")
            if not new_code:
                return None

            # Generate diff
            diff = "\n".join(difflib.unified_diff(
                source.content.split("\n")[:200],
                new_code.split("\n")[:200],
                fromfile=f"{source.module}.py (original)",
                tofile=f"{source.module}.py (improved)",
                lineterm="",
            ))

            return RecursiveModification(
                id=f"recursive_{hashlib.md5(new_code.encode()).hexdigest()[:8]}",
                target=self._module_to_target(source.module),
                file_path=str(source.path),
                description=result.get("description", f"Improve {source.module}"),
                original_code=source.content,
                new_code=new_code,
                diff=diff,
                reasoning=result.get("reasoning", ""),
                expected_benefit=result.get("expected_benefit", ""),
                risks=[],
            )
        except Exception as e:
            self.logger.error("code_generation_failed", module=source.module, error=str(e))
            return None

    def _module_to_target(self, module: str) -> ModificationTarget:
        for target in ModificationTarget:
            if target.value == module:
                return target
        return ModificationTarget.ORCHESTRATOR

    def _validate_syntax(self, code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _check_import_safety(self, code: str) -> bool:
        dangerous = {"os", "subprocess", "shutil", "sys", "ctypes", "socket"}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in dangerous:
                            return False
            return True
        except SyntaxError:
            return False

    async def _test_module_import(self, new_code: str, module_name: str) -> bool:
        """Test that the modified module can be imported."""
        test_code = f"""
import sys
sys.path.insert(0, 'src')
try:
    # Write the modified code to a temp file and try to compile
    import ast
    ast.parse('''{new_code.replace("'", "\\'")}''')
    print("COMPILE_OK")
except Exception as e:
    print(f"COMPILE_FAIL: {{e}}")
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return "COMPILE_OK" in result.stdout
        except Exception:
            return False
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def _apply_source_modification(self, mod: RecursiveModification) -> bool:
        """Apply modification with backup."""
        file_path = Path(mod.file_path)
        if not file_path.exists():
            return False

        # Backup original
        backup_path = self.backup_dir / f"{file_path.stem}_{mod.id}.py"
        shutil.copy2(file_path, backup_path)

        # Write new code
        try:
            file_path.write_text(mod.new_code, encoding="utf-8")
            mod.applied = True
            self.logger.info(
                "source_file_modified",
                file=str(file_path),
                backup=str(backup_path),
            )
            return True
        except Exception as e:
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            self.logger.error("source_modification_failed", error=str(e))
            return False

    async def rollback_modification(self, mod_id: str) -> bool:
        """Rollback a modification using backup."""
        mod = next((m for m in self.modifications if m.id == mod_id), None)
        if not mod or not mod.applied:
            return False

        # Find backup
        file_path = Path(mod.file_path)
        backup_path = self.backup_dir / f"{file_path.stem}_{mod.id}.py"

        if backup_path.exists():
            shutil.copy2(backup_path, file_path)
            mod.rolled_back = True
            mod.applied = False
            self.logger.info("source_file_restored", file=str(file_path))
            self._save_history()
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_modifications": len(self.modifications),
            "applied": sum(1 for m in self.modifications if m.applied),
            "rolled_back": sum(1 for m in self.modifications if m.rolled_back),
            "syntax_valid": sum(1 for m in self.modifications if m.syntax_valid),
            "import_safe": sum(1 for m in self.modifications if m.import_safe),
            "sandbox_passed": sum(1 for m in self.modifications if m.sandbox_passed),
        }
