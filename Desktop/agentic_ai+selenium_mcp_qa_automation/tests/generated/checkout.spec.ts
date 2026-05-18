import { test, expect, type Page } from '@playwright/test';
import { findElement } from '../helpers/locator-heal';

/**
 * Adds Wireless Headphones ($59.99) + Coffee Maker ($44.99) = $104.98 total,
 * then navigates to /checkout.
 */
async function setupCartAndGoToCheckout(page: Page): Promise<void> {
  await page.goto('/');
  // index 0 → Wireless Headphones
  await page.getByTestId('add-to-cart-btn').or(page.locator('form button[type="submit"]')).nth(0).click();
  await page.waitForLoadState('networkidle');
  await page.goto('/');
  // index 2 → Coffee Maker
  await page.getByTestId('add-to-cart-btn').or(page.locator('form button[type="submit"]')).nth(2).click();
  await page.waitForLoadState('networkidle');
  await page.goto('/checkout');
  await page.waitForLoadState('networkidle');
}

test.describe('Checkout', () => {
  test('TC-CO01: visiting checkout with an empty cart redirects to home with a flash message', async ({ page }) => {
    await page.goto('/checkout');
    await expect(page).toHaveURL('http://localhost:5050/');

    const { locator: flash } = await findElement(page, {
      description: 'empty-cart flash message',
      testId: 'flash-info',
      css: '.flash-info',
    });
    await expect(flash).toContainText(/empty/i);
  });

  test('TC-CO02: checkout form has Contact, Shipping, and Payment sections', async ({ page }) => {
    await setupCartAndGoToCheckout(page);

    const { locator: form } = await findElement(page, {
      description: 'checkout form',
      testId: 'checkout-form',
      css: '.checkout-form',
    });
    const sections = form.locator('.form-section');
    await expect(sections).toHaveCount(3);

    const headings = await sections.locator('h3').allTextContents();
    expect(headings).toContain('Contact Information');
    expect(headings).toContain('Shipping Address');
    expect(headings).toContain('Payment Details');
  });

  test('TC-CO03: order review panel lists 2 items', async ({ page }) => {
    await setupCartAndGoToCheckout(page);
    const reviewItems = page.locator('.review-item');
    await expect(reviewItems).toHaveCount(2);
  });

  test('TC-CO04: order review total is $104.98 (Headphones + Coffee Maker)', async ({ page }) => {
    await setupCartAndGoToCheckout(page);
    const { locator: totalEl } = await findElement(page, {
      description: 'order review total',
      css: '.review-total',
    });
    await expect(totalEl).toContainText('$104.98');
  });

  test('TC-CO05: submitting the form with empty required fields stays on checkout', async ({ page }) => {
    await setupCartAndGoToCheckout(page);
    const { locator: submitBtn } = await findElement(page, {
      description: 'Place Order button',
      testId: 'place-order-btn',
      role: 'button',
      roleName: /place order/i,
      css: 'button[type="submit"]',
    });
    // Click without filling any fields — Flask re-renders with an error flash
    await submitBtn.click();
    await expect(page).toHaveURL(/checkout/);
  });

  test('TC-CO06: completing checkout with valid details shows the success page', async ({ page }) => {
    await setupCartAndGoToCheckout(page);

    // Fill required fields using healing locators (label → name attr → placeholder fallback)
    const nameField = page
      .getByLabel(/full name/i)
      .or(page.locator('input[name="name"]'));
    await nameField.fill('Jane Doe');

    const emailField = page
      .getByLabel(/email/i)
      .or(page.locator('input[name="email"]'));
    await emailField.fill('jane@example.com');

    const addressField = page
      .getByLabel(/street address/i)
      .or(page.locator('input[name="address"]'));
    await addressField.fill('123 Main St, New York');

    // Payment fields are optional in the Flask app but fill them for realism
    const cardField = page.locator('input[name="card"]');
    if (await cardField.count()) await cardField.fill('4111111111111111');
    const expiryField = page.locator('input[name="expiry"]');
    if (await expiryField.count()) await expiryField.fill('12/26');
    const cvvField = page.locator('input[name="cvv"]');
    if (await cvvField.count()) await cvvField.fill('123');

    const { locator: submitBtn } = await findElement(page, {
      description: 'Place Order button',
      testId: 'place-order-btn',
      role: 'button',
      roleName: /place order/i,
      css: 'button[type="submit"]',
    });
    await submitBtn.click();

    // Verify the success page
    const { locator: successPage } = await findElement(page, {
      description: 'order success page container',
      testId: 'success-page',
      css: '.success-page',
    });
    await expect(successPage).toBeVisible();

    const { locator: title } = await findElement(page, {
      description: 'Order Placed heading',
      testId: 'success-title',
      role: 'heading',
      roleName: /order placed/i,
      css: 'h1',
    });
    await expect(title).toContainText('Order Placed');

    const { locator: msg } = await findElement(page, {
      description: 'success confirmation message',
      testId: 'success-msg',
      css: '.success-msg',
    });
    await expect(msg).toContainText('Jane Doe');
    await expect(page.locator('body')).toContainText('$104.98');
  });
});
