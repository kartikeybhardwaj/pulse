import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

function getStorage() {
	if (!browser) return null;
	// If token exists in localStorage, user chose "remember me"
	if (localStorage.getItem('pulse-token')) return localStorage;
	if (sessionStorage.getItem('pulse-token')) return sessionStorage;
	return null;
}

const store = getStorage();
const stored = store?.getItem('pulse-token') || '';
const storedUser = store?.getItem('pulse-user') || '';

export const token = writable(stored);
export const user = writable(storedUser);
export const isLoggedIn = derived(token, (t) => !!t);

let activeStorage = store;

if (browser) {
	token.subscribe((v) => {
		if (!activeStorage) return;
		v ? activeStorage.setItem('pulse-token', v) : activeStorage.removeItem('pulse-token');
	});
	user.subscribe((v) => {
		if (!activeStorage) return;
		v ? activeStorage.setItem('pulse-user', v) : activeStorage.removeItem('pulse-user');
	});
}

export function login(t, u, remember = true) {
	activeStorage = browser ? (remember ? localStorage : sessionStorage) : null;
	token.set(t);
	user.set(u);
}

export function logout() {
	if (browser) {
		localStorage.removeItem('pulse-token');
		localStorage.removeItem('pulse-user');
		sessionStorage.removeItem('pulse-token');
		sessionStorage.removeItem('pulse-user');
	}
	activeStorage = null;
	token.set('');
	user.set('');
}
