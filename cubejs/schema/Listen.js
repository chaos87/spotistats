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
    totalDurationSeconds: { // Renamed from totalDurationMs
      // This sums the duration in seconds from the Tracks table.
      // It will be updated in Module 3.3 to handle podcasts.
      sql: `${Tracks}.durationSeconds`, // References the updated dimension in Tracks
      type: `sum`,
      format: `decimal(2)`, // Format to two decimal places
      title: `Total Listen Duration (s)`
    }
  },

  preAggregations: {
    // Pre-Aggregations can be added here later for performance optimization
  }
});
