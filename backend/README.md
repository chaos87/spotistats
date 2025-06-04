# Backend Ingestion Service

This directory contains the Python application responsible for ingesting data from the Spotify API and storing it in the PostgreSQL database.

## Dockerization

The application is containerized using Docker.

### Build the Docker Image

To build the Docker image locally, navigate to the `backend` directory and run:

```bash
docker build -t spotify-ingestion-backend .
```

### Run the Docker Container

To run the Docker container locally, you need to provide the necessary environment variables. These include:

*   `SPOTIFY_CLIENT_ID`: Your Spotify application client ID.
*   `SPOTIFY_CLIENT_SECRET`: Your Spotify application client secret.
*   `SPOTIFY_REFRESH_TOKEN`: Your Spotify refresh token.
*   `DATABASE_URL`: The connection string for your PostgreSQL database (e.g., `postgresql://user:password@host:port/database`).

You can run the container using the following command, replacing the placeholder values with your actual credentials:

```bash
docker run \
  -e SPOTIFY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID" \
  -e SPOTIFY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET" \
  -e SPOTIFY_REFRESH_TOKEN="YOUR_SPOTIFY_REFRESH_TOKEN" \
  -e DATABASE_URL="YOUR_DATABASE_URL" \
  spotify-ingestion-backend
```

Alternatively, you can use a `.env` file (make sure it's in the `backend` directory when running the `docker run` command if you choose to mount it, though the Dockerfile itself doesn't copy it) and pass it to Docker:

```bash
# Create a .env file in the backend directory with your environment variables:
# SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
# SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET
# SPOTIFY_REFRESH_TOKEN=YOUR_SPOTIFY_REFRESH_TOKEN
# DATABASE_URL=YOUR_DATABASE_URL

docker run --env-file .env spotify-ingestion-backend
```
Note: The current Dockerfile does not copy the `.env` file into the image. The `--env-file` flag for `docker run` reads the file from your local machine where you execute the command.
The application itself (main.py) is configured to load environment variables from a `.env` file if present when run locally (not in Docker), or directly from the environment when deployed (e.g., in Cloud Run or when passed via `docker run -e`).
```
