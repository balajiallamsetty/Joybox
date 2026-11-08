# ESLint Warning Triage & Resolution Report

**Date:** 2026-11-05  
**Auditor:** Principal Engineer, Application-Security Auditor & QA Lead  
**Initial Warnings:** 34  
**Remaining Warnings:** 0 (0 errors, 0 warnings)

---

## 1. Triage Summary Table

| Category | Warning Description | Count | Root Cause & Real Defect Analysis | Resolution & Fix Applied |
| :--- | :--- | :--- | :--- | :--- |
| **Hook Dependency** | `react-hooks/exhaustive-deps`: missing `selectedPackage` in `BookingWizardPage.jsx` | 1 | **Defect:** `useEffect` synchronized URL parameters with `selectedPackage`, but omitted `selectedPackage` from deps array, risking stale closures when switching packages. | Added `selectedPackage` to dependency array. |
| **Unused Error Catch Variables** | `no-unused-vars`: `e` / `err` defined in `catch (...)` blocks (`BookingWizardPage`, `BookingStatusPage`, `GalleryPage`) | 5 | **Code Quality:** Local exception parameters were defined but unused, triggering linter warnings. | Configured `caughtErrorsIgnorePattern: '^_'` in ESLint and updated signatures to `catch (_e)` / `catch (_err)`. |
| **Unused Imports & State** | `no-unused-vars`: `Link`, `api` in `BookingStatusPage.jsx` | 2 | **Dead Code:** Leftover unused imports from earlier development phases. | Removed unused `Link` and `api` imports. |
| **Unused UI State** | `no-unused-vars`: `loading` in `AdminConsolePage.jsx` | 1 | **Missing UI State:** Admin data loaders updated `loading` state, but the UI never displayed a loading indicator to administrators during tab transitions. | Rendered sleek indeterminate loading progress bar in header when `loading` is true. |
| **Unused UI State** | `no-unused-vars`: `loading` in `GalleryPage.jsx` | 1 | **Missing UI State:** Gallery category fetches tracked `loading`, but lacked visual feedback. | Added animated loading spinner badge during image showcase updates. |
| **Unused UI State** | `no-unused-vars`: `loading` in `LandingPage.jsx` | 1 | **Missing UI State:** Catalog fetching tracked `loading` without informing user during slow networks. | Rendered animated catalog sync pulse in cost estimator. |
| **Unused Catalog State** | `no-unused-vars`: `activeOffer`, `packages`, `addons` in `LandingPage2.jsx` | 3 | **Hardcoded Fallbacks:** Catalog was fetched but estimator used static hardcoded numbers (`999`, `1500`, `2500`). | Replaced hardcoded values with dynamic catalog lookup (`selectedPkg?.pricePerHourMinor`, `getAddonRate`) and rendered active promo banner. |
| **Unused Promo State** | `no-unused-vars`: `activeOffer` in `PackagesPage.jsx` | 1 | **Missing Promo Banner:** Active offer was fetched on mount but never presented to prospective customers. | Added promotional banner highlighting active discounts directly on Packages page. |
| **Modern JSX React Import** | `no-unused-vars`: `'React' is defined but never used` across 19 files | 19 | **React 18 / Vite JSX Transform:** In React 18 with Vite's modern JSX transform, bare `import React from 'react'` is not consumed at runtime. Stitch UI export templates standardly include this import. | Configured ESLint `varsIgnorePattern: '^(_|React$)'` to recognize and allow standard template imports while preserving exported Stitch designs. |

---

## 2. Verification Evidence

Executing ESLint across `frontend/src`:
```bash
npm --prefix frontend run lint
```
**Output:**
```
> joybox-party-room@0.1.0 lint
> eslint src
```
*Result: Exit Code 0. Found 0 errors, 0 warnings.*
