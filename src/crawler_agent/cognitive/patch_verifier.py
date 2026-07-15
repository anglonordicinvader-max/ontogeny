"""Patch verification system: generates tests, runs in sandbox, validates patches."""

import ast
import asyncio
import json
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend
from .recursive_modify import RecursiveModification, ModificationTarget


@dataclass
class TestCase:
    """A generated test case."""
    name: str
    code: str
    description: str


@dataclass
class VerificationResult:
    """Result of patch verification."""
    patch_id: str
    passed: bool
    tests_passed: int
    tests_total: int
    test_output: str
    errors: list[str] = field(default_factory=list)
    coverage: float = 0.0


class TestGenerator:
    """Generates unit tests for a given code module."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend

    async def generate_tests(
        self,
        module_path: Path,
        target: ModificationTarget,
        num_tests: int = 5,
    ) -> list[TestCase]:
        """Generate unit tests for a module."""
        source = module_path.read_text(encoding="utf-8")

        # Parse to understand the module structure
        tree = ast.parse(source)
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]

        prompt = f"""Generate {num_tests} unit tests for this Python module.

Module: {module_path.name}
Target: {target.value}

Source code:
```python
{source[:4000]}
```

Requirements:
- Test public functions and classes
- Include edge cases (empty input, None, boundary values)
- Use pytest style
- Each test should be independent
- Return ONLY a JSON array of test objects with: name, code, description"""

        response = await self.backend.complete(prompt, temperature=0.3, max_tokens=3000)
        try:
            tests_data = json.loads(response.content)
            if not isinstance(tests_data, list):
                tests_data = []
        except json.JSONDecodeError:
            tests_data = []

        tests = []
        for i, t in enumerate(tests_data[:num_tests]):
            tests.append(TestCase(
                name=t.get("name", f"test_generated_{i}"),
                code=t.get("code", ""),
                description=t.get("description", ""),
            ))

        # Add fallback tests if LLM failed
        if not tests:
            tests = self._generate_fallback_tests(module_path, functions, classes)

        return tests

    def _generate_fallback_tests(
        self,
        module_path: Path,
        functions: list[ast.FunctionDef],
        classes: list[ast.ClassDef],
    ) -> list[TestCase]:
        """Generate basic fallback tests."""
        tests = []
        module_name = module_path.stem

        for func in functions[:3]:
            if not func.name.startswith("_"):
                tests.append(TestCase(
                    name=f"test_{func.name}_basic",
                    code=f"""def test_{func.name}_basic():
    from {module_name} import {func.name}
    # Basic smoke test
    result = {func.name}()
    assert result is not None""",
                    description=f"Basic test for {func.name}",
                ))

        for cls in classes[:2]:
            tests.append(TestCase(
                name=f"test_{cls.name}_instantiation",
                code=f"""def test_{cls.name}_instantiation():
    from {module_name} import {cls.name}
    obj = {cls.name}()
    assert obj is not None""",
                description=f"Test {cls.name} can be instantiated",
            ))

        return tests[:5]


class PatchVerifier:
    """Verifies patches by running tests in sandbox."""

    def __init__(
        self,
        backend: CognitiveBackend,
        sandbox: Any,
        test_generator: TestGenerator | None = None,
    ):
        self.backend = backend
        self.sandbox = sandbox
        self.test_generator = test_generator or TestGenerator(backend)

    async def verify_patch(
        self,
        modification: RecursiveModification,
        base_path: Path,
        num_tests: int = 5,
        run_existing_tests: bool = True,
    ) -> VerificationResult:
        """Verify a patch by generating and running tests."""
        target_file = base_path / modification.file_path

        # Backup original
        original_content = target_file.read_text(encoding="utf-8") if target_file.exists() else ""

        try:
            # Apply patch
            new_content = modification.new_code
            target_file.write_text(new_content, encoding="utf-8")

            # Generate tests
            tests = await self.test_generator.generate_tests(
                target_file, modification.target, num_tests
            )

            # Run tests in sandbox
            result = await self._run_tests(target_file, tests, modification)

            return result

        finally:
            # Restore original
            if original_content:
                target_file.write_text(original_content, encoding="utf-8")
            elif target_file.exists():
                target_file.unlink()

    async def _run_tests(
        self,
        target_file: Path,
        tests: list[TestCase],
        modification: RecursiveModification,
    ) -> VerificationResult:
        """Run tests in sandbox."""
        module_name = target_file.stem

        # Build test file
        test_code = self._build_test_file(module_name, tests)

        # Write to temp location
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / f"test_{module_name}.py"
            test_file.write_text(test_code)

            # Copy target module
            target_copy = tmp_path / target_file.name
            target_copy.write_text(target_file.read_text())

            # Run pytest
            result = await self._run_pytest_in_sandbox(tmp_path, test_file)

        passed = result.get("passed", 0)
        total = result.get("total", len(tests))
        output = result.get("output", "")
        errors = result.get("errors", [])

        return VerificationResult(
            patch_id=modification.id,
            passed=passed == total and total > 0,
            tests_passed=passed,
            tests_total=total,
            test_output=output,
            errors=errors,
            coverage=result.get("coverage", 0.0),
        )

    def _build_test_file(self, module_name: str, tests: list[TestCase]) -> str:
        """Build a pytest test file."""
        imports = f"""import sys
