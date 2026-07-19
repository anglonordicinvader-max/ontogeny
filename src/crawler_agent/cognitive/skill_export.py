"""Portable skill export module.

Provides:
- Export learned skills as standalone Python modules
- Package skills with dependencies and metadata
- Import skills from external sources
- Skill versioning and compatibility checks
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog


@dataclass
class SkillManifest:
    """Manifest for a portable skill package."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = "Ontogeny Agent"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    python_version: str = "3.11"
    min_agent_version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    hash: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "python_version": self.python_version,
            "min_agent_version": self.min_agent_version,
            "created_at": self.created_at,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PortableSkill:
    """A skill packaged for portability."""

    manifest: SkillManifest
    code: str
    tests: str = ""
    examples: str = ""
    readme: str = ""

    def to_module(self) -> str:
        """Generate a complete Python module."""
        lines = [
            '"""',
            f"{self.manifest.name} v{self.manifest.version}",
            "",
            f"{self.manifest.description}",
            "",
            f"Author: {self.manifest.author}",
            f"Category: {self.manifest.category}",
            f"Tags: {', '.join(self.manifest.tags)}",
            '"""',
            "",
            f'__version__ = "{self.manifest.version}"',
            f'__author__ = "{self.manifest.author}"',
            "",
            f"# Dependencies: {', '.join(self.manifest.dependencies) if self.manifest.dependencies else 'none'}",
            "",
            self.code,
        ]
        if self.tests:
            lines.extend(
                [
                    "",
                    'if __name__ == "__main__":',
                    "    # Run tests",
                    "    import sys",
                    "    sys.exit(0 if __test__() else 1)",
                    "",
                    self.tests,
                ]
            )
        return "\n".join(lines)

    def to_package(self) -> dict[str, str]:
        """Generate a complete skill package."""
        files = {
            "manifest.json": json.dumps(self.manifest.to_dict(), indent=2),
            f"{self.manifest.name}.py": self.to_module(),
        }
        if self.tests:
            files["test_skill.py"] = self.tests
        if self.examples:
            files["examples.py"] = self.examples
        if self.readme:
            files["README.md"] = self.readme
        return files


