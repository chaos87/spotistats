## Project Blueprint: Spotify Listening Dashboard

This blueprint outlines the development process in distinct phases, each broken down into smaller, test-driven modules and individual steps (LLM prompts).

### Phase 1: Core Infrastructure & Setup

This phase focuses on setting up the foundational elements of the project, including repository structure, cloud environment, and the database schema.

**Module 1.1: Project Initialization & Repository Setup**
* Initialize Git repository.
* Set up basic project directory structure for frontend, backend (ingestion), and Cube.js.
* Define initial `pyproject.toml` for Python dependencies.

**Module 1.2: Database & Schema Foundation (Neon)**
* Provision a PostgreSQL database instance on Neon.tech.
* Create `recently_played_tracks_raw` table schema.
* Create initial normalized table schemas: `artists`, `albums`, `tracks`, `listens`.

### Phase 2: Data Ingestion Pipeline (Backend - Python on Cloud Run)

This phase builds the Python script responsible for fetching data from Spotify, processing it, and loading it into the PostgreSQL database. Emphasis on idempotency and error handling.

**Module 2.1: Spotify API Client & Authentication**
* Implement Spotify OAuth client with refresh token handling.
* Securely load credentials from environment variables.

**Module 2.2: Raw Data Ingestion**
* Fetch recently played tracks from Spotify.
* Store raw JSON into `recently_played_tracks_raw`.

**Module 2.3: Initial Normalized Data Processing & Loading**
* Set up ORM (SQLAlchemy) for normalized tables.
* Implement basic normalization logic for tracks, albums, artists.
* Implement UPSERT logic for these entities.
* Implement de-duplication for `listens` table based on `played_at`.

**Module 2.4: Podcast Data Integration**
* Update database schema for podcast entities.
* Enhance normalization and loading logic to handle podcasts.

**Module 2.5: Advanced Ingestion Features & Robustness**
* Implement `tracks.last_played_at` update logic.
* Implement comprehensive error handling and structured logging.

**Module 2.6: Deployment & Scheduling**
* Dockerize the Python application.
* Deploy to Google Cloud Run.
* Set up Cloud Scheduler for hourly execution.

### Phase 3: API Layer (Cube.js)

This phase focuses on creating the Cube.js semantic layer to expose the data for the frontend, handling complex aggregations and relationships.

**Module 3.1: Cube.js Project Setup & DB Connection**
* Initialize Cube.js project.
* Configure connection to the Neon PostgreSQL database.

**Module 3.2: Core Data Modeling**
* Model basic cubes for `artists`, `albums`, `tracks`, `listens`.
* Define core measures (`count`, `total_duration`) and dimensions.

**Module 3.3: Podcast & Advanced Relationship Modeling**
* Model cubes for `podcast_series` and `podcast_episodes`.
* Refine `listens` cube to handle polymorphic relationship (`item_type`, `track_id`, `episode_id`).

**Module 3.4: Feature-Specific Data Modeling**
* Model `artists.genres` for "Taste Evolution" (e.g., using unwind/unnest).
* Define custom measures for "You Used to Love This" (past/prior 12 months listen times).

**Module 3.5: Cube.js Deployment**
* Dockerize Cube.js application.
* Deploy to Google Cloud Run.

### Phase 4: Frontend Dashboard (React)

This phase builds the interactive React application using Ant Design and Chart.js, consuming data from Cube.js.

**Module 4.1: React Project Setup & Basic Structure**
* Initialize React project (Vite/Create React App).
* Integrate Ant Design and Chart.js.
* Set up Cube.js client.

**Module 4.2: Feature Implementation: Taste Evolution**
* Develop component for "Taste Evolution" line chart.
* Query Cube.js for relevant data.

**Module 4.3: Feature Implementation: You Used to Love This**
* Develop component for "You Used to Love This" list.
* Implement frontend comparison logic.

**Module 4.4: Dynamic Query Builder: Core UI**
* Build the form with dropdowns for measures, dimensions, time dimension, and filters.
* Implement "RUN" button.

**Module 4.5: Dynamic Query Builder: Data Display**
* Implement table display for query results.
* Implement basic chart type selection logic (line/bar).

**Module 4.6: Dynamic Query Builder: Advanced Charting**
* Refine chart type selection for stacked bars, multiple lines, and top N limiting.

**Module 4.7: Dashboard Polish & Deployment**
* Implement loading states and error handling.
* Set up CI/CD for Vercel deployment.

---

### LLM Prompts for Step-by-Step Implementation

Each prompt below corresponds to a small, isolated, and testable step. It provides context, specifies libraries, outlines expected output, and emphasizes testing and integration.

---

### **Phase 1: Core Infrastructure & Setup**

#### **Module 1.1: Project Initialization & Repository Setup**

1.  **Prompt: Initialize Monorepo Structure and Python Project**
    ```text
    You are tasked with setting up the foundational project structure for a Spotify Listening Dashboard. This project will eventually be a monorepo containing a Python backend (for data ingestion), a Cube.js API layer, and a React frontend.

    **Task:**
    1.  Create a new root directory named `spotify-dashboard`.
    2.  Inside `spotify-dashboard`, create the following subdirectories: `backend`, `cubejs`, `frontend`.
    3.  Inside the `backend` directory, initialize a new Python project using `poetry`. Create a `pyproject.toml` file.
    4.  Add the following initial dependencies to `backend/pyproject.toml`:
        * `requests`: For making HTTP requests to the Spotify API.
        * `psycopg2-binary`: For PostgreSQL database connectivity.
        * `SQLAlchemy`: For ORM capabilities.
        * `python-dotenv`: For local environment variable management.
        * `pytest`: For unit testing.
        * `pyjwt`: For JWT handling (potentially for Spotify auth).
    5.  Create a basic `backend/main.py` file with just a `print("Backend service started.")` statement.
    6.  Create a `backend/tests/test_main.py` file with a simple passing test that verifies the backend directory exists or similar.
    7.  Provide instructions on how to set up `poetry` and install these dependencies.

    **Expected Output:**
    * The complete directory structure.
    * The `backend/pyproject.toml` file content.
    * The `backend/main.py` file content.
    * The `backend/tests/test_main.py` file content.
    * Poetry commands for installation.
    ```

#### **Module 1.2: Database & Schema Foundation (Neon)**

