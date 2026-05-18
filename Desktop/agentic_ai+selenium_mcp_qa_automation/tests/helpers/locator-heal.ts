import { type Locator, type Page } from '@playwright/test';

/**
 * Describes all the ways a test might find a particular element.
 * Strategies are tried in priority order: testId → ariaLabel → placeholder
 * → role → text → css. The first one that resolves to an attached element wins.
 */
export interface ElementSpec {
  /** Human-readable description used in error messages */
  description: string;
  /** data-testid attribute value — most stable; survives CSS/text refactors */
  testId?: string;
  /** aria-label value — semantic and stable */
  ariaLabel?: string;
  /** input placeholder text */
  placeholder?: string;
  /** ARIA role */
  role?: Parameters<Page['getByRole']>[0];
  /** Accessible name for role-based lookup */
  roleName?: string | RegExp;
  /** Visible text content */
  text?: string | RegExp;
  /** CSS selector — fallback when semantic strategies fail */
  css?: string;
}

export interface FindResult {
  locator: Locator;
  /** Name of the strategy that succeeded */
  usedStrategy: string;
  /** true when a fallback strategy was used because the primary failed */
  healed: boolean;
}

/**
 * Tries each strategy in ElementSpec until one resolves to an attached element.
 * Logs a [HEALED] warning whenever a fallback strategy is used so the test
 * report makes self-healing visible.
 */
export async function findElement(page: Page, spec: ElementSpec): Promise<FindResult> {
  type Strategy = { name: string; get: () => Locator };
  const strategies: Strategy[] = [];

  if (spec.testId)
    strategies.push({ name: 'testId', get: () => page.getByTestId(spec.testId!) });
  if (spec.ariaLabel)
    strategies.push({ name: 'ariaLabel', get: () => page.getByLabel(spec.ariaLabel!) });
  if (spec.placeholder)
    strategies.push({ name: 'placeholder', get: () => page.getByPlaceholder(spec.placeholder!) });
  if (spec.role)
    strategies.push({
      name: 'role',
      get: () => page.getByRole(spec.role!, spec.roleName ? { name: spec.roleName } : undefined),
    });
  if (spec.text)
    strategies.push({ name: 'text', get: () => page.getByText(spec.text!, { exact: false }) });
  if (spec.css)
    strategies.push({ name: 'css', get: () => page.locator(spec.css!) });

  if (strategies.length === 0) {
    throw new Error(`ELEMENT_NOT_FOUND: "${spec.description}" — no strategies defined`);
  }

  const primaryName = strategies[0].name;

  for (let i = 0; i < strategies.length; i++) {
    const { name, get } = strategies[i];
    try {
      const locator = get();
      await locator.first().waitFor({ state: 'attached', timeout: 3000 });
      if (i > 0) {
        console.warn(
          `[HEALED] "${spec.description}": primary "${primaryName}" failed — succeeded via "${name}"`
        );
      }
      return { locator, usedStrategy: name, healed: i > 0 };
    } catch {
      // strategy failed — try the next one
    }
  }

  throw new Error(
    `ELEMENT_NOT_FOUND: "${spec.description}" — exhausted all strategies: [${strategies
      .map((s) => s.name)
      .join(', ')}]`
  );
}
