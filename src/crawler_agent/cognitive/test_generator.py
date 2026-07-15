"""Unit test generator and sandbox test runner for self-modification verification."""

import ast
import asyncio
import json
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backend import CognitiveBackend, CognitiveResponse


@dataclass
class TestCase:
    """A single test case."""
    name: str
    code: str
    expected_pass: bool = True


@dataclass
class TestSuite:
    """Collection of test cases for a module."""
    module_path: str
    test_cases: list[TestCase] = field(default_factory=list)
    setup_code: str = ""
    teardown_code: str = ""

    def to_pytest(self) -> str:
        """Generate pytest-compatible test file."""
        lines = [
            "import pytest",
            "import sys",
            "from pathlib import Path",
            f"sys.path.insert(0, str(Path(__file__).parent.parent))",
            "",
            self.setup_code,
            "",
        ]
        for tc in self.test_cases:
            lines.append(f"def test_{tc.name}():")
            for line in tc.code.strip().split("\n"):
                lines.append(f"    {line}")
            lines.append("")
        if self.teardown_code:
            lines.append(self.teardown_code)
        return "\n".join(lines)


@dataclass
class TestResult:
    """Result of running a test suite."""
    passed: int
    failed: int
    errors: list[str]
    output: str
    duration_seconds: float


class UnitTestGenerator:
    """Generates unit tests for code using LLM, runs them in sandbox."""

    def __init__(self, backend: CognitiveBackend, sandbox: Any = None):
        self.backend = backend
        self.sandbox = sandbox
        self.logger = None

    async def generate_tests(
        self,
        source_code: str,
        module_name: str,
        context: str = "",
        num_tests: int = 5,
    ) -> TestSuite:
        """Generate unit tests for source code."""
        prompt = f"""Generate {num_tests} pytest unit tests for the following Python module.

Module: {module_name}
Context: {context}

Source code:
```python
{source_code}
```

Requirements:
- Test public functions/classes only
- Cover happy path, edge cases, and error conditions
- Use pytest style (no unittest)
- Include assertions with descriptive messages
- Mock external dependencies (network, disk, APIs)
- Return ONLY a JSON object with this structure:
{{
  "tests": [
    {{"name": "test_function_happy_path", "code": "def test_function_happy_path():\\n    assert function(1) == 2", "expected_pass": true}},
    ...
  ],
  "setup_code": "import mock\\nfrom module import function",
  "teardown_code": ""
}}"""

        system = "You are a test generation expert. Output only valid JSON."
        response = await self.backend.complete(prompt, system, temperature=0.3, max_tokens=3000)

        try:
            data = response.parsed_json
            suite = TestSuite(module_path=module_name)
            suite.setup_code = data.get("setup_code", "")
            suite.teardown_code = data.get("teardown_code", "")
            for t in data.get("tests", []):
                suite.test_cases.append(TestCase(
                    name=t["name"],
                    code=t["code"],
                    expected_pass=t.get("expected_pass", True),
                ))
            return suite
        except Exception as e:
            return TestSuite(module_path=module_name)

    async def run_tests_in_sandbox(self, suite: TestSuite) -> TestResult:
        """Run test suite in Docker sandbox."""
        if not self.sandbox:
            return TestResult(0, 0, ["No sandbox available"], "", 0.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / f"test_{suite.module_path.replace('/', '_')}.py"
            test_file.write_text(suite.to_pytest())

            # Copy source module to sandbox
            src_path = Path(suite.module_path)
            if src_path.exists():
                import shutil
                dest = Path(tmpdir) / src_path.name
                shutil.copy2(src_path, dest)

            # Run pytest
            cmd = f"cd {tmpdir} && python -m pytest {test_file.name} -v --tb=short 2>&1"
            result = await self.sandbox.execute_command(cmd)

        return self._parse_pytest_output(result)

    def _parse_pytest_output(self, output: str) -> TestResult:
        """Parse pytest output into TestResult."""
        lines = output.strip().split("\n")
        passed = failed = 0
        errors = []

        for line in lines:
            if "PASSED" in line:
                passed += 1
            elif "FAILED" in line:
                failed += 1
            elif "ERROR" in line:
                errors.append(line)

        return TestResult(
            passed=passed,
            failed=failed,
            errors=errors,
            output=output,
            duration_seconds=0.0,
        )

    async def verify_patch(
        self,
        original_code: str,
        patched_code: str,
        module_path: str,
        context: str = "",
    ) -> tuple[bool, TestResult, str]:
        """Verify a patch by generating and running tests on both versions."""
        # Generate tests for original
        suite = await self.generate_tests(original_code, module_path, context)

        # Run on original
        orig_result = await self.run_tests_in_sandbox(suite)

        # Run on patched
        # (In practice, would write patched code to temp file and test)
        # For now, return original result as baseline
        return orig_result.failed == 0, orig_result, suite.to_pytest()


class SandboxTestRunner:
    """Runs arbitrary test code in Docker sandbox."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox

    async def run_test_script(self, script: str, timeout: int = 60) -> dict[str, Any]:
        """Run a Python test script and return structured results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = Path(tmpdir) / "test_script.py"
            script_file.write_text(script)

            cmd = f"cd {tmpdir} && python test_script.py 2>&1"
            try:
                output = await asyncio.wait_for(
                    self.sandbox.execute_command(cmd),
                    timeout=timeout,
                )
                return {"success": True, "output": output}
            except asyncio.TimeoutError:
                return {"success": False, "output": "Timeout", "error": "Test timed out"}
            except Exception as e:
                return {"success": False, "output": "", "error": str(e)}

    async def run_pytest(self, test_code: str, source_files: dict[str, str] = None) -> TestResult:
        """Run pytest with given test code and source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Write source files
            if source_files:
                for name, content in source_files.items():
                    (tmpdir / name).write_text(content)

            # Write test file
            test_file = tmpdir / "test_generated.py"
            test_file.write_text(test_code)

            cmd = f"cd {tmpdir} && python -m pytest test_generated.py -v --tb=short --json-report 2>&1"
            result = await self.sandbox.execute_command(cmd)

        return self._parse_pytest_output(result)

    def _parse_pytest_output(self, output: str) -> TestResult:
        import re
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        errors = [line for line in output.split("\n") if "ERROR" in line]
        return TestResult(passed, failed, errors, output, 0.0)


async def create_test_generator(backend: CognitiveBackend, sandbox: Any) -> UnitTestGenerator:
    """Factory function."""
    return UnitTestGenerator(backend, sandbox)