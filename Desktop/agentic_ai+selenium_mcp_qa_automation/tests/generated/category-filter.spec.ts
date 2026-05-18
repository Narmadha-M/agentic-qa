import { test, expect } from '@playwright/test';
import { findElement } from '../helpers/locator-heal';

test.describe('Category Filter', () => {
  const ALL_CATEGORIES = [
    'All', 'Accessories', 'Electronics', 'Fitness',
    'Footwear', 'Home', 'Kitchen', 'Stationery',
  ];

  test('TC-CF01: all eight category pill buttons are visible on the home page', async ({ page }) => {
    await page.goto('/');
    for (const cat of ALL_CATEGORIES) {
      const { locator: pill } = await findElement(page, {
        description: `category pill: ${cat}`,
        testId: `cat-btn-${cat}`,
        css: `.cat-btn`,
        text: cat,
      });
      await expect(pill.first()).toBeVisible();
    }
  });

  test('TC-CF02: Electronics shows 2 products — Wireless Headphones and Smart Watch', async ({ page }) => {
    await page.goto('/?category=Electronics');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(2);

    const names = await cards.getByTestId('product-name').or(cards.locator('h3')).allTextContents();
    expect(names.some((n) => n.includes('Headphones'))).toBeTruthy();
    expect(names.some((n) => n.includes('Smart Watch'))).toBeTruthy();

    const { locator: active } = await findElement(page, {
      description: 'active category button',
      testId: 'cat-btn-Electronics',
      css: '.cat-btn.active',
    });
    await expect(active.first()).toContainText('Electronics');
  });

  test('TC-CF03: Fitness shows 2 products — Yoga Mat and Water Bottle', async ({ page }) => {
    await page.goto('/?category=Fitness');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(2);

    const names = await cards.getByTestId('product-name').or(cards.locator('h3')).allTextContents();
    expect(names).toContain('Yoga Mat');
    expect(names).toContain('Water Bottle');
  });

  test('TC-CF04: Footwear shows exactly one product — Running Shoes', async ({ page }) => {
    await page.goto('/?category=Footwear');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(1);
    await expect(cards.getByTestId('product-name').or(cards.locator('h3'))).toContainText('Running Shoes');
  });

  test('TC-CF05: Kitchen shows exactly one product — Coffee Maker', async ({ page }) => {
    await page.goto('/?category=Kitchen');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(1);
    await expect(cards.getByTestId('product-name').or(cards.locator('h3'))).toContainText('Coffee Maker');
  });

  test('TC-CF06: Stationery shows exactly one product — Notebook Set', async ({ page }) => {
    await page.goto('/?category=Stationery');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(1);
    await expect(cards.getByTestId('product-name').or(cards.locator('h3'))).toContainText('Notebook');
  });

  test('TC-CF07: Accessories shows 2 products — Sunglasses and Backpack', async ({ page }) => {
    await page.goto('/?category=Accessories');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(2);

    const names = await cards.getByTestId('product-name').or(cards.locator('h3')).allTextContents();
    expect(names.some((n) => n.includes('Sunglasses'))).toBeTruthy();
    expect(names.some((n) => n.includes('Backpack'))).toBeTruthy();
  });

  test('TC-CF08: Home category shows exactly one product — Desk Lamp', async ({ page }) => {
    await page.goto('/?category=Home');
    const cards = page.getByTestId('product-card').or(page.locator('.card'));
    await expect(cards).toHaveCount(1);
    await expect(cards.getByTestId('product-name').or(cards.locator('h3'))).toContainText('Desk Lamp');
  });
});
