import { writable } from 'svelte/store';

function createToasts() {
	const { subscribe, update } = writable([]);
	let id = 0;
	return {
		subscribe,
		add(message, type = 'info') {
			const toast = { id: ++id, message, type };
			update((t) => [...t, toast]);
			setTimeout(() => update((t) => t.filter((x) => x.id !== toast.id)), 3000);
		}
	};
}

export const toasts = createToasts();
