import { test, expect } from '@playwright/test';
import { findElement } from '../helpers/locator-heal';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('TC-H01: page loads with ShopEasy in the title', async ({ page }) => {
    await expect(page).toHaveTitle(/ShopEasy/);
  });

  test('TC-H02: product grid displays all 10 products', async ({ page }) => {
    const { locator: grid } = await findElement(page, {
      description: 'product grid',
      testId: 'product-grid',
      css: '.product-grid',
    });
    const cards = grid.getByTestId('product-card').or(grid.locator('.card'));
    await expect(cards).toHaveCount(10);
  });

  test('TC-H03: hero banner shows welcome headline and quality-products tagline', async ({ page }) => {
    const { locator: hero } = await findElement(page, {
      description: 'hero section',
      testId: 'hero-section',
      css: '.hero',
    });
    await expect(hero).toContainText('Welcome to ShopEasy');
    await expect(hero).toContainText('quality products');
  });

  test('TC-H04: navbar contains Home link and Cart link', async ({ page }) => {
    const { locator: homeLink } = await findElement(page, {
      description: 'Home nav link',
      testId: 'nav-home',
      role: 'link',
      roleName: 'Home',
    });
    await expect(homeLink).toBeVisible();

    const { locator: cartLink } = await findElement(page, {
      description: 'Cart nav link',
      testId: 'nav-cart',
      css: '.cart-link',
    });
    await expect(cartLink).toContainText('Cart');
  });

  test('TC-H05: every product card shows a dollar price and an Add-to-Cart button', async ({ page }) => {
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);

    for (let i = 0; i < count; i++) {
      const card = cards.nth(i);
      const price = card.getByTestId('product-price').or(card.locator('.price'));
      await expect(price).toContainText('$');
      const btn = card
        .getByRole('button', { name: /add to cart/i })
        .or(card.locator('button[type="submit"]'));
      await expect(btn).toBeVisible();
    }
  });
});
