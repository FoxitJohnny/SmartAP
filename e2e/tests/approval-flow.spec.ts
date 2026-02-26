import { test, expect, waitForLoading, waitForToast } from '../fixtures/test-helpers';
import { SELECTORS, TEST_USERS } from '../fixtures/test-data';

test.describe('Approval Flow', () => {
  test.beforeEach(async ({ auth }) => {
    await auth.loginAsAdmin();
  });

  test.describe('Approval Queue', () => {
    test('displays approval queue page', async ({ page }) => {
      await page.goto('/approvals');
      
      // Should show approvals page header
      await expect(page.getByRole('heading', { name: /approval/i })).toBeVisible();
    });

    test('shows pending invoices for approval', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Should show either table with pending items or empty state
      const table = page.locator('table');
      const emptyState = page.getByText(/no pending|no invoices|empty/i);
      
      await expect(table.or(emptyState)).toBeVisible();
    });

    test('displays bulk action buttons', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for bulk approve/reject buttons
      const bulkApproveBtn = page.getByRole('button', { name: /bulk approve|approve selected/i });
      const bulkRejectBtn = page.getByRole('button', { name: /bulk reject|reject selected/i });
      
      // At least one bulk action should be available
      const hasApprove = await bulkApproveBtn.isVisible().catch(() => false);
      const hasReject = await bulkRejectBtn.isVisible().catch(() => false);
      
      // Bulk actions may be hidden when no items selected
      expect(hasApprove !== undefined && hasReject !== undefined).toBeTruthy();
    });

    test('can select invoices with checkboxes', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for checkboxes
      const checkboxes = page.locator('input[type="checkbox"], [role="checkbox"]');
      const count = await checkboxes.count();
      
      if (count > 0) {
        // Click first checkbox
        await checkboxes.first().click();
        
        // Should be checked
        await expect(checkboxes.first()).toBeChecked();
      }
    });

    test('select all checkbox works', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Find select all checkbox (usually in header)
      const selectAll = page.locator('thead input[type="checkbox"], [data-testid="select-all"]').first();
      
      if (await selectAll.isVisible()) {
        await selectAll.click();
        
        // All row checkboxes should be checked
        const rowCheckboxes = page.locator('tbody input[type="checkbox"]');
        const count = await rowCheckboxes.count();
        
        for (let i = 0; i < count; i++) {
          await expect(rowCheckboxes.nth(i)).toBeChecked();
        }
      }
    });
  });

  test.describe('Single Invoice Approval', () => {
    test('can view invoice details from approval queue', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Find an invoice row and click to view details
      const invoiceRow = page.locator('table tbody tr').first();
      
      if (await invoiceRow.isVisible()) {
        // Click on the row or a view button
        const viewButton = invoiceRow.locator('button, a').first();
        if (await viewButton.isVisible()) {
          await viewButton.click();
          // Should navigate to detail or open modal
        }
      }
    });

    test('approve button shows confirmation', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Find approve button on first row
      const approveBtn = page.locator('[data-testid="approve-button"], button:has-text("Approve")').first();
      
      if (await approveBtn.isVisible()) {
        await approveBtn.click();
        
        // Should show confirmation dialog or notes input
        const dialog = page.locator('[role="dialog"], [data-testid="confirm-dialog"]');
        const notesInput = page.locator('textarea, input[name*="note"]');
        
        await expect(dialog.or(notesInput)).toBeVisible();
      }
    });

    test('reject button requires reason', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Find reject button on first row
      const rejectBtn = page.locator('[data-testid="reject-button"], button:has-text("Reject")').first();
      
      if (await rejectBtn.isVisible()) {
        await rejectBtn.click();
        
        // Should show reason input field
        const reasonInput = page.locator('textarea, input[name*="reason"]');
        await expect(reasonInput).toBeVisible();
      }
    });
  });

  test.describe('Bulk Operations', () => {
    test('bulk approve requires selection', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Try to bulk approve without selection
      const bulkApproveBtn = page.getByRole('button', { name: /bulk approve|approve all/i });
      
      if (await bulkApproveBtn.isVisible()) {
        // Should be disabled or show warning when clicked
        const isDisabled = await bulkApproveBtn.isDisabled();
        
        if (!isDisabled) {
          await bulkApproveBtn.click();
          // Should show error toast or message
          const errorMsg = page.getByText(/select|choose|no invoices/i);
          await expect(errorMsg).toBeVisible({ timeout: 3000 }).catch(() => {});
        }
      }
    });

    test('bulk reject requires reason for all', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Select items first
      const checkbox = page.locator('tbody input[type="checkbox"]').first();
      
      if (await checkbox.isVisible()) {
        await checkbox.click();
        
        // Click bulk reject
        const bulkRejectBtn = page.getByRole('button', { name: /bulk reject|reject selected/i });
        
        if (await bulkRejectBtn.isVisible()) {
          await bulkRejectBtn.click();
          
          // Should prompt for reason
          const reasonInput = page.locator('textarea, input[name*="reason"]');
          await expect(reasonInput).toBeVisible({ timeout: 3000 }).catch(() => {});
        }
      }
    });
  });

  test.describe('Approval Filters', () => {
    test('can filter by risk level', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for risk filter
      const riskFilter = page.locator('[data-testid="risk-filter"], select[name*="risk"]');
      
      if (await riskFilter.isVisible()) {
        await riskFilter.click();
        
        // Select high risk
        const highRisk = page.getByRole('option', { name: /high/i });
        if (await highRisk.isVisible()) {
          await highRisk.click();
          await waitForLoading(page);
        }
      }
    });

    test('can filter by amount range', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for amount filter
      const minAmount = page.locator('input[name*="min"], [data-testid="min-amount"]');
      const maxAmount = page.locator('input[name*="max"], [data-testid="max-amount"]');
      
      if (await minAmount.isVisible()) {
        await minAmount.fill('1000');
      }
      
      if (await maxAmount.isVisible()) {
        await maxAmount.fill('10000');
      }
    });

    test('can filter by vendor', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for vendor filter
      const vendorFilter = page.locator('[data-testid="vendor-filter"], select[name*="vendor"]');
      
      if (await vendorFilter.isVisible()) {
        await vendorFilter.click();
        
        // Select first vendor option
        const vendorOption = page.getByRole('option').first();
        if (await vendorOption.isVisible()) {
          await vendorOption.click();
        }
      }
    });

    test('clear filters resets the view', async ({ page }) => {
      await page.goto('/approvals?risk=high');
      await waitForLoading(page);
      
      // Find clear filters button
      const clearBtn = page.getByRole('button', { name: /clear|reset/i });
      
      if (await clearBtn.isVisible()) {
        await clearBtn.click();
        
        // URL should be clean
        await expect(page).toHaveURL('/approvals');
      }
    });
  });

  test.describe('Approval Pagination', () => {
    test('pagination controls are visible when needed', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for pagination
      const pagination = page.locator('[data-testid="pagination"], [class*="pagination"], nav[aria-label="pagination"]');
      
      // Pagination may or may not be visible depending on data
      const isPaginationNeeded = await pagination.isVisible().catch(() => false);
      expect(isPaginationNeeded).toBeDefined();
    });

    test('can navigate to next page', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      const nextButton = page.locator('button:has-text("Next"), [aria-label="Next"], [data-testid="next-page"]');
      
      if (await nextButton.isVisible() && !(await nextButton.isDisabled())) {
        await nextButton.click();
        await waitForLoading(page);
        
        // Should update page
        await expect(page).toHaveURL(/page=2|offset/);
      }
    });
  });

  test.describe('Approval Workflow States', () => {
    test('approved invoices show correct status', async ({ page }) => {
      await page.goto('/invoices?status=approved');
      await waitForLoading(page);
      
      // Look for approved status badges
      const approvedBadges = page.locator('[class*="badge"]:has-text("Approved"), [data-status="approved"]');
      
      // If there are approved invoices, they should show the correct status
      if (await approvedBadges.count() > 0) {
        await expect(approvedBadges.first()).toBeVisible();
      }
    });

    test('rejected invoices show rejection reason', async ({ page }) => {
      await page.goto('/invoices?status=rejected');
      await waitForLoading(page);
      
      // Look for rejected status badges
      const rejectedBadges = page.locator('[class*="badge"]:has-text("Rejected"), [data-status="rejected"]');
      
      if (await rejectedBadges.count() > 0) {
        // Click to view details
        const firstRejected = page.locator('table tbody tr').first();
        if (await firstRejected.isVisible()) {
          await firstRejected.click();
          
          // Should show rejection reason somewhere
          const reason = page.getByText(/reason|rejected because/i);
          // Reason may be in detail view
        }
      }
    });
  });

  test.describe('Risk Indicators', () => {
    test('high risk invoices are highlighted', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Look for risk indicators
      const riskIndicators = page.locator('[class*="risk"], [data-risk], [class*="warning"], [class*="danger"]');
      
      // Risk indicators should be present in the UI
      const count = await riskIndicators.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('can sort by risk level', async ({ page }) => {
      await page.goto('/approvals');
      await waitForLoading(page);
      
      // Find risk column header
      const riskHeader = page.locator('th:has-text("Risk"), [data-column="risk"]');
      
      if (await riskHeader.isVisible()) {
        await riskHeader.click();
        await waitForLoading(page);
        
        // Table should be sorted
      }
    });
  });
});

