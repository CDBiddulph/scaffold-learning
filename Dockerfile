FROM python:3.10-slim

# Install Python dependencies
RUN pip install anthropic openai python-dotenv

# Copy source files
COPY llm_interfaces.py /app/
COPY templates/docker_executor_template.py /app/llm_executor.py

# Create workspace directory
WORKDIR /workspace

# Set Python path to include app directory
ENV PYTHONPATH=/app:/workspace