"""Run target-Core tests with network isolation and explicit pytest plugins."""

import os
import sys
from pathlib import Path

os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# HA must alias httpx2 before any test tool imports httpx.
import homeassistant  # noqa: F401
import pytest

raise SystemExit(
    pytest.main(
        [
            "-q",
            "tests_ha",
            "-p",
            "pytest_asyncio.plugin",
            "-p",
            "pytest_socket",
            "-p",
            "pytest_cov",
            "--asyncio-mode=auto",
            "--disable-socket",
            "--allow-unix-socket",
            "--cov=custom_components.sonos_mode_switch",
            "--cov-report=term-missing",
        ]
    )
)
