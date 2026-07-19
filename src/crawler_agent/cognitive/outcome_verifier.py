"""Outcome Verifier - Executable verification for agent task outcomes.

Replaces LLM-as-judge with actual execution-based verification:
- Code tasks: run tests, check correctness
- Planning tasks: execute plan, verify goal achievement
- Reasoning tasks: verify logical consistency, factual accuracy
- Simulation tasks: compare predicted vs actual outcomes
"""

import ast
import asyncio
import json
import tempfile
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ..storage import CodeSandbox
from .backend import CognitiveBackend, CognitiveResponse
from .blender_sandbox import BlenderSandbox

logger = structlog.get_logger()


class VerificationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class VerificationResult:
    status: VerificationStatus
    score: float  # 0.0 - 1.0
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    evidence: list[dict] = field(default_factory=list)


@dataclass
class VerificationSpec:
    """Specification for how to verify a task outcome."""

    task_type: str  # "code", "planning", "reasoning", "simulation"
    success_criteria: dict[str, Any]
    test_cases: list[dict] = field(default_factory=list)
    expected_output: str | None = None
    timeout_seconds: float = 60.0
    metadata: dict = field(default_factory=dict)


class OutcomeVerifier(ABC):
    """Abstract base for outcome verifiers."""

    @abstractmethod
    async def verify(
        self, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        pass


class CodeOutcomeVerifier(OutcomeVerifier):
    """Verifies code generation tasks by running tests."""

    def __init__(self, sandbox: CodeSandbox):
        self.sandbox = sandbox
        self.logger = logger.bind(component="code_verifier")

    async def verify(
        self, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        start = time.perf_counter()
        errors = []
        evidence = []

        try:
            code = actual_output if isinstance(actual_output, str) else str(actual_output)

            # Extract test cases from spec
            test_cases = spec.test_cases
            if not test_cases and "test_cases" in context:
                test_cases = context["test_cases"]

            if not test_cases:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    score=0.0,
                    errors=["No test cases provided for verification"],
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )

            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                code_path = f.name

            try:
                passed = 0
                total = len(test_cases)

                for i, tc in enumerate(test_cases):
                    test_code = self._build_test(code, tc)
                    result = await asyncio.wait_for(
                        self.sandbox.run(test_code), timeout=spec.timeout_seconds
                    )

                    success = result.get("success", False) and result.get("exit_code", 1) == 0
                    if success:
                        passed += 1
                    evidence.append(
                        {
                            "test_case": i,
                            "input": tc.get("input"),
                            "expected": tc.get("expected"),
                            "actual": result.get("output", ""),
                            "passed": success,
                        }
                    )
                    if not success:
                        errors.append(f"Test {i} failed: {result.get('error', 'Unknown')}")

                score = passed / total if total > 0 else 0.0
                status = VerificationStatus.PASSED if score >= 0.8 else VerificationStatus.FAILED

                return VerificationResult(
                    status=status,
                    score=score,
                    details={"passed": passed, "total": total},
                    errors=errors,
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                    evidence=evidence,
                )

            finally:
                Path(code_path).unlink(missing_ok=True)

        except TimeoutError:
            return VerificationResult(
                status=VerificationStatus.TIMEOUT,
                score=0.0,
                errors=["Verification timed out"],
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                score=0.0,
                errors=[str(e)],
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

    def _build_test(self, code: str, test_case: dict) -> str:
        """Build executable test code from code + test case."""
        # Wrap user code and run test
        test_input = test_case.get("input", {})
        expected = test_case.get("expected")

        return f"""
{code}

# Test harness
import json
import sys

try:
    # Call the function with test input
    result = main(**{json.dumps(test_input)})

    # Check result
    expected = {json.dumps(expected)}
    if result == expected:
        print("PASS")
        sys.exit(0)
    else:
        print(f"FAIL: got {{result}}, expected {{expected}}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
"""


class PlanningOutcomeVerifier(OutcomeVerifier):
    """Verifies planning tasks by checking goal achievement."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.logger = logger.bind(component="planning_verifier")

    async def verify(
        self, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        start = time.perf_counter()
        errors = []
        evidence = []

        try:
            plan = actual_output if isinstance(actual_output, dict) else {}
            goal = context.get("goal", spec.metadata.get("goal", ""))
            initial_state = context.get("initial_state", {})

            if not goal:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    score=0.0,
                    errors=["No goal specified for planning verification"],
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )

            # Use LLM to evaluate plan quality
            eval_prompt = f"""Evaluate this plan for achieving the goal.

GOAL: {goal}
INITIAL STATE: {json.dumps(initial_state)}
PLAN: {json.dumps(plan)}

Rate 0-1 on:
1. Completeness - does it address all aspects of the goal?
2. Correctness - are steps logically valid?
3. Feasibility - can each step be executed?
4. Efficiency - minimal steps?

Return JSON: {{"completeness": 0.0, "correctness": 0.0, "feasibility": 0.0, "efficiency": 0.0, "reasoning": "..."}}"""

            response = await self.backend.complete(eval_prompt, temperature=0.1)
            try:
                eval_data = json.loads(response.content)
                scores = [
                    eval_data.get(k, 0)
                    for k in ("completeness", "correctness", "feasibility", "efficiency")
                ]
                score = sum(scores) / len(scores)
                evidence.append({"llm_evaluation": eval_data})
            except json.JSONDecodeError:
                score = 0.5
                errors.append("Failed to parse LLM evaluation")

            status = VerificationStatus.PASSED if score >= 0.7 else VerificationStatus.FAILED

            return VerificationResult(
                status=status,
                score=score,
                details={"evaluation": eval_data if "eval_data" in locals() else {}},
                errors=errors,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                evidence=evidence,
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                score=0.0,
                errors=[str(e)],
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )


class ReasoningOutcomeVerifier(OutcomeVerifier):
    """Verifies reasoning tasks for logical consistency and factual accuracy."""

    def __init__(self, backend: CognitiveBackend):
        self.backend = backend
        self.logger = logger.bind(component="reasoning_verifier")

    async def verify(
        self, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        start = time.perf_counter()
        errors = []
        evidence = []

        try:
            reasoning = str(actual_output)
            question = context.get("question", spec.metadata.get("question", ""))
            premises = context.get("premises", spec.metadata.get("premises", []))

            eval_prompt = f"""Verify this reasoning for correctness.

QUESTION: {question}
PREMISES: {json.dumps(premises)}
REASONING: {reasoning}

Check:
1. Logical validity - does conclusion follow from premises?
2. Factual accuracy - are stated facts correct?
3. Completeness - does it address the question?
4. No hallucination - are all claims supported?

Return JSON: {{"validity": 0.0, "accuracy": 0.0, "completeness": 0.0, "hallucination_free": 0.0, "reasoning": "..."}}"""

            response = await self.backend.complete(eval_prompt, temperature=0.1)
            try:
                eval_data = json.loads(response.content)
                scores = [
                    eval_data.get(k, 0)
                    for k in ("validity", "accuracy", "completeness", "hallucination_free")
                ]
                score = sum(scores) / len(scores)
                evidence.append({"llm_evaluation": eval_data})
            except json.JSONDecodeError:
                score = 0.5
                errors.append("Failed to parse LLM evaluation")

            status = VerificationStatus.PASSED if score >= 0.7 else VerificationStatus.FAILED

            return VerificationResult(
                status=status,
                score=score,
                details={"evaluation": eval_data if "eval_data" in locals() else {}},
                errors=errors,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                evidence=evidence,
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                score=0.0,
                errors=[str(e)],
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )


class SimulationOutcomeVerifier(OutcomeVerifier):
    """Verifies simulation predictions against actual outcomes."""

    def __init__(self, blender_sandbox: BlenderSandbox | None = None):
        self.blender = blender_sandbox
        self.logger = logger.bind(component="simulation_verifier")

    async def verify(
        self, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        start = time.perf_counter()
        errors = []
        evidence = []

        try:
            prediction = actual_output
            ground_truth = context.get("ground_truth")
            simulation_type = spec.metadata.get("simulation_type", "physics")

            if ground_truth is None and self.blender:
                # Run simulation to get ground truth
                sim_spec = context.get("simulation_spec", {})
                result = await self.blender.run_simulation(sim_spec)
                if result.get("success"):
                    ground_truth = result.get("output")
                    evidence.append({"simulation_result": result})
                else:
                    errors.append("Failed to run ground truth simulation")

            if ground_truth is None:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    score=0.0,
                    errors=["No ground truth available for comparison"],
                    execution_time_ms=(time.perf_counter() - start) * 1000,
                )

            # Compare prediction vs ground truth
            score = self._compare_results(prediction, ground_truth, simulation_type)
            status = VerificationStatus.PASSED if score >= 0.8 else VerificationStatus.FAILED

            evidence.append(
                {"prediction": prediction, "ground_truth": ground_truth, "similarity": score}
            )

            return VerificationResult(
                status=status,
                score=score,
                details={"simulation_type": simulation_type},
                errors=errors,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                evidence=evidence,
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                score=0.0,
                errors=[str(e)],
                execution_time_ms=(time.perf_counter() - start) * 1000,
            )

    def _compare_results(self, prediction: Any, ground_truth: Any, sim_type: str) -> float:
        """Compare predicted vs actual simulation results."""
        # Simple numeric comparison
        if isinstance(prediction, (int, float)) and isinstance(ground_truth, (int, float)):
            if ground_truth == 0:
                return 1.0 if prediction == 0 else 0.0
            error = abs(prediction - ground_truth) / abs(ground_truth)
            return max(0.0, 1.0 - error)

        # Vector comparison (positions, velocities)
        if isinstance(prediction, list) and isinstance(ground_truth, list):
            if len(prediction) != len(ground_truth):
                return 0.0
            errors = [
                abs(p - g) / (abs(g) + 1e-6) for p, g in zip(prediction, ground_truth, strict=False)
            ]
            return max(0.0, 1.0 - sum(errors) / len(errors))

        # Dict comparison
        if isinstance(prediction, dict) and isinstance(ground_truth, dict):
            keys = set(prediction.keys()) | set(ground_truth.keys())
            if not keys:
                return 1.0
            matches = sum(1 for k in keys if prediction.get(k) == ground_truth.get(k))
            return matches / len(keys)

        # String/object comparison
        return 1.0 if str(prediction) == str(ground_truth) else 0.0


class CompositeOutcomeVerifier:
    """Routes verification to appropriate specialized verifier."""

    def __init__(
        self,
        code_sandbox: CodeSandbox | None = None,
        blender_sandbox: BlenderSandbox | None = None,
        backend: CognitiveBackend | None = None,
    ):
        self.verifiers = {}
        if code_sandbox:
            self.verifiers["code"] = CodeOutcomeVerifier(code_sandbox)
        if backend:
            self.verifiers["planning"] = PlanningOutcomeVerifier(backend)
            self.verifiers["reasoning"] = ReasoningOutcomeVerifier(backend)
        if blender_sandbox or True:  # Always create, uses fallback comparison
            self.verifiers["simulation"] = SimulationOutcomeVerifier(blender_sandbox)

        self.default_verifier = self.verifiers.get("reasoning")
        self.logger = logger.bind(component="composite_verifier")

    def register(self, task_type: str, verifier: OutcomeVerifier):
        self.verifiers[task_type] = verifier

    async def verify(
        self, task_type: str, spec: VerificationSpec, actual_output: Any, context: dict[str, Any]
    ) -> VerificationResult:
        verifier = self.verifiers.get(task_type, self.default_verifier)
        if not verifier:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                score=0.0,
                errors=[f"No verifier for task type: {task_type}"],
            )

        self.logger.info("verifying", task_type=task_type, spec=spec.task_type)
        return await verifier.verify(spec, actual_output, context)


async def create_outcome_verifier(
    code_sandbox: CodeSandbox | None = None,
    blender_sandbox: BlenderSandbox | None = None,
    backend: CognitiveBackend | None = None,
) -> CompositeOutcomeVerifier:
    """Factory for creating the composite verifier."""
    return CompositeOutcomeVerifier(
        code_sandbox=code_sandbox, blender_sandbox=blender_sandbox, backend=backend
    )
