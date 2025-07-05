FROM python:3.10-slim

# Create app directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY pyproject.toml /app/

# Install Python dependencies from pyproject.toml
RUN pip install -e .

# Copy source files
RUN mkdir -p /app/scaffold_learning/core
COPY src/scaffold_learning/__init__.py /app/scaffold_learning/
COPY src/scaffold_learning/core/__init__.py /app/scaffold_learning/core/
COPY src/scaffold_learning/core/llm_interfaces.py /app/scaffold_learning/core/
COPY src/scaffold_learning/runtime/llm_executor.py /app/llm_executor.py

# Create workspace directory
WORKDIR /workspace

# Set Python path to include app directory
ENV PYTHONPATH=/app:/workspace