2.  **Prompt: Define Initial Database Schema for Raw and Core Normalized Data**
    ```text
    You are responsible for defining the initial PostgreSQL database schema for the Spotify Listening Dashboard. This schema will be hosted on Neon.tech.

    **Context:**
    * We need a table to store raw JSON responses from the Spotify API.
    * We need core normalized tables for artists, albums, tracks, and listens.
    * URLs for Spotify web player pages should be included in entity tables.
    * The `tracks` table needs a `last_played_at` column to track the most recent listen time for that specific track.

    **Task:**
    1.  Provide the SQL DDL (Data Definition Language) statements to create the following tables:
        * `recently_played_tracks_raw`:
            * `id` (BIGSERIAL PRIMARY KEY)
            * `data` (JSONB NOT NULL)
            * `ingestion_timestamp` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())
        * `artists`:
            * `artist_id` (TEXT PRIMARY KEY)
            * `name` (TEXT NOT NULL)
            * `spotify_url` (TEXT)
            * `image_url` (TEXT)
            * `genres` (TEXT[]) - to store an array of genre strings
        * `albums`:
            * `album_id` (TEXT PRIMARY KEY)
            * `name` (TEXT NOT NULL)
            * `release_date` (DATE)
            * `album_type` (TEXT)
            * `spotify_url` (TEXT)
            * `image_url` (TEXT)
            * `primary_artist_id` (TEXT REFERENCES artists(artist_id))
        * `tracks`:
            * `track_id` (TEXT PRIMARY KEY)
            * `name` (TEXT NOT NULL)
            * `duration_ms` (INTEGER)
            * `explicit` (BOOLEAN)
            * `popularity` (INTEGER)
            * `preview_url` (TEXT)
            * `spotify_url` (TEXT)
            * `album_id` (TEXT REFERENCES albums(album_id))
            * `available_markets` (TEXT[])
            * `last_played_at` (TIMESTAMP WITH TIME ZONE) - This will be updated by the ingestion script.
        * `listens`:
            * `listen_id` (BIGSERIAL PRIMARY KEY)
            * `played_at` (TIMESTAMP WITH TIME ZONE NOT NULL UNIQUE) - Crucial for de-duplication and time-series analysis.
            * `item_type` (TEXT NOT NULL CHECK (item_type IN ('track', 'episode')))
            * `track_id` (TEXT REFERENCES tracks(track_id))
            * `episode_id` (TEXT) - This will be a FK to `podcast_episodes` later. Keep as TEXT for now.
            * `artist_id` (TEXT REFERENCES artists(artist_id)) - Primary artist of the played item.
            * `album_id` (TEXT REFERENCES albums(album_id)) - Album of the played item.
            * Add a `CHECK` constraint: `CHECK ( (item_type = 'track' AND track_id IS NOT NULL AND episode_id IS NULL) OR (item_type = 'episode' AND episode_id IS NOT NULL AND track_id IS NULL) )`

    **Expected Output:**
    * A single block of SQL DDL statements for all the tables, ensuring correct foreign key dependencies (e.g., `artists` before `albums` before `tracks`).
    ```

---

### **Phase 2: Data Ingestion Pipeline (Backend - Python on Cloud Run)**

#### **Module 2.1: Spotify API Client & Authentication**

