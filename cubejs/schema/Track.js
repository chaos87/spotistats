cube(`Tracks`, {
  sql_table: `public.tracks`,

  dimensions: {
    trackId: {
      sql: `track_id`,
      type: `string`,
      primaryKey: true,
      shown: true,
      description: "The unique identifier for the track."
    },
    name: {
      sql: `name`,
      type: `string`,
      description: "The name of the track."
    },
    durationSeconds: { // Renamed from durationMs
      sql: `duration_ms / 1000.0`, // Convert to seconds
      type: `number`,
      description: "The duration of the track in seconds."
    },
    explicit: {
      sql: `explicit`,
      type: `boolean`,
      description: "Indicates if the track has explicit content."
    },
    popularity: {
      sql: `popularity`,
      type: `number`,
      description: "The popularity of the track (0-100)."
    },
    previewUrl: {
      sql: `preview_url`,
      type: `string`,
      description: "The URL of the track's preview."
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`,
      description: "The Spotify URL of the track."
    },
    availableMarkets: {
      sql: `available_markets`,
      type: `string`, // Cube.js will handle array type appropriately
      description: "A list of markets where the track is available."
    },
    lastPlayedAt: {
      sql: `last_played_at`,
      type: `time`,
      description: "The timestamp when the track was last played."
    }
  },

  joins: {
    Albums: {
      sql: `${Tracks}.album_id = ${Albums}.album_id`,
      relationship: `belongsTo`
    }
  },

  measures: {
    count: {
      type: `count`,
      description: "The total number of tracks."
    },
    totalDurationSeconds: { // Renamed from totalDuration
      sql: `duration_ms / 1000.0`, // Use the original ms value for sum then implicitly it's in seconds
      type: `sum`,
      format: `decimal(2)`, // Format to two decimal places
      description: "The total duration of all tracks in seconds."
    }
  }
});
