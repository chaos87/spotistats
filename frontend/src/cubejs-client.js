import cube from '@cubejs-client/core';

const cubejsApi = cube(
  import.meta.env.VITE_CUBEJS_API_TOKEN,
  { apiUrl: import.meta.env.VITE_CUBEJS_API_URL }
);

export default cubejsApi;
