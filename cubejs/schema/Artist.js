cube(`Artists`, {
  sql_table: `public.artists`,

  dimensions: {
    artistId: {
      sql: `artist_id`,
      type: `string`,
      primaryKey: true,
      shown: true
    },
    name: {
      sql: `name`,
      type: `string`
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`
    },
    imageUrl: {
      sql: `image_url`,
      type: `string`
    },
    genres: {
      sql: `genres`,
      type: `string` // Cube.js will handle array type appropriately
    }
  },

  measures: {
    count: {
      type: `count`
    }
  }
});
