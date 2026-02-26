/**
 * API client switcher — uses mock API in demo mode, real API otherwise.
 * Build with VITE_DEMO=true for a fully functional frontend without a backend.
 */

const isDemo = import.meta.env.VITE_DEMO === 'true';

let api;

if (isDemo) {
	const mock = await import('./api.mock.js');
	api = mock.api;
} else {
	const real = await import('./api.real.js');
	api = real.api;
}

export { api };
