FROM python:3.10-slim

# Create app directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY pyproject.toml /app/

# Install Python dependencies from pyproject.toml
RUN pip install -e .

# Copy source files
COPY llm_interfaces.py /app/
COPY templates/docker_executor_template.py /app/llm_executor.py

# Create workspace directory
WORKDIR /workspace

# Set Python path to include app directory
ENV PYTHONPATH=/app:/workspace