"""Frontend validation script.

Runs TypeScript compilation check and production build
to verify the frontend is healthy.
"""

import os
import subprocess
import sys

RENDERER_DIR = os.path.join(os.path.dirname(__file__), "desktop", "renderer")


def run_cmd(cmd, label):
    """Run a command and return (success, output)."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(
        cmd, shell=True, cwd=RENDERER_DIR, capture_output=True, text=True, timeout=120
    )
    if result.stdout:
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.stderr:
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
    return result.returncode == 0


def main():
    failures = []

    # 1. TypeScript compilation
    if not run_cmd("npx tsc --noEmit", "TypeScript Type Check"):
        failures.append("TypeScript type check failed")

    # 2. Production build
    if not run_cmd("npm run build", "Production Build"):
        failures.append("Production build failed")

    # 3. ESLint
    if not run_cmd("npx eslint src/ --max-warnings 50", "ESLint"):
        failures.append("ESLint check failed")

    print(f"\n{'=' * 60}")
    if failures:
        print(f"  FRONTEND VALIDATION FAILED ({len(failures)} issues)")
        for f in failures:
            print(f"    - {f}")
        sys.exit(1)
    else:
        print("  FRONTEND VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
