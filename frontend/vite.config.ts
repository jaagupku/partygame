import { purgeCss } from 'vite-plugin-tailwind-purgecss';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit(), purgeCss()],
	server: {
		proxy: {
			"/api": "http://localhost:8000",
			"/api/v1/game": {
				target: "ws://localhost:8000",
				ws: true,
			},
		},
	},
});