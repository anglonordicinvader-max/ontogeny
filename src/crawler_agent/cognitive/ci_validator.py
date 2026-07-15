"""External validation - GitHub Actions CI integration for patch verification."""

import asyncio
import base64
import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp


@dataclass
class CIResult:
    """Result of a CI run."""
    run_id: str
    status: str  # queued, in_progress, completed
    conclusion: str | None  # success, failure, cancelled
    workflow: str
    branch: str
    commit_sha: str
    url: str
    started_at: str
    completed_at: str | None = None
    logs: str = ""


@dataclass
class PatchValidationJob:
    """A patch validation job for CI."""
    id: str
    patch_content: str
    target_file: str
    test_command: str
    created_at: float = field(default_factory=time.time)
    ci_result: CIResult | None = None


class GitHubActionsValidator:
    """Validates patches using GitHub Actions CI."""

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        token: str | None = None,
        workflow_file: str = ".github/workflows/validate-patch.yml",
    ):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.workflow_file = workflow_file
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        } if self.token else {}

    async def validate_patch(
        self,
        patch: str,
        target_file: str,
        test_command: str = "pytest -v",
        branch_prefix: str = "patch-validation",
    ) -> CIResult | None:
        """Create branch, apply patch, trigger CI, wait for result."""
        if not self.token:
            return None

        branch_name = f"{branch_prefix}-{int(time.time())}"

        # 1. Create branch from main
        sha = await self._get_main_sha()
        if not sha:
            return None

        await self._create_branch(branch_name, sha)

        # 2. Apply patch to file
        await self._apply_patch_to_branch(branch_name, patch, target_file)

        # 3. Update CI workflow if needed
        await self._ensure_workflow(test_command)

        # 4. Trigger workflow
        run_id = await self._trigger_workflow(branch_name)
        if not run_id:
            return None

        # 5. Wait for completion
        return await self._wait_for_completion(run_id)

    async def _get_main_sha(self) -> str | None:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/main"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["object"]["sha"]
        return None

    async def _create_branch(self, branch_name: str, sha: str) -> bool:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/git/refs",
                json={"ref": f"refs/heads/{branch_name}", "sha": sha},
            ) as resp:
                return resp.status == 201

    async def _apply_patch_to_branch(
        self,
        branch_name: str,
        patch: str,
        target_file: str,
    ) -> bool:
        # Get current file content
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{target_file}",
                params={"ref": branch_name},
            ) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                current_content = base64.b64decode(data["content"]).decode()
                file_sha = data["sha"]

        # Apply patch (simplified - real implementation would use proper patch library)
        # For now, just replace if patch looks like full file
        new_content = patch if "+++" not in patch else self._apply_unified_diff(current_content, patch)

        # Commit new content
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.put(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{target_file}",
                json={
                    "message": f"Apply patch for validation",
                    "content": base64.b64encode(new_content.encode()).decode(),
                    "sha": file_sha,
                    "branch": branch_name,
                },
            ) as resp:
                return resp.status in (200, 201)

    def _apply_unified_diff(self, original: str, patch: str) -> str:
        """Apply unified diff to original content."""
        # Simplified - would use `patch` library in production
        lines = original.splitlines(keepends=True)
        # This is a placeholder - real implementation needed
        return original

    async def _ensure_workflow(self, test_command: str) -> bool:
        """Ensure validation workflow exists."""
        workflow_content = f"""name: Patch Validation

on:
  workflow_dispatch:
    inputs:
      test_command:
        description: 'Test command to run'
        required: true
        default: '{test_command}'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio
      - name: Run tests
        run: ${{{{ github.event.inputs.test_command }}}}
"""
        # Check if workflow exists
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{self.workflow_file}"
            ) as resp:
                if resp.status == 404:
                    # Create workflow
                    async with session.put(
                        f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{self.workflow_file}",
                        json={
                            "message": "Add patch validation workflow",
                            "content": base64.b64encode(workflow_content.encode()).decode(),
                            "branch": "main",
                        },
                    ) as put_resp:
                        return put_resp.status in (200, 201)
                return resp.status == 200

    async def _trigger_workflow(self, branch_name: str) -> int | None:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{self.workflow_file}/dispatches",
                json={"ref": branch_name, "inputs": {"test_command": "pytest -v"}},
            ) as resp:
                if resp.status == 204:
                    # Get run ID
                    await asyncio.sleep(2)
                    return await self._get_latest_run_id(branch_name)
        return None

    async def _get_latest_run_id(self, branch_name: str) -> int | None:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs",
                params={"branch": branch_name, "per_page": 1},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["workflow_runs"]:
                        return data["workflow_runs"][0]["id"]
        return None

    async def _wait_for_completion(
        self,
        run_id: int,
        timeout: int = 600,
        poll_interval: int = 15,
    ) -> CIResult | None:
        start = time.time()
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while time.time() - start < timeout:
                async with session.get(
                    f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data["status"]
                        conclusion = data.get("conclusion")

                        if status == "completed":
                            # Get logs
                            logs = await self._get_run_logs(session, run_id)
                            return CIResult(
                                run_id=str(run_id),
                                status=status,
                                conclusion=conclusion,
                                workflow=data["workflow_id"],
                                branch=data["head_branch"],
                                commit_sha=data["head_sha"],
                                url=data["html_url"],
                                started_at=data["created_at"],
                                completed_at=data.get("updated_at"),
                                logs=logs,
                            )
                await asyncio.sleep(poll_interval)
        return None

    async def _get_run_logs(self, session: aiohttp.ClientSession, run_id: int) -> str:
        async with session.get(
            f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/logs"
        ) as resp:
            if resp.status == 200:
                return await resp.text()
        return ""


class LocalCIValidator:
    """Validates patches using local Docker-based CI."""

    def __init__(self, sandbox: Any):
        self.sandbox = sandbox

    async def validate_patch(
        self,
        patch: str,
        target_file: str,
        test_command: str = "pytest -v",
        additional_files: dict[str, str] | None = None,
    ) -> CIResult:
        """Validate patch locally in sandbox."""
        run_id = f"local-{int(time.time())}"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Write target file with patch applied
            target_path = tmpdir / target_file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(patch)

            # Write additional files
            if additional_files:
                for name, content in additional_files.items():
                    (tmpdir / name).write_text(content)

            # Run tests
            cmd = f"cd {tmpdir} && {test_command} 2>&1"
            try:
                result = await self.sandbox.execute_command(cmd)
                success = result.get("exit_code", 1) == 0
                output = result.get("output", "")
            except Exception as e:
                success = False
                output = str(e)

        return CIResult(
            run_id=run_id,
            status="completed",
            conclusion="success" if success else "failure",
            workflow="local-validation",
            branch="local",
            commit_sha="local",
            url="local",
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            logs=output,
        )


class CompositeValidator:
    """Combines multiple validators with fallback."""

    def __init__(
        self,
        validators: list[Any] = None,
    ):
        self.validators = validators or []

    def add_validator(self, validator: Any) -> None:
        self.validators.append(validator)

    async def validate(
        self,
        patch: str,
        target_file: str,
        test_command: str = "pytest -v",
    ) -> CIResult | None:
        """Try each validator until one succeeds."""
        for validator in self.validators:
            try:
                result = await validator.validate_patch(patch, target_file, test_command)
                if result:
                    return result
            except Exception:
                continue
        return None