class SkillExporter:
    """Export and import portable skills."""

    def __init__(self, output_dir: str = "data/exported_skills"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = structlog.get_logger(component="skill_export")

    def export_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        code: str,
        category: str = "general",
        tags: list[str] = None,
        dependencies: list[str] = None,
        tests: str = "",
        examples: str = "",
        version: str = "1.0.0",
    ) -> PortableSkill:
        """Export a skill as a portable package."""
        manifest = SkillManifest(
            name=name,
            version=version,
            description=description,
            category=category,
            tags=tags or [],
            dependencies=dependencies or [],
        )

        # Calculate hash of code
        manifest.hash = hashlib.sha256(code.encode()).hexdigest()[:16]

        portable = PortableSkill(
            manifest=manifest,
            code=code,
            tests=tests,
            examples=examples,
        )

        # Save to disk
        skill_dir = self.output_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        files = portable.to_package()
        for filename, content in files.items():
            (skill_dir / filename).write_text(content)

        self.logger.info("skill_exported", name=name, version=version, path=str(skill_dir))
        return portable

    def export_from_library(self, skill_library, skill_id: str) -> PortableSkill | None:
        """Export a skill from the skill library."""
        skill = skill_library.get_skill(skill_id)
        if not skill:
            self.logger.warning("skill_not_found", skill_id=skill_id)
            return None

        return self.export_skill(
            skill_id=skill.id,
            name=skill.name,
            description=skill.description,
            code=skill.code,
            category=skill.category,
            tags=skill.tags,
            version=f"1.0.{skill.version}",
        )

    def import_skill(self, skill_path: str) -> PortableSkill | None:
        """Import a skill from a directory."""
        skill_dir = Path(skill_path)
        if not skill_dir.exists():
            self.logger.warning("skill_dir_not_found", path=skill_path)
            return None

        manifest_file = skill_dir / "manifest.json"
        if not manifest_file.exists():
            self.logger.warning("manifest_not_found", path=skill_path)
            return None

        try:
            manifest_data = json.loads(manifest_file.read_text())
            manifest = SkillManifest.from_dict(manifest_data)

            # Find main Python file
            code_file = skill_dir / f"{manifest.name}.py"
            if not code_file.exists():
                # Try any .py file
                py_files = list(skill_dir.glob("*.py"))
                if py_files:
                    code_file = py_files[0]
                else:
                    self.logger.warning("code_file_not_found", path=skill_path)
                    return None

            code = code_file.read_text()

            # Optional files
            tests = ""
            tests_file = skill_dir / "test_skill.py"
            if tests_file.exists():
                tests = tests_file.read_text()

            examples = ""
            examples_file = skill_dir / "examples.py"
            if examples_file.exists():
                examples = examples_file.read_text()

            readme = ""
            readme_file = skill_dir / "README.md"
            if readme_file.exists():
                readme = readme_file.read_text()

            portable = PortableSkill(
                manifest=manifest,
                code=code,
                tests=tests,
                examples=examples,
                readme=readme,
            )

            self.logger.info("skill_imported", name=manifest.name, version=manifest.version)
            return portable

        except Exception as e:
            self.logger.warning("skill_import_failed", error=str(e))
            return None

    def import_to_library(self, skill_library, skill_path: str) -> str | None:
        """Import a portable skill into the skill library."""
        portable = self.import_skill(skill_path)
        if not portable:
            return None

        from .skill_library import Skill

        skill = Skill(
            id=f"imported_{portable.manifest.name}_{int(time.time())}",
            name=portable.manifest.name,
            description=portable.manifest.description,
            code=portable.code,
            signature="",  # Will be extracted from code
            category=portable.manifest.category,
            tags=portable.manifest.tags,
            verified=False,
        )

        skill_id = skill_library.add_skill(skill)
        self.logger.info(
            "skill_imported_to_library", skill_id=skill_id, name=portable.manifest.name
        )
        return skill_id

    def list_exported(self) -> list[dict]:
        """List all exported skills."""
        skills = []
        for skill_dir in self.output_dir.iterdir():
            if skill_dir.is_dir():
                manifest_file = skill_dir / "manifest.json"
                if manifest_file.exists():
                    try:
                        manifest_data = json.loads(manifest_file.read_text())
                        skills.append(
                            {
                                "name": manifest_data.get("name", skill_dir.name),
                                "version": manifest_data.get("version", "unknown"),
                                "description": manifest_data.get("description", ""),
                                "path": str(skill_dir),
                            }
                        )
                    except Exception:
                        pass
        return skills

    def create_skill_template(
        self,
        name: str,
        description: str,
        category: str = "general",
    ) -> PortableSkill:
        """Create a skill template for new skills."""
        template_code = '''"""{name} skill."""


def execute(context: dict) -> dict:
    """Execute the skill.

    Args:
        context: Execution context with input data

    Returns:
        dict: Execution result
    """
    # TODO: Implement skill logic
    return {"success": True, "output": "Not implemented"}


def validate_input(context: dict) -> bool:
    """Validate input context."""
    return True


# Test function
def __test__() -> bool:
    """Test the skill."""
    result = execute({"test": True})
    return result.get("success", False)
'''

        template_tests = f'''"""Tests for {name} skill."""


def test_execute():
    result = execute({{"test": True}})
    assert result["success"], f"Execution failed: {{result}}"


def test_validate():
    assert validate_input({{"test": True}})


if __name__ == "__main__":
    test_execute()
    test_validate()
    print("All tests passed!")
'''

        manifest = SkillManifest(
            name=name,
            description=description,
            category=category,
        )

        return PortableSkill(
            manifest=manifest,
            code=template_code,
            tests=template_tests,
        )
