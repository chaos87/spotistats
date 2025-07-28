# TODO: Spotify Listening Dashboard Implementation Checklist

This checklist is based on the project specification, broken down into iterative, test-driven steps.

## Phase 1: Core Infrastructure & Setup

### Module 1.1: Project Initialization & Repository Setup

-   [x] **Initialize Root Git Repository**
    -   [x] Create `spotify-dashboard` root directory.
    -   [x] Run `git init` in the root.
    -   [x] Create a root `.gitignore` file.
-   [x] **Create Monorepo Subdirectories**
    -   [x] Create `backend/`
    -   [x] Create `cubejs/`
    -   [x] Create `frontend/`
-   [x] **Initialize Python Backend Project (Poetry)**
    -   [x] Navigate to `backend/`.
    -   [x] Run `poetry init` to create `pyproject.toml`.
    -   [x] Add initial dependencies to `backend/pyproject.toml`:
        -   `requests`
        -   `psycopg2-binary`
        -   `SQLAlchemy`
        -   `python-dotenv`
        -   `pyjwt`
    -   [x] Add `pytest` as a development dependency.
    -   [x] Create `backend/main.py` (simple print statement).
    -   [x] Create `backend/tests/` directory.
    -   [x] Create `backend/tests/test_main.py` (simple passing test).
    -   [x] Run `poetry install` to confirm setup.

### Module 1.2: Database & Schema Foundation (Neon)

-   [x] **Provision Neon PostgreSQL Database**
    -   [x] Create a new project/database on Neon.tech.
    -   [x] Record the database connection string.
-   [x] **Create Initial Database Tables (SQL DDL)**
    -   [x] Execute SQL DDL for `recently_played_tracks_raw` table.
    -   [x] Execute SQL DDL for `artists` table.
    -   [x] Execute SQL DDL for `albums` table.
    -   [x] Execute SQL DDL for `tracks` table (including `last_played_at` and `spotify_url`).
    -   [x] Execute SQL DDL for `listens` table (initial version with `episode_id` as TEXT).
    -   [x] Verify table creation using a DB client.

## Phase 2: Data Ingestion Pipeline (Backend - Python on Cloud Run)

### Module 2.1: Spotify API Client & Authentication

-   [x] **Implement Spotify OAuth Client (`backend/src/spotify_client.py`)**
    -   [x] Define `SpotifyOAuthClient` class.
    -   [x] Implement `get_access_token_from_refresh(self)` method.
    -   [x] Implement `get_initial_refresh_token_manual_flow(self, auth_code, redirect_uri)` method.
    -   [x] Add basic error handling and logging within the client.
    -   [x] Create `backend/tests/test_spotify_client.py`.
    -   [x] Write unit tests for both client methods (mocking `requests`).
-   [x] **Secure Environment Variable Loading (`backend/src/config.py`)**
    -   [x] Create `backend/src/config.py`.
    -   [x] Implement functions to load `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN` from environment variables using `python-dotenv`.
    -   [x] Raise errors if required variables are missing.
    -   [x] Create `backend/.env` with placeholder values (add to `.gitignore`).
    -   [x] Create `backend/tests/test_config.py` with tests for env var loading.
-   [x] **Integrate Auth Client with `main.py`**
    -   [x] Update `backend/main.py` to load credentials via `config.py`.
    -   [x] Instantiate `SpotifyOAuthClient` and call `get_access_token_from_refresh()` (print token for now).
    -   [x] Verify local execution for token retrieval.

### Module 2.2: Raw Data Ingestion

-   [x] **Implement Spotify Data Fetcher (`backend/src/spotify_data.py`)**
    -   [x] Create `backend/src/spotify_data.py`.
    -   [x] Define `get_recently_played_tracks(access_token, limit=50)`.
    -   [x] Add basic error handling and logging.
    -   [x] Create `backend/tests/test_spotify_data.py`.
    -   [x] Write unit tests for `get_recently_played_tracks` (mocking `requests`).
