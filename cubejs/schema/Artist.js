cube(`Artists`, {
  sql_table: `public.artists`,

  dimensions: {
    artistId: {
      sql: `artist_id`,
      type: `string`,
      primaryKey: true,
      shown: true,
      description: "The unique identifier for the artist."
    },
    name: {
      sql: `name`,
      type: `string`,
      description: "The name of the artist."
    },
    spotifyUrl: {
      sql: `spotify_url`,
      type: `string`,
      description: "The Spotify URL of the artist."
    },
    imageUrl: {
      sql: `image_url`,
      type: `string`,
      description: "The URL of the artist's image."
    },
    genres: {
      sql: `genres`,
      type: `string`, // Cube.js will handle array type appropriately
      description: "The genres associated with the artist."
    }
  },

  measures: {
    count: {
      type: `count`,
      description: "The total number of artists."
    }
  }
});
