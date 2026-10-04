import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { GoogleButton } from '../components/GoogleButton';
import { Spinner } from '../components/ui';

export default function Login() {
  const { status, login } = useAuth();
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  if (status === 'authed') return <Navigate to="/" replace />;
  if (status === 'loading') return <div className="center"><Spinner label="Restoring your session…" /></div>;
  return (
    <div className="center">
      <div className="login">
        <h1>Jarvis</h1>
        <p className="muted">Your courses, notes, practice and deadlines in one place.</p>
        {busy ? <Spinner label="Signing you in…" /> : (
          <GoogleButton
            onToken={async (t) => { setBusy(true); setErr(''); try { await login(t); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } }}
            onError={setErr}
          />
        )}
        {err && <p className="errnote" role="alert">{err}</p>}
      </div>
    </div>
  );
}
