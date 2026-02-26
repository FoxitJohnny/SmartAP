# E2E Test Fixtures

This directory contains test fixtures for E2E tests.

## Files

- `test-data.ts` - Shared test data, selectors, and constants
- `test-helpers.ts` - Authentication helpers and custom test fixtures
- `sample-invoice.pdf` - Sample PDF invoice for upload tests (add your own)
- `sample-invoice.png` - Sample image invoice for upload tests (add your own)

## Adding Test Files

For upload tests, add sample files:

1. `sample-invoice.pdf` - A valid PDF invoice
2. `sample-invoice.png` - A valid image invoice
3. `invalid-file.txt` - An invalid file type for negative testing
4. `large-invoice.pdf` - A large PDF for performance testing

**Note:** Sample files are not committed to the repository. Add your own test files.
