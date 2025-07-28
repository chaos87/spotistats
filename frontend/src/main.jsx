import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import { CubeProvider } from '@cubejs-client/react';
import cubejsApi from './cubejs-client.js';
import 'antd/dist/reset.css';
import './index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CubeProvider cubejsApi={cubejsApi}>
      <ConfigProvider>
        <App />
      </ConfigProvider>
    </CubeProvider>
  </StrictMode>
);
