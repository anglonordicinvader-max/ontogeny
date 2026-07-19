"""Self-modification engine for autonomous capability expansion."""

import ast
import hashlib
import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

import structlog

from .backend import CognitiveBackend


class ModificationType(StrEnum):
    SKILL = "skill"  # Add new skill/capability
    CONFIG = "config"  # Modify configuration
    STRATEGY = "strategy"  # Change approach/strategy
    TOOL = "tool"  # Create or modify tool
    WORKFLOW = "workflow"  # Modify workflow/process


class SafetyLevel(StrEnum):
    SAFE = "safe"  # No risk, always allowed
    LOW_RISK = "low_risk"  # Minimal risk, auto-approved
    MEDIUM_RISK = "medium_risk"  # Moderate risk, needs review
    HIGH_RISK = "high_risk"  # Significant risk, needs approval
    CRITICAL = "critical"  # Dangerous, requires human approval


@dataclass
class Modification:
    """A proposed self-modification."""

    id: str
    mod_type: ModificationType
    description: str
    code: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    safety_level: SafetyLevel = SafetyLevel.LOW_RISK
    reasoning: str = ""
    expected_benefit: str = ""
    risks: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    approved: bool = False
    applied: bool = False
    rolled_back: bool = False
    performance_delta: float = 0.0


class CodeGenerator:
    """Generates code modifications safely."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.logger = structlog.get_logger()

    async def generate_skill(
        self,
        name: str,
        description: str,
        context: str = "",
    ) -> tuple[str, str]:
        """Generate a new skill function."""
        system_prompt = """Generate Python code for a skill function. The function should:
1. Be self-contained with clear inputs/outputs
2. Include error handling
3. Be safe (no destructive operations)
4. Include docstring

Return JSON with: code, explanation"""

        user_prompt = f"""Create a skill named '{name}'.
Description: {description}
Context: {context}

Generate the skill code:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            result = response.parsed_json
            return result.get("code", ""), result.get("explanation", "")
        except Exception as e:
            self.logger.error("code_generation_failed", error=str(e))
            return "", "Generation failed"

    async def generate_optimizer(
        self,
        current_code: str,
        performance_issue: str,
    ) -> tuple[str, str]:
        """Generate optimized version of existing code."""
        system_prompt = """Optimize the given code. Focus on:
1. Performance improvements
2. Better algorithms
3. Reduced complexity
4. Maintain safety

Return JSON with: optimized_code, improvements_made"""

        user_prompt = f"""Current code:
```python
{current_code}
```

Performance issue: {performance_issue}

Optimize:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            result = response.parsed_json
            return result.get("optimized_code", current_code), result.get("improvements_made", "")
        except Exception:
            return current_code, "Optimization failed"

    async def generate_fix(
        self,
        broken_code: str,
        error_message: str,
    ) -> tuple[str, str]:
        """Generate fix for broken code."""
        system_prompt = "Fix the broken code. Return JSON with: fixed_code, explanation"

        user_prompt = f"""Broken code:
```python
{broken_code}
```

Error: {error_message}

Fix:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=2000,
            temperature=0.3,
        )

        try:
            result = response.parsed_json
            return result.get("fixed_code", broken_code), result.get("explanation", "")
        except Exception:
            return broken_code, "Fix generation failed"


class CodeValidator:
    """Validates generated code for safety and correctness."""

    def __init__(self):
        self.logger = structlog.get_logger()
        self.dangerous_imports = {"os", "subprocess", "shutil", "sys", "ctypes"}
        self.dangerous_functions = {"exec", "eval", "compile", "__import__"}

    def validate_syntax(self, code: str) -> tuple[bool, str]:
        """Check if code is valid Python."""
        try:
            ast.parse(code)
            return True, "Valid syntax"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

    def check_safety(self, code: str) -> tuple[SafetyLevel, list[str]]:
        """Check code for safety issues."""
        issues = []
        level = SafetyLevel.SAFE

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return SafetyLevel.HIGH_RISK, ["Invalid syntax"]

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.dangerous_imports:
                        issues.append(f"Dangerous import: {alias.name}")
                        level = SafetyLevel.MEDIUM_RISK

            # Check function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.dangerous_functions:
                        issues.append(f"Dangerous function: {node.func.id}")
                        level = SafetyLevel.HIGH_RISK

            # Check file operations
            if isinstance(node, ast.Attribute):
                if node.attr in ("write", "delete", "remove", "rmdir"):
                    issues.append(f"File operation: {node.attr}")
                    level = max(level, SafetyLevel.LOW_RISK, key=lambda x: x.value)

        return level, issues

    def estimate_complexity(self, code: str) -> dict[str, Any]:
        """Estimate code complexity metrics."""
        try:
            tree = ast.parse(code)
            lines = len(code.splitlines())
            functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
            classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

            return {
                "lines": lines,
                "functions": functions,
                "classes": classes,
                "complexity_score": min(1.0, (lines * 0.01 + functions * 0.1 + classes * 0.2)),
            }
        except SyntaxError:
            return {"lines": 0, "functions": 0, "classes": 0, "complexity_score": 1.0}


