from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

import mcp_atlassian_attachments.config as config_module


@pytest.fixture(autouse=True)
def _no_user_config_file(monkeypatch):
    """Point the config file at a nonexistent path so tests ignore ~/.config.

    load_config() falls back to ~/.config/mcp-atlassian-attachments/config.json for
    any credential the environment does not supply. On a machine where that file
    exists, deleting an env var does not make the value missing, so the required-
    field tests never reach their error branch and instead make a live network
    call. Tests that exercise the file source patch this path themselves.
    """
    nonexistent = Path(tempfile.gettempdir()) / "mcp_atlassian_attachments_test_nonexistent"
    monkeypatch.setattr(config_module, "_CONFIG_PATH", nonexistent / "config.json")