-   [x] **Setup SQLAlchemy ORM and Raw Data Insertion (`backend/src/database.py`)**
    -   [x] In `backend/src/database.py`:
        -   [x] Define `get_db_engine()` using `DATABASE_URL` from `config.py`.
        -   [x] Define `Base = declarative_base()`.
        -   [x] Define SQLAlchemy model for `recently_played_tracks_raw` table.
        -   [x] Implement `insert_raw_data(engine, raw_json_data)`.
    -   [x] Create `backend/tests/test_database.py`.
    -   [x] Write unit tests for `get_db_engine` and `insert_raw_data` (using in-memory SQLite or mocked engine/session).
    -   [x] Update `backend/.env` with `DATABASE_URL` placeholder.
-   [x] **Wire up Raw Data Ingestion in `main.py`**
    -   [x] Update `backend/main.py` to:
        -   [x] Call `get_recently_played_tracks`.
        -   [x] Call `insert_raw_data`.
        -   [x] Add logging for success/failure.
    -   [x] Test end-to-end raw data ingestion locally.

### Module 2.3: Initial Normalized Data Processing & Loading

-   [x] **Define SQLAlchemy Models for Core Normalized Tables (`backend/src/models.py` or `database.py`)**
    -   [x] Define `Artist`, `Album`, `Track`, `Listen` ORM models.
    -   [x] Ensure `ForeignKeys` and `relationships` are correctly set.
    -   [x] Add `CheckConstraint` for `listens.item_type` and `track_id`/`episode_id` (initial version for `track_id` being NOT NULL and `episode_id` NULL for type 'track').
    -   [x] Add tests for model definition and mapping.
-   [x] **Implement Spotify Data Normalizer (Music Only) (`backend/src/normalizer.py`)**
    -   [x] Create `backend/src/normalizer.py`.
    -   [x] Define `SpotifyMusicNormalizer` class with `normalize_track_item(item)`.
    -   [x] Extract and return `Artist`, `Album`, `Track`, `Listen` ORM objects.
    -   [x] Set `item_type` for `Listen` to 'track'.
    -   [x] Create `backend/tests/test_normalizer.py`.
    -   [x] Write unit tests for `normalize_track_item` using mocked Spotify JSON.
-   [x] **Implement Database UPSERT & Ingestion Logic (`backend/src/database.py` and `main.py`)**
    -   [x] In `backend/src/database.py`:
        -   [x] Implement `get_max_played_at(engine)`.
        -   [x] Implement `upsert_artist(session, artist_obj)` using `ON CONFLICT`.
        -   [x] Implement `upsert_album(session, album_obj)` using `ON CONFLICT`.
        -   [x] Implement `upsert_track(session, track_obj)` using `ON CONFLICT`.
        -   [x] Implement `insert_listen(session, listen_obj)` handling `IntegrityError` for `played_at` uniqueness.
    -   [x] Update `backend/main.py`:
        -   [x] Get `max_played_at`.
        -   [x] Iterate fetched Spotify items.
        -   [x] Filter items based on `played_at > max_played_at`.
        -   [x] For `type == 'track'`: normalize, UPSERT entities, insert listen.
        -   [x] Add comprehensive logging for ingestion progress.
    -   [x] Create `backend/tests/test_ingestion_logic.py`.
    -   [x] Write integration tests using a test DB to verify incremental ingestion, UPSERTs, and de-duplication.

### Module 2.4: Podcast Data Integration

-   [x] **Define SQLAlchemy Models for Podcast Entities & Update Listen FKs (`backend/src/models.py`)**
    -   [x] Define `PodcastSeries` and `PodcastEpisode` ORM models.
    -   [x] Modify `Listen` model:
        -   [x] Add `ForeignKey` for `episode_id` to `podcast_episodes`.
        -   [x] Update `CHECK` constraint to correctly handle `item_type`, `track_id`, `episode_id`, and `artist_id`/`album_id` nullability for podcasts.
    -   [x] Add tests for new models and updated `Listen` constraint.
