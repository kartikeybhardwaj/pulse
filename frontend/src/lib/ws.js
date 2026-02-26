import { writable } from 'svelte/store';

const WS_URL = import.meta.env.VITE_WS_URL || '';

let socket = null;
let currentPollId = null;

export const wsData = writable(null);

export function subscribe(pollId) {
	if (!WS_URL) return;
	if (socket) socket.close();
	currentPollId = pollId;

	socket = new WebSocket(WS_URL);
	socket.onopen = () => {
		socket.send(JSON.stringify({ action: 'subscribe', pollId }));
	};
	socket.onmessage = (e) => {
		try {
			const msg = JSON.parse(e.data);
			wsData.set(msg);
		} catch {}
	};
	socket.onclose = () => {
		// Reconnect after 2s
		setTimeout(() => {
			if (currentPollId === pollId) subscribe(pollId);
		}, 2000);
	};
}

export function disconnect() {
	currentPollId = null;
	if (socket) {
		socket.close();
		socket = null;
	}
}
