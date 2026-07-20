"""Root conftest for pytest configuration."""

import os
import sys

# Ensure this repository's source tree wins over any editable sibling checkout.
repo_dir = os.path.dirname(os.path.dirname(__file__))
src_dir = os.path.join(repo_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

backend_dir = os.path.join(repo_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
