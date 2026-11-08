import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../components/AdminProtectedRoute';
import { adminApi } from '../services/adminApi';

function formatCurrency(paise) {
  if (paise === undefined || paise === null) return '₹0';
  return `₹${(paise / 100).toLocaleString('en-IN')}`;
}

function formatIST(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return isoString;
  }
}

export default function AdminConsolePage() {
  const { user, csrfToken, logout } = useAdminAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const handleTabClick = (tab) => {
    setActiveTab(tab);
    setMobileNavOpen(false);
  };
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState(null);
  const [successBanner, setSuccessBanner] = useState(null);

  // Data states
  const [dashboardData, setDashboardData] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [bookingFilterStatus, setBookingFilterStatus] = useState('');
  const [bookingSearch, setBookingSearch] = useState('');
  const [selectedBooking, setSelectedBooking] = useState(null);

  const [inquiries, setInquiries] = useState([]);
  const [inquiryFilterStatus, setInquiryFilterStatus] = useState('');

  const [packages, setPackages] = useState([]);
  const [addOns, setAddOns] = useState([]);

  const [availabilityBlocks, setAvailabilityBlocks] = useState([]);
  const [newBlock, setNewBlock] = useState({
    roomId: 'main',
    reason: '',
    slotStart: '',
    slotEnd: '',
  });

  const [payments, setPayments] = useState([]);
  const [paymentReviewFilter, setPaymentReviewFilter] = useState('');

  const [auditLogs, setAuditLogs] = useState([]);

  // Modals & Panels
  const [showManualBookingModal, setShowManualBookingModal] = useState(false);
  const [manualBookingForm, setManualBookingForm] = useState({
    customerName: '',
    customerPhone: '',
    customerEmail: '',
    packageSlug: 'gold',
    slotStart: '',
    slotEnd: '',
    advancePaidPaise: 50000,
    paymentMethod: 'offline_cash',
    internalNotes: '',
  });

  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [pwdForm, setPwdForm] = useState({ currentPassword: '', newPassword: '' });

  // Notifications
  const notifySuccess = (msg) => {
    setSuccessBanner(msg);
    setTimeout(() => setSuccessBanner(null), 5000);
  };
  const notifyError = (msg) => {
    setErrorBanner(msg);
    setTimeout(() => setErrorBanner(null), 7000);
  };

  // Fetch Dashboard
  const loadDashboard = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminApi.getDashboard();
      setDashboardData(data);
    } catch (err) {
      notifyError(err.message || 'Failed to load dashboard KPIs');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch Bookings
  const loadBookings = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getBookings({
        status: bookingFilterStatus,
        search: bookingSearch,
      });
      setBookings(res?.bookings || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load bookings');
    } finally {
      setLoading(false);
    }
  }, [bookingFilterStatus, bookingSearch]);

  // Fetch Inquiries
  const loadInquiries = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getInquiries({ status: inquiryFilterStatus });
      setInquiries(res?.inquiries || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load inquiries');
    } finally {
      setLoading(false);
    }
  }, [inquiryFilterStatus]);

  // Fetch Catalog
  const loadCatalog = useCallback(async () => {
    try {
      setLoading(true);
      const [pkgs, addons] = await Promise.all([
        adminApi.getPackages(),
        adminApi.getAddOns(),
      ]);
      setPackages(pkgs?.packages || []);
      setAddOns(addons?.addOns || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load catalog');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch Availability Blocks
  const loadBlocks = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getAvailabilityBlocks();
      setAvailabilityBlocks(res?.availabilityBlocks || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load availability blocks');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch Payments
  const loadPayments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getPayments({
        needsReview: paymentReviewFilter,
      });
      setPayments(res?.payments || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load payments');
    } finally {
      setLoading(false);
    }
  }, [paymentReviewFilter]);

  // Fetch Audit Logs
  const loadAuditLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getAuditLogs({ limit: 50 });
      setAuditLogs(res?.auditLogs || []);
    } catch (err) {
      notifyError(err.message || 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, []);

  // Tab switch effect
  useEffect(() => {
    if (activeTab === 'dashboard') loadDashboard();
    else if (activeTab === 'schedule') loadBookings();
    else if (activeTab === 'inquiries') loadInquiries();
    else if (activeTab === 'packages') loadCatalog();
    else if (activeTab === 'blocks') loadBlocks();
    else if (activeTab === 'payments') loadPayments();
    else if (activeTab === 'audit') loadAuditLogs();
  }, [
    activeTab,
    loadDashboard,
    loadBookings,
    loadInquiries,
    loadCatalog,
    loadBlocks,
    loadPayments,
    loadAuditLogs,
  ]);

  // Handle Logout
  const handleLogout = async () => {
    await logout();
    navigate('/admin/login', { replace: true });
  };

  // Handle Manual Booking Submit
  const handleCreateManualBooking = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        customerName: manualBookingForm.customerName.trim(),
        customerPhone: manualBookingForm.customerPhone.trim(),
        customerEmail: manualBookingForm.customerEmail.trim() || undefined,
        packageSlug: manualBookingForm.packageSlug,
        slotStart: new Date(manualBookingForm.slotStart).toISOString(),
        slotEnd: new Date(manualBookingForm.slotEnd).toISOString(),
        advancePaidPaise: Number(manualBookingForm.advancePaidPaise),
        paymentMethod: manualBookingForm.paymentMethod,
        internalNotes: manualBookingForm.internalNotes.trim(),
      };
      const res = await adminApi.createManualBooking(payload, csrfToken);
      notifySuccess(`Booking created successfully! Reference: ${res.booking.bookingReference}`);
      setShowManualBookingModal(false);
      setManualBookingForm({
        customerName: '',
        customerPhone: '',
        customerEmail: '',
        packageSlug: 'gold',
        slotStart: '',
        slotEnd: '',
        advancePaidPaise: 50000,
        paymentMethod: 'offline_cash',
        internalNotes: '',
      });
      loadBookings();
    } catch (err) {
      notifyError(err.message || 'Failed to create manual booking');
    }
  };

  // Handle Booking Status Update
  const handleUpdateBookingStatus = async (bookingRef, newStatus, cancelReason = '') => {
    try {
      await adminApi.updateBooking(bookingRef, { status: newStatus, internalNotes: cancelReason }, csrfToken);
      notifySuccess(`Booking ${bookingRef} status updated to ${newStatus}`);
      loadBookings();
      if (selectedBooking && selectedBooking.bookingReference === bookingRef) {
        setSelectedBooking((prev) => ({ ...prev, status: newStatus }));
      }
    } catch (err) {
      notifyError(err.message || 'Failed to update booking status');
    }
  };

  // Handle Inquiry Status Update
  const handleUpdateInquiryStatus = async (id, status) => {
    try {
      await adminApi.updateInquiry(id, { status }, csrfToken);
      notifySuccess('Inquiry status updated');
      loadInquiries();
    } catch (err) {
      notifyError(err.message || 'Failed to update inquiry');
    }
  };

  // Handle Create Availability Block
  const handleCreateBlock = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        roomId: newBlock.roomId,
        reason: newBlock.reason.trim(),
        slotStart: new Date(newBlock.slotStart).toISOString(),
        slotEnd: new Date(newBlock.slotEnd).toISOString(),
      };
      await adminApi.createAvailabilityBlock(payload, csrfToken);
      notifySuccess('Availability block created. Slots locked atomically.');
      setNewBlock({ roomId: 'main', reason: '', slotStart: '', slotEnd: '' });
      loadBlocks();
    } catch (err) {
      notifyError(err.message || 'Failed to create availability block');
    }
  };

  // Handle Delete Availability Block
  const handleDeleteBlock = async (id) => {
    if (!window.confirm('Are you sure you want to release this availability block?')) return;
    try {
      await adminApi.deleteAvailabilityBlock(id, csrfToken);
      notifySuccess('Availability block removed and slots released.');
      loadBlocks();
    } catch (err) {
      notifyError(err.message || 'Failed to delete availability block');
    }
  };

  // Handle Retry Refund
  const handleRetryRefund = async (paymentId) => {
    try {
      await adminApi.retryRefund(paymentId, csrfToken);
      notifySuccess('Refund retry initiated successfully.');
      loadPayments();
    } catch (err) {
      notifyError(err.message || 'Refund retry failed');
    }
  };

  // Handle Change Password
  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!pwdForm.currentPassword) {
      notifyError('Please enter your current password.');
      return;
    }
    if (pwdForm.newPassword.length < 10) {
      notifyError('New password must be at least 10 characters long.');
      return;
    }
    if (
      !/[A-Z]/.test(pwdForm.newPassword) ||
      !/[a-z]/.test(pwdForm.newPassword) ||
      !/[0-9]/.test(pwdForm.newPassword) ||
      !/[!@#$%^&*(),.?":{}|<>]/.test(pwdForm.newPassword)
    ) {
      notifyError('New password must contain uppercase, lowercase, number, and special character.');
      return;
    }
    try {
      await adminApi.changePassword({
        currentPassword: pwdForm.currentPassword,
        oldPassword: pwdForm.currentPassword,
        newPassword: pwdForm.newPassword,
      }, csrfToken);
      notifySuccess('Password changed successfully.');
      setShowChangePasswordModal(false);
      setPwdForm({ currentPassword: '', newPassword: '' });
    } catch (err) {
      notifyError(err.message || 'Failed to change password');
    }
  };

  return (
    <div className="w-full min-h-screen bg-surface flex selection:bg-secondary-fixed selection:text-on-secondary-fixed">
      {/* Mobile Backdrop */}
      {mobileNavOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      {/* Sidebar Navigation */}
      <aside className={`fixed left-0 top-0 h-full w-72 bg-surface-container-low shadow-[0_1px_8px_rgba(0,0,0,0.04)] z-50 flex flex-col justify-between transition-transform duration-200 ${
        mobileNavOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      }`}>
        <div className="flex flex-col">
          <div className="h-16 px-gutter flex items-center justify-between border-b border-outline bg-surface-container-lowest/60">
            <div className="flex items-center gap-space-sm">
              <div className="w-9 h-9 rounded bg-primary-container flex items-center justify-center text-on-primary-container font-headline-sm text-headline-sm font-bold shadow-[0_2px_8px_rgba(53,16,120,0.18)]">
                J
              </div>
              <div className="flex flex-col">
                <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">Joybox</span>
                <span className="font-label-sm text-label-sm text-on-surface-variant font-semibold tracking-wider uppercase">Admin Console</span>
              </div>
            </div>
            <span className="px-space-xs py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-bold uppercase">
              {user?.role || 'HQ'}
            </span>
          </div>

          <div className="px-gutter pt-space-md pb-space-xs">
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider font-bold">
              Operations Center
            </span>
          </div>

          <nav className="flex flex-col gap-1 px-space-sm">
            <button
              type="button"
              onClick={() => handleTabClick('dashboard')}
              className={`w-full text-left flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">space_dashboard</span>
              <span>Dashboard &amp; KPIs</span>
            </button>

            <button
              type="button"
              onClick={() => handleTabClick('schedule')}
              className={`w-full text-left flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'schedule'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">calendar_month</span>
              <span>Schedule &amp; Bookings</span>
            </button>

            <button
              type="button"
              onClick={() => handleTabClick('inquiries')}
              className={`w-full text-left flex items-center justify-between px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'inquiries'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[20px]">mark_email_unread</span>
                <span>Inquiries &amp; Leads</span>
              </div>
              {dashboardData?.pendingInquiriesCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-secondary-container text-on-secondary-container font-label-sm text-label-sm font-bold">
                  {dashboardData.pendingInquiriesCount}
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => handleTabClick('packages')}
              className={`w-full text-left flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'packages'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">loyalty</span>
              <span>Packages &amp; Add-ons</span>
            </button>

            <button
              type="button"
              onClick={() => handleTabClick('blocks')}
              className={`w-full text-left flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'blocks'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">block</span>
              <span>Hall Blocks &amp; Slots</span>
            </button>

            <button
              type="button"
              onClick={() => handleTabClick('payments')}
              className={`w-full text-left flex items-center justify-between px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                activeTab === 'payments'
                  ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[20px]">payments</span>
                <span>Payments &amp; Refunds</span>
              </div>
              {dashboardData?.needsReviewCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-error-container text-on-error-container font-label-sm text-label-sm font-bold">
                  !
                </span>
              )}
            </button>

            {(user?.role === 'owner' || user?.role === 'manager') && (
              <button
                type="button"
                onClick={() => handleTabClick('audit')}
                className={`w-full text-left flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md transition-colors ${
                  activeTab === 'audit'
                    ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_2px_8px_rgba(53,16,120,0.12)]'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                }`}
              >
                <span className="material-symbols-outlined text-[20px]">receipt_long</span>
                <span>Audit Logs</span>
              </button>
            )}

            <Link
              to="/"
              className="flex items-center gap-space-sm px-space-sm py-2.5 rounded font-label-md text-label-md text-secondary hover:bg-surface-container-high transition-colors mt-4"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
              <span>Back to Public Website</span>
            </Link>
          </nav>
        </div>
      </aside>

      {/* Main Content Pane */}
      <div className="lg:pl-72 pl-0 w-full flex flex-col min-h-screen">
        {/* Top Header */}
        <header className="h-16 bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)] z-40 flex items-center justify-between px-gutter border-b border-outline sticky top-0">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileNavOpen(!mobileNavOpen)}
              className="lg:hidden p-2 rounded text-primary hover:bg-surface-container"
              aria-label="Toggle navigation menu"
            >
              <span className="material-symbols-outlined text-[24px]">menu</span>
            </button>
            <div className="hidden sm:flex items-center gap-space-xs px-3 py-1.5 rounded-full bg-surface-container border border-outline text-on-surface font-label-sm text-label-sm">
              <span className="material-symbols-outlined text-secondary text-[18px]">storefront</span>
              <span className="font-semibold">Vadlamudi Venue</span>
              <span className="text-on-surface-variant">(Beside Durga Mart)</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary">
                <span className="material-symbols-outlined text-sm">person</span>
              </div>
              <div className="flex flex-col text-right">
                <span className="text-xs font-bold text-primary">
                  {user?.displayName || user?.username} ({user?.role})
                </span>
                <span className="text-[11px] text-on-surface-variant">Host: Kiran Kumar</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowChangePasswordModal(true)}
              title="Change Password"
              className="p-1.5 rounded hover:bg-surface-container-high text-on-surface-variant transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">key</span>
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-surface-container border border-outline hover:bg-surface-container-high text-on-surface font-label-sm text-label-sm font-semibold transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">logout</span>
              <span>Sign Out</span>
            </button>
          </div>
        </header>

        {loading && (
          <div className="mx-gutter mt-2 h-1 bg-primary/20 overflow-hidden rounded-full">
            <div className="h-full bg-primary animate-pulse w-full" />
          </div>
        )}

        {/* Alerts & Toasts */}
        {errorBanner && (
          <div className="mx-gutter mt-4 p-3.5 rounded-lg bg-error-container text-on-error-container text-sm font-medium flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-error text-[20px]">error</span>
              <span>{errorBanner}</span>
            </div>
            <button type="button" onClick={() => setErrorBanner(null)} className="text-on-error-container hover:opacity-75">
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>
        )}

        {successBanner && (
          <div className="mx-gutter mt-4 p-3.5 rounded-lg bg-[#dcfce7] text-[#166534] text-sm font-medium flex items-center justify-between border border-[#bbf7d0]">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">check_circle</span>
              <span>{successBanner}</span>
            </div>
            <button type="button" onClick={() => setSuccessBanner(null)} className="hover:opacity-75">
              <span className="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>
        )}

        {/* Main Body */}
        <main className="p-gutter flex-1 space-y-6">
          {/* TAB: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6 animate-fadeIn">
              {/* Needs Review Urgent Warning */}
              {dashboardData?.needsReviewCount > 0 && (
                <div className="p-4 rounded-xl bg-error-container text-on-error-container flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-error text-2xl">warning</span>
                    <div>
                      <p className="font-bold">Attention: {dashboardData.needsReviewCount} Payment(s) Need Review</p>
                      <p className="text-xs">There are automated refund failures or booking conflict anomalies requiring manual resolution.</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveTab('payments');
                      setPaymentReviewFilter('true');
                    }}
                    className="px-3 py-1.5 rounded bg-error text-on-error font-semibold text-xs shadow-sm hover:opacity-90"
                  >
                    View in Payments
                  </button>
                </div>
              )}

              {/* Operational KPI Ribbon */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-space-md">
                <div className="p-space-md rounded-lg bg-surface-container-lowest shadow-sm flex flex-col justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-bold">Today's Bookings</span>
                  <div className="my-2 flex items-baseline gap-2">
                    <span className="font-headline-md text-headline-md font-bold text-primary">
                      {dashboardData?.todayBookingsCount ?? '0'}
                    </span>
                    <span className="text-xs text-secondary font-bold">Confirmed</span>
                  </div>
                  <span className="text-xs text-on-surface-variant">Scheduled for today</span>
                </div>

                <div className="p-space-md rounded-lg bg-surface-container-lowest shadow-sm flex flex-col justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-bold">Monthly Revenue</span>
                  <div className="my-2 flex items-baseline gap-2">
                    <span className="font-headline-md text-headline-md font-bold text-[#166534]">
                      {formatCurrency(dashboardData?.totalRevenuePaise ?? 0)}
                    </span>
                  </div>
                  <span className="text-xs text-on-surface-variant">Advance payments collected this month</span>
                </div>

                <div className="p-space-md rounded-lg bg-surface-container-lowest shadow-sm flex flex-col justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-bold">Monthly Quota Cycle</span>
                  <div className="my-2 flex items-baseline gap-2">
                    <span className="font-headline-md text-headline-md font-bold text-primary">
                      {dashboardData?.promoUsageCount ?? 0}
                    </span>
                    <span className="text-xs text-secondary font-bold">Promo redemptions</span>
                  </div>
                  <span className="text-xs text-on-surface-variant">Resets 1st of every calendar month</span>
                </div>

                <div className="p-space-md rounded-lg bg-surface-container-lowest shadow-sm flex flex-col justify-between">
                  <span className="font-label-sm text-label-sm text-on-surface-variant uppercase font-bold">Pending Inquiries</span>
                  <div className="my-2 flex items-baseline gap-2">
                    <span className="font-headline-md text-headline-md font-bold text-primary">
                      {dashboardData?.pendingInquiriesCount ?? 0}
                    </span>
                    <span className="text-xs text-secondary font-bold">Unresponded</span>
                  </div>
                  <span className="text-xs text-on-surface-variant">Leads requiring follow-up</span>
                </div>
              </div>

              {/* Recent Bookings Table */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">Recent Reservations</h3>
                    <p className="text-xs text-on-surface-variant">Latest bookings made online or manually at the venue</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveTab('schedule')}
                    className="text-xs font-bold text-primary hover:underline"
                  >
                    View All &rarr;
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-outline text-on-surface-variant text-xs uppercase font-semibold">
                      <tr>
                        <th className="pb-3">Reference</th>
                        <th className="pb-3">Customer</th>
                        <th className="pb-3">Slot Time (IST)</th>
                        <th className="pb-3">Package</th>
                        <th className="pb-3">Total / Advance</th>
                        <th className="pb-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/20">
                      {(dashboardData?.recentBookings || []).length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-6 text-center text-on-surface-variant">
                            No reservations recorded yet.
                          </td>
                        </tr>
                      ) : (
                        dashboardData.recentBookings.map((b) => (
                          <tr key={b._id || b.bookingReference} className="hover:bg-surface-container/50">
                            <td className="py-3 font-mono font-bold text-primary">{b.bookingReference}</td>
                            <td className="py-3">
                              <p className="font-semibold text-on-surface">{b.customerName}</p>
                              <p className="text-xs text-on-surface-variant">{b.customerPhone}</p>
                            </td>
                            <td className="py-3 text-xs">
                              <p>{formatIST(b.slotStart)}</p>
                              <p className="text-on-surface-variant">to {formatIST(b.slotEnd)}</p>
                            </td>
                            <td className="py-3 capitalize">{b.packageSlug}</td>
                            <td className="py-3 text-xs">
                              <p className="font-semibold">{formatCurrency(b.totalPricePaise)}</p>
                              <p className="text-on-surface-variant">Adv: {formatCurrency(b.advancePaidPaise)}</p>
                            </td>
                            <td className="py-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                                  b.status === 'confirmed'
                                    ? 'bg-[#dcfce7] text-[#166534]'
                                    : b.status === 'pending'
                                    ? 'bg-[#fef9c3] text-[#854d0e]'
                                    : 'bg-surface-container-high text-on-surface-variant'
                                }`}
                              >
                                {b.status}
                              </span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB: SCHEDULE & BOOKINGS */}
          {activeTab === 'schedule' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Bookings &amp; Schedule</h2>
                  <p className="text-xs text-on-surface-variant">Manage customer reservations, inspect audit trails, and create offline bookings</p>
                </div>

                <button
                  type="button"
                  onClick={() => setShowManualBookingModal(true)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-bold shadow-sm hover:bg-primary-container transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">add</span>
                  <span>New Manual Booking</span>
                </button>
              </div>

              {/* Filters */}
              <div className="p-4 rounded-xl bg-surface-container-lowest shadow-sm flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-[200px]">
                  <input
                    type="text"
                    value={bookingSearch}
                    onChange={(e) => setBookingSearch(e.target.value)}
                    placeholder="Search customer, phone, or reference..."
                    className="w-full px-3 py-1.5 rounded-lg bg-surface-container border border-outline text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div>
                  <select
                    value={bookingFilterStatus}
                    onChange={(e) => setBookingFilterStatus(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container border border-outline text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="">All Statuses</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="pending">Pending</option>
                    <option value="cancelled">Cancelled</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
                <button
                  type="button"
                  onClick={loadBookings}
                  className="px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-sm font-semibold transition-colors"
                >
                  Refresh
                </button>
              </div>

              {/* Bookings Table */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-outline text-on-surface-variant text-xs uppercase font-semibold">
                    <tr>
                      <th className="pb-3">Reference</th>
                      <th className="pb-3">Customer</th>
                      <th className="pb-3">Slot Window (IST)</th>
                      <th className="pb-3">Package</th>
                      <th className="pb-3">Total Price</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20">
                    {bookings.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-on-surface-variant">
                          No bookings found matching filters.
                        </td>
                      </tr>
                    ) : (
                      bookings.map((b) => (
                        <tr key={b._id || b.bookingReference} className="hover:bg-surface-container/50">
                          <td className="py-3 font-mono font-bold text-primary">{b.bookingReference}</td>
                          <td className="py-3">
                            <p className="font-semibold text-on-surface">{b.customerName}</p>
                            <p className="text-xs text-on-surface-variant">{b.customerPhone}</p>
                          </td>
                          <td className="py-3 text-xs">
                            <p className="font-medium">{formatIST(b.slotStart)}</p>
                            <p className="text-on-surface-variant">to {formatIST(b.slotEnd)}</p>
                          </td>
                          <td className="py-3 capitalize">{b.packageSlug}</td>
                          <td className="py-3">
                            <p className="font-semibold">{formatCurrency(b.totalPricePaise)}</p>
                            <p className="text-xs text-on-surface-variant">Paid: {formatCurrency(b.advancePaidPaise)}</p>
                          </td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                                b.status === 'confirmed'
                                  ? 'bg-[#dcfce7] text-[#166534]'
                                  : b.status === 'pending'
                                  ? 'bg-[#fef9c3] text-[#854d0e]'
                                  : 'bg-surface-container-high text-on-surface-variant'
                              }`}
                            >
                              {b.status}
                            </span>
                          </td>
                          <td className="py-3 text-right space-x-2">
                            <button
                              type="button"
                              onClick={() => setSelectedBooking(b)}
                              className="px-2 py-1 rounded bg-surface-container text-xs font-bold text-primary hover:bg-surface-container-high"
                            >
                              Details
                            </button>
                            {b.status === 'confirmed' && (
                              <button
                                type="button"
                                onClick={() => {
                                  const reason = prompt('Cancellation reason / note:');
                                  if (reason !== null) {
                                    handleUpdateBookingStatus(b.bookingReference, 'cancelled', reason);
                                  }
                                }}
                                className="px-2 py-1 rounded bg-error-container text-xs font-bold text-on-error-container hover:opacity-80"
                              >
                                Cancel
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: INQUIRIES & LEADS */}
          {activeTab === 'inquiries' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Customer Inquiries</h2>
                  <p className="text-xs text-on-surface-variant">Leads captured from the landing page and contact form</p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={inquiryFilterStatus}
                    onChange={(e) => setInquiryFilterStatus(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container border border-outline text-sm"
                  >
                    <option value="">All Statuses</option>
                    <option value="new">New</option>
                    <option value="responded">Responded</option>
                    <option value="booked">Booked</option>
                    <option value="archived">Archived</option>
                  </select>
                  <button
                    type="button"
                    onClick={loadInquiries}
                    className="px-3 py-1.5 rounded bg-surface-container-high text-sm font-semibold hover:bg-surface-container-highest"
                  >
                    Refresh
                  </button>
                </div>
              </div>

              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                {inquiries.length === 0 ? (
                  <p className="text-center py-8 text-on-surface-variant text-sm">No customer inquiries found.</p>
                ) : (
                  <div className="divide-y divide-outline-variant/20">
                    {inquiries.map((inq) => (
                      <div key={inq._id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="space-y-1 max-w-xl">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-on-surface">{inq.name}</span>
                            <span className="text-xs px-2 py-0.5 rounded bg-surface-container font-mono text-on-surface-variant">
                              {inq.phone}
                            </span>
                            {inq.partyType && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-secondary-fixed text-on-secondary-fixed font-semibold">
                                {inq.partyType}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-on-surface">{inq.message}</p>
                          <p className="text-xs text-on-surface-variant">
                            Received: {formatIST(inq.createdAt)} · Preferred Date: {inq.requestedDate || 'Not specified'}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <select
                            value={inq.status}
                            onChange={(e) => handleUpdateInquiryStatus(inq._id, e.target.value)}
                            className="px-2 py-1 rounded bg-surface-container border border-outline text-xs font-semibold"
                          >
                            <option value="new">New</option>
                            <option value="responded">Responded</option>
                            <option value="booked">Booked</option>
                            <option value="archived">Archived</option>
                          </select>
                          <a
                            href={`https://wa.me/${inq.phone.replace(/[^0-9]/g, '')}`}
                            target="_blank"
                            rel="noreferrer"
                            className="px-3 py-1 rounded bg-[#25D366] text-white text-xs font-bold flex items-center gap-1 shadow-sm hover:opacity-90"
                          >
                            <span>WhatsApp</span>
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB: PACKAGES & ADD-ONS */}
          {activeTab === 'packages' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Catalog &amp; Pricing</h2>
                <p className="text-xs text-on-surface-variant">Base hourly package rates and add-on services</p>
              </div>

              {/* Base Packages */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                <h3 className="font-bold text-on-surface">Base Packages (Hourly Rates)</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {packages.map((pkg) => (
                    <div key={pkg._id || pkg.slug} className="p-4 rounded-xl border border-outline bg-surface-container-low space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-primary capitalize">{pkg.name}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-primary-container text-on-primary-container font-bold">
                          {formatCurrency(pkg.pricePerHourMinor)}/hr
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant">{pkg.description}</p>
                      <ul className="text-xs space-y-1 text-on-surface pt-2 border-t border-outline">
                        {(pkg.features || []).map((f, i) => (
                          <li key={i} className="flex items-center gap-1">
                            <span className="material-symbols-outlined text-secondary text-sm">check</span>
                            <span>{f}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>

              {/* Add-ons */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                <h3 className="font-bold text-on-surface">Add-ons</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {addOns.map((addon) => (
                    <div key={addon._id || addon.slug} className="p-4 rounded-xl border border-outline bg-surface-container-low space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-on-surface capitalize">{addon.name}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed font-bold">
                          {formatCurrency(addon.priceMinor)}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant">{addon.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB: AVAILABILITY BLOCKS */}
          {activeTab === 'blocks' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Emergency Hall Blocks &amp; Slots</h2>
                <p className="text-xs text-on-surface-variant">
                  Block room slots for private reservations, maintenance, or holidays. Locks slots atomically against double-booking.
                </p>
              </div>

              {/* New Block Form */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm">
                <h3 className="font-bold text-on-surface mb-4">Create New Hall Block</h3>
                <form onSubmit={handleCreateBlock} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">Reason</label>
                    <input
                      type="text"
                      required
                      value={newBlock.reason}
                      onChange={(e) => setNewBlock({ ...newBlock, reason: e.target.value })}
                      placeholder="e.g. Deep Cleaning / Private Event"
                      className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">Start Time (IST)</label>
                    <input
                      type="datetime-local"
                      required
                      value={newBlock.slotStart}
                      onChange={(e) => setNewBlock({ ...newBlock, slotStart: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-on-surface-variant mb-1">End Time (IST)</label>
                    <input
                      type="datetime-local"
                      required
                      value={newBlock.slotEnd}
                      onChange={(e) => setNewBlock({ ...newBlock, slotEnd: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      type="submit"
                      className="w-full py-2.5 px-4 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-container transition-colors shadow-sm"
                    >
                      Block Slots
                    </button>
                  </div>
                </form>
              </div>

              {/* Active Blocks List */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                <h3 className="font-bold text-on-surface">Active Hall Blocks</h3>
                {availabilityBlocks.length === 0 ? (
                  <p className="text-center py-6 text-on-surface-variant text-sm">No active hall blocks.</p>
                ) : (
                  <div className="divide-y divide-outline-variant/20">
                    {availabilityBlocks.map((blk) => (
                      <div key={blk._id} className="py-3 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-on-surface">{blk.reason}</p>
                          <p className="text-xs text-on-surface-variant">
                            {formatIST(blk.slotStart)} &rarr; {formatIST(blk.slotEnd)} (Room: {blk.roomId})
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteBlock(blk._id)}
                          className="px-3 py-1 rounded bg-error-container text-on-error-container text-xs font-bold hover:opacity-80"
                        >
                          Release Block
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB: PAYMENTS & REFUNDS */}
          {activeTab === 'payments' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">Payments &amp; Refunds</h2>
                  <p className="text-xs text-on-surface-variant">Audit gateway transactions, track advances, and retry failed refunds</p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={paymentReviewFilter}
                    onChange={(e) => setPaymentReviewFilter(e.target.value)}
                    className="px-3 py-1.5 rounded-lg bg-surface-container border border-outline text-sm"
                  >
                    <option value="">All Payments</option>
                    <option value="true">Needs Review Only</option>
                  </select>
                  <button
                    type="button"
                    onClick={loadPayments}
                    className="px-3 py-1.5 rounded bg-surface-container-high text-sm font-semibold hover:bg-surface-container-highest"
                  >
                    Refresh
                  </button>
                </div>
              </div>

              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-outline text-on-surface-variant text-xs uppercase font-semibold">
                    <tr>
                      <th className="pb-3">Payment ID / Order</th>
                      <th className="pb-3">Booking Ref</th>
                      <th className="pb-3">Amount</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Method</th>
                      <th className="pb-3">Review Flag</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20">
                    {payments.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-on-surface-variant">
                          No payments found matching criteria.
                        </td>
                      </tr>
                    ) : (
                      payments.map((p) => (
                        <tr key={p._id} className="hover:bg-surface-container/50">
                          <td className="py-3 font-mono text-xs">
                            <p className="font-bold text-on-surface">{p.providerPaymentId || 'Pending Provider ID'}</p>
                            <p className="text-on-surface-variant">{p.providerOrderId}</p>
                          </td>
                          <td className="py-3 font-mono font-bold text-primary">{p.bookingReference}</td>
                          <td className="py-3 font-semibold">{formatCurrency(p.amountPaise)}</td>
                          <td className="py-3">
                            <span
                              className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                                p.status === 'captured'
                                  ? 'bg-[#dcfce7] text-[#166534]'
                                  : p.status === 'refunded'
                                  ? 'bg-secondary-fixed text-on-secondary-fixed'
                                  : 'bg-surface-container-high text-on-surface-variant'
                              }`}
                            >
                              {p.status}
                            </span>
                          </td>
                          <td className="py-3 text-xs capitalize">{p.paymentMethod || 'Razorpay'}</td>
                          <td className="py-3">
                            {p.needsReview ? (
                              <span className="px-2 py-0.5 rounded-full bg-error-container text-on-error-container font-bold text-xs">
                                Needs Review
                              </span>
                            ) : (
                              <span className="text-xs text-on-surface-variant">Normal</span>
                            )}
                          </td>
                          <td className="py-3 text-right">
                            {p.needsReview && (
                              <button
                                type="button"
                                onClick={() => handleRetryRefund(p._id)}
                                className="px-2.5 py-1 rounded bg-error text-on-error text-xs font-bold hover:opacity-90"
                              >
                                Retry Refund
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: AUDIT LOGS */}
          {activeTab === 'audit' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">System Audit Trail</h2>
                <p className="text-xs text-on-surface-variant">Immutable record of admin logins, cancellations, price modifications, and block updates</p>
              </div>

              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm space-y-4">
                {auditLogs.length === 0 ? (
                  <p className="text-center py-6 text-on-surface-variant text-sm">No audit logs recorded.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-outline text-on-surface-variant text-xs uppercase font-semibold">
                        <tr>
                          <th className="pb-3">Timestamp (IST)</th>
                          <th className="pb-3">User &amp; Role</th>
                          <th className="pb-3">Action</th>
                          <th className="pb-3">Target</th>
                          <th className="pb-3">IP Address</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-outline-variant/20">
                        {auditLogs.map((log) => (
                          <tr key={log._id} className="hover:bg-surface-container/50">
                            <td className="py-3 text-xs font-mono">{formatIST(log.timestamp)}</td>
                            <td className="py-3">
                              <span className="font-bold text-on-surface">{log.username}</span>
                              <span className="text-xs text-on-surface-variant block">({log.role})</span>
                            </td>
                            <td className="py-3 font-semibold text-primary">{log.action}</td>
                            <td className="py-3 text-xs font-mono">{log.target || '—'}</td>
                            <td className="py-3 text-xs text-on-surface-variant font-mono">{log.ipAddress || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* MODAL: Booking Detail */}
      {selectedBooking && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-gutter">
          <div className="bg-surface-container-lowest max-w-lg w-full rounded-2xl shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-outline pb-3">
              <div>
                <span className="text-xs text-on-surface-variant font-bold uppercase">Booking Details</span>
                <h3 className="font-headline-sm font-bold text-primary">{selectedBooking.bookingReference}</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedBooking(null)}
                className="p-1 rounded hover:bg-surface-container-high"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-xs text-on-surface-variant block">Customer</span>
                  <span className="font-semibold text-on-surface">{selectedBooking.customerName}</span>
                </div>
                <div>
                  <span className="text-xs text-on-surface-variant block">Phone</span>
                  <span className="font-semibold text-on-surface">{selectedBooking.customerPhone}</span>
                </div>
              </div>

              <div>
                <span className="text-xs text-on-surface-variant block">Slot (IST)</span>
                <span className="font-medium">
                  {formatIST(selectedBooking.slotStart)} &rarr; {formatIST(selectedBooking.slotEnd)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-xs text-on-surface-variant block">Package</span>
                  <span className="font-semibold capitalize">{selectedBooking.packageSlug}</span>
                </div>
                <div>
                  <span className="text-xs text-on-surface-variant block">Current Status</span>
                  <span className="font-bold text-primary uppercase">{selectedBooking.status}</span>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-surface-container text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Total Price:</span>
                  <span className="font-bold">{formatCurrency(selectedBooking.totalPricePaise)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Advance Required:</span>
                  <span>{formatCurrency(selectedBooking.advanceRequiredPaise)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Advance Paid:</span>
                  <span className="font-bold text-[#166534]">{formatCurrency(selectedBooking.advancePaidPaise)}</span>
                </div>
              </div>

              {selectedBooking.internalNotes && (
                <div>
                  <span className="text-xs text-on-surface-variant block">Internal Notes</span>
                  <p className="text-xs bg-surface-container-low p-2 rounded">{selectedBooking.internalNotes}</p>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-outline flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedBooking(null)}
                className="px-4 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high font-semibold text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Manual Booking */}
      {showManualBookingModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-gutter">
          <div className="bg-surface-container-lowest max-w-md w-full rounded-2xl shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-outline pb-3">
              <h3 className="font-headline-sm font-bold text-on-surface">Create Manual Booking</h3>
              <button
                type="button"
                onClick={() => setShowManualBookingModal(false)}
                className="p-1 rounded hover:bg-surface-container-high"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleCreateManualBooking} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Customer Name</label>
                <input
                  type="text"
                  required
                  value={manualBookingForm.customerName}
                  onChange={(e) => setManualBookingForm({ ...manualBookingForm, customerName: e.target.value })}
                  placeholder="e.g. Ramesh Reddy"
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Customer Phone (10 digits)</label>
                <input
                  type="tel"
                  required
                  value={manualBookingForm.customerPhone}
                  onChange={(e) => setManualBookingForm({ ...manualBookingForm, customerPhone: e.target.value })}
                  placeholder="e.g. 9876543210"
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Package</label>
                <select
                  value={manualBookingForm.packageSlug}
                  onChange={(e) => setManualBookingForm({ ...manualBookingForm, packageSlug: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline"
                >
                  <option value="basic">Basic (₹999/hr)</option>
                  <option value="gold">Gold (₹1,500/hr)</option>
                  <option value="diamond">Diamond (₹2,500/hr)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Start (IST)</label>
                  <input
                    type="datetime-local"
                    required
                    value={manualBookingForm.slotStart}
                    onChange={(e) => setManualBookingForm({ ...manualBookingForm, slotStart: e.target.value })}
                    className="w-full px-2 py-2 rounded-lg bg-surface-container border border-outline text-xs"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">End (IST)</label>
                  <input
                    type="datetime-local"
                    required
                    value={manualBookingForm.slotEnd}
                    onChange={(e) => setManualBookingForm({ ...manualBookingForm, slotEnd: e.target.value })}
                    className="w-full px-2 py-2 rounded-lg bg-surface-container border border-outline text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Advance (₹)</label>
                  <input
                    type="number"
                    value={manualBookingForm.advancePaidPaise / 100}
                    onChange={(e) => setManualBookingForm({ ...manualBookingForm, advancePaidPaise: Number(e.target.value) * 100 })}
                    className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-on-surface-variant mb-1">Method</label>
                  <select
                    value={manualBookingForm.paymentMethod}
                    onChange={(e) => setManualBookingForm({ ...manualBookingForm, paymentMethod: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                  >
                    <option value="offline_cash">Cash</option>
                    <option value="offline_upi">Direct UPI QR</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Internal Notes</label>
                <textarea
                  value={manualBookingForm.internalNotes}
                  onChange={(e) => setManualBookingForm({ ...manualBookingForm, internalNotes: e.target.value })}
                  placeholder="Notes about setup or special customer requests"
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline text-sm"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowManualBookingModal(false)}
                  className="px-4 py-2 rounded-lg bg-surface-container font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-primary text-on-primary font-bold shadow-sm hover:bg-primary-container"
                >
                  Create Booking
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Change Password */}
      {showChangePasswordModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-gutter">
          <div className="bg-surface-container-lowest max-w-sm w-full rounded-2xl shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-outline pb-3">
              <h3 className="font-headline-sm font-bold text-on-surface">Change Password</h3>
              <button
                type="button"
                onClick={() => setShowChangePasswordModal(false)}
                className="p-1 rounded hover:bg-surface-container-high"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">Current Password</label>
                <input
                  type="password"
                  required
                  value={pwdForm.currentPassword}
                  onChange={(e) => setPwdForm({ ...pwdForm, currentPassword: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-on-surface-variant mb-1">
                  New Password (min 10 chars, uppercase, lowercase, number, symbol)
                </label>
                <input
                  type="password"
                  required
                  value={pwdForm.newPassword}
                  onChange={(e) => setPwdForm({ ...pwdForm, newPassword: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-surface-container border border-outline"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowChangePasswordModal(false)}
                  className="px-4 py-2 rounded-lg bg-surface-container font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-primary text-on-primary font-bold shadow-sm hover:bg-primary-container"
                >
                  Update
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
