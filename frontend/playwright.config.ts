import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: './e2e',
	fullyParallel: false,
	workers: 1,
	timeout: 90_000,
	expect: { timeout: 10_000 },
	reporter: 'list',
	use: {
		baseURL: process.env.PRICE_E2E_URL || 'http://127.0.0.1:18080',
		viewport: { width: 2007, height: 1256 },
		trace: 'retain-on-failure',
		screenshot: 'only-on-failure'
	}
});
