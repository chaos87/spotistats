cube(`Albums`, {
  sql_table: `public.albums`,

  dimensions: {
    albumId: {
      sql: `album_id`,
      type: `string`,
      primaryKey: true,
      shown: true
    },
    name: {
      sql: `name`,
      type: `string`
    },
    releaseDate: {
      sql: `release_date`,
      type: `time`
    },
    albumType: {
      sql: `album_type`,
      type: `string`
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`
    },
    imageUrl: {
      sql: `image_url`,
      type: `string`
    }
  },

  joins: {
    Artists: {
      sql: `${Albums}.primary_artist_id = ${Artists}.artist_id`,
      relationship: `belongsTo`
    }
  },

  measures: {
    count: {
      type: `count`
    }
  }
});
