import { test, expect } from '@playwright/test';

test('user adds 3 items to cart, removes 1, applies a coupon code, and sees the correct discounted total at checkout', async ({ page }) => {
  // Navigation
  await page.goto('http://localhost:3000');
  await page.waitForLoadState('networkidle');

  // --- Add item 1 ---
  const addButtons = page.getByRole('button', { name: /add to cart/i });
  await addButtons.first().click();
  await page.waitForLoadState('networkidle');

  // Capture the price of item 1
  const item1PriceText = await page
    .locator('[data-testid="product-price"], .product-price, .price')
    .first()
    .textContent();
  const item1Price = parseFloat((item1PriceText ?? '0').replace(/[^0-9.]/g, ''));

  // --- Add item 2 ---
  const addButtons2 = page.getByRole('button', { name: /add to cart/i });
  await addButtons2.nth(1).click();
  await page.waitForLoadState('networkidle');

  const item2PriceText = await page
    .locator('[data-testid="product-price"], .product-price, .price')
    .nth(1)
    .textContent();
  const item2Price = parseFloat((item2PriceText ?? '0').replace(/[^0-9.]/g, ''));

  // --- Add item 3 ---
  const addButtons3 = page.getByRole('button', { name: /add to cart/i });
  await addButtons3.nth(2).click();
  await page.waitForLoadState('networkidle');

  const item3PriceText = await page
    .locator('[data-testid="product-price"], .product-price, .price')
    .nth(2)
    .textContent();
  const item3Price = parseFloat((item3PriceText ?? '0').replace(/[^0-9.]/g, ''));

  // --- Navigate to cart ---
  const cartLink = page.getByRole('link', { name: /cart|basket|bag/i });
  await cartLink.click();
  await page.waitForLoadState('networkidle');

  // Assert 3 items are in the cart
  const cartItems = page.locator('[data-testid="cart-item"], .cart-item, .cart-line-item');
  await expect(cartItems).toHaveCount(3);

  // --- Remove the first item from the cart ---
  const removeButton = page.getByRole('button', { name: /remove|delete/i }).first();
  await removeButton.click();
  await page.waitForLoadState('networkidle');

  // Assert 2 items remain
  await expect(cartItems).toHaveCount(2);

  // --- Proceed to checkout ---
  const checkoutButton = page.getByRole('button', { name: /checkout|proceed/i });
  await checkoutButton.click();
  await page.waitForLoadState('networkidle');

  // --- Assert the pre-coupon total reflects item2 + item3 ---
  const preCouponTotal = item2Price + item3Price;
  const totalLocator = page.locator(
    '[data-testid="checkout-total"], [data-testid="order-total"], .checkout-total, .order-total, .total-price'
  );
  await expect(totalLocator).toBeVisible();

  const preCouponTotalText = await totalLocator.textContent();
  const preCouponActual = parseFloat((preCouponTotalText ?? '0').replace(/[^0-9.]/g, ''));

  // Allow a small floating-point tolerance on pre-coupon total
  expect(preCouponActual).toBeCloseTo(preCouponTotal, 2);

  // --- Apply a coupon code ---
  const couponInput = page.getByRole('textbox', { name: /coupon|promo|discount code/i })
    .or(page.getByPlaceholder(/coupon|promo|discount/i))
    .or(page.locator('[data-testid="coupon-input"], [data-testid="promo-input"], #coupon, #promo-code'));
  await expect(couponInput).toBeVisible();
  await couponInput.fill('SAVE10');

  const applyCouponButton = page.getByRole('button', { name: /apply|redeem/i });
  await applyCouponButton.click();
  await page.waitForLoadState('networkidle');

  // Assert a discount/coupon confirmation message is shown
  const couponConfirmation = page.locator(
    '[data-testid="coupon-applied"], [data-testid="discount-applied"], .coupon-success, .promo-success, .discount-message'
  ).or(page.getByText(/coupon applied|promo applied|discount applied|SAVE10/i));
  await expect(couponConfirmation).toBeVisible();

  // --- Assert the discounted total is less than the pre-coupon total ---
  const discountedTotalText = await totalLocator.textContent();
  const discountedActual = parseFloat((discountedTotalText ?? '0').replace(/[^0-9.]/g, ''));

  // The discounted total should be strictly less than the original total
  expect(discountedActual).toBeLessThan(preCouponActual);
  // And it should be greater than zero (sanity check)
  expect(discountedActual).toBeGreaterThan(0);
});
