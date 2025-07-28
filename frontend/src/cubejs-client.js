import cube from '@cubejs-client/core';

const cubejsApi = cube(
  process.env.VITE_CUBEJS_API_TOKEN,
  { apiUrl: process.env.VITE_CUBEJS_API_URL }
);

export default cubejsApi;
