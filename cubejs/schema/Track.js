cube(`Tracks`, {
  sql_table: `public.tracks`,

  dimensions: {
    trackId: {
      sql: `track_id`,
      type: `string`,
      primaryKey: true,
      shown: true
    },
    name: {
      sql: `name`,
      type: `string`
    },
    durationSeconds: { // Renamed from durationMs
      sql: `duration_ms / 1000.0`, // Convert to seconds
      type: `number`
    },
    explicit: {
      sql: `explicit`,
      type: `boolean`
    },
    popularity: {
      sql: `popularity`,
      type: `number`
    },
    previewUrl: {
      sql: `preview_url`,
      type: `string`
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`
    },
    availableMarkets: {
      sql: `available_markets`,
      type: `string` // Cube.js will handle array type appropriately
    },
    lastPlayedAt: {
      sql: `last_played_at`,
      type: `time`
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
      type: `count`
    },
    totalDurationSeconds: { // Renamed from totalDuration
      sql: `duration_ms / 1000.0`, // Use the original ms value for sum then implicitly it's in seconds
      type: `sum`,
      format: `decimal(2)` // Format to two decimal places
    }
  }
});
