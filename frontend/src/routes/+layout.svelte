<script>
	import '../app.css';
	import { theme } from '$lib/theme.js';
	import { toasts } from '$lib/toast.js';
	import { user, isLoggedIn, logout } from '$lib/user.js';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let { children } = $props();
	let offline = $state(false);

	onMount(() => {
		offline = !navigator.onLine;
		const on = () => (offline = false);
		const off = () => (offline = true);
		window.addEventListener('online', on);
		window.addEventListener('offline', off);
		return () => {
			window.removeEventListener('online', on);
			window.removeEventListener('offline', off);
		};
	});

	function toggleTheme() {
		theme.update((t) => (t === 'dark' ? 'light' : 'dark'));
	}
</script>

<div class="shell">
	{#if offline}
		<div class="offline-bar">You're offline — some features may not work</div>
	{/if}
	<nav>
		<a href="/" class="logo">◉ Pulse</a>
		<div class="nav-links">
			<a href="/" class:active={$page.url.pathname === '/'}>Recent</a>
			{#if $isLoggedIn}
				<a href="/mine" class:active={$page.url.pathname === '/mine'}>My Polls</a>
				<a href="/new" class:active={$page.url.pathname === '/new'}>Create</a>
			{/if}
		</div>
		{#if $isLoggedIn}
			<span class="user-badge">{$user}</span>
			<button class="nav-btn" onclick={logout}>Sign out</button>
		{:else}
			<a href="/auth" class="nav-btn">Sign in</a>
		{/if}
		<button class="theme-toggle" onclick={toggleTheme} aria-label="Toggle theme">
			{$theme === 'dark' ? '☀' : '☾'}
		</button>
	</nav>

	<main>
		{@render children()}
	</main>

	<div class="toasts">
		{#each $toasts as toast (toast.id)}
			<div class="toast {toast.type}">{toast.message}</div>
		{/each}
	</div>
</div>

<style>
	.shell {
		max-width: 640px;
		margin: 0 auto;
		padding: 0 1rem;
		min-height: 100dvh;
	}
	.offline-bar {
		text-align: center;
		padding: 0.4rem;
		font-size: 0.78rem;
		background: var(--danger);
		color: white;
		border-radius: var(--radius-sm);
		margin-top: 0.5rem;
	}
	nav {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 0;
		border-bottom: 1px solid var(--border);
		margin-bottom: 2rem;
	}
	.logo {
		font-weight: 600;
		font-size: 1.1rem;
		color: var(--text);
		margin-right: auto;
	}
	.nav-links {
		display: flex;
		gap: 0.25rem;
	}
	.nav-links a {
		padding: 0.4rem 0.75rem;
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
		color: var(--text-muted);
		transition: all var(--transition);
	}
	.nav-links a:hover,
	.nav-links a.active {
		color: var(--text);
		background: var(--bg-hover);
	}
	.user-badge {
		font-size: 0.78rem;
		color: var(--text-muted);
		padding: 0.3rem 0.6rem;
		border: 1px solid var(--border);
		border-radius: 999px;
	}
	.nav-btn {
		font-size: 0.8rem;
		padding: 0.35rem 0.7rem;
		border-radius: var(--radius-sm);
		background: var(--bg-hover);
		color: var(--text-muted);
		transition: all var(--transition);
	}
	.nav-btn:hover {
		color: var(--text);
	}
	.theme-toggle {
		background: none;
		font-size: 1.1rem;
		padding: 0.4rem;
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		transition: color var(--transition);
	}
	.theme-toggle:hover {
		color: var(--text);
	}
	main {
		padding-bottom: 4rem;
	}
	.toasts {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		z-index: 100;
	}
	.toast {
		padding: 0.7rem 1rem;
		border-radius: var(--radius-sm);
		font-size: 0.85rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		animation: slideIn 0.2s ease;
	}
	.toast.error {
		border-color: var(--danger);
		color: var(--danger);
	}
	.toast.success {
		border-color: var(--success);
		color: var(--success);
	}
	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
