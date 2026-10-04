import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { Layout } from './components/Layout';
import { Spinner } from './components/ui';
import Login from './pages/Login';
import Home from './pages/Home';
import Courses from './pages/Courses';
import Materials from './pages/Materials';
import Chat from './pages/Chat';
import Plan from './pages/Plan';
import Practice from './pages/Practice';
import Progress from './pages/Progress';
import Inbox from './pages/Inbox';
import Profile from './pages/Profile';

function Protected() {
  const { status } = useAuth();
  if (status === 'loading') return <div className="center"><Spinner label="Restoring your session…" /></div>;
  if (status === 'anon') return <Navigate to="/login" replace />;
  return <Layout />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Protected />}>
          <Route index element={<Home />} />
          <Route path="courses" element={<Courses />} />
          <Route path="materials" element={<Materials />} />
          <Route path="chat" element={<Chat />} />
          <Route path="plan" element={<Plan />} />
          <Route path="practice" element={<Practice />} />
          <Route path="progress" element={<Progress />} />
          <Route path="notifications" element={<Inbox />} />
          <Route path="profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
