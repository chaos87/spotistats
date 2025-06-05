cube(`Listens`, {
  sql_table: `public.listens`,

  dimensions: {
    listenId: {
      sql: `listen_id`,
      type: `number`,
      primaryKey: true,
      shown: true,
      description: "The unique identifier for the listen event."
    },
    playedAt: {
      sql: `played_at`,
      type: `time`,
      description: "The timestamp when the listen event occurred."
    },
    itemType: {
      sql: `item_type`,
      type: `string`,
      description: "The type of item listened to (e.g., track, podcast episode)."
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
      type: `count`,
      description: "The total number of listen events."
    },
    totalDurationSeconds: { // Renamed from totalDurationMs
      // This sums the duration in seconds from the Tracks table.
      // It will be updated in Module 3.3 to handle podcasts.
      sql: `${Tracks}.durationSeconds`, // References the updated dimension in Tracks
      type: `sum`,
      format: `decimal(2)`, // Format to two decimal places
      title: `Total Listen Duration (s)`,
      description: "The total duration of all listen events in seconds."
    }
  },

  preAggregations: {
    // Pre-Aggregations can be added here later for performance optimization
  }
});
