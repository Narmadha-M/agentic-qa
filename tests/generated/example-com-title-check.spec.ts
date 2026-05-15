import { test, expect } from '@playwright/test';

test('navigates to example.com and checks the page title contains Example Domain', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example Domain/);
});
