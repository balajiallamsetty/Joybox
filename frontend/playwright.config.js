import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: path.resolve(__dirname, 'e2e'),
  testMatch: '**/*.spec.js',
  timeout: 60000,
  expect: {
    timeout: 15000,
  },
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
      },
    },
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 7'],
        viewport: { width: 375, height: 812 },
      },
    },
  ],
  webServer: [
    {
      command: 'python run.py',
      cwd: path.resolve(__dirname, '../backend'),
      url: 'http://127.0.0.1:5000/api/health',
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        MONGODB_DB: 'joybox_party_room_test',
        HOST: '127.0.0.1',
        PORT: '5000',
        FLASK_ENV: 'testing',
        FRONTEND_ORIGIN: 'http://localhost:5173,http://127.0.0.1:5173',
        RATE_LIMIT_HOLD_PER_IP_MAX: '200',
        RATE_LIMIT_HOLD_PER_PHONE_MAX: '50',
        BOOKINGS_OPEN: 'true',
        PAYMENTS_ENABLED: 'true',
      },
    },
    {
      command: 'npm run dev -- --port 5173',
      cwd: __dirname,
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        VITE_API_BASE_URL: 'http://127.0.0.1:5000/api',
        VITE_PAYMENTS_ENABLED: 'true',
      },
    },
  ],
});
