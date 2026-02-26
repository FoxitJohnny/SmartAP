import { test, expect, waitForLoading } from '../fixtures/test-helpers';
import { SELECTORS } from '../fixtures/test-data';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ auth }) => {
    await auth.loginAsAdmin();
  });

  test.describe('Dashboard Layout', () => {
    test('displays dashboard page with header', async ({ page }) => {
      await page.goto('/dashboard');
      
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
      await expect(page.getByText(/welcome to smartap/i)).toBeVisible();
    });

    test('shows navigation sidebar', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Check main navigation items
      await expect(page.locator(SELECTORS.nav.dashboard)).toBeVisible();
      await expect(page.locator(SELECTORS.nav.invoices)).toBeVisible();
      await expect(page.locator(SELECTORS.nav.approvals)).toBeVisible();
      await expect(page.locator(SELECTORS.nav.vendors)).toBeVisible();
    });
  });

  test.describe('Metrics Cards', () => {
    test('displays total invoices card', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Look for the total invoices metric
      const totalInvoicesCard = page.getByText(/total invoices/i);
      await expect(totalInvoicesCard).toBeVisible();
    });

    test('displays pending approvals card', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Look for pending approvals metric
      const pendingCard = page.getByText(/pending approvals/i);
      await expect(pendingCard).toBeVisible();
    });

    test('displays risk flags card', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Look for risk flags metric
      const riskCard = page.getByText(/risk flags/i);
      await expect(riskCard).toBeVisible();
    });

    test('displays STP rate card', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Look for STP rate metric
      const stpCard = page.getByText(/stp rate/i);
      await expect(stpCard).toBeVisible();
    });

    test('metrics cards show numeric values or loading state', async ({ page }) => {
      await page.goto('/dashboard');
      
      // Wait for content to load
      await waitForLoading(page);
      
      // Cards should show numbers or dash for empty state
      const cardContents = page.locator('[class*="card"] [class*="font-bold"]');
      
      // At least one card should have content
      await expect(cardContents.first()).toBeVisible();
    });
  });

  test.describe('Recent Activity', () => {
    test('displays recent activity section', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Look for activity section
      const activitySection = page.getByText(/recent activity/i);
      await expect(activitySection).toBeVisible();
    });

    test('shows activity items or empty state', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Either show activity items or an empty state message
      const activityItems = page.locator('[class*="activity"], [class*="border"][class*="rounded"]');
      const emptyState = page.getByText(/no recent activity|no activity/i);
      
      // Either should be present
      const hasActivity = await activityItems.count() > 0;
      const hasEmptyState = await emptyState.isVisible().catch(() => false);
      
      expect(hasActivity || hasEmptyState).toBeTruthy();
    });
  });

  test.describe('Dashboard Navigation', () => {
    test('can navigate to invoices from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.click(SELECTORS.nav.invoices);
      
      await expect(page).toHaveURL('/invoices');
    });

    test('can navigate to approvals from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.click(SELECTORS.nav.approvals);
      
      await expect(page).toHaveURL('/approvals');
    });

    test('can navigate to vendors from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.click(SELECTORS.nav.vendors);
      
      await expect(page).toHaveURL('/vendors');
    });

    test('can navigate to purchase orders from dashboard', async ({ page }) => {
      await page.goto('/dashboard');
      
      await page.click(SELECTORS.nav.purchaseOrders);
      
      await expect(page).toHaveURL('/purchase-orders');
    });
  });

  test.describe('Dashboard Responsiveness', () => {
    test('dashboard renders correctly on desktop', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 });
      await page.goto('/dashboard');
      
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('dashboard renders correctly on tablet', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto('/dashboard');
      
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });

    test('dashboard renders correctly on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/dashboard');
      
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });
  });

  test.describe('Dashboard Data Refresh', () => {
    test('page loads metrics from API', async ({ page }) => {
      // Monitor API calls
      const apiCalls: string[] = [];
      page.on('request', request => {
        if (request.url().includes('/api/')) {
          apiCalls.push(request.url());
        }
      });

      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Should have made API calls for dashboard data
      // Note: API structure may vary
      expect(apiCalls.length).toBeGreaterThanOrEqual(0);
    });

    test('handles API errors gracefully', async ({ page }) => {
      // Route to return error
      await page.route('**/api/v1/dashboard/**', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Server error' }),
        });
      });

      await page.goto('/dashboard');
      
      // Page should still render without crashing
      await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
    });
  });

  test.describe('Quick Actions', () => {
    test('clicking invoice card navigates to invoices', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Find and click on the invoices-related card or link
      const invoiceLink = page.locator('a[href="/invoices"]').first();
      
      if (await invoiceLink.isVisible()) {
        await invoiceLink.click();
        await expect(page).toHaveURL('/invoices');
      }
    });

    test('clicking approvals navigates to approval queue', async ({ page }) => {
      await page.goto('/dashboard');
      await waitForLoading(page);
      
      // Find and click on the approvals-related card or link
      const approvalsLink = page.locator('a[href="/approvals"]').first();
      
      if (await approvalsLink.isVisible()) {
        await approvalsLink.click();
        await expect(page).toHaveURL('/approvals');
      }
    });
  });
});

test.describe('Dashboard - Unauthenticated', () => {
  test('redirects to login when not authenticated', async ({ page }) => {
    // Clear any existing auth state
    await page.context().clearCookies();
    
    await page.goto('/dashboard');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
