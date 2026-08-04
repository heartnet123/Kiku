import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import adapter from '@sveltejs/adapter-vercel';
import { sveltekit } from '@sveltejs/kit/vite';

const apiOrigin: string | null = process.env.PUBLIC_API_BASE_URL
	? new URL(process.env.PUBLIC_API_BASE_URL).origin
	: null;

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter(),
			csp: {
				mode: 'auto',
				directives: {
					'default-src': ['self'],
					'base-uri': ['self'],
					'object-src': ['none'],
					'frame-ancestors': ['none'],
					'img-src': ['self', 'data:', 'blob:'],
					'font-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'script-src': ['self', 'https://code.iconify.design'],
					'connect-src': [
						'self',
						'https://api.iconify.design',
						...(apiOrigin ? [apiOrigin as 'self' | 'https://api.iconify.design'] : [])
					]
				}
			}
		})
	],
	server: {
		proxy: {
			'/api': 'http://localhost:8000'
		}
	},
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'client',
					browser: {
						enabled: true,
						provider: playwright(),
						instances: [{ browser: 'chromium', headless: true }]
					},
					include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
					exclude: ['src/lib/server/**']
				}
			},
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
