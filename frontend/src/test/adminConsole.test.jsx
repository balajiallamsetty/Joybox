import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import AdminLoginPage from '../pages/AdminLoginPage';
import AdminProtectedRoute, { AdminAuthProvider } from '../components/AdminProtectedRoute';
import { adminApi } from '../services/adminApi';

describe('Admin Authentication & Protected Route Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('validates empty inputs and displays error message on AdminLoginPage', async () => {
    vi.spyOn(adminApi, 'getMe').mockRejectedValue({ status: 401 });

    await act(async () => {
      render(
        <AdminAuthProvider>
          <MemoryRouter initialEntries={['/admin/login']}>
            <AdminLoginPage />
          </MemoryRouter>
        </AdminAuthProvider>
      );
    });

    const submitBtn = screen.getByRole('button', { name: /Sign In/i });
    await act(async () => {
      fireEvent.submit(submitBtn.closest('form'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Please enter both username and password/i)).toBeInTheDocument();
    });
  });

  it('handles invalid credentials gracefully and displays 401 error message', async () => {
    vi.spyOn(adminApi, 'getMe').mockRejectedValue({ status: 401 });
    vi.spyOn(adminApi, 'login').mockRejectedValue({ status: 401, code: 'INVALID_CREDENTIALS' });

    await act(async () => {
      render(
        <AdminAuthProvider>
          <MemoryRouter initialEntries={['/admin/login']}>
            <AdminLoginPage />
          </MemoryRouter>
        </AdminAuthProvider>
      );
    });

    const userInput = screen.getByLabelText(/Username/i);
    const passInput = screen.getByLabelText(/Password/i);
    const submitBtn = screen.getByRole('button', { name: /Sign In/i });

    await act(async () => {
      fireEvent.change(userInput, { target: { value: 'bad_user' } });
      fireEvent.change(passInput, { target: { value: 'wrong_pass' } });
      fireEvent.submit(submitBtn.closest('form'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Invalid username or password/i)).toBeInTheDocument();
    });
  });

  it('displays account lockout warning when account is locked', async () => {
    vi.spyOn(adminApi, 'getMe').mockRejectedValue({ status: 401 });
    vi.spyOn(adminApi, 'login').mockRejectedValue({ status: 423, code: 'ACCOUNT_LOCKED' });

    await act(async () => {
      render(
        <AdminAuthProvider>
          <MemoryRouter initialEntries={['/admin/login']}>
            <AdminLoginPage />
          </MemoryRouter>
        </AdminAuthProvider>
      );
    });

    const userInput = screen.getByLabelText(/Username/i);
    const passInput = screen.getByLabelText(/Password/i);
    const submitBtn = screen.getByRole('button', { name: /Sign In/i });

    await act(async () => {
      fireEvent.change(userInput, { target: { value: 'locked_user' } });
      fireEvent.change(passInput, { target: { value: 'some_pass' } });
      fireEvent.submit(submitBtn.closest('form'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Account temporarily locked due to repeated failed login attempts/i)).toBeInTheDocument();
    });
  });

  it('AdminProtectedRoute redirects unauthenticated visitors to login', async () => {
    vi.spyOn(adminApi, 'getMe').mockRejectedValue({ status: 401 });

    await act(async () => {
      render(
        <AdminAuthProvider>
          <MemoryRouter initialEntries={['/admin']}>
            <Routes>
              <Route path="/admin/login" element={<div>Admin Login Viewport</div>} />
              <Route
                path="/admin"
                element={
                  <AdminProtectedRoute>
                    <div>Secret Admin Dashboard</div>
                  </AdminProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </AdminAuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Admin Login Viewport/i)).toBeInTheDocument();
      expect(screen.queryByText(/Secret Admin Dashboard/i)).not.toBeInTheDocument();
    });
  });

  it('AdminProtectedRoute renders protected child content when authenticated', async () => {
    vi.spyOn(adminApi, 'getMe').mockResolvedValue({
      user: { username: 'sec_owner', role: 'owner', displayName: 'Security Owner' },
      csrfToken: 'valid-csrf-token',
    });

    await act(async () => {
      render(
        <AdminAuthProvider>
          <MemoryRouter initialEntries={['/admin']}>
            <Routes>
              <Route path="/admin/login" element={<div>Admin Login Viewport</div>} />
              <Route
                path="/admin"
                element={
                  <AdminProtectedRoute>
                    <div>Secret Admin Dashboard</div>
                  </AdminProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </AdminAuthProvider>
      );
    });

    await waitFor(() => {
      expect(screen.getByText(/Secret Admin Dashboard/i)).toBeInTheDocument();
    });
  });
});
