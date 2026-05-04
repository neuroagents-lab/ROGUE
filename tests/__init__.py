from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Keep the real local packages registered before individual tests install
# lightweight stubs for selected heavy submodules.
import desktop_env  # noqa: F401
import mm_agents  # noqa: F401
