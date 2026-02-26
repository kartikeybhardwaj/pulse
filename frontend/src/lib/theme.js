import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const stored = browser && localStorage.getItem('pulse-theme');
export const theme = writable(stored || 'dark');

if (browser) {
	theme.subscribe((v) => {
		localStorage.setItem('pulse-theme', v);
		document.documentElement.setAttribute('data-theme', v);
	});
}
