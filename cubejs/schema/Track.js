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
    durationMs: {
      sql: `duration_ms`,
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
    totalDuration: {
      sql: `duration_ms`,
      type: `sum`
    }
  }
});
