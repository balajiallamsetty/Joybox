import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LanguageProvider } from './components/LanguageContext';
import { AdminAuthProvider } from './components/AdminProtectedRoute';
import AdminProtectedRoute from './components/AdminProtectedRoute';
import LandingPage from './pages/LandingPage';
import MobileBookingPage from './pages/MobileBookingPage';
import PackagesPage from './pages/PackagesPage';
import AddonsPage from './pages/AddonsPage';
import BookingWizardPage from './pages/BookingWizardPage';
import BookingStatusPage from './pages/BookingStatusPage';
import GalleryPage from './pages/GalleryPage';
import ContactPage from './pages/ContactPage';
import TermsPage from './pages/TermsPage';
import PrivacyPage from './pages/PrivacyPage';
import RefundPolicyPage from './pages/RefundPolicyPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminConsolePage from './pages/AdminConsolePage';

export default function App() {
  return (
    <LanguageProvider>
      <AdminAuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Customer Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/landing-2" element={<Navigate to="/" replace />} />
            <Route path="/packages" element={<PackagesPage />} />
            <Route path="/add-ons" element={<AddonsPage />} />
            <Route path="/addons" element={<Navigate to="/add-ons" replace />} />
            <Route path="/book" element={<BookingWizardPage />} />
            <Route path="/booking" element={<BookingWizardPage />} />
            <Route path="/mobile-booking" element={<MobileBookingPage />} />
            <Route path="/booking/:ref" element={<BookingStatusPage />} />
            <Route path="/booking-status" element={<BookingStatusPage />} />
            <Route path="/gallery" element={<GalleryPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/refund-policy" element={<RefundPolicyPage />} />

            {/* Administrator Routes (Phase 7 RBAC & Secure Session) */}
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route
              path="/admin"
              element={
                <AdminProtectedRoute>
                  <AdminConsolePage />
                </AdminProtectedRoute>
              }
            />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AdminAuthProvider>
    </LanguageProvider>
  );
}
