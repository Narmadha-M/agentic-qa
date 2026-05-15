import { chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const PAGES: { name: string; url: string }[] = [
  { name: 'home', url: 'https://example.com/' },
];

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const dir = '.visual-regression/baseline';
  fs.mkdirSync(dir, { recursive: true });

  for (const { name, url } of PAGES) {
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: true });
    console.log(`Captured baseline: ${name}`);
  }

  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
