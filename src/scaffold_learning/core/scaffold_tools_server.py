"""HTTP server for scaffold tools API.

Provides a Flask server that scaffolds can use to access scoring functions
and other tools while running in Docker containers.
"""

import logging
import threading
import time
from typing import Callable, Dict, Any

import requests
from flask import Flask, request, jsonify


logger = logging.getLogger(__name__)

DEFAULT_SERVER_PORT = 8080
HEALTH_CHECK_DELAY_SECONDS = 0.1
HEALTH_CHECK_TIMEOUT_SECONDS = 1


class ScaffoldToolsServer:
    """HTTP server that provides scaffold tools API."""

    def __init__(
        self, scoring_function: Callable[[str, Dict[str, Any]], float], port: int
    ):
        """Initialize the server.

        Args:
            scoring_function: Function to handle scoring requests
            port: Port to listen on
        """
        self.scoring_function = scoring_function
        self.port = port
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.WARNING)  # Reduce Flask logging

        # Disable Flask request logging
        logging.getLogger("werkzeug").setLevel(logging.WARNING)

        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/score", methods=["POST"])
        def score():
            """Handle scoring requests."""
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request must contain JSON data"}), 400

            attempt = data.get("attempt")
            scoring_data = data.get("scoring_data")

            if attempt is None or scoring_data is None:
                return (
                    jsonify(
                        {
                            "error": "Request must contain 'attempt' and 'scoring_data' fields"
                        }
                    ),
                    400,
                )

            score_value = self.scoring_function(attempt, scoring_data)
            return jsonify({"score": score_value})

        @self.app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "ok"})

    def run(self):
        """Start the server (blocking)."""
        logger.info(f"Starting scaffold tools server on port {self.port}")
        self.app.run(host="0.0.0.0", port=self.port, debug=False, threaded=True)


def start_server(
    scoring_function: Callable[[str, Dict[str, Any]], float],
    port: int = DEFAULT_SERVER_PORT,
) -> ScaffoldToolsServer:
    """Start a scaffold tools server in a background daemon thread.

    The server runs in a daemon thread, meaning it will automatically terminate
    when the main process exits. No manual cleanup is required.

    Includes a health check to verify the server started successfully.

    Args:
        scoring_function: Function to handle scoring requests
        port: Port to listen on

    Returns:
        Server instance (already running in background)

    Raises:
        RuntimeError: If server fails to start or health check fails
    """
    server = ScaffoldToolsServer(scoring_function, port)

    def run_server():
        server.run()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # Wait briefly for server to start
    time.sleep(HEALTH_CHECK_DELAY_SECONDS)

    # Health check to ensure server is running
    try:
        response = requests.get(
            f"http://localhost:{port}/health", timeout=HEALTH_CHECK_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.RequestException:
        raise RuntimeError(f"Failed to start scaffold tools server on port {port}")

    return server
