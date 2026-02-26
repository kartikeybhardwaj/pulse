<script>
	import { api } from '$lib/api.js';
	import { subscribe, disconnect, wsData } from '$lib/ws.js';
	import { toasts } from '$lib/toast.js';
	import { isLoggedIn } from '$lib/user.js';
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';

	let { data } = $props();
	let poll = $state(null);
	let myVote = $state(null);
	let loading = $state(true);
	let expanded = $state({});
	let showAllVoters = $state({});

	onMount(async () => {
		try {
			poll = await api.getPoll(data.pollId);
			myVote = poll.myVote;
			subscribe(data.pollId);
		} catch (e) {
			// Poll not found — the 404 UI will show, no need for a toast
		} finally {
			loading = false;
		}
	});

	onDestroy(() => disconnect());

	// React to WebSocket updates — refresh full poll to get accurate myVote
	let voting = $state(false);
	$effect(() => {
		const msg = $wsData;
		if (!msg || !poll || voting) return;
		if (msg.type === 'update' || msg.type === 'reset') {
			api.getPoll(data.pollId).then((fresh) => {
				myVote = fresh.myVote;
				poll = fresh;
			});
			if (msg.type === 'reset') toasts.add('Poll was edited — votes have been reset', 'info');
		}
		if (msg.type === 'deleted') {
			toasts.add('Poll was deleted', 'error');
			goto('/');
		}
	});

	async function castVote(option) {
		myVote = myVote === option ? null : option;
		voting = true;
		try {
			await api.vote(data.pollId, option);
			const fresh = await api.getPoll(data.pollId);
			myVote = fresh.myVote;
			poll = fresh;
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			voting = false;
		}
	}

	let actionLoading = $state('');

	async function togglePoll() {
		actionLoading = 'toggle';
		try {
			const res = await api.closePoll(data.pollId);
			poll = { ...poll, status: res.status };
			toasts.add(res.status === 'closed' ? 'Poll closed' : 'Poll reopened', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			actionLoading = '';
		}
	}

	// ── Edit mode ──
	let editing = $state(false);
	let editQuestion = $state('');
	let editDescription = $state('');
	let editQuestionLink = $state('');
	let editOptions = $state([]);
	let editOptionLinks = $state([]);

	function startEdit() {
		editQuestion = poll.question;
		editDescription = poll.description || '';
		editQuestionLink = poll.questionLink || '';
		editOptions = [...poll.options];
		editOptionLinks = poll.results.map((r) => r.link || '');
		editing = true;
	}

	async function saveEdit() {
		const trimmed = editOptions.map((o) => o.trim()).filter(Boolean);
		if (!editQuestion.trim() || trimmed.length < 2) {
			toasts.add('Need question and at least 2 options', 'error');
			return;
		}
		actionLoading = 'save';
		try {
			const res = await api.editPoll(data.pollId, {
				question: editQuestion.trim(),
				description: editDescription.trim() || undefined,
				questionLink: editQuestionLink.trim() || undefined,
				options: trimmed,
				optionLinks: editOptionLinks.slice(0, trimmed.length)
			});
			poll = await api.getPoll(data.pollId);
			myVote = poll.myVote;
			editing = false;
			toasts.add(res.votesReset ? 'Poll updated — votes were reset' : 'Poll updated', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			actionLoading = '';
		}
	}

	async function deletePoll() {
		if (!confirm('Delete this poll?')) return;
		actionLoading = 'delete';
		try {
			await api.deletePoll(data.pollId);
			toasts.add('Poll deleted', 'success');
			goto('/');
		} catch (e) {
			toasts.add(e.message, 'error');
			actionLoading = '';
		}
	}

	function toggleExpand(option) {
		expanded = { ...expanded, [option]: !expanded[option] };
	}

	function pct(count, total) {
		return total > 0 ? Math.round((count / total) * 100) : 0;
	}

	function timeLeft(ts) {
		if (!ts) return null;
		const diff = ts - Math.floor(Date.now() / 1000);
		if (diff <= 0) return 'Expired';
		if (diff < 3600) return `${Math.floor(diff / 60)}m`;
		if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
		if (diff < 2592000) return `${Math.floor(diff / 86400)}d`;
		return `${Math.floor(diff / 2592000)}mo`;
	}

	function copyLink() {
		navigator.clipboard.writeText(window.location.href);
		toasts.add('Link copied!', 'success');
	}
</script>

<svelte:head
	><title>{poll ? `Pulse — ${poll.question.slice(0, 50)}` : loading ? 'Pulse' : 'Pulse — Not Found'}</title
	></svelte:head
>

{#if loading}
	<p class="muted">Loading…</p>
{:else if !poll}
	<div class="not-found">
		<span class="nf-icon">◉</span>
		<h2>Poll not found</h2>
		<p>This poll may have been deleted or the link is invalid.</p>
		<a href="/" class="nf-link">← Back to Recent</a>
	</div>
{:else}
	<div class="poll-page">
		{#if editing}
			<div class="edit-form">
				<h1>Edit Poll</h1>
				<label>
					<span>Question</span>
					<input type="text" bind:value={editQuestion} maxlength="140" />
				</label>
				<label>
					<span>Description</span>
					<input type="text" bind:value={editDescription} maxlength="160" placeholder="Brief context for voters" />
				</label>
				<label>
					<span>Question Link</span>
					<input type="url" bind:value={editQuestionLink} placeholder="https://..." />
				</label>
				{#each editOptions as _, i}
					<div class="edit-option">
						<input type="text" bind:value={editOptions[i]} placeholder="Option {i + 1}" maxlength="140" />
						<input type="url" class="link-input" bind:value={editOptionLinks[i]} placeholder="Link (optional)" />
					</div>
				{/each}
				<div class="edit-actions">
					<button class="btn-primary" onclick={saveEdit} disabled={actionLoading === 'save'}>
						{actionLoading === 'save' ? 'Saving…' : 'Save'}
					</button>
					<button class="btn-secondary" onclick={() => (editing = false)}>Cancel</button>
				</div>
			</div>
		{:else}
			<div class="header">
				<h1>
					{poll.question}
					{#if poll.questionLink}
						<a href={poll.questionLink} target="_blank" rel="noopener" class="q-link" data-tooltip={poll.questionLink}
							>🔗</a
						>
					{/if}
				</h1>
				{#if poll.description}
					<p class="description">{poll.description}</p>
				{/if}
				<div class="meta">
					<span>{poll.creator}</span>
					<span>·</span>
					<span>{poll.totalVotes} vote{poll.totalVotes !== 1 ? 's' : ''}</span>
					{#if poll.status === 'scheduled' && poll.startsAt}
						<span>·</span>
						<span>🕐 starts in {timeLeft(poll.startsAt)}</span>
					{:else if timeLeft(poll.expiresAt)}
						<span>·</span>
						<span>⏳ {timeLeft(poll.expiresAt)} to vote</span>
					{/if}
					{#if timeLeft(poll.deletesAt)}
						<span>·</span>
						<span>🗑️ {timeLeft(poll.deletesAt)} to auto-delete</span>
					{/if}
				</div>
				<div class="badges">
					{#if poll.anonCreator}
						<span class="badge">🔒 Anonymous creator</span>
					{/if}
					{#if poll.private}
						<span class="badge">🔗 Private</span>
					{/if}
					{#if poll.anonVoters}
						<span class="badge">🔒 Anonymous votes</span>
					{:else if poll.visibleVoters}
						<span class="badge">👤 Voters visible</span>
					{/if}
					{#if poll.status !== 'active'}
						<span class="badge status">{poll.status}</span>
					{/if}
				</div>
			</div>

			<div class="results">
				{#each poll.results as r (r.option)}
					{@const p = pct(r.count, poll.totalVotes)}
					{@const canVote = poll.status === 'active' && $isLoggedIn}
					<div class="result-wrapper">
						<button
							class="result-row"
							class:voted={myVote === r.option}
							class:clickable={canVote}
							onclick={() => canVote && castVote(r.option)}
							disabled={!canVote}
						>
							<div class="bar" style="width: {p}%"></div>
							<div class="result-content">
								<span class="option-label">
									{r.option}
									{#if myVote === r.option}
										<span class="check">✓</span>
									{/if}
								</span>
								<span class="count">{r.count} ({p}%)</span>
							</div>
						</button>
						{#if r.link}
							<a href={r.link} target="_blank" rel="noopener" class="opt-link" data-tooltip={r.link}>🔗</a>
						{/if}
					</div>

					{#if r.voters && r.voters.length > 0}
						<button class="voter-toggle" onclick={() => toggleExpand(r.option)}>
							{expanded[r.option] ? '▾' : '▸'}
							{r.voters.length} voter{r.voters.length !== 1 ? 's' : ''}
						</button>
						{#if expanded[r.option]}
							{@const limit = showAllVoters[r.option] ? r.voters.length : 10}
							{@const visible = r.voters.slice(0, limit)}
							{@const remaining = r.voters.length - visible.length}
							<div class="voter-list">
								{#each visible as voter}
									<span class="voter">{voter}</span>
								{/each}
								{#if remaining > 0}
									<button class="voter-more" onclick={() => (showAllVoters = { ...showAllVoters, [r.option]: true })}>
										+{remaining} more
									</button>
								{/if}
							</div>
						{/if}
					{/if}
				{/each}
			</div>

			<div class="actions">
				<button class="btn-secondary" onclick={copyLink}>Copy link</button>
				{#if poll.isOwner && $isLoggedIn}
					{#if poll.status === 'active'}
						<button class="btn-secondary" onclick={startEdit} disabled={!!actionLoading}>Edit</button>
						<button class="btn-secondary" onclick={togglePoll} disabled={!!actionLoading}>
							{actionLoading === 'toggle' ? 'Closing…' : 'Close poll'}
						</button>
					{:else if poll.status === 'closed'}
						<button class="btn-secondary" onclick={togglePoll} disabled={!!actionLoading}>
							{actionLoading === 'toggle' ? 'Reopening…' : 'Reopen poll'}
						</button>
					{/if}
					<button class="btn-danger" onclick={deletePoll} disabled={!!actionLoading}>
						{actionLoading === 'delete' ? 'Deleting…' : 'Delete'}
					</button>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.muted {
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.not-found {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 4rem 0;
		text-align: center;
	}
	.nf-icon {
		font-size: 2.5rem;
		color: var(--border);
	}
	.not-found h2 {
		font-size: 1.2rem;
		font-weight: 600;
	}
	.not-found p {
		font-size: 0.85rem;
		color: var(--text-muted);
	}
	.nf-link {
		margin-top: 0.5rem;
		font-size: 0.85rem;
		color: var(--accent);
	}
	.poll-page {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	.header h1 {
		font-size: 1.4rem;
		font-weight: 600;
		line-height: 1.3;
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	.description {
		font-size: 0.85rem;
		color: var(--text-muted);
		margin-top: 0.2rem;
	}
	.q-link,
	.opt-link {
		font-size: 0.75rem;
		color: var(--accent);
		text-decoration: none;
		position: relative;
		opacity: 0.7;
		transition: opacity var(--transition);
	}
	.q-link:hover,
	.opt-link:hover {
		opacity: 1;
	}
	.q-link[data-tooltip]:hover::after,
	.opt-link[data-tooltip]:hover::after {
		content: attr(data-tooltip);
		position: absolute;
		bottom: 100%;
		left: 50%;
		transform: translateX(-50%);
		padding: 0.35rem 0.6rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-size: 0.7rem;
		color: var(--text-muted);
		white-space: nowrap;
		max-width: 300px;
		overflow: hidden;
		text-overflow: ellipsis;
		z-index: 10;
		pointer-events: none;
	}
	.result-wrapper {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	.result-wrapper .result-row {
		flex: 1;
	}
	.opt-link {
		font-size: 0.8rem;
	}
	.meta {
		display: flex;
		gap: 0.4rem;
		font-size: 0.82rem;
		color: var(--text-muted);
		margin-top: 0.4rem;
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-top: 0.5rem;
	}
	.badge {
		padding: 0.2rem 0.6rem;
		border-radius: 999px;
		font-size: 0.72rem;
		background: var(--accent-soft);
		color: var(--accent);
	}
	.badge.status {
		background: var(--danger);
		color: white;
	}
	.results {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.result-row {
		position: relative;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 0.75rem 1rem;
		overflow: hidden;
		text-align: left;
		color: var(--text);
		transition:
			border-color var(--transition),
			background var(--transition);
	}
	.result-row.clickable:hover {
		border-color: var(--accent);
	}
	.result-row.voted {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.bar {
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		background: var(--accent-soft);
		transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
		border-radius: var(--radius-sm);
	}
	.result-content {
		position: relative;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.option-label {
		font-weight: 500;
		font-size: 0.9rem;
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}
	.check {
		color: var(--accent);
		font-size: 0.85rem;
	}
	.count {
		font-size: 0.82rem;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}
	.voter-toggle {
		background: none;
		color: var(--text-muted);
		font-size: 0.78rem;
		padding: 0.2rem 0;
		text-align: left;
	}
	.voter-toggle:hover {
		color: var(--text);
	}
	.voter-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		padding-left: 0.5rem;
	}
	.voter {
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		background: var(--bg-hover);
		border-radius: 999px;
		color: var(--text-muted);
	}
	.voter-more {
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		background: var(--accent-soft);
		border-radius: 999px;
		color: var(--accent);
	}
	.voter-more:hover {
		background: var(--accent);
		color: white;
	}
	.actions {
		display: flex;
		gap: 0.5rem;
	}
	.btn-secondary {
		padding: 0.5rem 1rem;
		background: var(--bg-hover);
		color: var(--text-muted);
		border-radius: var(--radius-sm);
		font-size: 0.82rem;
		transition: all var(--transition);
	}
	.btn-secondary:hover {
		color: var(--text);
	}
	.btn-danger {
		padding: 0.5rem 1rem;
		background: var(--bg-hover);
		color: var(--text-muted);
		border-radius: var(--radius-sm);
		font-size: 0.82rem;
		transition: all var(--transition);
	}
	.btn-danger:hover {
		color: var(--danger);
	}
	.edit-form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.edit-form h1 {
		font-size: 1.3rem;
		font-weight: 600;
	}
	.edit-form label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.edit-form label > span {
		font-size: 0.82rem;
		font-weight: 500;
		color: var(--text-muted);
	}
	.edit-option {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.link-input {
		font-size: 0.8rem;
		padding: 0.4rem 0.8rem;
		opacity: 0.7;
	}
	.edit-actions {
		display: flex;
		gap: 0.5rem;
	}
	.btn-primary {
		padding: 0.5rem 1rem;
		background: var(--accent);
		color: white;
		border-radius: var(--radius-sm);
		font-size: 0.82rem;
		transition: background var(--transition);
	}
	.btn-primary:hover {
		background: var(--accent-hover);
	}
</style>
