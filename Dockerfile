# Get the Python version provided as a build argument
ARG PYTHON_VERSION=3.10

# Use the slim variant of the Python image
FROM python:${PYTHON_VERSION}-slim-bookworm

# Set the working directory
WORKDIR /app

# Add the parent directory to PYTHONPATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m myuser

# Switch to the non-root user
USER myuser

# Install Poetry as the non-root user
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/home/myuser/.local/bin:$PATH"

# Copy pyproject.toml and poetry.lock
COPY pyproject.toml poetry.lock ./

# Install dependencies using Poetry
RUN poetry install --no-root --only main

# Copy the rest of the application code
COPY . .

# Expose the port that the application listens on
EXPOSE 8000

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Command to run the application
CMD ["poetry", "run", "gunicorn", "app.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
