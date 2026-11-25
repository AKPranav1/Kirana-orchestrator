import React, { useEffect, useState } from 'react';
import { API_BASE } from '../config';

/** Single-store operator access; the backend remains the authorization authority. */
export default function OperatorAccess({ children }: { children: React.ReactNode }) {
  const [required, setRequired] = useState(false);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState('');
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    let active = true;
    const auth = () => { setRequired(true); sessionStorage.removeItem('kirana_operator_token'); };
    const failed = (event: Event) => setNotice((event as CustomEvent<string>).detail);
    window.addEventListener('kirana-auth-required', auth);
    window.addEventListener('kirana-api-error', failed);
    const key = sessionStorage.getItem('kirana_operator_token');
    fetch(`${API_BASE}/ready`, { headers: key ? { 'X-API-Key': key } : {} })
      .then(response => {
        if (!active) return;
        if (response.status === 401) auth();
        else if (!response.ok) setNotice('The backend is unavailable. Check the connection and refresh.');
      })
      .catch(() => { if (active) setNotice('Cannot connect to the backend. Check the connection and refresh.'); })
      .finally(() => { if (active) setChecking(false); });
    return () => {
      active = false;
      window.removeEventListener('kirana-auth-required', auth);
      window.removeEventListener('kirana-api-error', failed);
    };
  }, []);
  if (checking) return <main className="min-h-screen bg-[#0A0A0A] text-white p-6"><p role="status">Connecting to your store...</p></main>;
  if (required) return (
    <main className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center p-6">
      <form className="w-full max-w-md space-y-4" onSubmit={async event => {
        event.preventDefault(); setPending(true); setError('');
        try {
          const response = await fetch(`${API_BASE}/ready`, { headers: { 'X-API-Key': token } });
          if (!response.ok) throw new Error(response.status === 401 ? 'The access key was not accepted.' : 'The backend is unavailable. Try again.');
          sessionStorage.setItem('kirana_operator_token', token);
          setToken(''); setNotice(''); setRequired(false);
        } catch (problem) {
          setError(problem instanceof Error ? problem.message : 'Unable to connect. Try again.');
        } finally { setPending(false); }
      }}>
        <h1 className="text-xl font-semibold">Open your Kirana store</h1>
        <p className="text-sm text-[#bcbcbc]">Enter the operator access key supplied by the store administrator.</p>
        <label htmlFor="operator-key" className="block text-sm">Access key</label>
        <input id="operator-key" type="password" autoComplete="current-password" required value={token}
          onChange={event => setToken(event.target.value)} aria-describedby={error ? 'operator-error' : undefined}
          className="w-full min-h-11 bg-[#121212] border border-[#888888] rounded p-3 focus:outline-2 focus:outline-white" />
        {error && <p id="operator-error" role="alert" className="text-sm text-red-300">{error}</p>}
        <button disabled={pending} className="min-h-11 w-full rounded bg-white text-black px-4 py-3 disabled:opacity-60">{pending ? 'Connecting...' : 'Open store'}</button>
      </form>
    </main>
  );
  return <>{notice && <div role="alert" className="fixed top-0 inset-x-0 z-[100] bg-amber-950 text-amber-100 p-3 text-sm flex justify-between gap-4">
    <span>{notice}</span><button aria-label="Dismiss connection message" onClick={() => setNotice('')}>Dismiss</button>
  </div>}{children}</>;
}
