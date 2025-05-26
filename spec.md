
# Spotify Listening Dashboard: Developer Specification

### I. Introduction

This document outlines the detailed specification for a personal dashboard designed to visualize historical listening data from Spotify. The primary goal is to provide insights into user listening habits, including time spent with artists, genre preferences, and rediscovery of past favorites.

----------

### II. Data Ingestion Pipeline Specification

**A. Objective & Scope**

-   **Objective:** To automatically and periodically collect the user's recent music and podcast listening history from Spotify and store it in a PostgreSQL database for analysis.
-   **Scope:** This automated process focuses exclusively on **ongoing listens**. The initial full historical data dump (obtained manually via Spotify's data request process) is considered out of scope for this automated pipeline but will be integrated into the dashboard's analysis.

**B. Technology Stack**

-   **Programming Language:** Python
-   **Deployment Environment:** Google Cloud Run (serverless container execution)
-   **Database:** PostgreSQL (hosted on Neon.tech)
-   **Source API:** Spotify Web API

**C. Spotify API & Authentication**

-   **Primary Endpoint:** `/me/player/recently-played`
    -   **Limitation:** This endpoint returns a maximum of 50 of the user's most recently played items.
-   **Authorization Flow:** Authorization Code Flow with Refresh Tokens. This is crucial for automated, server-side access without requiring repeated manual user interaction.
-   **Credential Management:**
    -   Spotify `CLIENT_ID`, `CLIENT_SECRET`, and the user's `REFRESH_TOKEN` will be stored securely as **environment variables** within the Google Cloud Run environment.
    -   **Initial Setup:** A one-time manual process will be required to obtain the initial `REFRESH_TOKEN` for the user. The Python script will then use this refresh token to periodically acquire new access tokens.

**D. Data Handling & Logic (Python Script)**

-   **Execution Frequency:** The Cloud Run script will be scheduled to run **every hour** via Google Cloud Scheduler.
-   **Idempotency & De-duplication Strategy:**
    1.  **Retrieve High Water Mark:** Before fetching new data, the script will query the `listens` table in the PostgreSQL database to retrieve the `max(played_at)` timestamp. If the table is empty, a suitable default (e.g., epoch start) will be used.
    2.  **Fetch from Spotify:** The script will call the `/me/player/recently-played` endpoint with `limit=50`.
    3.  **Filter New Data:** The fetched Spotify items (tracks or episodes) will be iterated through. Only items with a `played_at` timestamp **strictly greater** than the retrieved `max(played_at)` from the database will be considered for insertion.
    4.  **Dependent Entity Insertion (UPSERT):**
        -   For each _new_ listen item, its associated entities (artists, albums, tracks for music; podcast series, podcast episodes for podcasts) will be processed.
        -   The script will attempt to insert these entities into their respective normalized tables using their Spotify IDs as unique identifiers. A PostgreSQL `INSERT ... ON CONFLICT (id_column) DO NOTHING` (UPSERT) mechanism will be used to ensure that existing entities are not duplicated, and only new entities are added.
        -   **`tracks.last_played_at` Update:** Whenever a `track_id` is encountered (either new or existing) during the ingestion of a `listens` record, its corresponding `tracks.last_played_at` column must be updated to the `played_at` timestamp of the _most recent_ listen for that track.
    5.  **Listen Record Insertion:** Finally, the new `listens` records will be inserted. The `played_at` column in the `listens` table is `UNIQUE`, acting as a final database-level safeguard against duplicates, even if the `max(played_at)` filtering has an edge case.
-   **Assumption:** Due to Spotify API limitations, all recorded `listens` (both music and podcasts) are assumed to represent a complete playback of the track/episode. The API does not provide duration of partial plays.

**E. Error Handling & Logging**

-   **API Call Errors:** Implement retry mechanisms (e.g., exponential backoff) for transient network or API rate limit errors. Log persistent API errors (e.g., invalid credentials, 4xx responses) with full details.
-   **Database Connection/Operation Errors:** Implement retry logic for connection issues. Log specific database errors (e.g., constraint violations that aren't handled by `ON CONFLICT`, data type mismatches).
-   **Data Processing Errors:** Log warnings for malformed or unexpected data structures in the Spotify API response. Gracefully skip invalid records if they cannot be parsed.
-   **Logging:** Use structured logging (e.g., `logging` module in Python, formatted as JSON) to ensure logs are easily consumable by Google Cloud Logging, allowing for filtering and analysis. Log successful runs, number of new records ingested, and any warnings/errors.

**F. Testing Plan (Ingestion Script)**

-   **Unit Tests:** Develop unit tests for:
    -   Spotify API client interaction (mocking API responses).
    -   Data parsing logic (converting raw JSON to structured Python objects).
    -   Database insertion functions (mocking database calls or using an in-memory DB).
    -   De-duplication logic (simulating `max_played_at` and new data).
-   **Integration Tests:**
    -   Test the script's ability to connect to a mocked/test Spotify API and a real (test) Neon PostgreSQL database.
    -   Verify correct data transformation and insertion.
-   **End-to-End Tests:**
    -   Deploy the script to a staging Cloud Run environment.
    -   Configure Cloud Scheduler to trigger it.
    -   Verify that data is correctly ingested into the staging database.
    -   Conduct data integrity checks post-ingestion (e.g., no duplicates, correct foreign key relationships, `last_played_at` updates).

----------

### III. Database Schema Specification (PostgreSQL on Neon)

**A. `recently_played_tracks_raw` Table**

-   **Purpose:** To store the complete raw JSON response from each Spotify API fetch for auditing and potential reprocessing.
-   **Schema:**
    
    SQL
    
    ```
    CREATE TABLE recently_played_tracks_raw (
        id BIGSERIAL PRIMARY KEY,
        data JSONB NOT NULL,
        ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    ```
    

**B. Normalized Tables**

-   **`artists` Table:**
    
    SQL
    
    ```
    CREATE TABLE artists (
        artist_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        spotify_url TEXT,
        image_url TEXT,
        genres TEXT[]
    );
    
    ```
    
-   **`albums` Table:**
    
    SQL
    
    ```
    CREATE TABLE albums (
        album_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        release_date DATE,
        album_type TEXT,
        spotify_url TEXT,
        image_url TEXT,
        primary_artist_id TEXT REFERENCES artists(artist_id)
    );
    
    ```
    
-   **`tracks` Table:**
    
    SQL
    
    ```
    CREATE TABLE tracks (
        track_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        duration_ms INTEGER,
        explicit BOOLEAN,
        popularity INTEGER,
        preview_url TEXT,
        spotify_url TEXT,
        album_id TEXT REFERENCES albums(album_id),
        available_markets TEXT[],
        last_played_at TIMESTAMP WITH TIME ZONE
    );
    
    ```
    
-   **`podcast_series` Table:**
    
    SQL
    
    ```
    CREATE TABLE podcast_series (
        series_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        publisher TEXT,
        description TEXT,
        image_url TEXT,
        spotify_url TEXT
    );
    
    ```
    
-   **`podcast_episodes` Table:**
    
    SQL
    
    ```
    CREATE TABLE podcast_episodes (
        episode_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        duration_ms INTEGER,
        explicit BOOLEAN,
        release_date DATE,
        spotify_url TEXT,
        series_id TEXT REFERENCES podcast_series(series_id)
    );
    
    ```
    

**C. `listens` Table**

-   **Purpose:** Central fact table recording individual listening events.
-   **Schema:**
    
    SQL
    
    ```
    CREATE TABLE listens (
        listen_id BIGSERIAL PRIMARY KEY,
        played_at TIMESTAMP WITH TIME ZONE NOT NULL UNIQUE,
        item_type TEXT NOT NULL CHECK (item_type IN ('track', 'episode')),
        track_id TEXT REFERENCES tracks(track_id),
        episode_id TEXT REFERENCES podcast_episodes(episode_id),
        artist_id TEXT REFERENCES artists(artist_id),
        album_id TEXT REFERENCES albums(album_id),
        -- Constraint to ensure exactly one of track_id or episode_id is populated
        CHECK ( (item_type = 'track' AND track_id IS NOT NULL AND episode_id IS NULL) OR
                (item_type = 'episode' AND episode_id IS NOT NULL AND track_id IS NULL) )
    );
    
    ```
    

----------

### IV. API Layer Specification (Cube.js)

**A. Objective:** To provide a robust, performant, and consistent semantic layer and API for the React frontend, abstracting direct database queries.

**B. Technology:** Cube.js.

**C. Modeling:**

-   Cube.js schema files (.js) will be created to map to the PostgreSQL tables defined above.
-   **Measures:**
    -   `listens.count`: Simple count of listens.
    -   `listens.total_duration`: A calculated measure summing `tracks.duration_ms` for music and `podcast_episodes.duration_ms` for podcasts, based on the `item_type`.
-   **Dimensions:** All relevant columns from `artists`, `albums`, `tracks`, `podcast_series`, `podcast_episodes` will be exposed as dimensions (e.g., `artists.name`, `albums.name`, `tracks.name`, `podcast_series.name`, `podcast_episodes.name`, `item_type`).
-   **Time Dimensions:** `listens.played_at` will be modeled as a time dimension, supporting various granularities (day, week, month, quarter, year).
-   **Genre Handling:** Cube.js will be configured to handle `artists.genres` (an array of strings). This will likely involve using Cube.js's `unnest` functionality or custom SQL within the Cube.js model to allow measures to be grouped by individual genres for the "Taste Evolution" feature, effectively attributing listen time to all relevant genres of an artist.
-   **"You Used to Love This" Logic:**
    -   Define two primary measures for artists:
        -   `artists.total_listen_time_past_12_months`: Total duration of listens by an artist in the most recent 12 months.
        -   `artists.total_listen_time_prior_12_months`: Total duration of listens by an artist in the 12-month period immediately preceding the "past 12 months" (i.e., 13-24 months ago).
    -   These measures will involve joining `artists` to `listens` and applying appropriate `timeDimensions` filters within Cube.js. The comparison logic will primarily reside in the frontend using the data from these two measures.

----------

### V. Frontend Dashboard Specification

**A. Objective:** To provide an interactive and intuitive user interface for exploring Spotify listening data.

**B. Technology Stack:**

-   **Framework:** React
-   **UI Library:** Ant Design (AntD)
-   **Charting Library:** Chart.js

**C. Key Features:**

**1. "Taste Evolution Over Time" Visualization**

-   **Type:** Line Chart.
-   **Data:** Shows the trend of total listen time (or count, if preferred) for the top N (e.g., 10 or 15) genres over time.
-   **Aggregation:** Data will be aggregated per week by default, with user-selectable options to group by month or year.
-   **Implementation:** The chart will query Cube.js for `listens.total_duration` (or `listens.count`) grouped by `listens.played_at` (with selected granularity) and `artists.genres` (using the unwound genre dimension). The frontend will then identify the top N genres based on total listen time over the selected period and render a distinct line for each.

**2. "You Used to Love This" Feature**

-   **Type:** List of artists.
-   **Content for each artist:** Thumbnail image, artist name, and a "velocity of listens" statement (e.g., "200 listens within 1 week 2 years ago" - this specific velocity phrasing will require frontend calculation/summary based on underlying data).
-   **Logic for identification:** An artist qualifies for this list if:
    -   Their `total_listen_time_past_12_months` (from Cube.js) is zero (i.e., not listened to in the last year), OR
    -   Their `total_listen_time_past_12_months` is less than 3% of their `total_listen_time_prior_12_months` (from Cube.js).
-   **Implementation:** The frontend will query Cube.js for the `artists.total_listen_time_past_12_months` and `artists.total_listen_time_prior_12_months` measures, potentially for all artists or a filtered set. The comparison logic will be implemented in the React component to display qualifying artists.

**3. Dynamic Query Builder**

-   **Objective:** Allow users to construct custom queries against the data model and visualize results dynamically.
-   **Layout:**
    -   A form section at the top of the page.
    -   A results section at the bottom, displaying generated charts and a table.
-   **Form Components (Ant Design):**
    -   **Measures (Multi-select):** Dropdown populated with available Cube.js measures (`listens.count`, `listens.total_duration`, etc.).
    -   **Dimensions (Multi-select):** Dropdown populated with available Cube.js dimensions (`artists.name`, `albums.name`, `tracks.name`, `item_type`, etc.).
    -   **Time Dimension (Single-select + Granularity + Date Range):**
        -   Dropdown for selecting a time field (e.g., `listens.played_at`).
        -   A separate dropdown for **Granularity/Grouping**: Options will include `no grouping`, `day`, `week`, `month`, `quarter`, `year`.
        -   An Ant Design `DatePicker.RangePicker` component for specifying the date range.
    -   **Filters (Dynamic Add/Remove):** Users can add multiple filter clauses. Each clause will have:
        -   Dropdown to select a Dimension or Measure to filter on.
        -   Dropdown for operator (e.g., `equals`, `notEquals`, `contains`, `gt`, `lt`, `in`, `notIn`).
        -   Input field(s) for the filter value(s).
    -   **"RUN" Button:** A prominent button. A Cube.js query is only executed when this button is clicked.
-   **Query Constraints:**
    -   A query must select at least one Measure or one Dimension.
    -   The `limit` parameter for all Cube.js queries initiated from the query builder will be set to `10000` items.
-   **Results Display:**
    -   **Table Chart (Always Present):** An Ant Design `Table` will always display the raw results of the Cube.js query below the form.
        
    -   **Dynamic Graphical Charts (Chart.js):** One or more charts will be generated based on the user's selections and the following logic:
        
        -   **Chart Type Selection Logic:**
            
            -   **Condition for Time-Series Charts (Line/Stacked Bar):**
                
                -   A Time Dimension is selected (e.g., `listens.played_at`) AND
                -   A **Granularity** is selected that is _not_ `no grouping` (i.e., `day`, `week`, `month`, `quarter`, `year`).
                -   If these conditions are met:
                    -   If **no other Dimensions** are selected (`dimensions.length === 0`) AND **multiple Measures** are selected (`measures.length > 1`): Generate a **Multiple Line Chart** (one line per measure over time).
                    -   If **exactly one other Dimension** is selected (`dimensions.length === 1`) AND **one Measure** is selected (`measures.length === 1`): Generate a **Multiple Line Chart** (one line per dimension value). This chart should display data for the top 12 values of the selected dimension, based on the total value of the selected measure over the queried period.
                    -   Otherwise (complex time + multiple dimensions): Only the **Table Chart** will be displayed.
            -   **Condition for Categorical/Distribution Charts (Bar/Stacked Bar):**
                
                -   NO Time Dimension is selected OR the selected Time Dimension has `no grouping` selected for its granularity.
                -   If these conditions are met:
                    -   If **exactly one Dimension** is selected (`dimensions.length === 1`) AND **multiple Measures** are selected (`measures.length > 1`): Generate a **Stacked Bar Chart**.
                    -   If **exactly one Measure** is selected (`measures.length === 1`) AND **exactly two Dimensions** are selected (`dimensions.length === 2`): Generate a **Stacked Bar Chart**. The chart should display data for the top 12 values of the _second_ selected dimension, based on the total value of the selected measure.
                    -   Otherwise (simple aggregates or complex non-time combinations): Only the **Table Chart** will be displayed.

**D. Error Handling & Loading States (Frontend)**

-   Display clear loading indicators (e.g., Ant Design Spin component) for all data fetches (initial page load, query builder runs).
-   Implement user-friendly error messages for API failures (Cube.js or others) or data processing issues, displayed in a prominent, non-obtrusive way (e.g., Ant Design `message` or `Alert` components).
-   Gracefully handle empty states for charts and tables when no data is returned.

**E. Testing Plan (Frontend)**

-   **Unit Tests:** For individual React components (e.g., dropdowns, filter logic, chart rendering logic in isolation).
-   **Integration Tests:** Test the interaction between React components and the Cube.js client (mocking Cube.js API responses). Verify that form inputs correctly construct Cube.js queries.
-   **End-to-End Tests (e.g., Cypress, Playwright):**
    -   Simulate user interaction with the query builder (selecting measures, dimensions, filters, clicking RUN).
    -   Verify that the correct chart types are rendered based on the logic.
    -   Verify that data is displayed correctly in both charts and tables.
    -   Test key features like "Taste Evolution" and "You Used to Love This" render as expected.
-   **Browser Compatibility:** Test the dashboard on major web browsers (Chrome, Firefox, Edge, Safari).

----------

### VI. Deployment & Operations

-   **Data Ingestion Script:** Deploy as a Python Docker container on Google Cloud Run. Schedule hourly execution using Google Cloud Scheduler.
-   **Database:** Utilize Neon.tech for hosted PostgreSQL. Ensure proper connection strings and credentials are provided to the Cloud Run script and Cube.js instance.
-   **Cube.js API:** Deploy the Cube.js instance as a Docker container on Google Cloud Run or a similar container orchestration service accessible by the frontend.
-   **Frontend Dashboard:** Deploy the React application as static files to **Vercel**.