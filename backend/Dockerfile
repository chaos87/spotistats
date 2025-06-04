# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Set PYTHONPATH
ENV PYTHONPATH="/app"

# Install poetry
RUN pip install poetry

# Configure poetry to not create virtualenvs, install into system python
RUN poetry config virtualenvs.create false

# Copy the dependency files
COPY pyproject.toml poetry.lock* /app/

# Install project dependencies
# --no-dev: Do not install development dependencies
# --no-root: Do not install the project itself, only dependencies
RUN poetry install --without dev --no-root

# Copy the rest of the application code
COPY ./src /app/src
COPY ./main.py /app/main.py

# Command to run the application
CMD ["python", "main.py"]
