cube(`Albums`, {
  sql_table: `public.albums`,

  dimensions: {
    albumId: {
      sql: `album_id`,
      type: `string`,
      primaryKey: true,
      shown: true,
      description: "The unique identifier for the album."
    },
    name: {
      sql: `name`,
      type: `string`,
      description: "The name of the album."
    },
    releaseDate: {
      sql: `release_date`,
      type: `time`,
      description: "The release date of the album."
    },
    albumType: {
      sql: `album_type`,
      type: `string`,
      description: "The type of the album (e.g., album, single)."
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`,
      description: "The Spotify URL of the album."
    },
    imageUrl: {
      sql: `image_url`,
      type: `string`,
      description: "The URL of the album's cover art."
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
      type: `count`,
      description: "The total number of albums."
    }
  }
});
