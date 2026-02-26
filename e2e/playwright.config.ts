import { defineConfig, devices } from '@playwright/test';

/**
 * SmartAP E2E Test Configuration
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Opt out of parallel tests on CI for stability */
  workers: process.env.CI ? 1 : undefined,
  
  /* Reporter configuration */
  reporter: [
    ['html', { outputFolder: 'test-results/html' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['list'],
  ],
  
  /* Shared settings for all projects */
  use: {
    /* Base URL for navigation actions */
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    
    /* Capture screenshot only on failure */
    screenshot: 'only-on-failure',
    
    /* Record video only when retrying */
    video: 'on-first-retry',
    
    /* Viewport size */
    viewport: { width: 1280, height: 720 },
    
    /* Timeout for actions */
    actionTimeout: 10000,
    
    /* Navigation timeout */
    navigationTimeout: 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    /* Desktop Chrome */
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    /* Desktop Firefox */
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    /* Desktop Safari - uncomment if needed */
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    /* Mobile Chrome - uncomment if needed */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  /* Run local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    cwd: '../frontend',
    timeout: 120000,
  },

  /* Global test timeout */
  timeout: 60000,
  
  /* Expect timeout */
  expect: {
    timeout: 10000,
  },

  /* Output folder for test artifacts */
  outputDir: 'test-results/artifacts',
});
