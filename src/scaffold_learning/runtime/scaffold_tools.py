"""Client module for scaffold tools API.

This module is injected into Docker containers to provide scaffolds
with access to external tools like scoring functions.
"""

import json
import requests
from typing import Dict, Any


SERVER_HOST = "host.docker.internal"
SERVER_PORT = 8080
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"


def score(attempt: str, scoring_data: Dict[str, Any]) -> float:
    """Score an attempt using the mesa-domain scoring function.
    
    Args:
        attempt: The attempt to score
        scoring_data: Scoring data for the mesa-domain
        
    Returns:
        Score value as a float
        
    Raises:
        requests.RequestException: If the request fails
        ValueError: If the server returns an error
    """
    response = requests.post(
        f"{BASE_URL}/score",
        json={
            "attempt": attempt,
            "scoring_data": scoring_data
        },
        timeout=30
    )
    response.raise_for_status()
    
    result = response.json()
    if "error" in result:
        raise ValueError(f"Scoring error: {result['error']}")
        
    return result["score"]