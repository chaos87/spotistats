# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy the dependency files
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies
# --no-dev: Do not install development dependencies
# --no-root: Do not install the project itself, only dependencies
RUN poetry install --no-dev --no-root

# Copy the rest of the application code
COPY ./src /app/src
COPY ./main.py /app/main.py

# Command to run the application
CMD ["python", "main.py"]