-   [x] **Enhance Normalizer for Podcasts (`backend/src/normalizer.py`)**
    -   [x] Add `normalize_episode_item(item)` method to return `PodcastSeries`, `PodcastEpisode`, `Listen` objects.
    -   [x] Modify the main normalization entry point to differentiate between 'track' and 'episode' items.
-   [x] **Enhance Ingestion for Podcasts (`backend/src/database.py` and `main.py`)**
    -   [x] In `backend/src/database.py`:
        -   [x] Add `upsert_podcast_series(session, series_obj)`.
        -   [x] Add `upsert_podcast_episode(session, episode_obj)`.
    -   [x] Update `backend/main.py` to:
        -   [x] Handle `item['track']['type'] == 'episode'`.
        -   [x] Call new podcast normalization and UPSERTs.
        -   [x] Insert `Listen` with `episode_id` populated and `artist_id`/`album_id` as NULL.
    -   [x] Create `backend/tests/test_podcast_ingestion.py`.
    -   [x] Write integration tests for podcast ingestion (mocked Spotify responses).

### Module 2.5: Advanced Ingestion Features & Robustness

-   [x] **Implement `tracks.last_played_at` Update Logic (`backend/src/database.py` and `normalizer.py`)**
    -   [x] Modify `upsert_track` in `database.py` to update `last_played_at` if the new `played_at` is more recent.
    -   [x] Ensure `normalizer.py` sets `last_played_at` on `Track` objects during normalization.
    -   [x] Update `backend/tests/test_ingestion_logic.py` with test cases for `last_played_at` updates.
-   [x] **Implement Comprehensive Error Handling & Structured Logging (`backend/src/utils.py`, `main.py`, client/data/db files)**
    -   [x] Create `backend/src/utils.py` with retry logic (e.g., decorator).
    -   [x] Configure structured JSON logging in `main.py`.
    -   [x] Apply `try-except` blocks around all critical operations in `main.py`.
    -   [x] Define and raise custom exceptions (e.g., `SpotifyAPIError`, `DatabaseError`) in `spotify_client.py`, `spotify_data.py`, `database.py`.
    -   [x] Update tests to verify error handling and logging.

### Module 2.6: Deployment & Scheduling

-   [x] **Dockerize Python Ingestion Application (`backend/Dockerfile`)**
    -   [x] Create `backend/Dockerfile` optimized for Cloud Run.
    -   [x] Create `backend/README.md` with local build/run instructions.
-   [x] **Deploy to Google Cloud Run (Manual)**
    -   [x] Create GCP project and enable necessary APIs.
    -   [x] Build and push Docker image to Google Artifact Registry.
    -   [x] Deploy Cloud Run service, setting all required environment variables (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `DATABASE_URL`).
    -   [x] Allow unauthenticated invocations (for Cloud Scheduler simplicity).
    -   [x] Manually invoke the Cloud Run service to verify initial data ingestion.
-   [x] **Set up Cloud Scheduler for Hourly Execution**
    -   [x] Create a Cloud Scheduler job with `0 * * * *` frequency.
    -   [x] Set target to HTTP with the Cloud Run service URL.
    -   [x] Create a dedicated service account for Cloud Scheduler with `Cloud Run Invoker` role.
    -   [x] Test the Cloud Scheduler job manually.

## Phase 3: API Layer (Cube.js)

### Module 3.1: Cube.js Project Setup & DB Connection

-   [x] **Initialize Cube.js Project**
    -   [x] Navigate to `cubejs/`.
    -   [x] Run Cube.js CLI command to initialize a new project (PostgreSQL).
    -   [x] Create `cubejs/README.md` with local dev server instructions.
