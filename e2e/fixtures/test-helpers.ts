import { test as base, Page } from '@playwright/test';
import { TEST_USERS, SELECTORS } from './test-data';

/**
 * Authentication helper class
 */
export class AuthHelper {
  constructor(private page: Page) {}

  /**
   * Log in with the given credentials
   */
  async login(email: string, password: string): Promise<void> {
    await this.page.goto('/login');
    await this.page.fill(SELECTORS.auth.emailInput, email);
    await this.page.fill(SELECTORS.auth.passwordInput, password);
    await this.page.click(SELECTORS.auth.loginButton);
    await this.page.waitForURL(/\/(dashboard|invoices)/);
  }

  /**
   * Log in as admin user
   */
  async loginAsAdmin(): Promise<void> {
    await this.login(TEST_USERS.admin.email, TEST_USERS.admin.password);
  }

  /**
   * Log in as approver user
   */
  async loginAsApprover(): Promise<void> {
    await this.login(TEST_USERS.approver.email, TEST_USERS.approver.password);
  }

  /**
   * Log in as viewer user
   */
  async loginAsViewer(): Promise<void> {
    await this.login(TEST_USERS.viewer.email, TEST_USERS.viewer.password);
  }

  /**
   * Log out the current user
   */
  async logout(): Promise<void> {
    await this.page.click(SELECTORS.auth.logoutButton);
    await this.page.waitForURL('/login');
  }

  /**
   * Check if user is logged in by looking for dashboard elements
   */
  async isLoggedIn(): Promise<boolean> {
    try {
      await this.page.waitForSelector(SELECTORS.nav.dashboard, { timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }
}

/**
 * Navigation helper class
 */
export class NavigationHelper {
  constructor(private page: Page) {}

  async goToDashboard(): Promise<void> {
    await this.page.click(SELECTORS.nav.dashboard);
    await this.page.waitForURL('/dashboard');
  }

  async goToInvoices(): Promise<void> {
    await this.page.click(SELECTORS.nav.invoices);
    await this.page.waitForURL('/invoices');
  }

  async goToApprovals(): Promise<void> {
    await this.page.click(SELECTORS.nav.approvals);
    await this.page.waitForURL('/approvals');
  }

  async goToVendors(): Promise<void> {
    await this.page.click(SELECTORS.nav.vendors);
    await this.page.waitForURL('/vendors');
  }

  async goToPurchaseOrders(): Promise<void> {
    await this.page.click(SELECTORS.nav.purchaseOrders);
    await this.page.waitForURL('/purchase-orders');
  }

  async goToAnalytics(): Promise<void> {
    await this.page.click(SELECTORS.nav.analytics);
    await this.page.waitForURL('/analytics');
  }
}

/**
 * Extended test fixtures with authentication
 */
type TestFixtures = {
  auth: AuthHelper;
  nav: NavigationHelper;
  authenticatedPage: Page;
};

export const test = base.extend<TestFixtures>({
  auth: async ({ page }, use) => {
    await use(new AuthHelper(page));
  },

  nav: async ({ page }, use) => {
    await use(new NavigationHelper(page));
  },

  authenticatedPage: async ({ page }, use) => {
    const auth = new AuthHelper(page);
    await auth.loginAsAdmin();
    await use(page);
  },
});

export { expect } from '@playwright/test';

/**
 * Wait for toast message to appear
 */
export async function waitForToast(page: Page, text?: string): Promise<void> {
  const toast = page.locator(SELECTORS.common.toast);
  await toast.waitFor({ state: 'visible' });
  if (text) {
    await toast.filter({ hasText: text }).waitFor({ state: 'visible' });
  }
}

/**
 * Wait for loading to complete
 */
export async function waitForLoading(page: Page): Promise<void> {
  const loader = page.locator(SELECTORS.common.loadingSpinner);
  // Wait for loader to appear (if it does)
  try {
    await loader.waitFor({ state: 'visible', timeout: 1000 });
    // Then wait for it to disappear
    await loader.waitFor({ state: 'hidden', timeout: 30000 });
  } catch {
    // Loader didn't appear, content was fast enough
  }
}

/**
 * Generate a unique test ID for isolation
 */
export function generateTestId(): string {
  return `test-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Format date for input fields
 */
export function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}
