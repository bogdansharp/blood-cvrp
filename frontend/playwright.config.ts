/// <reference types="node" />

import { defineConfig } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173';

export default defineConfig({
	testDir: './tests/e2e',
	testMatch: '**/*.spec.ts',
	use: { baseURL },
	webServer: process.env.PLAYWRIGHT_BASE_URL
		? undefined
		: {
				command: 'npm run dev -- --host 127.0.0.1 --port 5173',
				url: 'http://127.0.0.1:5173',
				reuseExistingServer: !process.env.CI
			}
});