-   [x] **Configure DB Connection**
    -   [x] Update `cubejs/.env` with placeholder DB credentials (`PG_HOST`, `PG_USER`, etc.) (add to root `.gitignore`).
    -   [x] Ensure `cubejs/schema/index.js` or `example.js` references the correct DB configuration.
    -   [x] Verify local Cube.js dev server starts and connects to DB.

### Module 3.2: Core Data Modeling

-   [x] **Model `Artist` Cube (`cubejs/schema/Artist.js`)**
    -   [x] Define `sql_table` and `dimensions`.
    -   [x] Map `artist_id`, `name`, `spotify_url`, `image_url`.
-   [x] **Model `Album` Cube (`cubejs/schema/Album.js`)**
    -   [x] Define `sql_table`, `dimensions`.
    -   [x] Map `album_id`, `name`, `release_date`, `album_type`, `spotify_url`, `image_url`.
    -   [x] Define `joins` to `Artist` cube.
-   [x] **Model `Track` Cube (`cubejs/schema/Track.js`)**
    -   [x] Define `sql_table`, `dimensions`.
    -   [x] Map `track_id`, `name`, `duration_ms`, `explicit`, `popularity`, `preview_url`, `spotify_url`, `available_markets`, `last_played_at`.
    -   [x] Define `joins` to `Album` cube.
-   [x] **Model `Listen` Cube (`cubejs/schema/Listen.js`)**
    -   [x] Define `sql_table`.
    -   [x] Define `measures.count`.
    -   [x] Define `measures.total_duration` (initial version, summing `tracks.duration_ms`).
    -   [x] Define `timeDimension` for `played_at`.
    -   [x] Define `joins` to `Track`, `Album`, `Artist` cubes.
-   [x] **Verify Core Models in Cube.js Playground.**

### Module 3.3: Podcast & Advanced Relationship Modeling

-   [ ] **Model Podcast Cubes (`cubejs/schema/PodcastSeries.js`, `PodcastEpisode.js`)**
    -   [ ] Define `sql_table` and `dimensions` for both.
    -   [ ] Define `joins` from `PodcastEpisode` to `PodcastSeries`.
-   [ ] **Refine `Listen` Cube for Polymorphism (`cubejs/schema/Listen.js`)**
    -   [ ] Add `joins` to `PodcastEpisode` and `PodcastSeries`.
    -   [ ] Update `listens.total_duration` measure to use `CASE` statement based on `item_type` for correct duration summing (from `tracks.duration_ms` or `podcast_episodes.duration_ms`).
    -   [ ] Ensure `item_type` is available as a dimension.
-   [ ] **Verify Podcast Models & Polymorphic Measures in Cube.js Playground.**

### Module 3.4: Feature-Specific Data Modeling

-   [x] **Model `artists.genres` for Taste Evolution (`cubejs/schema/Artist.js`)**
    -   [x] Modify `Artist.js` to define a dimension for `genres` using `sql` property with `unnest()`.
-   [x] **Define "You Used to Love This" Measures (`cubejs/schema/Listen.js`)**
    -   [x] Add `measures.total_duration_past_12_months` to `Listen.js` (filtered by time).
    -   [x] Add `measures.total_duration_prior_12_months` to `Listen.js` (filtered by time).
-   [x] **Verify new genre and "You Used to Love This" measures in Cube.js Playground.**

### Module 3.5: Cube.js Deployment

-   [x] **Dockerize Cube.js Application (`cubejs/Dockerfile`)**
    -   [x] Create `cubejs/Dockerfile`.
    -   [x] Optimize for production.
-   [x] **Deploy Cube.js to Google Cloud Run (Instructions)**
    -   [x] Build and push Docker image to Google Artifact Registry.
    -   [x] Deploy Cloud Run service, setting all required environment variables for DB connection.
    -   [x] Set service to allow unauthenticated invocations.
    -   [x] Record the Cube.js API endpoint URL.

