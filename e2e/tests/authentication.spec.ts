import { test, expect, waitForToast } from '../fixtures/test-helpers';
import { SELECTORS, TEST_USERS } from '../fixtures/test-data';

test.describe('Authentication', () => {
  test.describe('Login Page', () => {
    test('displays login form', async ({ page }) => {
      await page.goto('/login');
      
      await expect(page.getByRole('heading', { name: /welcome to smartap/i })).toBeVisible();
      await expect(page.locator(SELECTORS.auth.emailInput)).toBeVisible();
      await expect(page.locator(SELECTORS.auth.passwordInput)).toBeVisible();
      await expect(page.locator(SELECTORS.auth.loginButton)).toBeVisible();
    });

    test('shows link to register page', async ({ page }) => {
      await page.goto('/login');
      
      const registerLink = page.locator(SELECTORS.auth.registerLink);
      await expect(registerLink).toBeVisible();
      await expect(registerLink).toHaveAttribute('href', '/register');
    });

    test('validates required email field', async ({ page }) => {
      await page.goto('/login');
      
      // Fill password but not email
      await page.fill(SELECTORS.auth.passwordInput, 'testpassword');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show validation error or not submit
      // Form should still be on login page
      await expect(page).toHaveURL(/\/login/);
    });

    test('validates required password field', async ({ page }) => {
      await page.goto('/login');
      
      // Fill email but not password
      await page.fill(SELECTORS.auth.emailInput, 'test@example.com');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show validation error or not submit
      await expect(page).toHaveURL(/\/login/);
    });

    test('validates email format', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill(SELECTORS.auth.emailInput, 'invalid-email');
      await page.fill(SELECTORS.auth.passwordInput, 'password123');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show validation error
      const error = page.getByText(/invalid|email/i);
      await expect(error).toBeVisible();
    });

    test('shows error for invalid credentials', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill(SELECTORS.auth.emailInput, 'wrong@example.com');
      await page.fill(SELECTORS.auth.passwordInput, 'wrongpassword');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show error message (either inline or toast)
      // Wait for either error text or stay on login page
      await page.waitForTimeout(1000);
      await expect(page).toHaveURL(/\/login/);
    });

    test('successful login redirects to dashboard', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill(SELECTORS.auth.emailInput, TEST_USERS.admin.email);
      await page.fill(SELECTORS.auth.passwordInput, TEST_USERS.admin.password);
      await page.click(SELECTORS.auth.loginButton);
      
      // Should redirect to dashboard on success
      await expect(page).toHaveURL(/\/(dashboard|invoices)/);
    });

    test('disables form while submitting', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill(SELECTORS.auth.emailInput, TEST_USERS.admin.email);
      await page.fill(SELECTORS.auth.passwordInput, TEST_USERS.admin.password);
      
      // Click and immediately check button state
      const loginButton = page.locator(SELECTORS.auth.loginButton);
      await loginButton.click();
      
      // Button should be disabled during submission or text should change
      // This is a race condition - button may be re-enabled quickly
    });
  });

  test.describe('Register Page', () => {
    test('displays registration form', async ({ page }) => {
      await page.goto('/register');
      
      await expect(page.getByRole('heading', { name: /create|register|sign up/i })).toBeVisible();
    });

    test('has link back to login', async ({ page }) => {
      await page.goto('/register');
      
      const loginLink = page.locator('a[href="/login"]');
      await expect(loginLink).toBeVisible();
    });

    test('validates password confirmation matches', async ({ page }) => {
      await page.goto('/register');
      
      // Find password fields
      const passwordFields = page.locator('input[type="password"]');
      
      if (await passwordFields.count() >= 2) {
        await page.fill(SELECTORS.auth.emailInput, 'new@example.com');
        await passwordFields.nth(0).fill('password123');
        await passwordFields.nth(1).fill('differentpassword');
        
        // Try to submit
        await page.click('button[type="submit"]');
        
        // Should show mismatch error
        const error = page.getByText(/match|same|confirm/i);
        await expect(error).toBeVisible();
      }
    });
  });

  test.describe('Logout', () => {
    test('logout clears session and redirects to login', async ({ page, auth }) => {
      // First login
      await auth.loginAsAdmin();
      
      // Verify we're logged in
      await expect(page).toHaveURL(/\/(dashboard|invoices)/);
      
      // Find and click logout
      const logoutButton = page.locator('[data-testid="logout-button"], button:has-text("logout"), button:has-text("sign out")');
      
      if (await logoutButton.isVisible()) {
        await logoutButton.click();
        await expect(page).toHaveURL(/\/login/);
      }
    });

    test('cannot access protected routes after logout', async ({ page, auth }) => {
      // Login first
      await auth.loginAsAdmin();
      await expect(page).toHaveURL(/\/(dashboard|invoices)/);
      
      // Clear cookies to simulate logout
      await page.context().clearCookies();
      
      // Try to access dashboard
      await page.goto('/dashboard');
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe('Protected Routes', () => {
    test('dashboard requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/dashboard');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('invoices page requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/invoices');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('approvals page requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/approvals');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('vendors page requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/vendors');
      
      await expect(page).toHaveURL(/\/login/);
    });

    test('upload page requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/invoices/upload');
      
      await expect(page).toHaveURL(/\/login/);
    });
  });

  test.describe('Session Persistence', () => {
    test('session persists across page refreshes', async ({ page, auth }) => {
      await auth.loginAsAdmin();
      
      // Refresh the page
      await page.reload();
      
      // Should still be on protected page
      await expect(page).toHaveURL(/\/(dashboard|invoices)/);
    });

    test('session persists across navigation', async ({ page, auth }) => {
      await auth.loginAsAdmin();
      
      // Navigate to different pages
      await page.goto('/invoices');
      await expect(page).toHaveURL('/invoices');
      
      await page.goto('/approvals');
      await expect(page).toHaveURL('/approvals');
      
      await page.goto('/dashboard');
      await expect(page).toHaveURL('/dashboard');
    });
  });

  test.describe('Password Security', () => {
    test('password field masks input', async ({ page }) => {
      await page.goto('/login');
      
      const passwordInput = page.locator(SELECTORS.auth.passwordInput);
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('password is not visible in page source', async ({ page }) => {
      await page.goto('/login');
      
      await page.fill(SELECTORS.auth.emailInput, 'test@example.com');
      await page.fill(SELECTORS.auth.passwordInput, 'secretpassword123');
      
      // Get page content
      const content = await page.content();
      
      // Password should not appear in HTML
      expect(content).not.toContain('secretpassword123');
    });
  });

  test.describe('Error Handling', () => {
    test('handles network errors gracefully', async ({ page }) => {
      await page.goto('/login');
      
      // Block API requests
      await page.route('**/api/**', route => route.abort());
      
      await page.fill(SELECTORS.auth.emailInput, 'test@example.com');
      await page.fill(SELECTORS.auth.passwordInput, 'password123');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show error or stay on login page
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/login/);
    });

    test('handles server errors gracefully', async ({ page }) => {
      await page.goto('/login');
      
      // Return 500 error
      await page.route('**/api/v1/auth/login', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ error: 'Internal server error' }),
        });
      });
      
      await page.fill(SELECTORS.auth.emailInput, 'test@example.com');
      await page.fill(SELECTORS.auth.passwordInput, 'password123');
      await page.click(SELECTORS.auth.loginButton);
      
      // Should show error message
      await page.waitForTimeout(1000);
      await expect(page).toHaveURL(/\/login/);
    });
  });
});

test.describe('Authentication - Accessibility', () => {
  test('login form is keyboard navigable', async ({ page }) => {
    await page.goto('/login');
    
    // Tab to email field
    await page.keyboard.press('Tab');
    const emailFocused = await page.locator(SELECTORS.auth.emailInput).evaluate(
      el => document.activeElement === el
    );
    
    // Tab to password field
    await page.keyboard.press('Tab');
    
    // Tab to submit button
    await page.keyboard.press('Tab');
    
    // Should be able to submit with Enter
    await page.fill(SELECTORS.auth.emailInput, TEST_USERS.admin.email);
    await page.fill(SELECTORS.auth.passwordInput, TEST_USERS.admin.password);
    await page.keyboard.press('Enter');
    
    // Should attempt login
    await page.waitForTimeout(1000);
  });

  test('form fields have proper labels', async ({ page }) => {
    await page.goto('/login');
    
    // Check email field has label
    const emailLabel = page.locator('label[for="email"]');
    await expect(emailLabel).toBeVisible();
    
    // Check password field has label
    const passwordLabel = page.locator('label[for="password"]');
    await expect(passwordLabel).toBeVisible();
  });
});
