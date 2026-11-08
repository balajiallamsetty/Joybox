import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAdminAuth } from '../components/AdminProtectedRoute';

export default function AdminLoginPage() {
  const { user, login } = useAdminAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // If already logged in, redirect directly to admin console
  React.useEffect(() => {
    if (user) {
      const destination = location.state?.from?.pathname || '/admin';
      navigate(destination, { replace: true });
    }
  }, [user, navigate, location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!username.trim() || !password) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    try {
      setLoading(true);
      await login(username.trim(), password);
      const destination = location.state?.from?.pathname || '/admin';
      navigate(destination, { replace: true });
    } catch (err) {
      if (err.code === 'ACCOUNT_LOCKED') {
        setErrorMsg('Account temporarily locked due to repeated failed login attempts. Please try again after 15 minutes or contact support.');
      } else if (err.status === 401 || err.code === 'INVALID_CREDENTIALS') {
        setErrorMsg('Invalid username or password.');
      } else {
        setErrorMsg(err.message || 'Login failed. Please check your credentials and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-between selection:bg-secondary-fixed selection:text-on-secondary-fixed">
      {/* Top Header */}
      <header className="h-16 px-gutter flex items-center justify-between border-b border-outline bg-surface-container-lowest/80 backdrop-blur-md">
        <Link to="/" className="flex items-center gap-space-sm group">
          <div className="w-9 h-9 rounded bg-primary-container flex items-center justify-center text-on-primary-container font-headline-sm text-headline-sm font-bold shadow-[0_2px_8px_rgba(53,16,120,0.18)] transition-transform group-hover:scale-105">
            J
          </div>
          <div className="flex flex-col">
            <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">Joybox</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant font-semibold tracking-wider uppercase">Party Room</span>
          </div>
        </Link>

        <Link
          to="/"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-outline text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors font-label-sm text-label-sm"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          <span>Back to Public Site</span>
        </Link>
      </header>

      {/* Main Login Card */}
      <main className="flex-1 flex items-center justify-center p-gutter">
        <div className="w-full max-w-md bg-surface-container-lowest rounded-2xl shadow-[0_4px_24px_rgba(36,22,61,0.08)] border border-outline p-8 sm:p-10 space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary-container text-on-primary-container shadow-[0_2px_12px_rgba(53,16,120,0.2)] mb-1">
              <span className="material-symbols-outlined text-[24px]">admin_panel_settings</span>
            </div>
            <h1 className="font-headline-sm text-headline-sm font-bold text-on-surface">Operations Console</h1>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Authorized venue managers and staff only.
            </p>
          </div>

          {errorMsg && (
            <div className="p-3.5 rounded-lg bg-error-container text-on-error-container font-body-sm text-body-sm flex items-start gap-2.5 animate-fadeIn">
              <span className="material-symbols-outlined text-error text-[20px] shrink-0 mt-0.5">error</span>
              <span className="leading-snug">{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="username"
                className="block font-label-md text-label-md font-semibold text-on-surface"
              >
                Username
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant text-[20px]">
                  person
                </span>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. kiran"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-surface-container border border-outline text-on-surface placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-body-md text-body-md transition-shadow"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="block font-label-md text-label-md font-semibold text-on-surface"
                >
                  Password
                </label>
              </div>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant text-[20px]">
                  lock
                </span>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-surface-container border border-outline text-on-surface placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-body-md text-body-md transition-shadow"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg bg-primary hover:bg-primary-container text-on-primary font-label-lg text-label-lg font-bold shadow-[0_2px_8px_rgba(30,0,81,0.24)] transition-all flex items-center justify-center gap-2 disabled:bg-surface-container-high disabled:text-on-surface-variant disabled:cursor-not-allowed mt-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 rounded-full border-2 border-on-primary border-t-transparent animate-spin" />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <span className="material-symbols-outlined text-[18px]">login</span>
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center border-t border-outline">
            <p className="font-label-sm text-label-sm text-on-surface-variant">
              Protected by multi-factor rate limiting and secure session rotation.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-4 text-center text-on-surface-variant font-label-sm text-label-sm border-t border-outline">
        © {new Date().getFullYear()} Joybox Party Room, Vadlamudi · Host: Kiran Kumar
      </footer>
    </div>
  );
}

