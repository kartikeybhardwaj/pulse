<script>
	import { api } from '$lib/api.js';
	import { toasts } from '$lib/toast.js';
	import { isLoggedIn } from '$lib/user.js';
	import { onMount } from 'svelte';

	let polls = $state([]);
	let loading = $state(true);
	let nextCursor = $state(null);
	let loadingMore = $state(false);

	onMount(async () => {
		try {
			const data = await api.getPolls('recent');
			polls = data.polls;
			nextCursor = data.nextCursor;
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			loading = false;
		}
	});

	async function loadMore() {
		if (!nextCursor || loadingMore) return;
		loadingMore = true;
		try {
			const data = await api.getPolls('recent', nextCursor);
			polls = [...polls, ...data.polls];
			nextCursor = data.nextCursor;
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			loadingMore = false;
		}
	}

	async function quickVote(pollId, option) {
		try {
			const existing = polls.find((p) => p.pollId === pollId);
			const newVote = existing?.myVote === option ? null : option;
			polls = polls.map((p) => (p.pollId === pollId ? { ...p, myVote: newVote } : p));
			await api.vote(pollId, option);
			const fresh = await api.getPoll(pollId);
			polls = polls.map((p) =>
				p.pollId === pollId ? { ...p, myVote: fresh.myVote, results: fresh.results, totalVotes: fresh.totalVotes } : p
			);
		} catch (e) {
			toasts.add(e.message, 'error');
		}
	}

	function timeAgo(ts) {
		if (!ts) return '';
		const diff = Math.floor(Date.now() / 1000) - ts;
		if (diff < 60) return 'just now';
		if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
		if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
		return `${Math.floor(diff / 86400)}d ago`;
	}
</script>

<svelte:head><title>Pulse — Recent</title></svelte:head>
<div class="page">
	<h1>Recent Polls</h1>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if polls.length === 0}
		<div class="empty">
			<span class="empty-icon">◉</span>
			<p>No polls yet</p>
			{#if $isLoggedIn}
				<a href="/new">Create the first one →</a>
			{/if}
		</div>
	{:else}
		<div class="poll-list">
			{#each polls as poll (poll.pollId)}
				<div class="card">
					<div class="card-header">
						<a href="/p/{poll.pollId}" class="question">{poll.question}</a>
						<span class="meta">
							{poll.creator} · {timeAgo(poll.createdAt)}
							{#if poll.totalVotes}· {poll.totalVotes} vote{poll.totalVotes !== 1 ? 's' : ''}{/if}
							{#if poll.status !== 'active'}
								<span class="badge {poll.status}">{poll.status}</span>
							{/if}
						</span>
					</div>
					{#if poll.status === 'active'}
						<div class="quick-options">
							{#each poll.options as option}
								<button
									class="option-btn"
									class:voted={poll.myVote === option}
									disabled={!$isLoggedIn}
									onclick={() => quickVote(poll.pollId, option)}
								>
									{option}
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
		{#if nextCursor}
			<button class="load-more" onclick={loadMore} disabled={loadingMore}>
				{loadingMore ? 'Loading…' : 'Load more'}
			</button>
		{/if}
	{/if}
</div>

<style>
	.page h1 {
		font-size: 1.3rem;
		font-weight: 600;
		margin-bottom: 1.5rem;
	}
	.muted {
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		padding: 4rem 0;
		text-align: center;
	}
	.empty-icon {
		font-size: 2.5rem;
		color: var(--border);
	}
	.empty p {
		font-size: 0.9rem;
		color: var(--text-muted);
	}
	.empty a {
		font-size: 0.85rem;
	}
	.poll-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
	.card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1rem 1.2rem;
		transition: border-color var(--transition);
	}
	.card:hover {
		border-color: var(--accent);
	}
	.card-header {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.question {
		font-weight: 500;
		color: var(--text);
		font-size: 0.95rem;
	}
	.meta {
		font-size: 0.78rem;
		color: var(--text-muted);
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.badge {
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		font-size: 0.7rem;
		font-weight: 500;
	}
	.badge.closed {
		background: var(--danger);
		color: white;
	}
	.badge.expired {
		background: var(--text-muted);
		color: white;
	}
	.quick-options {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-top: 0.75rem;
	}
	.option-btn {
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		font-size: 0.8rem;
		background: var(--accent-soft);
		color: var(--accent);
		transition: all var(--transition);
	}
	.option-btn:hover {
		background: var(--accent);
		color: white;
	}
	.option-btn.voted {
		background: var(--accent);
		color: white;
	}
	.option-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.load-more {
		width: 100%;
		padding: 0.6rem;
		margin-top: 0.75rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		font-size: 0.85rem;
		transition: all var(--transition);
	}
	.load-more:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--text);
	}
	.load-more:disabled {
		opacity: 0.5;
	}
</style>
