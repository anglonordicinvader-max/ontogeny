"""Build reproducible desktop-side Python artifacts for the Ontogeny demo."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
RESOURCE_DIR = BACKEND_DIR / "package_resources"

REQUIRED_ASSETS = (
    ROOT_DIR / "data" / "mujoco" / "models" / "unitree_g1" / "g1.xml",
    ROOT_DIR / "data" / "blender" / "models" / "tocabi" / "combined" / "meshes",
)


def run(*args: str) -> None:
    subprocess.run(args, cwd=BACKEND_DIR, check=True)


def prepare_blender_vendor() -> None:
    import websockets

    destination = RESOURCE_DIR / "blender_vendor" / "websockets"
    if destination.parent.exists():
        shutil.rmtree(destination.parent)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(websockets.__file__).resolve().parent, destination)


def validate_assets() -> None:
    missing = [str(path) for path in REQUIRED_ASSETS if not path.exists()]
    if missing:
        joined = "\n  - ".join(missing)
        raise SystemExit(
            "Required local embodiment assets are missing:\n"
            f"  - {joined}\n"
            "See PACKAGING.md for asset provisioning."
        )


def main() -> None:
    validate_assets()
    prepare_blender_vendor()
    run(sys.executable, "-m", "PyInstaller", "backend.spec", "--clean", "--noconfirm")
    run(sys.executable, "-m", "PyInstaller", "mujoco.spec", "--clean", "--noconfirm")

    expected = (
        BACKEND_DIR / "dist" / "ontogeny-backend.exe",
        BACKEND_DIR / "dist" / "ontogeny-mujoco.exe",
    )
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise SystemExit(f"Packaging completed without expected artifacts: {missing}")

    for artifact in expected:
        print(f"built {artifact.name} ({artifact.stat().st_size / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
