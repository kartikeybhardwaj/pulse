import { get } from 'svelte/store';
import { token, logout } from '$lib/user.js';
import { toasts } from '$lib/toast.js';

const BASE = '/api';

async function request(method, path, body) {
	const t = get(token);
	const headers = { 'Content-Type': 'application/json' };
	if (t) headers['Authorization'] = `Bearer ${t}`;
	const opts = { method, headers };
	if (body) opts.body = JSON.stringify(body);
	const res = await fetch(`${BASE}${path}`, opts);
	if (!res.ok) {
		if (res.status === 401 && t && !path.startsWith('/auth/')) {
			logout();
			toasts.add('Session expired — please sign in again', 'error');
			throw new Error('Session expired');
		}
		if (res.status === 429) throw new Error('Too many requests — please slow down');
		const text = await res.text();
		try {
			const err = JSON.parse(text);
			throw new Error(err.error || err.message || 'Request failed');
		} catch (e) {
			if (e.message && !e.message.includes('JSON')) throw e;
			throw new Error(`Request failed (${res.status})`);
		}
	}
	const text = await res.text();
	try {
		return JSON.parse(text);
	} catch {
		throw new Error('Unexpected response from server');
	}
}

export const api = {
	// Auth
	signup: (data) => request('POST', '/auth/signup', data),
	verify: (data) => request('POST', '/auth/verify', data),
	resend: (data) => request('POST', '/auth/resend', data),
	signin: (data) => request('POST', '/auth/signin', data),
	forgot: (data) => request('POST', '/auth/forgot', data),
	resetPassword: (data) => request('POST', '/auth/reset', data),
	me: () => request('GET', '/auth/me'),
	// Polls
	createPoll: (data) => request('POST', '/polls', data),
	getPolls: (filter = 'recent', cursor = '') => {
		let url = `/polls?filter=${filter}&limit=10`;
		if (cursor) url += `&cursor=${encodeURIComponent(cursor)}`;
		return request('GET', url);
	},
	getPoll: (id) => request('GET', `/polls/${id}`),
	closePoll: (id) => request('PATCH', `/polls/${id}`),
	editPoll: (id, data) => request('PUT', `/polls/${id}`, data),
	deletePoll: (id) => request('DELETE', `/polls/${id}`),
	vote: (id, option) => request('POST', `/polls/${id}/vote`, { option })
};