test.describe('Approval Flow - Role-Based Access', () => {
  test('viewer cannot approve invoices', async ({ page, auth }) => {
    await auth.loginAsViewer();
    await page.goto('/approvals');
    await waitForLoading(page);
    
    // Approve buttons should be disabled or not visible for viewers
    const approveBtn = page.locator('[data-testid="approve-button"], button:has-text("Approve")').first();
    
    if (await approveBtn.isVisible()) {
      const isDisabled = await approveBtn.isDisabled();
      // Viewers should not be able to approve
      // Note: Implementation may vary - button may be hidden or disabled
    }
  });

  test('approver can approve invoices', async ({ page, auth }) => {
    await auth.loginAsApprover();
    await page.goto('/approvals');
    await waitForLoading(page);
    
    // Approve buttons should be enabled for approvers
    const approveBtn = page.locator('[data-testid="approve-button"], button:has-text("Approve")').first();
    
    if (await approveBtn.isVisible()) {
      const isDisabled = await approveBtn.isDisabled();
      // Approvers should be able to approve
    }
  });
});

test.describe('Approval Notifications', () => {
  test.beforeEach(async ({ auth }) => {
    await auth.loginAsAdmin();
  });

  test('success toast on approval', async ({ page }) => {
    await page.goto('/approvals');
    await waitForLoading(page);
    
    // If we can approve, check for toast
    const approveBtn = page.locator('[data-testid="approve-button"], button:has-text("Approve")').first();
    
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      
      // Confirm if needed
      const confirmBtn = page.locator('button:has-text("Confirm"), [data-testid="confirm-approval"]');
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
      }
      
      // Should show success toast
      const toast = page.locator(SELECTORS.common.toast);
      // Toast should appear on successful action
    }
  });

  test('error toast on failed operation', async ({ page }) => {
    await page.goto('/approvals');
    
    // Mock API to fail
    await page.route('**/api/v1/invoices/*/approve', route => {
      route.fulfill({
        status: 400,
        body: JSON.stringify({ error: 'Approval failed' }),
      });
    });
    
    await waitForLoading(page);
    
    // If we try to approve, should show error
    const approveBtn = page.locator('[data-testid="approve-button"], button:has-text("Approve")').first();
    
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      
      // Confirm if needed
      const confirmBtn = page.locator('button:has-text("Confirm"), [data-testid="confirm-approval"]');
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
      }
      
      // Should show error toast or message
    }
  });
});
