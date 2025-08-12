"""Utilities for managing Docker containers and images."""

import subprocess
import logging


def build_docker_image(
    image_name: str = "scaffold-runner", dockerfile_path: str = "."
) -> None:
    """Force rebuild the Docker image.

    Args:
        image_name: Name of the Docker image to build
        dockerfile_path: Path to the directory containing the Dockerfile

    Raises:
        subprocess.CalledProcessError: If Docker build fails
    """
    # Clean up unused Docker resources before building to prevent disk quota issues
    subprocess.run(["docker", "system", "prune", "-f"], check=False)
    logging.info("Cleaned up unused Docker resources")

    subprocess.run(["docker", "build", "-t", image_name, dockerfile_path], check=True)
    logging.info(f"Docker image '{image_name}' built successfully!")
