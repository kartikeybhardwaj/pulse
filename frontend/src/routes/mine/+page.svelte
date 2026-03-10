<script>
	import { api } from '$lib/api.js';
	import { toasts } from '$lib/toast.js';
	import { isLoggedIn } from '$lib/user.js';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		if (!$isLoggedIn) goto('/');
	});

	let polls = $state([]);
	let loading = $state(true);
	let nextCursor = $state(null);
	let loadingMore = $state(false);

	onMount(async () => {
		try {
			const data = await api.getPolls('mine');
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
			const data = await api.getPolls('mine', nextCursor);
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
	async function togglePoll(id) {
		try {
			const res = await api.closePoll(id);
			polls = polls.map((p) => (p.pollId === id ? { ...p, status: res.status } : p));
			toasts.add(res.status === 'closed' ? 'Poll closed' : 'Poll reopened', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		}
	}

	async function deletePoll(id) {
		if (!confirm('Delete this poll?')) return;
		try {
			await api.deletePoll(id);
			polls = polls.filter((p) => p.pollId !== id);
			toasts.add('Poll deleted', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		}
	}
</script>

<svelte:head><title>Pulse — My Polls</title></svelte:head>
<div class="page">
	<h1>My Polls</h1>

	{#if loading}
		<p class="muted">Loading…</p>
	{:else if polls.length === 0}
		<div class="empty">
			<span class="empty-icon">◉</span>
			<p>You haven't created any polls</p>
			<a href="/new">Create your first poll →</a>
		</div>
	{:else}
		<div class="poll-list">
			{#each polls as poll (poll.pollId)}
				<div class="card">
					<a href="/p/{poll.pollId}" class="question">{poll.question}</a>
					<div class="quick-options">
						{#each poll.options as option}
							<button
								class="option-btn"
								class:voted={poll.myVote === option}
								disabled={poll.status !== 'active'}
								onclick={() => quickVote(poll.pollId, option)}
							>
								{option}
							</button>
						{/each}
					</div>
					<div class="card-footer">
						<span class="badge {poll.status}">{poll.status}</span>
						<div class="actions">
							{#if poll.status === 'active'}
								<button class="btn-sm" onclick={() => togglePoll(poll.pollId)}>Close</button>
							{:else if poll.status === 'closed'}
								<button class="btn-sm" onclick={() => togglePoll(poll.pollId)}>Reopen</button>
							{/if}
							<button class="btn-sm danger" onclick={() => deletePoll(poll.pollId)}>Delete</button>
						</div>
					</div>
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
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.question {
		font-weight: 500;
		color: var(--text);
		font-size: 0.95rem;
	}
	.card-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.quick-options {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
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
	.badge {
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		font-size: 0.7rem;
		font-weight: 500;
		background: var(--accent-soft);
		color: var(--accent);
	}
	.badge.closed {
		background: rgba(248, 113, 113, 0.15);
		color: var(--danger);
	}
	.badge.expired {
		background: var(--bg-hover);
		color: var(--text-muted);
	}
	.actions {
		display: flex;
		gap: 0.4rem;
	}
	.btn-sm {
		padding: 0.3rem 0.7rem;
		border-radius: var(--radius-sm);
		font-size: 0.78rem;
		background: var(--bg-hover);
		color: var(--text-muted);
		transition: all var(--transition);
	}
	.btn-sm:hover {
		color: var(--text);
	}
	.btn-sm.danger:hover {
		color: var(--danger);
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
