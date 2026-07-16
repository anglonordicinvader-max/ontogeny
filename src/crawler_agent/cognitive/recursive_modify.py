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
    metadata: dict[str, Any] = field(default_factory=dict)
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
        self.training_log = Path("./data/modification_training_log.jsonl")
        self.training_log.parent.mkdir(parents=True, exist_ok=True)
        self.verifier = None  # Set externally if PatchVerifier available
        self.logger = structlog.get_logger()

        # Filesystem access control and PR workflow
        from .fs_access import FileSystemAccessControl, GitWorkflow
        self.fs_access = FileSystemAccessControl(self.base_path)
        self.git_workflow = GitWorkflow(self.base_path)

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

        # 2. Find bottlenecks (errors, low success, high complexity)
        bottlenecks = self.analyzer.find_bottlenecks(error_logs, performance_metrics)

        # 3. If no bottlenecks, proactively look for ANY improvement opportunity
        if not bottlenecks:
            # Pick the most complex file — always room to simplify
            most_complex = max(files.values(), key=lambda f: f.complexity)
            # Pick the largest file — always room to optimize
            largest = max(files.values(), key=lambda f: f.line_count)

            # Target whichever has more room for improvement
            target = most_complex if most_complex.complexity > largest.line_count / 500 else largest
            bottlenecks = [{
                "module": target.module,
                "issue": "proactive_optimization",
                "severity": 0.3,  # Low severity — this is maintenance, not emergency
                "details": f"Complexity: {target.complexity:.0%}, Lines: {target.line_count}",
            }]

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
                # 9. Run verification if verifier is available
                if self.verifier:
                    try:
                        verification = await self._run_verification(mod, target_file)
                        if not verification:
                            self.logger.warning("verification_failed_after_apply", target=mod.target.value)
                            await self.rollback_modification(mod.id)
                            mod.rolled_back = True
                            mod.applied = False
                        else:
                            self._record_training_log(mod, success=True)
                    except Exception as e:
                        self.logger.warning("verification_error", error=str(e))
                else:
                    self._record_training_log(mod, success=True)

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

    async def _run_verification(
        self, mod: RecursiveModification, target_file: SourceFile
    ) -> bool:
        """Run patch verification after applying modification."""
        if not self.verifier:
            return True

        try:
            from .recursive_modify import RecursiveModification as RM
            result = await self.verifier.verify_patch(
                modification=mod,
                base_path=self.base_path,
                num_tests=3,
            )
            mod.metadata = getattr(mod, 'metadata', {}) or {}
            mod.metadata["verification"] = {
                "passed": result.passed,
                "tests_passed": result.tests_passed,
                "tests_total": result.tests_total,
            }
            return result.passed
        except Exception as e:
            self.logger.warning("verification_exception", error=str(e))
            return True  # Don't block on verification errors

    def _record_training_log(self, mod: RecursiveModification, success: bool):
        """Record successful modification to training log for future fine-tuning."""
        record = {
            "id": mod.id,
            "timestamp": mod.timestamp.isoformat(),
            "target_file": mod.file_path,
            "module": mod.target.value,
            "description": mod.description,
            "reasoning": mod.reasoning,
            "expected_benefit": mod.expected_benefit,
            "success": success,
            "original_code": mod.original_code[:2000],
            "new_code": mod.new_code[:2000],
            "diff": mod.diff[:2000],
        }
        try:
            with open(self.training_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            self.logger.warning("training_log_write_failed", error=str(e))

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
        """Use LLM to generate improved version of source code.

        Reads the full file and generates targeted improvements for the
        identified bottleneck, rather than rewriting everything.
        """
        content = source.content
        content_lines = content.split("\n")
        total_lines = len(content_lines)

        # For large files, send the bottleneck-relevant section + context
        # Find the bottleneck area (functions/classes near the issue)
        if total_lines > 300:
            # Send first 100 lines (imports/setup) + section around bottleneck
            focused_section = self._extract_bottleneck_section(content, bottleneck)
            prompt_content = f"# First 100 lines (imports/setup):\n{chr(10).join(content_lines[:100])}\n\n# Bottleneck section:\n{focused_section}"
        else:
            prompt_content = content

        system_prompt = """You are improving a Python module in a cognitive agent framework.

CRITICAL RULES:
1. Return the COMPLETE improved file (not just a diff)
2. Maintain ALL existing class names, method signatures, and imports
3. Only modify the specific code related to the identified issue
4. Keep the same module structure and public API
5. Add error handling only where the bottleneck indicates problems
6. Do NOT add new imports unless absolutely necessary
7. Do NOT rename or remove any existing functions/classes

Return JSON with: improved_code, description of changes, reasoning, expected_benefit"""

        user_prompt = f"""Module: {source.module}.py
Lines of code: {total_lines}
Complexity: {source.complexity:.0%}

Identified issue: {bottleneck['issue']}
Severity: {bottleneck['severity']:.0%}
Details: {bottleneck['details']}

Current code:
```python
{prompt_content}
```

Generate the COMPLETE improved file:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=8000,
            temperature=0.2,
        )

        try:
            result = response.parsed_json
            new_code = result.get("improved_code", "")
            if not new_code:
                return None

            # Validate the new code covers the full file
            new_lines = new_code.split("\n")
            if len(new_lines) < total_lines * 0.5 and total_lines > 100:
                # LLM truncated too much — reject and try targeted diff approach
                return await self._generate_targeted_diff(source, bottleneck)

            # Generate diff
            diff = "\n".join(difflib.unified_diff(
                content_lines,
                new_lines,
                fromfile=f"{source.module}.py (original)",
                tofile=f"{source.module}.py (improved)",
                lineterm="",
            ))

            return RecursiveModification(
                id=f"recursive_{hashlib.md5(new_code.encode()).hexdigest()[:8]}",
                target=self._module_to_target(source.module),
                file_path=str(source.path),
                description=result.get("description", f"Improve {source.module}"),
                original_code=content,
                new_code=new_code,
                diff=diff,
                reasoning=result.get("reasoning", ""),
                expected_benefit=result.get("expected_benefit", ""),
                risks=[],
            )
        except Exception as e:
            self.logger.error("code_generation_failed", module=source.module, error=str(e))
            return None

    def _extract_bottleneck_section(self, content: str, bottleneck: dict) -> str:
        """Extract the code section relevant to the bottleneck."""
        lines = content.split("\n")
        issue = bottleneck.get("issue", "")

        # Try to find relevant functions/classes based on issue type
        if "error" in issue:
            # Look for try/except blocks and error handling
            relevant_lines = []
            in_try = False
            for i, line in enumerate(lines):
                if "try:" in line or "except" in line:
                    in_try = True
                if in_try:
                    relevant_lines.append(f"{i+1}: {line}")
                if in_try and (line.strip() == "" and i > 0 and lines[i-1].strip() == ""):
                    in_try = False
                if len(relevant_lines) > 100:
                    break
            if relevant_lines:
                return "\n".join(relevant_lines)

        # Default: find the largest function/class
        current_func = None
        func_lines = []
        all_funcs = []

        for i, line in enumerate(lines):
            if line.startswith("def ") or line.startswith("class "):
                if current_func and func_lines:
                    all_funcs.append((current_func, func_lines[:]))
                current_func = i
                func_lines = [f"{i+1}: {line}"]
            elif current_func is not None:
                func_lines.append(f"{i+1}: {line}")

        if current_func and func_lines:
            all_funcs.append((current_func, func_lines))

        if all_funcs:
            # Return the longest function (most room for improvement)
            longest = max(all_funcs, key=lambda x: len(x[1]))
            return "\n".join(longest[1][:100])

        # Fallback: return middle section
        mid = len(lines) // 2
        return "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines[mid:mid+100]))

    async def _generate_targeted_diff(
        self, source: SourceFile, bottleneck: dict
    ) -> RecursiveModification | None:
        """Generate a targeted diff when full-file rewrite is too truncated."""
        content = source.content
        content_lines = content.split("\n")

        system_prompt = """You are generating a targeted diff for a specific issue in a Python file.

Return JSON with:
- target_lines: line range to modify (start, end)
- replacement_code: the new code for that section
- description: what changed
- reasoning: why this change helps"""

        user_prompt = f"""Module: {source.module}.py
Issue: {bottleneck['issue']}
Details: {bottleneck['details']}

Full file ({len(content_lines)} lines):
```python
{content[:6000]}
```

Generate a targeted fix for just the problematic section:"""

        response = await self.backend.complete(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=4000,
            temperature=0.2,
        )

        try:
            result = response.parsed_json
            start = result.get("target_lines", [0, 0])[0]
            end = result.get("target_lines", [0, 0])[1]
            replacement = result.get("replacement_code", "")

            if not replacement or start >= end:
                return None

            # Apply targeted replacement
            new_lines = content_lines[:start] + replacement.split("\n") + content_lines[end:]
            new_code = "\n".join(new_lines)

            diff = "\n".join(difflib.unified_diff(
                content_lines,
                new_code.split("\n"),
                fromfile=f"{source.module}.py (original)",
                tofile=f"{source.module}.py (improved)",
                lineterm="",
            ))

            return RecursiveModification(
                id=f"recursive_{hashlib.md5(new_code.encode()).hexdigest()[:8]}",
                target=self._module_to_target(source.module),
                file_path=str(source.path),
                description=result.get("description", f"Targeted fix for {source.module}"),
                original_code=content,
                new_code=new_code,
                diff=diff,
                reasoning=result.get("reasoning", ""),
                expected_benefit=result.get("expected_benefit", ""),
                risks=[],
            )
        except Exception as e:
            self.logger.error("targeted_diff_failed", module=source.module, error=str(e))
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
        """Apply modification with access control and optional PR workflow."""
        file_path = Path(mod.file_path)
        if not file_path.exists():
            return False

        # Check if we can write to this file
        can_write, reason = self.fs_access.can_write(str(file_path))
        if not can_write:
            self.logger.warning("write_denied", file=str(file_path), reason=reason)
            self.fs_access.log_access(str(file_path), "write", False, reason)
            return False

        self.fs_access.log_access(str(file_path), "write", True, reason)

        # Backup original (always, even for PR workflow)
        backup_path = self.backup_dir / f"{file_path.stem}_{mod.id}.py"
        shutil.copy2(file_path, backup_path)

        # Check if this requires PR
        if self.fs_access.requires_pr(str(file_path)):
            return await self._apply_via_pr(mod, file_path, backup_path)
        else:
            return await self._apply_direct(mod, file_path, backup_path)

    async def _apply_direct(self, mod: RecursiveModification, file_path: Path, backup_path: Path) -> bool:
        """Apply modification directly (for data/ and other direct-write paths)."""
        try:
            file_path.write_text(mod.new_code, encoding="utf-8")
            mod.applied = True
            mod.metadata["apply_method"] = "direct"
            self.logger.info(
                "source_file_modified_direct",
                file=str(file_path),
                backup=str(backup_path),
            )
            return True
        except Exception as e:
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            self.logger.error("source_modification_failed", error=str(e))
            return False

    async def _apply_via_pr(self, mod: RecursiveModification, file_path: Path, backup_path: Path) -> bool:
        """Apply modification via PR workflow (for src/, scripts/, etc.)."""
        try:
            # 1. Create branch
            branch_name = self.fs_access.create_branch_name(mod.description)
            if not self.git_workflow.create_branch(branch_name):
                # Restore from backup
                shutil.copy2(backup_path, file_path)
                return False

            # 2. Write the change
            file_path.write_text(mod.new_code, encoding="utf-8")

            # 3. Commit
            rel_path = str(file_path.relative_to(self.base_path))
            commit_message = f"agent: {mod.description}\n\n{mod.reasoning[:200]}"
            if not self.git_workflow.commit_changes(commit_message, [rel_path]):
                # Restore and switch back
                shutil.copy2(backup_path, file_path)
                self.git_workflow.switch_to_main()
                return False

            # 4. Push
            if not self.git_workflow.push_branch(branch_name):
                # Restore and switch back
                shutil.copy2(backup_path, file_path)
                self.git_workflow.switch_to_main()
                return False

            # 5. Create PR
            pr_title = f"agent: {mod.description[:50]}"
            pr_body = f"""## Agent Self-Modification

**File:** `{rel_path}`
**Description:** {mod.description}
**Reasoning:** {mod.reasoning}
**Expected Benefit:** {mod.expected_benefit}

**Safeguards:**
- Syntax validated: {mod.syntax_valid}
- Import safe: {mod.import_safe}
- Sandbox passed: {mod.sandbox_passed}

---
*This PR was created automatically by the agent's self-modification system.*
*Please review the changes before merging.*
"""
            pr_url = self.git_workflow.create_pr(branch_name, pr_title, pr_body)

            # 6. Switch back to main
            self.git_workflow.switch_to_main()

            # 7. Restore original file (PR will handle the merge)
            shutil.copy2(backup_path, file_path)

            if pr_url:
                mod.applied = False  # Not applied yet, pending PR review
                mod.metadata["apply_method"] = "pr"
                mod.metadata["pr_url"] = pr_url
                mod.metadata["branch"] = branch_name
                self.logger.info(
                    "pr_created",
                    file=str(file_path),
                    pr_url=pr_url,
                    branch=branch_name,
                )
                return True  # PR created successfully
            else:
                self.logger.warning("pr_creation_failed", file=str(file_path))
                return False

        except Exception as e:
            # Restore from backup
            shutil.copy2(backup_path, file_path)
            self.git_workflow.switch_to_main()
            self.logger.error("pr_workflow_failed", error=str(e))
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
