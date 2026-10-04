import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useGet } from '../lib/hooks';
import { asList } from '../api/client';

const PRIMARY: [string, string, string][] = [['/', 'Home', '🏠'], ['/chat', 'Tutor', '💬'], ['/materials', 'Materials', '📄'], ['/plan', 'Plan', '🗓️']];
const MORE: [string, string][] = [['/courses', 'Courses'], ['/practice', 'Practice'], ['/progress', 'Progress'], ['/notifications', 'Inbox'], ['/profile', 'Profile']];

export function Layout() {
  const { student, logout } = useAuth();
  const [more, setMore] = useState(false);
  const loc = useLocation();
  const n = useGet(`/api/notifications/${student!.id}`);
  const unread = asList(n.data).filter((x: any) => x.read === false).length;
  useEffect(() => setMore(false), [loc.pathname]);
  useEffect(() => {
    if (!more) return;
    const k = (e: KeyboardEvent) => e.key === 'Escape' && setMore(false);
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [more]);
  const link = (to: string, label: string, extra?: React.ReactNode) => (
    <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'on' : '')}>{label}{extra}</NavLink>
  );
  const badge = (to: string) => (to === '/notifications' && unread > 0 ? <b className="dot">{unread}</b> : null);
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Jarvis</div>
        <nav aria-label="Main">
          {PRIMARY.map(([to, l]) => link(to, l))}
          {MORE.map(([to, l]) => link(to, l, badge(to)))}
        </nav>
        <div className="me">
          <div className="who">{student!.full_name || student!.email}</div>
          <button className="linkbtn" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <div className="main">
        <header className="top"><span className="brand sm">Jarvis</span></header>
        <main id="content"><Outlet /></main>
      </div>
      <nav className="tabbar" aria-label="Main">
        {PRIMARY.map(([to, l, ic]) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'on' : '')}><span aria-hidden>{ic}</span>{l}</NavLink>
        ))}
        <button className={more ? 'on' : ''} aria-expanded={more} onClick={() => setMore(!more)}><span aria-hidden>⋯</span>More{unread > 0 && <b className="dot">{unread}</b>}</button>
      </nav>
      {more && (
        <div className="sheet-bg" onClick={() => setMore(false)}>
          <div className="sheet" role="dialog" aria-label="More" onClick={(e) => e.stopPropagation()}>
            {MORE.map(([to, l]) => link(to, l, badge(to)))}
            <button className="linkbtn" onClick={logout}>Sign out ({student!.full_name?.split(' ')[0] || student!.email})</button>
          </div>
        </div>
      )}
    </div>
  );
}
