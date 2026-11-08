import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { adminApi } from '../services/adminApi';

const AdminAuthContext = createContext(null);

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider or AdminProtectedRoute');
  }
  return context;
}

export function AdminAuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [csrfToken, setCsrfToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getMe();
      if (res && res.user) {
        setUser(res.user);
        setCsrfToken(res.csrfToken || null);
      } else {
        setUser(null);
        setCsrfToken(null);
      }
    } catch (err) {
      setUser(null);
      setCsrfToken(null);
      // 401 is normal when not logged in
      if (err.status !== 401) {
        setError(err.message || 'Authentication check failed');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (username, password) => {
    const res = await adminApi.login({ username, password });
    if (res && res.user) {
      setUser(res.user);
      setCsrfToken(res.csrfToken || null);
    }
    return res;
  };

  const logout = async () => {
    try {
      await adminApi.logout(csrfToken);
    } catch {
      // ignore network errors on logout
    } finally {
      setUser(null);
      setCsrfToken(null);
    }
  };

  return (
    <AdminAuthContext.Provider value={{ user, csrfToken, loading, error, login, logout, refreshUser: checkAuth }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export default function AdminProtectedRoute({ children, requiredRoles = [] }) {
  const { user, loading } = useAdminAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="w-full min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary-container border-t-primary animate-spin" />
          <p className="font-label-md text-label-md text-on-surface-variant font-medium">
            Verifying Admin Session...
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  if (requiredRoles.length > 0 && !requiredRoles.includes(user.role)) {
    return (
      <div className="w-full min-h-screen bg-surface flex items-center justify-center p-gutter">
        <div className="max-w-md w-full p-6 rounded-2xl bg-surface-container-lowest shadow-md text-center">
          <span className="material-symbols-outlined text-error text-5xl mb-2">lock_person</span>
          <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Access Restricted</h2>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-2 mb-6">
            Your role ({user.role}) does not have permission to view this section.
          </p>
          <a
            href="/admin"
            className="inline-block px-4 py-2 rounded bg-primary text-on-primary font-semibold text-sm"
          >
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  return children;
}

