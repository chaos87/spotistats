const PostgresDriver = require('@cubejs-backend/postgres-driver');

// Cube configuration options: https://cube.dev/docs/config
/** @type{ import('@cubejs-backend/server-core').CreateOptions } */
module.exports = {
  driverFactory: () => {
    const dbType = process.env.CUBEJS_DB_TYPE;
    if (dbType === 'postgres') {
      return new PostgresDriver({
        host: process.env.PG_HOST,
        database: process.env.PG_DATABASE,
        user: process.env.PG_USER,
        password: process.env.PG_PASSWORD,
        port: parseInt(process.env.PG_PORT, 10) || 5432,
        ssl: process.env.PG_SSL === 'true' ? { rejectUnauthorized: false } : false,
        keepAlive: true, // Enable TCP Keepalives
      });
    }
    return undefined; 
  },
  
  // Enforce token presence even in dev mode by checking the result of Cube.js's internal JWT validation.
  checkAuth: (req, auth) => { // 'auth' is the decoded JWT payload if a valid token was provided and validated by Cube.js
    if (!auth) { 
      // If 'auth' is null or undefined, it means no valid token was processed by Cube.js.
      // This will now cause an error, requiring a token for all API access.
      throw new Error("Authentication required: No valid token provided or token was invalid.");
    }
    // Optional: Log successful authentication for debugging
    // console.log(`Authenticated request with security context: ${JSON.stringify(auth)}`);
  },

  schemaPath: 'model'
};
