cube(`Listens`, {
  sql_table: `public.listens`,

  dimensions: {
    listenId: {
      sql: `listen_id`,
      type: `number`,
      primaryKey: true,
      shown: true
    },
    playedAt: {
      sql: `played_at`,
      type: `time`
    },
    itemType: {
      sql: `item_type`,
      type: `string`
    }
  },

  joins: {
    Tracks: {
      sql: `${Listens}.track_id = ${Tracks}.track_id`,
      relationship: `belongsTo`
    },
    Albums: {
      // Joined through Tracks
      sql: `${Tracks}.album_id = ${Albums}.album_id`,
      relationship: `belongsTo`
    },
    Artists: {
      // Joined through Albums
      sql: `${Albums}.primary_artist_id = ${Artists}.artist_id`,
      relationship: `belongsTo`
    }
  },

  measures: {
    count: {
      type: `count`
    },
    totalDurationMs: { // Renamed to avoid conflict if we sum durations directly from other cubes
      // This initial version sums duration_ms from the Tracks table.
      // It will be updated in Module 3.3 to handle podcasts.
      sql: `${Tracks}.duration_ms`,
      type: `sum`,
      title: `Total Listen Duration (ms)`
    }
  },

  preAggregations: {
    // Pre-Aggregations can be added here later for performance optimization
  }
});
