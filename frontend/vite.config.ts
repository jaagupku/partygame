import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const apiTarget = process.env.DEV_API_TARGET || 'http://localhost:8000';

// SvelteKit 3 reads its configuration from the Vite plugin instead of svelte.config.js.
// Options SvelteKit does not use itself (such as `inspector`) are forwarded to vite-plugin-svelte.
export const svelteKitConfig = {
	adapter: adapter(),
	preprocess: [vitePreprocess()],
	inspector: true
} satisfies Parameters<typeof sveltekit>[0];

export default defineConfig({
	plugins: [tailwindcss(), sveltekit(svelteKitConfig)],
	server: {
		watch: {
			usePolling: process.env.DEV_USE_POLLING === 'true',
			interval: 300
		},
		proxy: {
			'/api': {
				target: apiTarget,
				ws: true
			}
		}
	}
});
