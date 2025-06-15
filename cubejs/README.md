# Cube.js Project

This is a Cube.js project configured to connect to a PostgreSQL database.

## Setup

### 1. Environment Variables

Create a `.env` file in this directory (`cubejs/.env`) and populate it with the following environment variables:

```env
# Database Connection Details
CUBEJS_DB_TYPE=postgres
PG_HOST=<your_database_host>
PG_PORT=<your_database_port> # e.g., 5432
PG_USER=<your_database_user>
PG_PASSWORD=<your_database_password>
PG_DATABASE=<your_database_name>
PG_SSL=<true_or_false> # e.g., true if your database requires SSL

# Cube.js Specific Settings
CUBEJS_API_SECRET=<your_super_strong_api_secret> # Used to secure your Cube.js instance
CUBEJS_DEV_MODE=true # Enables development mode, providing more detailed error messages
CUBEJS_WEB_SOCKETS=true # Enables WebSocket transport for real-time features
```

### 2. Install Dependencies

Navigate to the `cubejs` directory and install the project dependencies. If you are using npm:

```bash
cd /app/cubejs
npm install
```

If you are using Yarn:

```bash
cd /app/cubejs
yarn install
```

### 3. Start the Development Server

Once the dependencies are installed and your `.env` file is configured, you can start the Cube.js development server.

Using npm:

```bash
npm run dev
```

Using Yarn:

```bash
yarn dev
```

The Cube.js server will typically start on `http://localhost:4000`. You can then access the Cube.js Playground to build and test your data schemas.

## Deployment to Google Cloud Run

This guide provides instructions to deploy the Cube.js application to Google Cloud Run.

### Prerequisites

1.  **Google Cloud SDK:** Ensure you have `gcloud` CLI installed and authenticated.
2.  **GCP Project:** Have a Google Cloud Project created and configured (set the project with `gcloud config set project YOUR_PROJECT_ID`).
3.  **APIs Enabled:** Enable the Cloud Run API and Artifact Registry API in your GCP project.
4.  **Docker:** Docker installed locally to build and push the image.
5.  **Database:** A running PostgreSQL database accessible from Google Cloud Run (e.g., Neon, Cloud SQL).

### Deployment Steps

1.  **Build the Docker Image:**
    Navigate to the `cubejs` directory and build the Docker image. Replace `YOUR_PROJECT_ID` with your GCP project ID and `cubejs-app` with your desired image name.

    ```bash
    docker build -t gcr.io/YOUR_PROJECT_ID/cubejs-app:latest .
    ```

2.  **Configure Docker Authentication for Artifact Registry:**
    Configure Docker to use `gcloud` as a credential helper for Artifact Registry.

    ```bash
    gcloud auth configure-docker
    ```
    If you are in a region other than `us-central1`, you might need to specify your region, e.g., `gcloud auth configure-docker europe-west1-docker.pkg.dev`. Check the Artifact Registry documentation for regional endpoints.

3.  **Push the Docker Image to Artifact Registry:**
    Push the image to Google Artifact Registry. If the repository does not exist, this command will offer to create it (or you can create it beforehand via GCP Console).

    ```bash
    docker push gcr.io/YOUR_PROJECT_ID/cubejs-app:latest
    ```

4.  **Deploy to Cloud Run:**
    Deploy the image to Cloud Run using the `gcloud` command. Replace placeholders accordingly.

    ```bash
    gcloud run deploy cubejs-service \
      --image gcr.io/YOUR_PROJECT_ID/cubejs-app:latest \
      --platform managed \
      --region YOUR_CLOUD_RUN_REGION \
      --allow-unauthenticated \
      --port 4000 \
      --set-env-vars="CUBEJS_DB_TYPE=postgres" \
      --set-env-vars="PG_HOST=YOUR_DB_HOST" \
      --set-env-vars="PG_DATABASE=YOUR_DB_NAME" \
      --set-env-vars="PG_USER=YOUR_DB_USER" \
      --set-env-vars="PG_PASSWORD=YOUR_DB_PASSWORD" \
      --set-env-vars="PG_PORT=YOUR_DB_PORT" \
      --set-env-vars="PG_SSL=true" \
      --set-env-vars="CUBEJS_API_SECRET=YOUR_CUBEJS_API_SECRET" \
      --set-env-vars="CUBEJS_DEV_MODE=false" \
      --set-env-vars="CUBEJS_WEB_SOCKETS=true"
    ```

    **Notes on Environment Variables:**
    *   `YOUR_CLOUD_RUN_REGION`: e.g., `us-central1`, `europe-west1`.
    *   `PG_HOST`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_PORT`: Replace with your actual PostgreSQL connection details.
    *   `PG_SSL`: Set to `true` if your database requires SSL (common for cloud-hosted DBs like Neon). Set to `false` otherwise. The `cube.js` file has logic for this.
    *   `CUBEJS_API_SECRET`: Set a long, random string for security. This is crucial for production.
    *   `CUBEJS_DEV_MODE`: Set to `false` for production.
    *   `CUBEJS_WEB_SOCKETS`: Set to `true` if you plan to use WebSockets.

    You can also set these environment variables via the GCP Console when creating or updating the Cloud Run service.

5.  **Verify Deployment:**
    Once deployed, Cloud Run will provide a service URL. You can access your Cube.js API at this URL (e.g., `https://YOUR_SERVICE_URL.run.app/cubejs-api/v1`).

### Local Development

To run the Cube.js server locally for development (pointing to your cloud database or a local one):

1.  Ensure you have a `.env` file in the `cubejs` directory with the following variables:
    ```env
    CUBEJS_DB_TYPE=postgres
    PG_HOST=your_db_host
    PG_DATABASE=your_db_name
    PG_USER=your_db_user
    PG_PASSWORD=your_db_password
    PG_PORT=5432 # or your db port
    PG_SSL=true # or false

    CUBEJS_API_SECRET=yourlocalapisecret
    CUBEJS_DEV_MODE=true
    CUBEJS_WEB_SOCKETS=true
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the server:
    ```bash
    npm run dev
    ```
    The Cube.js playground will typically be available at `http://localhost:4000`.
