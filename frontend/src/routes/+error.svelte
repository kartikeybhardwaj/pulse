<script>
	import { page } from '$app/stores';
</script>

<div class="error-page">
	<span class="error-icon">◉</span>
	<h2>{$page.status || 'Error'}</h2>
	<p>{$page.error?.message || 'Something went wrong'}</p>
	<a href="/">← Back to Recent</a>
</div>

<style>
	.error-page {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 4rem 0;
		text-align: center;
	}
	.error-icon {
		font-size: 2.5rem;
		color: var(--danger);
	}
	h2 {
		font-size: 1.2rem;
		font-weight: 600;
	}
	p {
		font-size: 0.85rem;
		color: var(--text-muted);
	}
	a {
		margin-top: 0.5rem;
		font-size: 0.85rem;
		color: var(--accent);
	}
</style>
