import { test, expect, type Page } from '@playwright/test';
import { findElement } from '../helpers/locator-heal';

/** Adds the product at grid position `index` (0-based) to the cart. */
async function addProduct(page: Page, index = 0): Promise<void> {
  await page.goto('/');
  const buttons = page
    .getByTestId('add-to-cart-btn')
    .or(page.locator('form button[type="submit"]'));
  await buttons.nth(index).click();
  await page.waitForLoadState('networkidle');
}

// ── Add-to-Cart behaviour ─────────────────────────────────────────────────────

test.describe('Add to Cart', () => {
  test('TC-AC01: clicking Add to Cart shows a success flash message', async ({ page }) => {
    await addProduct(page, 0);
    const { locator: flash } = await findElement(page, {
      description: 'success flash banner',
      testId: 'flash-success',
      css: '.flash-success',
      text: /added to cart/i,
    });
    await expect(flash).toContainText(/added to cart/i);
  });

  test('TC-AC02: cart badge shows count 1 after first add', async ({ page }) => {
    await addProduct(page, 0);
    const { locator: badge } = await findElement(page, {
      description: 'cart badge counter',
      testId: 'cart-badge',
      css: '.badge',
    });
    await expect(badge).toHaveText('1');
  });

  test('TC-AC03: cart badge increments to 2 after adding two different products', async ({ page }) => {
    await addProduct(page, 0);
    await addProduct(page, 1);
    const { locator: badge } = await findElement(page, {
      description: 'cart badge counter',
      testId: 'cart-badge',
      css: '.badge',
    });
    await expect(badge).toHaveText('2');
  });
});

// ── Cart page — single item ───────────────────────────────────────────────────

test.describe('Cart page — single item', () => {
  test.beforeEach(async ({ page }) => {
    await addProduct(page, 0); // Wireless Headphones $59.99
    await page.goto('/cart');
  });

  test('TC-CP01: cart page lists the added item by name', async ({ page }) => {
    const { locator: rows } = await findElement(page, {
      description: 'cart item rows',
      testId: 'cart-item',
      css: '.cart-row',
    });
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toContainText('Wireless Headphones');
  });

  test('TC-CP02: order summary subtotal matches the product price ($59.99)', async ({ page }) => {
    const summaryRows = page.locator('.summary-row');
    await expect(summaryRows.first()).toContainText('$59.99');
  });

  test('TC-CP03: order summary shows FREE shipping', async ({ page }) => {
    const shippingRow = page.locator('.summary-row').filter({ hasText: 'Shipping' });
    await expect(shippingRow).toContainText('FREE');
  });

  test('TC-CP04: increasing quantity updates the qty display and recalculates the total', async ({ page }) => {
    const { locator: increaseBtn } = await findElement(page, {
      description: 'quantity increase button',
      testId: 'qty-increase',
      css: '.qty-form button[value="increase"]',
    });
    await increaseBtn.first().click();
    await page.waitForLoadState('networkidle');

    const { locator: qtyDisplay } = await findElement(page, {
      description: 'quantity number',
      testId: 'qty-num',
      css: '.qty-num',
    });
    await expect(qtyDisplay.first()).toHaveText('2');

    const totalRow = page.locator('.total-row');
    await expect(totalRow).toContainText('$119.98');
  });

  test('TC-CP05: decreasing quantity back to 1 shows correct qty', async ({ page }) => {
    const { locator: increaseBtn } = await findElement(page, {
      description: 'quantity increase button',
      testId: 'qty-increase',
      css: '.qty-form button[value="increase"]',
    });
    await increaseBtn.first().click();
    await page.waitForLoadState('networkidle');

    const { locator: decreaseBtn } = await findElement(page, {
      description: 'quantity decrease button',
      testId: 'qty-decrease',
      css: '.qty-form button[value="decrease"]',
    });
    await decreaseBtn.first().click();
    await page.waitForLoadState('networkidle');

    const { locator: qtyDisplay } = await findElement(page, {
      description: 'quantity number',
      testId: 'qty-num',
      css: '.qty-num',
    });
    await expect(qtyDisplay.first()).toHaveText('1');
  });

  test('TC-CP06: removing the only item reveals the empty cart state', async ({ page }) => {
    const { locator: removeBtn } = await findElement(page, {
      description: 'remove item button',
      testId: 'remove-btn',
      css: 'button[value="remove"]',
    });
    await removeBtn.first().click();
    await page.waitForLoadState('networkidle');

    const { locator: emptyState } = await findElement(page, {
      description: 'empty cart message',
      testId: 'empty-cart',
      css: '.empty-state',
    });
    await expect(emptyState).toContainText(/empty/i);
  });

  test('TC-CP07: Proceed to Checkout button navigates to /checkout', async ({ page }) => {
    const { locator: checkoutBtn } = await findElement(page, {
      description: 'Proceed to Checkout link',
      testId: 'checkout-btn',
      role: 'link',
      roleName: /proceed to checkout/i,
    });
    await checkoutBtn.click();
    await expect(page).toHaveURL(/checkout/);
  });
});

// ── Cart page — multiple items ────────────────────────────────────────────────

test.describe('Cart page — multiple items', () => {
  test('TC-CP08: two different products appear as two separate cart rows', async ({ page }) => {
    await addProduct(page, 0);
    await addProduct(page, 3);
    await page.goto('/cart');

    const { locator: rows } = await findElement(page, {
      description: 'cart item rows',
      testId: 'cart-item',
      css: '.cart-row',
    });
    await expect(rows).toHaveCount(2);
  });
});

// ── Empty cart ────────────────────────────────────────────────────────────────

test.describe('Empty cart', () => {
  test('TC-EC01: visiting /cart when empty shows the Shop Now link', async ({ page }) => {
    await page.goto('/cart');
    const { locator: shopNow } = await findElement(page, {
      description: 'Shop Now link on empty cart',
      testId: 'shop-now-btn',
      role: 'link',
      roleName: 'Shop Now',
    });
    await expect(shopNow).toBeVisible();
  });
});
