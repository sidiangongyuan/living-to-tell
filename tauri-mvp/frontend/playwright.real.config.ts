import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: /.*\.real\.e2e\.ts/,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:1421',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'python run.py',
      url: 'http://127.0.0.1:18080/health',
      cwd: '../backend',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        WRITER_USE_DEV_DB: '1',
        WRITER_PORT: '18080',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 1421',
      url: 'http://127.0.0.1:1421',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_API_BASE_URL: 'http://127.0.0.1:18080',
      },
    },
  ],
  projects: [
    {
      name: 'msedge',
      use: { ...devices['Desktop Chrome'], channel: 'msedge' },
    },
  ],
})
