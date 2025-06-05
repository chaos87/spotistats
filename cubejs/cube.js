// Cube configuration options: https://cube.dev/docs/config
/** @type{ import('@cubejs-backend/server-core').CreateOptions } */
module.exports = {
  driverFactory: () => {
    const dbType = process.env.CUBEJS_DB_TYPE;
    if (dbType === 'postgres') {
      return {
        host: process.env.PG_HOST,
        database: process.env.PG_DATABASE,
        user: process.env.PG_USER,
        password: process.env.PG_PASSWORD,
        port: parseInt(process.env.PG_PORT, 10) || 5432,
        ssl: process.env.PG_SSL === 'true' ? { rejectUnauthorized: false } : false,
      };
    }
    // Add other database types if needed
    // For other DB types, Cube.js will rely on CUBEJS_DB_* environment variables if this function returns an empty object or undefined.
    return undefined; // Explicitly return undefined if not postgres to let Cube.js use its default env var logic for other DBs
  },
  // CUBEJS_DB_TYPE, CUBEJS_API_SECRET, CUBEJS_DEV_MODE, CUBEJS_WEB_SOCKETS
  // are typically picked up from environment variables automatically
  // and do not need to be explicitly set here if already in .env
};
