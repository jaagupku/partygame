import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const apiTarget = process.env.DEV_API_TARGET || 'http://localhost:8000';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
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