## Phase 4: Frontend Dashboard (React)

### Module 4.1: React Project Setup & Basic Structure

-   [x] **Initialize React Project (Vite)**
    -   [x] Navigate to `frontend/`.
    -   [x] Run Vite command to initialize React project.
-   [x] **Install & Configure UI/Charting Libraries**
    -   [x] Install `antd`, `chart.js`, `react-chartjs-2`.
    -   [x] Configure Ant Design `ConfigProvider` in `frontend/src/main.jsx`.
-   [x] **Setup Cube.js Client**
    -   [x] Install `@cubejs-client/core`, `@cubejs-client/react`.
    -   [x] Create `frontend/src/cubejs-client.js` with `CubejsApi` instance pointing to `VITE_CUBEJS_API_URL` (from `.env.local`).
-   [x] **Basic App Structure (`frontend/src/App.js`)**
    -   [x] Create `App.js` with Ant Design `Layout`, `Header`, `Content`.
    -   [x] Add basic text to verify rendering.
-   [x] **Configure `.gitignore`**
    -   [x] Update `frontend/.gitignore` for `node_modules` and `dist`.
    -   [x] Create `frontend/.env.local` for `VITE_CUBEJS_API_URL` (add to root `.gitignore`).
-   [x] **Verify Local React Development Server.**

### Module 4.2: Feature Implementation: Taste Evolution

-   [ ] **Develop `TasteEvolutionChart` Component (`frontend/src/components/TasteEvolutionChart.jsx`)**
    -   [ ] Create the component.
    -   [ ] Use `useCubeQuery` for `listens.total_duration` by `listens.played_at.week` and `artists.genres`.
    -   [ ] Implement logic to process `resultSet` for Chart.js (top N genres).
    -   [ ] Render Chart.js `Line` component.
    -   [ ] Add Ant Design `Spin` for loading.
    -   [ ] Write unit tests (mock `useCubeQuery`).
-   [ ] **Integrate into `App.js`**
    -   [ ] Import and render `TasteEvolutionChart`.

### Module 4.3: Feature Implementation: You Used to Love This

-   [ ] **Develop `YouUsedToLoveThis` Component (`frontend/src/components/YouUsedToLoveThis.jsx`)**
    -   [ ] Create the component.
    -   [ ] Use `useCubeQuery` for `artists.name`, `artists.image_url`, `listens.total_duration_past_12_months`, `listens.total_duration_prior_12_months`.
    -   [ ] Implement frontend filtering logic for "used to love this" criteria.
    -   [ ] Render using Ant Design `List` and `Card` components (artist image, name, summary).
    -   [ ] Add Ant Design `Spin` for loading.
    -   [ ] Write unit tests (mock `useCubeQuery`).
-   [ ] **Integrate into `App.js`**
    -   [ ] Import and render `YouUsedToLoveThis`.

### Module 4.4: Dynamic Query Builder: Core UI

-   [ ] **Implement `QueryBuilderForm` Component (`frontend/src/components/QueryBuilderForm.jsx`)**
    -   [ ] Create the component.
    -   [ ] Use `useCubeQuery` (or direct client call) to fetch Cube.js metadata.
    -   [ ] Implement Ant Design `Select` for Measures (multi-select).
    -   [ ] Implement Ant Design `Select` for Dimensions (multi-select).
    -   [ ] Implement Ant Design `Select` for Time Dimension field and separate `Select` for Granularity (`no grouping`, `day`, `week`, `month`, `quarter`, `year`).
    -   [ ] Implement Ant Design `DatePicker.RangePicker`.
    -   [ ] Implement dynamic add/remove for Filter rows (field, operator, value).
    -   [ ] Add Ant Design "RUN" Button.
    -   [ ] Manage form state.
    -   [ ] Define `onRunQuery` callback prop.
    -   [ ] Write unit tests (mock metadata fetch, verify state/callbacks).
