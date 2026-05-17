/// <reference types="node" />

import { defineConfig } from '@playwright/test';

const externalBaseURL = process.env.PLAYWRIGHT_BASE_URL?.trim();
const baseURL = externalBaseURL || 'http://127.0.0.1:5173';

export default defineConfig({
	testDir: './tests/e2e',
	testMatch: '**/*.spec.ts',
	use: {
		baseURL
	},
	webServer: externalBaseURL
		? undefined
		: {
				command: 'npm run dev -- --host 127.0.0.1 --port 5173',
				url: 'http://127.0.0.1:5173',
				reuseExistingServer: !process.env.CI,
				timeout: 120_000
			}
});