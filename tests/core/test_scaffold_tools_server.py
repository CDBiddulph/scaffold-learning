"""Tests for scaffold_tools_server module."""

import os
import sys
import importlib.util
import pytest
from unittest.mock import Mock, patch

from scaffold_learning.core.scaffold_tools_server import (
    ScaffoldToolsServer,
    start_server,
)


class TestScaffoldToolsServer:
    """Test scaffold tools server functionality."""

    @pytest.fixture
    def mock_scoring_function(self):
        """Create a mock scoring function for testing."""

        def mock_score(attempt: str, scoring_data: dict) -> float:
            if attempt == "correct" and scoring_data.get("correct_answer") == "correct":
                return 1.0
            elif (
                attempt == "partial" and scoring_data.get("correct_answer") == "correct"
            ):
                return 0.5
            else:
                return 0.0

        return mock_score

    def test_scaffold_tools_server_initialization(self, mock_scoring_function):
        """Test that ScaffoldToolsServer initializes correctly."""
        server = ScaffoldToolsServer(mock_scoring_function, port=8081)
        assert server.scoring_function == mock_scoring_function
        assert server.port == 8081
        assert server.app is not None

    def test_scaffold_tools_client_import(self):
        """Test that scaffold tools client can be imported."""
        # Get path to scaffold_tools.py
        scaffold_tools_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src",
            "scaffold_learning",
            "runtime",
            "scaffold_tools.py",
        )

        # Mock HOST_IP environment variable
        with patch.dict("os.environ", {"HOST_IP": "192.168.1.100"}):
            # Load module using importlib
            spec = importlib.util.spec_from_file_location(
                "scaffold_tools", scaffold_tools_path
            )
            scaffold_tools = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scaffold_tools)

            assert hasattr(scaffold_tools, "score")
            assert scaffold_tools.SERVER_HOST == "192.168.1.100"