3.  **Prompt: Implement Spotify OAuth Client with Refresh Token Handling**
    ```text
    You need to implement a Python client for Spotify's OAuth 2.0 Authorization Code Flow with Refresh Tokens. This client will handle acquiring access tokens and refreshing them.

    **Context:**
    * This will be part of the `backend` service.
    * We'll use `requests` for HTTP calls.
    * `CLIENT_ID`, `CLIENT_SECRET`, and `REFRESH_TOKEN` will come from environment variables.
    * The primary goal is to get a valid access token for API calls.

    **Task:**
    1.  Create a new file `backend/src/spotify_client.py`.
    2.  Define a class `SpotifyOAuthClient` that:
        * Initializes with `client_id`, `client_secret`, and `refresh_token`.
        * Has a method `get_access_token_from_refresh(self)` that:
            * Makes a POST request to Spotify's token endpoint (`https://accounts.spotify.com/api/token`).
            * Uses the `refresh_token` to get a new `access_token`.
            * Handles potential errors (e.g., invalid refresh token).
            * Returns the `access_token` string.
        * Has a method `get_initial_refresh_token_manual_flow(self, auth_code, redirect_uri)` that:
            * Makes a POST request to get the initial `access_token` and `refresh_token` using an authorization code.
            * This method is for a *one-time manual execution* to acquire the initial refresh token, not for the automated script.
            * Returns both the `access_token` and `refresh_token`.
    3.  Implement basic error handling (e.g., raise exceptions for non-200 responses) and logging (using Python's `logging` module).
    4.  Create `backend/tests/test_spotify_client.py`.
    5.  Write unit tests for `SpotifyOAuthClient`:
        * Test `get_access_token_from_refresh` with mocked successful and failed responses (e.g., using `unittest.mock` or `requests_mock`).
        * Test `get_initial_refresh_token_manual_flow` with mocked responses.

    **Expected Output:**
    * `backend/src/spotify_client.py` content.
    * `backend/tests/test_spotify_client.py` content.
    ```

4.  **Prompt: Secure Loading of Environment Variables & Integration**
    ```text
    You need to implement secure loading of Spotify API credentials from environment variables and integrate this with the `SpotifyOAuthClient`.

    **Context:**
    * We have `backend/src/spotify_client.py` with `SpotifyOAuthClient`.
    * Credentials (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`) will be available as environment variables (locally via `.env` file, in Cloud Run directly).
    * The `main.py` script will be the entry point for the ingestion process.

    **Task:**
    1.  In `backend/src/config.py`, create a module to load environment variables:
        * Use `python-dotenv` to load variables from a `.env` file for local development.
        * Define functions to get `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`. Raise an error if any required variable is missing.
    2.  Update `backend/main.py`:
        * Import `SpotifyOAuthClient` and the config functions.
        * Load the credentials using the config functions.
        * Instantiate `SpotifyOAuthClient` with the loaded credentials.
        * Call `get_access_token_from_refresh()` to verify functionality (print the token for now).
    3.  Create a placeholder `backend/.env` file with dummy values for the required environment variables.
    4.  Add a simple test in `backend/tests/test_config.py` to ensure environment variables are loaded correctly (e.g., using `monkeypatch` to set test env vars).
    5.  Update `.gitignore` to ignore `backend/.env`.

    **Expected Output:**
    * `backend/src/config.py` content.
    * Updated `backend/main.py` content.
    * `backend/.env` file content.
    * `backend/tests/test_config.py` content.
    * Updated `.gitignore` content.
    ```

#### **Module 2.2: Raw Data Ingestion**

5.  **Prompt: Implement Spotify Data Fetcher**
    ```text
    You need to implement a function to fetch the user's recently played tracks from the Spotify API.

    **Context:**
    * We have `backend/src/spotify_client.py` which provides access tokens.
    * The endpoint is `/me/player/recently-played`.
    * We need to handle the `limit` parameter (max 50).
    * This function should return the raw JSON response.

    **Task:**
    1.  In `backend/src/spotify_data.py`, create a function `get_recently_played_tracks(access_token: str, limit: int = 50) -> dict`.
        * This function should make a GET request to `https://api.spotify.com/v1/me/player/recently-played`.
        * Include the `Authorization` header with the bearer token.
        * Include the `limit` query parameter.
        * Raise an exception for non-200 responses.
        * Return the parsed JSON response as a dictionary.
    2.  Update `backend/main.py` to integrate this:
        * Import `get_recently_played_tracks`.
        * After getting the access token, call `get_recently_played_tracks` and print the raw JSON response.
    3.  Create `backend/tests/test_spotify_data.py`.
    4.  Write unit tests for `get_recently_played_tracks` using `requests_mock` to simulate successful and failed API responses, verifying headers and parameters.

    **Expected Output:**
    * `backend/src/spotify_data.py` content.
    * Updated `backend/main.py` content.
    * `backend/tests/test_spotify_data.py` content.
    ```

6.  **Prompt: Setup SQLAlchemy ORM and Insert Raw Data**
    ```text
    You need to set up SQLAlchemy ORM for database interaction and implement a function to insert raw Spotify JSON data into the `recently_played_tracks_raw` table.

    **Context:**
    * We have the database schema defined (from Prompt 2).
    * We're using `SQLAlchemy` and `psycopg2-binary`.
    * We need to define the SQLAlchemy model for `recently_played_tracks_raw`.
    * The `DATABASE_URL` for Neon will be an environment variable.

    **Task:**
    1.  In `backend/src/database.py`:
        * Define a function `get_db_engine()` that reads `DATABASE_URL` from environment variables (using `config.py`) and returns a SQLAlchemy `Engine` instance.
        * Define `Base = declarative_base()`.
        * Define the SQLAlchemy ORM model for `recently_played_tracks_raw` table. The `data` column should be `JSONB`.
        * Implement a function `insert_raw_data(engine, raw_json_data: dict) -> None` that:
            * Creates a session.
            * Instantiates the `recently_played_tracks_raw` model with the provided JSON.
            * Adds and commits the record.
    2.  Update `backend/main.py`:
        * Import `get_db_engine` and `insert_raw_data`.
        * After fetching raw data from Spotify, pass it to `insert_raw_data`.
        * Add basic logging to confirm successful insertion.
    3.  Create `backend/tests/test_database.py`.
    4.  Write unit tests for `get_db_engine` (e.g., mock env var) and `insert_raw_data` (e.g., using `sqlite` in-memory DB for quick testing or mocking session/engine).

    **Expected Output:**
    * `backend/src/database.py` content.
    * Updated `backend/main.py` content.
    * `backend/tests/test_database.py` content.
    * Update `backend/.env` with a dummy `DATABASE_URL`.
    ```

#### **Module 2.3: Initial Normalized Data Processing & Loading**

7.  **Prompt: Define SQLAlchemy Models for Core Normalized Tables**
    ```text
    You need to define SQLAlchemy ORM models for the `artists`, `albums`, `tracks`, and `listens` tables based on their DDL.

    **Context:**
    * We are using `backend/src/database.py` for `Base = declarative_base()`.
    * The DDL for these tables was provided in Prompt 2.
    * `listens` table initially has `episode_id` as TEXT, it will be a FK later.

    **Task:**
    1.  In `backend/src/database.py` (or a new `backend/src/models.py` if preferred, then import Base and link models there):
        * Define SQLAlchemy ORM models for `Artist`, `Album`, `Track`, and `Listen`.
        * Ensure correct column types, primary keys, and foreign key relationships are defined using `ForeignKey` and `relationship` for `primary_artist_id` in `Album`, `album_id` in `Track`, `artist_id` and `album_id` in `Listen`.
        * For `Listen`, define `track_id` and `episode_id` as nullable columns.
        * Implement the `CHECK` constraint for the `listens` table within the SQLAlchemy model definition if possible (e.g., using `CheckConstraint` from `sqlalchemy.schema`).
    2.  Add a simple test in `backend/tests/test_database.py` (or `test_models.py`) that verifies the models can be created and mapped (e.g., by creating a small in-memory database and calling `Base.metadata.create_all`).

    **Expected Output:**
    * Updated `backend/src/database.py` (or new `backend/src/models.py` and import statements).
    * Updated `backend/tests/test_database.py` (or `test_models.py`) content.
    ```

8.  **Prompt: Implement Spotify Data Normalizer (Music)**
    ```text
    You need to implement a Python function to normalize raw Spotify JSON data specifically for music tracks into the structured format suitable for our `Artist`, `Album`, `Track`, and `Listen` SQLAlchemy models.

    **Context:**
    * We have `backend/src/database.py` (or `models.py`) with `Artist`, `Album`, `Track`, `Listen` ORM models.
    * The `get_recently_played_tracks` function returns raw Spotify data.
    * Focus only on `track` items for now (ignore `episode` items if present).
    * Assume a listen always has a primary artist and album.
    * Extract `spotify_url` for `track`, `album`, `artist`.
    * Extract `genres` array for `artists`.
    * The `last_played_at` for tracks will be handled in a later step.

    **Task:**
    1.  Create `backend/src/normalizer.py`.
    2.  Define a class `SpotifyMusicNormalizer` with a method `normalize_track_item(self, item: dict) -> Tuple[Artist, Album, Track, Listen]`.
        * This method takes a single item (dictionary) from the `items` list in the Spotify API response.
        * It should extract relevant data for `Artist`, `Album`, `Track`, and `Listen` objects.
        * Handle nested structures gracefully (e.g., `item['track']['artists'][0]`, `item['track']['album']`).
        * Return instantiated (but not yet persisted) ORM objects: `Artist`, `Album`, `Track`, `Listen`.
        * Ensure `played_at` for `Listen` is a `datetime` object.
        * Set `item_type` for `Listen` to 'track'.
    3.  Create `backend/tests/test_normalizer.py`.
    4.  Write unit tests for `SpotifyMusicNormalizer.normalize_track_item`:
        * Mock a sample Spotify "recently played" track item JSON.
        * Verify that the method correctly extracts data and returns populated ORM objects with correct types.

    **Expected Output:**
    * `backend/src/normalizer.py` content.
    * `backend/tests/test_normalizer.py` content.
    ```

9.  **Prompt: Implement Database UPSERT and Ingestion Logic (Music Only)**
    ```text
    You need to implement the core database insertion logic for normalized Spotify music data, ensuring idempotency and de-duplication.

    **Context:**
    * We have `SpotifyMusicNormalizer` to get ORM objects.
    * We have `get_db_engine()` and `insert_raw_data`.
    * The goal is to insert `Artist`, `Album`, `Track`, and `Listen` records.
    * We need to find `max(played_at)` and filter new listens.
    * UPSERT (ON CONFLICT DO NOTHING) is required for `artists`, `albums`, `tracks`.
    * `listens` table has a `UNIQUE` constraint on `played_at`.

    **Task:**
    1.  In `backend/src/database.py`, add the following functions:
        * `get_max_played_at(engine) -> Optional[datetime]`: Queries `listens` table for `max(played_at)`.
        * `upsert_artist(session, artist_obj: Artist) -> None`: Inserts or updates an `Artist` record. Use `ON CONFLICT` for `artist_id`.
        * `upsert_album(session, album_obj: Album) -> None`: Inserts or updates an `Album` record. Use `ON CONFLICT` for `album_id`.
        * `upsert_track(session, track_obj: Track) -> None`: Inserts or updates a `Track` record. Use `ON CONFLICT` for `track_id`. (Note: `last_played_at` update will be handled in a later step, for now just basic UPSERT).
        * `insert_listen(session, listen_obj: Listen) -> None`: Inserts a `Listen` record. Handle `IntegrityError` if `played_at` is duplicated (e.g., from `UNIQUE` constraint).
    2.  Update `backend/main.py`:
        * Import relevant functions from `database` and `normalizer`.
        * Refactor the main logic:
            * Get DB engine.
            * Get `max_played_at`.
            * Fetch raw data from Spotify.
            * Iterate through fetched items:
                * If `item['track']['type'] == 'track'` (for music):
                    * Check if `item['played_at']` (converted to datetime) is greater than `max_played_at`. If not, `continue`.
                    * Use `SpotifyMusicNormalizer` to get ORM objects.
                    * Start a DB session.
                    * Call `upsert_artist`, `upsert_album`, `upsert_track`.
                    * Call `insert_listen`.
                    * Commit the session.
                * (Ignore podcast types for now).
            * Add comprehensive logging for each step (e.g., "Fetched X items", "Inserted Y new listens").
    3.  Create `backend/tests/test_ingestion_logic.py`.
    4.  Write integration tests that:
        * Use a temporary/test PostgreSQL database.
        * Mock Spotify API responses to return controlled sets of "recently played" data, including some new and some old/duplicate records.
        * Verify that `get_max_played_at` works.
        * Verify that only new records are inserted into `listens`.
        * Verify that `artists`, `albums`, `tracks` are correctly UPSERTed.
        * Verify foreign key relationships hold.

    **Expected Output:**
    * Updated `backend/src/database.py` content.
    * Updated `backend/main.py` content.
    * `backend/tests/test_ingestion_logic.py` content.
    ```

#### **Module 2.4: Podcast Data Integration**

10. **Prompt: Define SQLAlchemy Models for Podcast Entities and Update Listen FKs**
    ```text
    You need to define SQLAlchemy ORM models for the `podcast_series` and `podcast_episodes` tables, and then update the `listens` table model to correctly link to these new entities.

    **Context:**
    * We have `backend/src/database.py` (or `models.py`) with existing ORM models.
    * The DDL for `podcast_series` and `podcast_episodes` was provided in Prompt 2.
    * The `listens` table needs its `episode_id` column to become a foreign key to `podcast_episodes` and its `CHECK` constraint updated.

    **Task:**
    1.  In `backend/src/database.py` (or `models.py`):
        * Define SQLAlchemy ORM models for `PodcastSeries` and `PodcastEpisode`.
        * Ensure correct column types, primary keys, and foreign key relationships are defined (e.g., `series_id` in `PodcastEpisode`).
        * **Modify the `Listen` model:**
            * Add a `ForeignKey` constraint for `episode_id` referencing `podcast_episodes.episode_id`.
            * Update the `CHECK` constraint to explicitly include the `item_type` condition for `episode_id`:
                `CHECK ( (item_type = 'track' AND track_id IS NOT NULL AND episode_id IS NULL AND artist_id IS NOT NULL AND album_id IS NOT NULL) OR (item_type = 'episode' AND episode_id IS NOT NULL AND track_id IS NULL AND artist_id IS NULL AND album_id IS NULL) )`
                (Note: Ensure `artist_id` and `album_id` are NULL for podcast listens, as per the spec).
    2.  Add a simple test in `backend/tests/test_database.py` (or `test_models.py`) that verifies the new podcast models can be created and mapped, and the `Listen` model's updated constraint is recognized (e.g., by attempting to create invalid `Listen` objects).

    **Expected Output:**
    * Updated `backend/src/database.py` (or `models.py`) content.
    * Updated `backend/tests/test_database.py` (or `test_models.py`) content.
    ```

11. **Prompt: Enhance Normalizer and Ingestion for Podcasts**
    ```text
    You need to enhance the Spotify data normalizer and the ingestion logic to correctly process and store podcast episodes.

    **Context:**
    * We have new `PodcastSeries` and `PodcastEpisode` ORM models.
    * The `SpotifyMusicNormalizer` currently only handles tracks.
    * The ingestion logic in `main.py` needs to differentiate between `track` and `episode` items.

    **Task:**
    1.  In `backend/src/normalizer.py`:
        * Add a new method `normalize_episode_item(self, item: dict) -> Tuple[PodcastSeries, PodcastEpisode, Listen]`.
        * This method should take a Spotify "episode" item (where `item['track']['type'] == 'episode'`) and extract data for `PodcastSeries`, `PodcastEpisode`, and a `Listen` object.
        * Ensure `item_type` for `Listen` is 'episode' and `track_id`, `artist_id`, `album_id` are `None`.
        * Return the instantiated ORM objects.
        * Modify `SpotifyMusicNormalizer` (or rename to `SpotifyItemNormalizer` if appropriate) to internally call `normalize_track_item` or `normalize_episode_item` based on `item['track']['type']`. It should return a more generic tuple or dict. Let's simplify and have `normalize_item(self, item: dict) -> Tuple[Any, Any, Listen]`.
    2.  In `backend/src/database.py`, add new UPSERT functions:
        * `upsert_podcast_series(session, series_obj: PodcastSeries) -> None`: UPSERT for `podcast_series`.
        * `upsert_podcast_episode(session, episode_obj: PodcastEpisode) -> None`: UPSERT for `podcast_episodes`.
    3.  Update `backend/main.py`:
        * Modify the iteration logic to check `item['track']['type']`.
        * If `type == 'track'`: call existing music normalization/UPSERT logic.
        * If `type == 'episode'`:
            * Call the new podcast normalization logic.
            * Call `upsert_podcast_series` and `upsert_podcast_episode`.
            * Insert the `Listen` record with `episode_id` populated.
        * Ensure a single database session is used for each batch of new items.
    4.  Create `backend/tests/test_podcast_ingestion.py`.
    5.  Write unit and integration tests:
        * Mock sample Spotify "recently played" episode item JSON and test `normalize_episode_item`.
        * Test the `main.py` flow with mixed track/episode mocked responses, verifying correct insertion into all respective tables and `listens` with correct `item_type` and foreign keys.

    **Expected Output:**
    * Updated `backend/src/normalizer.py` content (or renamed with modified method).
    * Updated `backend/src/database.py` content.
    * Updated `backend/main.py` content.
    * `backend/tests/test_podcast_ingestion.py` content.
    ```

#### **Module 2.5: Advanced Ingestion Features & Robustness**

12. **Prompt: Implement `tracks.last_played_at` Update Logic**
    ```text
    You need to implement the logic to update the `last_played_at` column in the `tracks` table whenever a new listen for that track occurs.

    **Context:**
    * We have the `tracks` table with `last_played_at`.
    * The `upsert_track` function currently just does a basic UPSERT.
    * The ingestion script processes new `listens` records.

    **Task:**
    1.  In `backend/src/database.py`:
        * Modify the `upsert_track(session, track_obj: Track)` function.
        * When an existing `Track` record is encountered (due to `ON CONFLICT` on `track_id`), ensure its `last_played_at` field is updated to `track_obj.last_played_at` (the `played_at` of the current listen being processed), but *only if* the new `played_at` is more recent than the existing `last_played_at`.
        * When a new `Track` record is inserted, its `last_played_at` should be set to `track_obj.last_played_at`.
        * Alternatively, you can create a separate `update_track_last_played_at(session, track_id: str, new_played_at: datetime)` function. Let's go with updating `upsert_track` for simplicity.
    2.  In `backend/src/normalizer.py` (or the relevant normalization method):
        * Ensure that when a `Track` object is instantiated during normalization, its `last_played_at` attribute is set to the `played_at` timestamp of the current `item` being processed. This value will then be used by `upsert_track`.
    3.  Update `backend/tests/test_ingestion_logic.py`:
        * Add a test case where the same track is "played" multiple times in mocked responses with different `played_at` timestamps.
        * Verify that `tracks.last_played_at` correctly reflects the most recent `played_at` after ingestion.

    **Expected Output:**
    * Updated `backend/src/database.py` content (specifically `upsert_track`).
    * Updated `backend/src/normalizer.py` content.
    * Updated `backend/tests/test_ingestion_logic.py` content.
    ```

13. **Prompt: Implement Comprehensive Error Handling and Structured Logging**
    ```text
    You need to implement robust error handling and structured logging throughout the Python ingestion script to improve observability and debugging.

    **Context:**
    * The `backend/main.py` script orchestrates the entire ingestion process.
    * We need to handle API errors, database errors, and general processing errors.
    * Logging should be structured and suitable for Cloud Logging.
    * Implement retries for transient errors.

    **Task:**
    1.  In `backend/src/utils.py`, create helper functions for retry logic (e.g., using `tenacity` or a custom decorator with exponential backoff) for API calls and DB operations.
    2.  Configure Python's `logging` module in `backend/main.py` (or a dedicated `backend/src/logger.py`) to output structured JSON logs (e.g., using `python-json-logger` or by manually formatting dicts).
        * Log successful runs (e.g., "Ingestion successful, X new listens inserted").
        * Log warnings (e.g., "Skipping item due to malformed data").
        * Log errors with full tracebacks (e.g., API errors, DB errors, unexpected exceptions).
    3.  Apply error handling (try-except blocks) in `backend/main.py` around:
        * Environment variable loading.
        * Spotify API calls (using retry helper).
        * Database connection and operations (using retry helper for transient, specific handling for integrity errors).
        * Data normalization steps.
    4.  Update `backend/src/spotify_client.py` and `backend/src/spotify_data.py` to raise specific exceptions (e.g., `SpotifyAPIError`, `SpotifyAuthError`) that can be caught by `main.py`.
    5.  Update `backend/src/database.py` functions to raise specific `DatabaseError` exceptions for unrecoverable DB issues.
    6.  Add tests (e.g., in `backend/tests/test_error_handling.py`) that verify error handling and logging behavior by mocking failures (API, DB) and checking log output.

    **Expected Output:**
    * `backend/src/utils.py` content (retry decorator/function).
    * Updated `backend/main.py` content (logging config, error handling).
    * Updated `backend/src/spotify_client.py` and `backend/src/spotify_data.py` (custom exceptions).
    * Updated `backend/src/database.py` (custom exceptions).
    * `backend/tests/test_error_handling.py` content.
    ```

#### **Module 2.6: Deployment & Scheduling**

14. **Prompt: Dockerize Python Ingestion Application**
    ```text
    You need to dockerize the Python ingestion application for deployment on Google Cloud Run.

    **Context:**
    * The Python application resides in the `backend` directory.
    * `main.py` is the entry point.
    * Dependencies are managed by `poetry`.
    * Cloud Run requires a Docker image.

    **Task:**
    1.  Create a `backend/Dockerfile`.
    2.  The Dockerfile should:
        * Use a suitable Python base image (e.g., `python:3.10-slim-buster`).
        * Set the working directory.
        * Copy `pyproject.toml` and `poetry.lock`.
        * Install `poetry` and then project dependencies.
        * Copy the `src` directory and `main.py`.
        * Define the `CMD` to run `main.py`.
        * Ensure the image is optimized for size.
    3.  Provide instructions on how to build the Docker image locally.
    4.  Add a `README.md` to the `backend` directory with basic build and run instructions.

    **Expected Output:**
    * `backend/Dockerfile` content.
    * `backend/README.md` content.
    * Local Docker build command.
    ```

15. **Prompt: Google Cloud Run Deployment & Cloud Scheduler Setup (Instructions)**
    ```text
    You need to provide detailed, step-by-step instructions for deploying the Dockerized Python ingestion application to Google Cloud Run and scheduling its hourly execution using Cloud Scheduler.

    **Context:**
    * The Docker image from the previous step is ready.
    * We need to configure environment variables in Cloud Run.
    * We need to set up a service account for Cloud Scheduler.

    **Task:**
    1.  **Google Cloud Setup:**
        * Instructions to create a new GCP project (if not already done).
        * Instructions to enable necessary APIs (Cloud Run Admin API, Cloud Scheduler API, Artifact Registry API).
    2.  **Docker Image Push:**
        * Commands to tag the Docker image.
        * Commands to push the Docker image to Google Artifact Registry.
    3.  **Cloud Run Service Deployment:**
        * `gcloud` commands or Console steps to deploy the Cloud Run service.
        * Specify how to set the `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, and `DATABASE_URL` as environment variables.
        * Set appropriate CPU/Memory limits and concurrency (e.g., 1).
        * Set the service to "Allow unauthenticated invocations" (as Cloud Scheduler will invoke it via HTTP, or use a specific service account if higher security is needed, for this project let's stick to simple setup).
        * Note the service URL.
    4.  **Cloud Scheduler Job Setup:**
        * `gcloud` commands or Console steps to create a new Cloud Scheduler job.
        * Define the frequency as hourly (e.g., `0 * * * *`).
        * Set the target to "HTTP".
        * Specify the Cloud Run service URL.
        * Specify the HTTP method (POST or GET, typically POST for scheduler).
        * Instructions for creating a service account for Cloud Scheduler with `Cloud Run Invoker` role.
        * Instructions on how to test the Cloud Scheduler job manually.

    **Expected Output:**
    * A markdown-formatted set of step-by-step instructions for a developer to follow in the Google Cloud Console or using `gcloud` CLI.
    ```

---

### **Phase 3: API Layer (Cube.js)**

#### **Module 3.1: Cube.js Project Setup & DB Connection**

16. **Prompt: Initialize Cube.js Project and Connect to Neon DB**
    ```text
    You need to initialize a new Cube.js project and configure it to connect to the Neon PostgreSQL database.

    **Context:**
    * The Cube.js project will reside in the `cubejs` directory.
    * It will connect to the same Neon PostgreSQL database used by the ingestion backend.
    * Database credentials (`PG_HOST`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`, `PG_PORT`, `PG_SSL`) will be environment variables.

    **Task:**
    1.  Initialize a new Cube.js project inside the `cubejs` directory using the Cube.js CLI. Choose PostgreSQL as the database.
    2.  Modify the generated `cubejs/.env` file to include placeholder environment variables for the PostgreSQL connection.
    3.  Modify `cubejs/schema/index.js` (or `cubejs/schema/example.js`) to ensure it's set up to query the database.
    4.  Add a `cubejs/README.md` with instructions on how to start the Cube.js dev server locally.
    5.  Update the root `.gitignore` to ignore `cubejs/.env` and `node_modules` within the `cubejs` directory.

    **Expected Output:**
    * Instructions for Cube.js CLI initialization.
    * `cubejs/.env` file content.
    * Relevant parts of `cubejs/schema/index.js` (or `example.js`) showing DB config.
    * `cubejs/README.md` content.
    * Updated root `.gitignore` content.
    ```

#### **Module 3.2: Core Data Modeling**

17. **Prompt: Model Core Cubes (Artists, Albums, Tracks, Listens)**
    ```text
    You need to define the initial Cube.js data models (cubes) for the core entities: `artists`, `albums`, `tracks`, and `listens`.

    **Context:**
    * We have our PostgreSQL schema for these tables.
    * Cube.js models will define measures, dimensions, and relationships.
    * `listens` is the central fact table.

    **Task:**
    1.  Create separate Cube.js schema files (e.g., `Artist.js`, `Album.js`, `Track.js`, `Listen.js`) within `cubejs/schema`.
    2.  For each cube:
        * Define the `sql_table` property.
        * Map relevant columns to `dimensions`. Include `spotify_url` for all entity cubes.
        * For `Listen` cube:
            * Define `measures.count` and `measures.total_duration` (using `sum(tracks.duration_ms)`).
            * Define `timeDimension` for `played_at`.
        * Define `joins` between cubes (e.g., `Listen` to `Track`, `Track` to `Album`, `Album` to `Artist`).
    3.  Provide the content of these Cube.js schema files.

    **Expected Output:**
    * Content for `cubejs/schema/Artist.js`.
    * Content for `cubejs/schema/Album.js`.
    * Content for `cubejs/schema/Track.js`.
    * Content for `cubejs/schema/Listen.js`.
    ```

#### **Module 3.3: Podcast & Advanced Relationship Modeling**

18. **Prompt: Model Podcast Cubes and Refine Listen Cube for Polymorphism**
    ```text
    You need to define Cube.js models for podcast series and episodes, and update the `listens` cube to correctly handle its polymorphic relationship with either tracks or podcast episodes.

    **Context:**
    * We have `podcast_series` and `podcast_episodes` tables in PostgreSQL.
    * The `listens` table links to either `tracks` or `podcast_episodes` via `track_id`/`episode_id` and `item_type`.
    * The `listens.total_duration` measure needs to correctly sum duration from *either* tracks or episodes.

    **Task:**
    1.  Create Cube.js schema files for `PodcastSeries.js` and `PodcastEpisode.js` in `cubejs/schema`.
        * Define their `sql_table` and relevant `dimensions`.
    2.  Modify `cubejs/schema/Listen.js`:
        * Add `joins` to `PodcastEpisode` and `PodcastSeries`.
        * Update the `listens.total_duration` measure to use a `CASE` statement (or similar SQL) that selects `tracks.duration_ms` when `listens.item_type = 'track'` and `podcast_episodes.duration_ms` when `listens.item_type = 'episode'`.
        * Ensure dimensions related to `tracks` (e.g., `tracks.name`) and `podcast_episodes` (e.g., `podcast_episodes.name`) are correctly joined and available.
    3.  Provide the content of these Cube.js schema files.

    **Expected Output:**
    * Content for `cubejs/schema/PodcastSeries.js`.
    * Content for `cubejs/schema/PodcastEpisode.js`.
    * Updated content for `cubejs/schema/Listen.js`.
    ```

#### **Module 3.4: Feature-Specific Data Modeling**

19. **Prompt: Model `artists.genres` for Taste Evolution**
    ```text
    You need to model the `artists.genres` array for "Taste Evolution" analysis within Cube.js. This will allow grouping listen data by individual genres.

    **Context:**
    * The `artists` table has a `genres` TEXT[] column.
    * For "Taste Evolution," we need to associate listen time with each individual genre an artist has.

    **Task:**
    1.  Modify `cubejs/schema/Artist.js` to define a dimension for `genres` that effectively "unwinds" the array. This typically involves using a `sql` property with a PostgreSQL `unnest()` function.
    2.  Provide the updated content for `cubejs/schema/Artist.js`.
    ```

20. **Prompt: Define "You Used to Love This" Measures in Cube.js**
    ```text
    You need to define custom measures in Cube.js to support the "You Used to Love This" feature, specifically calculating listen time for artists in two distinct periods.

    **Context:**
    * The feature compares listen time in the "last 12 months" versus the "prior 12 months" (13-24 months ago).
    * These measures should be defined within the `Artist.js` cube for convenience, or within `Listen.js` and aggregated by artist. Let's define them in `Listen.js` and group by artist when querying.

    **Task:**
    1.  Modify `cubejs/schema/Listen.js` to define new measures:
        * `listens.total_duration_past_12_months`: Sum of `total_duration` where `played_at` is in the last 12 months relative to the current date.
        * `listens.total_duration_prior_12_months`: Sum of `total_duration` where `played_at` is in the 12-month period immediately preceding the "past 12 months".
    2.  These measures will use `filters` or `timeDimension` filtering within their `sql` definition.
    3.  Provide the updated content for `cubejs/schema/Listen.js`.

    **Expected Output:**
    * Updated content for `cubejs/schema/Listen.js` with the new measures.
    ```

#### **Module 3.5: Cube.js Deployment**

21. **Prompt: Dockerize Cube.js Application and Provide Deployment Instructions**
    ```text
    You need to dockerize the Cube.js application and provide instructions for its deployment on Google Cloud Run.

    **Context:**
    * The Cube.js project is in the `cubejs` directory.
    * It uses environment variables for DB connection.
    * It needs to be accessible by the frontend.

    **Task:**
    1.  Create a `cubejs/Dockerfile`.
    2.  The Dockerfile should:
        * Use an appropriate Node.js base image (e.g., `node:18-slim`).
        * Set the working directory.
        * Copy `package.json` and `package-lock.json` (or `yarn.lock`).
        * Install Node.js dependencies.
        * Copy the `schema` directory and other necessary Cube.js files.
        * Define the `CMD` to start the Cube.js server.
        * Expose the default Cube.js port (usually 4000).
    3.  Provide detailed instructions (`README.md` for `cubejs` or general `docs/deployment.md`) for deploying Cube.js to Google Cloud Run:
        * Commands to tag and push the Docker image to Google Artifact Registry.
        * `gcloud` commands or Console steps to deploy the Cloud Run service.
        * Specify how to set the `PG_HOST`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`, `PG_PORT`, `PG_SSL` as environment variables.
        * Set appropriate CPU/Memory limits.
        * Set the service to "Allow unauthenticated invocations" (as it's an API for the frontend).
    4.  Update the root `.gitignore` to include any new Cube.js specific files that should be ignored (e.g., `cubejs/node_modules`).

    **Expected Output:**
    * `cubejs/Dockerfile` content.
    * Markdown-formatted deployment instructions.
    * Updated root `.gitignore` content.
    ```

---

### **Phase 4: Frontend Dashboard (React)**

#### **Module 4.1: React Project Setup & Basic Structure**

22. **Prompt: Initialize React Project with Ant Design and Chart.js**
    ```text
    You need to initialize a new React project and integrate Ant Design and Chart.js.

    **Context:**
    * The React project will reside in the `frontend` directory.
    * We'll use Vite for a fast setup.
    * Ant Design will be the UI library.
    * Chart.js will be for charting.
    * We need to set up the Cube.js client configuration.

    **Task:**
    1.  Initialize a new React project inside `frontend` using Vite (choose React and JavaScript/TypeScript as preferred).
    2.  Install `antd` and its dependencies. Configure Ant Design's `ConfigProvider` for a basic theme.
    3.  Install `chart.js` and `react-chartjs-2`.
    4.  Install Cube.js client libraries: `@cubejs-client/core` and `@cubejs-client/react`.
    5.  Configure a basic `CubejsApi` instance in `frontend/src/cubejs-client.js` (or similar) that points to the Cube.js API endpoint (which will be an environment variable).
    6.  Create a simple `frontend/src/App.js` that displays an Ant Design `Layout` with a `Header` and `Content`, and imports the `CubejsApi` instance.
    7.  Update `frontend/src/main.jsx` (or `index.js`) to render `App.js` wrapped in `ConfigProvider`.
    8.  Update `frontend/.gitignore` to ignore `node_modules` and `dist` (Vite build output).
    9.  Provide a `.env.local` placeholder for `VITE_CUBEJS_API_URL`.

    **Expected Output:**
    * Vite setup commands.
    * `frontend/package.json` (showing dependencies).
    * `frontend/src/cubejs-client.js` content.
    * `frontend/src/App.js` content.
    * `frontend/src/main.jsx` content.
    * `frontend/.gitignore` content.
    * `frontend/.env.local` content.
    ```

#### **Module 4.2: Feature Implementation: Taste Evolution**

23. **Prompt: Develop "Taste Evolution" Component (Basic Line Chart)**
    ```text
    You need to develop the "Taste Evolution" component, displaying a basic line chart of genre listen time over time.

    **Context:**
    * We have React project setup with AntD and Chart.js.
    * Cube.js is configured via `cubejs-client.js`.
    * Cube.js models handle `listens.total_duration` and `artists.genres` (unwound).
    * The chart should show top N genres, aggregated by week.

    **Task:**
    1.  Create a new React component `frontend/src/components/TasteEvolutionChart.jsx`.
    2.  Inside this component:
        * Use `@cubejs-client/react`'s `useCubeQuery` hook.
        * Construct a Cube.js query for `listens.total_duration` over `listens.played_at.week`, broken down by `artists.genres`.
        * Add a `limit` and `order` clause to get top genres.
        * Process the `resultSet` from Cube.js to transform it into a format suitable for Chart.js. This will involve identifying the top N genres and potentially filtering data to only include those.
        * Render a Chart.js `Line` component using the processed data.
        * Add basic Ant Design `Spin` component for loading state.
    3.  Integrate `TasteEvolutionChart.jsx` into `App.js`.
    4.  Add a simple test for `TasteEvolutionChart.jsx` (e.g., mocking `useCubeQuery` response) to verify rendering and data transformation.

    **Expected Output:**
    * `frontend/src/components/TasteEvolutionChart.jsx` content.
    * Updated `frontend/src/App.js` content.
    * Test file for `TasteEvolutionChart.jsx`.
    ```

#### **Module 4.3: Feature Implementation: You Used to Love This**

24. **Prompt: Develop "You Used to Love This" Component**
    ```text
    You need to develop the "You Used to Love This" component, displaying a list of artists based on specific listening criteria.

    **Context:**
    * Cube.js provides `listens.total_duration_past_12_months` and `listens.total_duration_prior_12_months` measures (or equivalent measures defined in `Artist` cube, if preferred).
    * The component should display artist image, name, and a summary statement.
    * Ant Design `List` and `Card` components would be suitable.

    **Task:**
    1.  Create a new React component `frontend/src/components/YouUsedToLoveThis.jsx`.
    2.  Inside this component:
        * Use `useCubeQuery` to fetch `artists.name`, `artists.image_url`, `listens.total_duration_past_12_months`, and `listens.total_duration_prior_12_months`, grouped by `artists.name` and `artists.image_url`.
        * Implement the logic in React to filter artists based on the criteria:
            * `total_duration_past_12_months` is zero, OR
            * `total_duration_past_12_months` < 3% of `total_duration_prior_12_months`.
        * Render the qualifying artists using Ant Design `List` with `ListItem`s, showing the artist's image and name.
        * For the "velocity of listens" statement, just display the calculated listen times for now (e.g., "Past 12 months: X, Prior 12 months: Y"). The exact phrasing can be refined later.
        * Add basic Ant Design `Spin` for loading state.
    3.  Integrate `YouUsedToLoveThis.jsx` into `App.js`.
    4.  Add a simple test for `YouUsedToLoveThis.jsx` (mocking `useCubeQuery`) to verify filtering logic and rendering.

    **Expected Output:**
    * `frontend/src/components/YouUsedToLoveThis.jsx` content.
    * Updated `frontend/src/App.js` content.
    * Test file for `YouUsedToLoveThis.jsx`.
    ```

#### **Module 4.4: Dynamic Query Builder: Core UI**

25. **Prompt: Implement Dynamic Query Builder Form UI**
    ```text
    You need to build the core UI for the dynamic query builder form using Ant Design components.

    **Context:**
    * The form will include dropdowns for Measures, Dimensions, Time Dimension, Granularity, and Filters.
    * It will have a "RUN" button.
    * It needs to fetch available Cube.js members (measures, dimensions, etc.) to populate the dropdowns.

    **Task:**
    1.  Create a new React component `frontend/src/components/QueryBuilderForm.jsx`.
    2.  Inside this component:
        * Use `useCubeQuery` (or a direct `CubejsApi` call) to fetch Cube.js metadata (`/v1/meta`). This metadata contains all available measures, dimensions, and time dimensions.
        * Use Ant Design `Select` components for:
            * Measures (multi-select)
            * Dimensions (multi-select)
            * Time Dimension (single-select, enabled only if a time field is selected).
            * Granularity (single-select, options: `no grouping`, `day`, `week`, `month`, `quarter`, `year`).
        * Use Ant Design `DatePicker.RangePicker` for the date range.
        * Implement a simple mechanism to add/remove filter rows, each with:
            * A `Select` for the field to filter on.
            * A `Select` for the operator.
            * An `Input` (or `Select` for enum types) for the value.
        * Add an Ant Design `Button` labeled "RUN".
        * Manage form state using React's `useState` or a form library.
    3.  Integrate `QueryBuilderForm.jsx` into `App.js`. The form should have a callback prop (e.g., `onRunQuery`) that passes the structured query object (measures, dimensions, timeDimensions, filters) up to `App.js` when the "RUN" button is clicked.
    4.  Add a basic test for `QueryBuilderForm.jsx` that mocks metadata fetching and verifies component rendering and form state updates.

    **Expected Output:**
    * `frontend/src/components/QueryBuilderForm.jsx` content.
    * Updated `frontend/src/App.js` content (passing `onRunQuery` prop).
    * Test file for `QueryBuilderForm.jsx`.
    ```

#### **Module 4.5: Dynamic Query Builder: Data Display**

26. **Prompt: Implement Table Display for Query Results**
    ```text
    You need to implement the table display for the dynamic query builder, which will always show the raw results.

    **Context:**
    * `QueryBuilderForm` passes a query object to `App.js`.
    * `App.js` will execute the Cube.js query and pass the `resultSet` to this component.
    * We need to use Ant Design `Table`.

    **Task:**
    1.  Create a new React component `frontend/src/components/QueryResultTable.jsx`.
    2.  This component should accept `resultSet` (from Cube.js) as a prop.
    3.  It should process the `resultSet` to extract column headers and row data suitable for Ant Design `Table`. Cube.js `resultSet.tablePivot()` is useful here.
    4.  Render an Ant Design `Table` with the processed data.
    5.  In `App.js`:
        * Add state to hold the `resultSet` from Cube.js.
        * Implement the `onRunQuery` callback:
            * Use `useCubeQuery` (or `CubejsApi.load()`) to execute the query passed from `QueryBuilderForm`.
            * Set the `resultSet` state.
            * Ensure the `limit` for the query is set to `10000`.
        * Pass the `resultSet` to `QueryResultTable`.
    6.  Add a basic test for `QueryResultTable.jsx` that mocks a `resultSet` and verifies table rendering.

    **Expected Output:**
    * `frontend/src/components/QueryResultTable.jsx` content.
    * Updated `frontend/src/App.js` content.
    * Test file for `QueryResultTable.jsx`.
    ```

27. **Prompt: Implement Basic Chart Type Selection Logic (Line/Bar)**
    ```text
    You need to implement the initial logic for dynamically selecting and rendering either a Line Chart or a Bar Chart based on the query builder's selections.

    **Context:**
    * `App.js` holds the query object and `resultSet`.
    * We need to apply the chart type selection logic from the spec.
    * Chart.js components will be rendered.

    **Task:**
    1.  Create a new React component `frontend/src/components/DynamicChart.jsx`.
    2.  This component should accept `query` and `resultSet` as props.
    3.  Inside `DynamicChart.jsx`, implement the simplified chart type selection logic:
        * **If a Time Dimension is selected AND Granularity is NOT 'no grouping':**
            * If **no other Dimensions** are selected (`dimensions.length === 0`): Render a Chart.js `Line` chart.
            * Otherwise: Render nothing (or a message "Chart not available for this combination").
        * **If NO Time Dimension is selected (or Granularity is 'no grouping'):**
            * If **exactly one Dimension** is selected (`dimensions.length === 1`): Render a Chart.js `Bar` chart.
            * Otherwise: Render nothing (or a message).
        * **Data Transformation:** For the selected chart type, transform the `resultSet` into Chart.js compatible `data` and `options` objects.
    4.  Integrate `DynamicChart.jsx` into `App.js`, rendering it below the `QueryResultTable`.
    5.  Add tests for `DynamicChart.jsx` that mock `query` and `resultSet` and verify that the correct Chart.js component type is rendered.

    **Expected Output:**
    * `frontend/src/components/DynamicChart.jsx` content.
    * Updated `frontend/src/App.js` content.
    * Test file for `DynamicChart.jsx`.
    ```

#### **Module 4.6: Dynamic Query Builder: Advanced Charting**

28. **Prompt: Refine Chart Type Logic for Stacked Bar and Multiple Lines**
    ```text
    You need to refine the chart type selection logic in `DynamicChart.jsx` to include Stacked Bar charts and handle multiple line charts, including the "top 12" limiting logic.

    **Context:**
    * We have the existing `DynamicChart.jsx` with basic line/bar logic.
    * The updated spec includes specific conditions for Stacked Bar and Multiple Line charts.
    * "Top 12" limiting for dimensions needs to be applied *before* rendering the chart.

    **Task:**
    1.  Update `frontend/src/components/DynamicChart.jsx` with the complete chart type selection logic from the specification:
        * **Condition for Time-Series Charts (Line/Stacked Bar):**
            * A Time Dimension is selected (e.g., `listens.played_at`) AND a Granularity is selected that is *not* `no grouping`.
            * If these conditions are met:
                * If **no other Dimensions** are selected (`dimensions.length === 0`) AND **multiple Measures** are selected (`measures.length > 1`): Generate a **Multiple Line Chart** (one line per measure over time).
                * If **exactly one other Dimension** is selected (`dimensions.length === 1`) AND **one Measure** is selected (`measures.length === 1`): Generate a **Multiple Line Chart** (one line per dimension value). This chart should display data for the top 12 values of the selected dimension (based on the total value of the single measure over the queried period).
                * Otherwise (complex time + multiple dimensions): Render nothing (or "Chart not available for this combination").
        * **Condition for Categorical/Distribution Charts (Bar/Stacked Bar):**
            * NO Time Dimension is selected OR the selected Time Dimension has `no grouping` selected for its granularity.
            * If these conditions are met:
                * If **exactly one Dimension** is selected (`dimensions.length === 1`) AND **multiple Measures** are selected (`measures.length > 1`): Generate a **Stacked Bar Chart**.
                * If **exactly one Measure** is selected (`measures.length === 1`) AND **exactly two Dimensions** are selected (`dimensions.length === 2`): Generate a **Stacked Bar Chart**. The chart should display data for the top 12 values of the *second* selected dimension, based on the total value of the selected measure.
                * Otherwise (simple aggregates or complex non-time combinations): Render nothing (or "Chart not available for this combination").
        * Implement the necessary data transformation functions for Chart.js to handle these new chart types (e.g., creating multiple datasets for line charts, structuring data for stacked bars).
        * Implement the "top 12" filtering logic by sorting dimension values by the measure's total and slicing the top 12.
    2.  Update tests for `DynamicChart.jsx` to cover these new complex scenarios with mocked `query` and `resultSet` data.

    **Expected Output:**
    * Updated `frontend/src/components/DynamicChart.jsx` content with complete chart logic.
    * Updated test file for `DynamicChart.jsx`.
    ```

#### **Module 4.7: Dashboard Polish & Deployment**

29. **Prompt: Implement Loading States and Error Handling in Frontend**
    ```text
    You need to implement robust loading states and user-friendly error handling throughout the React frontend.

    **Context:**
    * All components using `useCubeQuery` or direct API calls can be in a loading state or encounter errors.
    * Ant Design `Spin` and `message`/`Alert` components are available.

    **Task:**
    1.  In `frontend/src/App.js` and other relevant components (`TasteEvolutionChart.jsx`, `YouUsedToLoveThis.jsx`, `QueryBuilderForm.jsx`, `DynamicChart.jsx`, `QueryResultTable.jsx`):
        * Utilize the `isLoading` state from `useCubeQuery` to display Ant Design `Spin` components.
        * Utilize the `error` state from `useCubeQuery` to display Ant Design `message.error` or `Alert` components with user-friendly messages.
        * Handle cases where `resultSet` is `null` or empty (e.g., display "No data available").
    2.  Ensure that network errors or API errors from Cube.js are caught and displayed appropriately to the user.
    3.  Add basic tests to verify loading states appear/disappear and error messages are displayed under mocked conditions.

    **Expected Output:**
    * Updated content for `frontend/src/App.js` and relevant components (`TasteEvolutionChart.jsx`, `YouUsedToLoveThis.jsx`, `QueryBuilderForm.jsx`, `DynamicChart.jsx`, `QueryResultTable.jsx`) to include loading and error handling.
    * Updated test files to cover these scenarios.
    ```

30. **Prompt: Configure Vercel Deployment for Frontend**
    ```text
    You need to provide instructions for deploying the React frontend application to Vercel.

    **Context:**
    * The frontend is a React project located in the `frontend` directory.
    * It uses Vite for building.
    * It needs to access the Cube.js API via `VITE_CUBEJS_API_URL`.

    **Task:**
    1.  Provide detailed, step-by-step instructions (e.g., in `frontend/README.md` or `docs/deployment.md`) for deploying the React application to Vercel:
        * Instructions to create a Vercel account and install Vercel CLI (if not already done).
        * Instructions to link the Vercel project to the Git repository (e.g., GitHub, GitLab).
        * Specify the build command (`npm run build` or `yarn build`).
        * Specify the output directory (`dist`).
        * Crucially, detail how to set the `VITE_CUBEJS_API_URL` environment variable within Vercel's project settings, as a production environment variable.
        * Instructions on how to trigger a deployment and verify the deployed application.
    2.  Add a simple Vercel project configuration file (e.g., `frontend/vercel.json` if needed, although Vercel often auto-detects Vite).

    **Expected Output:**
    * Markdown-formatted Vercel deployment instructions.
    * (Optional, if necessary) `frontend/vercel.json` content.
    ```