class Sandbox:
    """Sandboxed execution environment."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.logger = structlog.get_logger()

    async def execute(self, code: str, timeout: int | None = None) -> dict[str, Any]:
        """Execute code in sandbox."""
        timeout = timeout or self.timeout

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Execution timed out",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
        finally:
            Path(temp_path).unlink(missing_ok=True)


class SelfModifier:
    """Self-modification engine for capability expansion."""

    def __init__(
        self,
        backend: CognitiveBackend,
        skills_dir: str = "./skills",
    ):
        self.generator = CodeGenerator(backend)
        self.validator = CodeValidator()
        self.sandbox = Sandbox()
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(exist_ok=True)
        self.modifications: list[Modification] = []
        self.skills: dict[str, str] = {}
        self.history_file = Path("./data/self_modification_history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.training_log = Path("./data/modification_training_log.jsonl")
        self.training_log.parent.mkdir(parents=True, exist_ok=True)
        self.verifier = None  # Set externally if PatchVerifier available
        self.logger = structlog.get_logger()
        self._load_history()

    def _load_history(self) -> None:
        """Load modification history from disk."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                for entry in data.get("modifications", []):
                    mod = Modification(
                        id=entry["id"],
                        mod_type=ModificationType(entry["mod_type"]),
                        description=entry.get("description", ""),
                        code=entry.get("code", ""),
                        config=entry.get("config", {}),
                        safety_level=SafetyLevel(entry.get("safety_level", "low_risk")),
                        reasoning=entry.get("reasoning", ""),
                        expected_benefit=entry.get("expected_benefit", ""),
                        risks=entry.get("risks", []),
                        approved=entry.get("approved", False),
                        applied=entry.get("applied", False),
                        rolled_back=entry.get("rolled_back", False),
                        performance_delta=entry.get("performance_delta", 0.0),
                    )
                    self.modifications.append(mod)
                # Reload saved skills
                for entry in data.get("modifications", []):
                    if entry.get("applied") and not entry.get("rolled_back") and entry.get("code"):
                        name = entry.get("config", {}).get("name", entry["id"])
                        self.skills[name] = entry["code"]
                        skill_path = self.skills_dir / f"{name}.py"
                        skill_path.write_text(entry["code"])
                self.logger.info("history_loaded", count=len(self.modifications))
            except Exception as e:
                self.logger.warning("history_load_failed", error=str(e))

    def _save_history(self) -> None:
        """Persist modification history to disk."""
        data = {
            "modifications": [
                {
                    "id": m.id,
                    "mod_type": m.mod_type.value,
                    "description": m.description,
                    "code": m.code,
                    "config": m.config,
                    "safety_level": m.safety_level.value,
                    "reasoning": m.reasoning,
                    "expected_benefit": m.expected_benefit,
                    "risks": m.risks,
                    "approved": m.approved,
                    "applied": m.applied,
                    "rolled_back": m.rolled_back,
                    "performance_delta": m.performance_delta,
                }
                for m in self.modifications
            ]
        }
        self.history_file.write_text(json.dumps(data, indent=2))

    async def propose_skill(
        self,
        name: str,
        description: str,
        context: str = "",
    ) -> Modification:
        """Propose a new skill."""
        code, explanation = await self.generator.generate_skill(name, description, context)

        # Validate
        valid, syntax_msg = self.validator.validate_syntax(code)
        safety_level, safety_issues = self.validator.check_safety(code)
        complexity = self.validator.estimate_complexity(code)

        mod = Modification(
            id=f"mod_{hashlib.md5(code.encode()).hexdigest()[:8]}",
            mod_type=ModificationType.SKILL,
            description=f"New skill: {name}",
            code=code,
            safety_level=safety_level,
            reasoning=explanation,
            expected_benefit=f"Adds capability: {description}",
            risks=safety_issues,
            config={"name": name, "complexity": complexity},
        )

        self.modifications.append(mod)
        return mod

    async def propose_optimization(
        self,
        skill_name: str,
        current_code: str,
        issue: str,
    ) -> Modification:
        """Propose optimization for existing skill."""
        optimized, improvements = await self.generator.generate_optimizer(current_code, issue)

        valid, _ = self.validator.validate_syntax(optimized)
        safety_level, issues = self.validator.check_safety(optimized)

        mod = Modification(
            id=f"opt_{hashlib.md5(optimized.encode()).hexdigest()[:8]}",
            mod_type=ModificationType.STRATEGY,
            description=f"Optimize {skill_name}",
            code=optimized,
            safety_level=safety_level,
            reasoning=improvements,
            expected_benefit=f"Improve performance of {skill_name}",
            risks=issues,
            config={"target_skill": skill_name},
        )

        self.modifications.append(mod)
        return mod

    async def apply_modification(
        self,
        mod_id: str,
        auto_approve: bool = False,
    ) -> bool:
        """Apply a modification."""
        mod = next((m for m in self.modifications if m.id == mod_id), None)
        if not mod:
            return False

        # Check safety
        if mod.safety_level in (SafetyLevel.HIGH_RISK, SafetyLevel.CRITICAL):
            if not auto_approve:
                self.logger.warning("high_risk_mod_blocked", mod_id=mod_id)
                return False

        # Test in sandbox first
        if mod.code:
            result = await self.sandbox.execute(mod.code)
            if not result["success"]:
                self.logger.warning("sandbox_test_failed", mod_id=mod_id, error=result["stderr"])
                mod.risks.append(f"Sandbox test failed: {result['stderr'][:200]}")
                return False

        # Apply based on type
        if mod.mod_type == ModificationType.SKILL:
            name = mod.config.get("name", "unknown")
            self.skills[name] = mod.code
            skill_path = self.skills_dir / f"{name}.py"
            skill_path.write_text(mod.code)

        mod.applied = True
        mod.approved = True

        # Record to training log
        self._record_training_log(mod, success=True)

        self.logger.info("modification_applied", mod_id=mod_id, type=mod.mod_type.value)
        self._save_history()
        return True

    def _record_training_log(self, mod: Modification, success: bool):
        """Record modification to training log for future fine-tuning."""
        record = {
            "id": mod.id,
            "timestamp": mod.timestamp.isoformat(),
            "mod_type": mod.mod_type.value,
            "description": mod.description,
            "reasoning": mod.reasoning,
            "expected_benefit": mod.expected_benefit,
            "safety_level": mod.safety_level.value,
            "success": success,
            "code": mod.code[:2000] if mod.code else "",
            "config": mod.config,
        }
        try:
            with open(self.training_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.warning("training_log_write_failed", error=str(e))

    async def test_modification(self, mod_id: str) -> dict[str, Any]:
        """Test a modification by executing it in sandbox and measuring results."""
        mod = next((m for m in self.modifications if m.id == mod_id), None)
        if not mod or not mod.code:
            return {"success": False, "error": "Modification not found or no code"}

        # Run the code in sandbox
        result = await self.sandbox.execute(mod.code, timeout=30)

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("stderr", "Execution failed"),
                "output": result.get("stdout", ""),
            }

        # Parse output for performance metrics
        output = result.get("stdout", "")
        metrics = {
            "success": True,
            "output": output[:500],
            "returncode": result.get("returncode", 0),
        }

        # Try to extract numeric metrics from output
        try:
            import ast

            # Look for common metric patterns
            if "success_rate" in output:
                for line in output.split("\n"):
                    if "success_rate" in line and ":" in line:
                        val = float(line.split(":")[-1].strip().rstrip("%")) / 100
                        metrics["success_rate"] = val
            if "items_per_minute" in output:
                for line in output.split("\n"):
                    if "items_per_minute" in line and ":" in line:
                        metrics["items_per_minute"] = float(line.split(":")[-1].strip())
        except (ValueError, IndexError):
            pass

        return metrics

    async def rollback(self, mod_id: str) -> bool:
        """Rollback a modification."""
        mod = next((m for m in self.modifications if m.id == mod_id), None)
        if not mod or not mod.applied:
            return False

        if mod.mod_type == ModificationType.SKILL:
            name = mod.config.get("name", "unknown")
            if name in self.skills:
                del self.skills[name]
                skill_path = self.skills_dir / f"{name}.py"
                skill_path.unlink(missing_ok=True)

        mod.rolled_back = True
        mod.applied = False
        self.logger.info("modification_rolled_back", mod_id=mod_id)
        self._save_history()
        return True

    async def learn_from_outcome(
        self,
        mod_id: str,
        success: bool,
        performance_delta: float = 0.0,
    ) -> None:
        """Learn from modification outcome."""
        mod = next((m for m in self.modifications if m.id == mod_id), None)
        if mod:
            mod.performance_delta = performance_delta
            # Update training log with actual outcome
            self._record_training_log(mod, success=success)
            if not success:
                await self.rollback(mod_id)
            self._save_history()

    def get_skills(self) -> dict[str, str]:
        """Get all learned skills."""
        return self.skills.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get modification statistics."""
        return {
            "total_modifications": len(self.modifications),
            "applied": sum(1 for m in self.modifications if m.applied),
            "rolled_back": sum(1 for m in self.modifications if m.rolled_back),
            "skills_learned": len(self.skills),
            "by_type": {
                t.value: sum(1 for m in self.modifications if m.mod_type == t)
                for t in ModificationType
            },
        }
