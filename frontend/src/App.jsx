import { Layout } from 'antd';
import './App.css';

const { Header, Content } = Layout;

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: 'white' }}>
        Spotify Listening Dashboard
      </Header>
      <Content style={{ padding: '0 50px', marginTop: 64 }}>
        <div style={{ background: '#fff', padding: 24, minHeight: 380 }}>
          Welcome to your dashboard!
        </div>
      </Content>
    </Layout>
  );
}

export default App;
