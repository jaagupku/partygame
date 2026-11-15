import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteKitConfig } from './vite.config.ts';

export default defineConfig({
	plugins: [sveltekit(svelteKitConfig)],
	resolve: {
		conditions: ['browser']
	},
	test: {
		environment: 'jsdom',
		include: ['src/**/*.test.ts']
	}
});
