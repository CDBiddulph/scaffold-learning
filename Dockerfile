FROM python:3.10-slim

# Create app directory
WORKDIR /app

# Copy source files first
COPY pyproject.toml /app/
COPY src/ /app/src/

# Install Python dependencies from pyproject.toml
RUN pip install -e .

# Copy llm_executor.py to root for import from scaffolds
COPY src/scaffold_learning/runtime/llm_executor.py /app/llm_executor.py

# Create workspace directory
WORKDIR /workspace

# Set Python path to include app directory
ENV PYTHONPATH=/app:/workspace