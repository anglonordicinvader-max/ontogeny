"""Filesystem Access Control — governs where the agent can read/write.

Safeguards:
- Agent CANNOT modify test files (tests/)
- Agent CANNOT modify config files (.env, pyproject.toml)
- Agent CAN modify source code (src/), scripts, documentation, data
- All modifications go through PR workflow for human review
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog


@dataclass
class AccessRule:
    """Defines read/write access for a path pattern."""
    pattern: str
    can_read: bool = True
    can_write: bool = False
    requires_pr: bool = True  # If True, changes go through PR
    reason: str = ""


@dataclass
class ModificationRequest:
    """A request to modify a file."""
    file_path: str
    content: str
    description: str
    reasoning: str
    branch_name: str = ""
    approved: bool = False
    error: str = ""


class FileSystemAccessControl:
    """Governs filesystem access for the agent.

    Rules:
    1. Test files (tests/) — READ ONLY, no writes
    2. Config files (.env, pyproject.toml) — READ ONLY, no writes
    3. Source code (src/) — Read/Write via PR
    4. Scripts (scripts/) — Read/Write via PR
    5. Data (data/) — Read/Write directly (training data, models)
    6. Documentation (README.md) — Read/Write via PR
    """

    # Paths that are completely off-limits for writes
    PROTECTED_PATHS = [
        "tests/",
        ".env",
        "pyproject.toml",
        ".git/",
        "node_modules/",
        "__pycache__/",
        "*.pyc",
    ]

    # Paths that require PR review
    PR_REQUIRED_PATHS = [
        "src/",
        "scripts/",
        "README.md",
        "Dockerfile*",
        "Modelfile*",
    ]

    # Paths that can be written directly (no PR needed)
    DIRECT_WRITE_PATHS = [
        "data/",
        "data/maldoror/",
        "data/modification_memory/",
        "data/blender/",
    ]

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(".")
        self.logger = structlog.get_logger()
        self.access_log: list[dict[str, Any]] = []

    def can_read(self, file_path: str) -> bool:
        """Check if agent can read a file."""
        rel_path = self._relative_path(file_path)

        # Check protected paths
        for protected in self.PROTECTED_PATHS:
            if self._matches_pattern(rel_path, protected):
                return True  # Agent CAN read protected paths

        return True  # Agent can read everything

    def can_write(self, file_path: str) -> tuple[bool, str]:
        """Check if agent can write a file. Returns (allowed, reason)."""
        rel_path = self._relative_path(file_path)

        # Check protected paths (cannot write)
        for protected in self.PROTECTED_PATHS:
            if self._matches_pattern(rel_path, protected):
                return False, f"Protected path: {protected}"

        # Check direct write paths (can write without PR)
        for direct in self.DIRECT_WRITE_PATHS:
            if self._matches_pattern(rel_path, direct):
                return True, "Direct write allowed"

        # Check PR-required paths
        for pr_path in self.PR_REQUIRED_PATHS:
            if self._matches_pattern(rel_path, pr_path):
                return True, "Requires PR review"

        # Default: require PR for safety
        return True, "Requires PR review (default)"

    def requires_pr(self, file_path: str) -> bool:
        """Check if a file modification requires a PR."""
        rel_path = self._relative_path(file_path)

        # Direct write paths don't need PR
        for direct in self.DIRECT_WRITE_PATHS:
            if self._matches_pattern(rel_path, direct):
                return False

        # Protected paths can't be written at all
        for protected in self.PROTECTED_PATHS:
            if self._matches_pattern(rel_path, protected):
                return False  # Can't write, so PR doesn't apply

        # Everything else requires PR
        return True

    def create_branch_name(self, description: str) -> str:
        """Create a git branch name from description."""
        # Sanitize description for branch name
        sanitized = description.lower()
        sanitized = "".join(c if c.isalnum() or c in "-_" else "-" for c in sanitized)
        sanitized = sanitized[:50]  # Limit length
        return f"agent/{sanitized}"

    def log_access(self, file_path: str, operation: str, allowed: bool, reason: str):
        """Log access attempt."""
        entry = {
            "file": file_path,
            "operation": operation,
            "allowed": allowed,
            "reason": reason,
        }
        self.access_log.append(entry)

        if allowed:
            self.logger.debug("fs_access_granted", **entry)
        else:
            self.logger.warning("fs_access_denied", **entry)

    def _relative_path(self, file_path: str) -> str:
        """Convert to relative path from project root."""
        path = Path(file_path)
        try:
            return str(path.relative_to(self.base_path))
        except ValueError:
            return str(path)

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches a pattern (supports * wildcards)."""
        if "*" in pattern:
            # Simple wildcard matching
            prefix = pattern.split("*")[0]
            suffix = pattern.split("*")[-1]
            return path.startswith(prefix) and path.endswith(suffix)
        return path == pattern or path.startswith(pattern + "/")


class GitWorkflow:
    """Manages git operations for the PR workflow."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path(".")
        self.logger = structlog.get_logger()

    def create_branch(self, branch_name: str) -> bool:
        """Create a new git branch."""
        try:
            # Fetch latest
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(self.base_path),
                capture_output=True,
                timeout=30,
            )

            # Create and switch to new branch
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("branch_created", branch=branch_name)
                return True
            else:
                self.logger.error("branch_creation_failed", error=result.stderr)
                return False

        except Exception as e:
            self.logger.error("git_error", error=str(e))
            return False

    def commit_changes(self, message: str, files: list[str] | None = None) -> bool:
        """Commit changes to the current branch."""
        try:
            # Stage files
            if files:
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        cwd=str(self.base_path),
                        capture_output=True,
                        timeout=30,
                    )
            else:
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(self.base_path),
                    capture_output=True,
                    timeout=30,
                )

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("changes_committed", message=message)
                return True
            else:
                self.logger.error("commit_failed", error=result.stderr)
                return False

        except Exception as e:
            self.logger.error("git_error", error=str(e))
            return False

    def push_branch(self, branch_name: str) -> bool:
        """Push branch to origin."""
        try:
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.logger.info("branch_pushed", branch=branch_name)
                return True
            else:
                self.logger.error("push_failed", error=result.stderr)
                return False

        except Exception as e:
            self.logger.error("git_error", error=str(e))
            return False

    def create_pr(self, branch_name: str, title: str, body: str) -> str | None:
        """Create a GitHub PR. Returns PR URL."""
        try:
            result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--head", branch_name,
                    "--title", title,
                    "--body", body,
                ],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Extract PR URL from output
                pr_url = result.stdout.strip()
                self.logger.info("pr_created", url=pr_url)
                return pr_url
            else:
                self.logger.error("pr_creation_failed", error=result.stderr)
                return None

        except FileNotFoundError:
            self.logger.error("gh_cli_not_found", hint="Install GitHub CLI: https://cli.github.com")
            return None
        except Exception as e:
            self.logger.error("pr_error", error=str(e))
            return None

    def get_diff(self) -> str:
        """Get current git diff."""
        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout
        except Exception:
            return ""

    def switch_to_main(self):
        """Switch back to main branch."""
        try:
            subprocess.run(
                ["git", "checkout", "master"],
                cwd=str(self.base_path),
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass
