"""Root conftest for pytest configuration."""

import os
import sys

# Ensure src/ is on the path for all tests
src_dir = os.path.join(os.path.dirname(__file__), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