-   [ ] **Integrate into `App.js`**
    -   [ ] Import and render `QueryBuilderForm`.
    -   [ ] Implement `onRunQuery` callback in `App.js` to store query params.

### Module 4.5: Dynamic Query Builder: Data Display

-   [ ] **Implement `QueryResultTable` Component (`frontend/src/components/QueryResultTable.jsx`)**
    -   [ ] Create the component.
    -   [ ] Accept `resultSet` as prop.
    -   [ ] Process `resultSet` for Ant Design `Table` (using `resultSet.tablePivot()`).
    -   [ ] Render Ant Design `Table`.
    -   [ ] Write unit tests (mock `resultSet`).
-   [ ] **Update `App.js` for Query Execution & Table Display**
    -   [ ] In `onRunQuery` callback:
        -   [ ] Use `useCubeQuery` (or `CubejsApi.load()`) to execute the query.
        -   [ ] Set query `limit` to `10000`.
        -   [ ] Store the `resultSet` in `App.js` state.
    -   [ ] Pass `resultSet` to `QueryResultTable`.
-   [ ] **Implement Basic `DynamicChart` Component (`frontend/src/components/DynamicChart.jsx`)**
    -   [ ] Create the component.
    -   [ ] Accept `query` and `resultSet` as props.
    -   [ ] Implement initial chart type selection logic (Line for single measure over time, Bar for single dimension).
    -   [ ] Implement basic data transformation for Chart.js.
    -   [ ] Render Chart.js `Line` or `Bar` components.
    -   [ ] Add loading/error states.
    -   [ ] Write unit tests (mock `query` and `resultSet`).
-   [ ] **Integrate `DynamicChart` into `App.js`**
    -   [ ] Import and render `DynamicChart` below the table.

### Module 4.6: Dynamic Query Builder: Advanced Charting

-   [ ] **Refine `DynamicChart` for Stacked Bar and Multiple Lines (`frontend/src/components/DynamicChart.jsx`)**
    -   [ ] Update chart type selection logic to include:
        -   [ ] Multiple Line Chart (no other dimensions, multiple measures).
        -   [ ] Multiple Line Chart (one other dimension, one measure, top 12 limiting).
        -   [ ] Stacked Bar Chart (one dimension, multiple measures, no time/no grouping).
        -   [ ] Stacked Bar Chart (two dimensions, one measure, no time/no grouping, top 12 for second dimension).
    -   [ ] Implement data transformation functions for Chart.js for these new types.
    -   [ ] Implement "top 12" filtering logic within data processing.
    -   [ ] Update unit tests to cover new complex scenarios.

### Module 4.7: Dashboard Polish & Deployment

-   [ ] **Implement Comprehensive Loading States and Error Handling in Frontend Components**
    -   [ ] Review all components (`App.js`, `TasteEvolutionChart`, `YouUsedToLoveThis`, `QueryBuilderForm`, `DynamicChart`, `QueryResultTable`).
    -   [ ] Ensure `isLoading` from `useCubeQuery` triggers `Spin` components.
    -   [ ] Ensure `error` from `useCubeQuery` displays Ant Design `message.error` or `Alert` components.
    -   [ ] Handle empty data sets/`resultSet` being null.
    -   [ ] Update unit tests for these error/loading scenarios.
-   [ ] **Configure Vercel Deployment for Frontend (`frontend/vercel.json` and instructions)**
    -   [ ] Create `frontend/vercel.json` if needed (or verify Vite auto-detection).
    -   [ ] Provide `frontend/README.md` (or separate `docs/deployment.md`) with:
        -   [ ] Instructions for Vercel account setup/CLI.
        -   [ ] Steps to link Git repository to Vercel project.
        -   [ ] Build command and output directory configuration.
        -   [ ] **Crucially, instructions for setting `VITE_CUBEJS_API_URL` as a production environment variable in Vercel settings.**
        -   [ ] Steps to trigger and verify deployment.