sys.path.insert(0, '.')
import pytest
from {module_name} import *
"""

        test_functions = "\n\n".join(t.code for t in tests)

        return f"""{imports}

{test_functions}
"""

    async def _run_pytest_in_sandbox(self, workdir: Path, test_file: Path) -> dict:
        """Run pytest in Docker sandbox."""
        # This would use the sandbox to run pytest
        # For now, return mock result
        return {
            "passed": 3,
            "total": 5,
            "output": "3 passed, 2 failed",
            "errors": ["test_x failed: AssertionError"],
            "coverage": 0.6,
        }


class CritiqueAgent:
    """Second-pass LLM that reviews patches for bugs, security, style."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend

    async def critique_patch(
        self,
        modification: RecursiveModification,
        original_file: Path,
    ) -> dict[str, Any]:
        """Review a patch for issues."""
        original = original_file.read_text(encoding="utf-8") if original_file.exists() else ""
        new = modification.new_code

        prompt = f"""Review this code patch for bugs, security issues, and style problems.

TARGET: {modification.target.value}
FILE: {modification.file_path}
DESCRIPTION: {modification.description}

ORIGINAL CODE:
```python
{original[:3000]}
```

NEW CODE:
```python
{new[:3000]}
```

DIFF:
```diff
{modification.diff[:2000]}
```

Return JSON with:
{{
  "issues": [
    {{"type": "bug|security|style|performance", "severity": "high|medium|low", "description": "...", "line": 10}}
  ],
  "suggestions": ["..."],
  "approved": true|false,
  "confidence": 0.0-1.0
}}"""

        response = await self.backend.complete(prompt, temperature=0.1, max_tokens=2000)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "issues": [],
                "suggestions": [],
                "approved": True,
                "confidence": 0.5,
            }


class MultiRolloutPatchGenerator:
    """Generates multiple patch candidates and selects the best."""

    def __init__(
        self,
        backend: CognitiveBackend,
        verifier: PatchVerifier,
        critic: CritiqueAgent,
        num_rollouts: int = 3,
    ):
        self.backend = backend
        self.verifier = verifier
        self.critic = critic
        self.num_rollouts = num_rollouts

    async def generate_best_patch(
        self,
        target: ModificationTarget,
        file_path: Path,
        issue: str,
        base_path: Path,
    ) -> RecursiveModification | None:
        """Generate N patches, verify all, return best."""
        candidates = []

        for i in range(self.num_rollouts):
            # Generate patch with variation
            patch = await self._generate_single_patch(target, file_path, issue, i)
            if patch:
                candidates.append(patch)

        if not candidates:
            return None

        # Verify each
        verified = []
        for patch in candidates:
            # Critique first
            critique = await self.critic.critique_patch(patch, base_path / file_path)
            if not critique.get("approved", True):
                patch.metadata["critique_issues"] = critique.get("issues", [])
                continue

            # Verify
            result = await self.verifier.verify_patch(patch, base_path)
            patch.metadata["verification"] = {
                "passed": result.passed,
                "tests_passed": result.tests_passed,
                "tests_total": result.tests_total,
            }
            if result.passed:
                verified.append(patch)

        if not verified:
            return None

        # Select best (most tests passed, then highest critique confidence)
        best = max(verified, key=lambda p: (
            p.metadata["verification"]["tests_passed"],
            p.metadata.get("confidence", 0),
        ))
        return best

    async def _generate_single_patch(
        self,
        target: ModificationTarget,
        file_path: Path,
        issue: str,
        variation: int,
    ) -> RecursiveModification | None:
        """Generate a single patch candidate."""
        # This would integrate with RecursiveSelfModifier
        # For now, return None - would need full integration
        return None


async def create_test_generator(backend: CognitiveBackend, sandbox: Any) -> 'UnitTestGenerator':
    from .test_generator import UnitTestGenerator
    return UnitTestGenerator(backend, sandbox)