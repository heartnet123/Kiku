import { writable, get } from 'svelte/store';

export type Theme = 'light' | 'dark' | 'system';

function getInitialTheme(): Theme {
	if (typeof window === 'undefined') return 'system';
	const stored = localStorage.getItem('kiku-theme') as Theme | null;
	if (stored === 'light' || stored === 'dark' || stored === 'system') {
		return stored;
	}
	return 'system';
}

export const themeStore = writable<Theme>('system');

let isInitialized = false;

export function applyTheme(theme: Theme) {
	if (typeof window === 'undefined') return;

	const root = document.documentElement;
	const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
	const isDark = theme === 'dark' || (theme === 'system' && prefersDark);

	if (isDark) {
		root.classList.add('dark');
	} else {
		root.classList.remove('dark');
	}
}

export function initTheme() {
	if (typeof window === 'undefined' || isInitialized) return;
	isInitialized = true;

	const initial = getInitialTheme();
	themeStore.set(initial);
	applyTheme(initial);

	// Watch for system theme changes if set to 'system'
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
		const currentTheme = get(themeStore);
		if (currentTheme === 'system') {
			applyTheme('system');
		}
	});
}

export function setTheme(theme: Theme) {
	if (typeof window === 'undefined') return;
	localStorage.setItem('kiku-theme', theme);
	themeStore.set(theme);
	applyTheme(theme);
}

export function toggleTheme() {
	if (typeof window === 'undefined') return;
	const current = get(themeStore);

	const isCurrentlyDark =
		current === 'dark' ||
		(current === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

	const nextTheme: Theme = isCurrentlyDark ? 'light' : 'dark';
	setTheme(nextTheme);
}
