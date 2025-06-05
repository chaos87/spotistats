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
