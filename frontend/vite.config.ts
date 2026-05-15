import { defineConfig } from 'vitest/config';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig(({ mode }) => {
	const isTest = mode === 'test';

	return {
		plugins: [tailwindcss(), sveltekit()],
		...(isTest
			? {
					resolve: {
						conditions: ['browser', 'development']
					}
				}
			: {}),
		test: {
			expect: { requireAssertions: true },
			coverage: {
				provider: 'v8',
				reporter: ['text', 'html', 'lcov'],
				include: ['src/**/*.{ts,svelte}'],
				exclude: ['src/**/*.d.ts', 'src/app.d.ts', 'src/app.html']
			},
			projects: [
				{
					extends: './vite.config.ts',
					test: {
						name: 'server',
						environment: 'jsdom',
						include: ['src/**/*.{test,spec}.{js,ts}', 'tests/unit/**/*.{test,spec}.{js,ts}'],
						exclude: ['src/**/*.svelte.{test,spec}.{js,ts}', 'tests/e2e/**']
					}
				}
			]
		}
	};
});
