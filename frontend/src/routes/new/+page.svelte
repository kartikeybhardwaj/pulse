<script>
	import { api } from '$lib/api.js';
	import { toasts } from '$lib/toast.js';
	import { isLoggedIn } from '$lib/user.js';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		if (!$isLoggedIn) goto('/');
	});

	let question = $state('');
	let description = $state('');
	let questionLink = $state('');
	let options = $state([
		{ text: '', link: '' },
		{ text: '', link: '' }
	]);
	let expiry = $state('24h');
	let useCustomSchedule = $state(false);
	let startDt = $state('');
	let endDt = $state('');

	function initScheduleDefaults() {
		const now = new Date();
		const mins = now.getMinutes();
		const next = Math.ceil((mins + 1) / 15) * 15;
		const start = new Date(now);
		start.setSeconds(0, 0);
		start.setMinutes(next); // JS auto-rolls hour if >= 60
		const end = new Date(start.getTime() + 86400000);
		startDt = fmt(start);
		endDt = fmt(end);
	}

	function fmt(d) {
		const p = (n) => String(n).padStart(2, '0');
		return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
	}

	function parseDt(s) {
		if (!s || s.length < 16) return null;
		const t = new Date(s.replace(' ', 'T'));
		return isNaN(t) ? null : Math.floor(t.getTime() / 1000);
	}
	let anonCreator = $state(false);
	let anonVoters = $state(false);
	let visibleVoters = $state(false);
	let isPrivate = $state(false);
	let submitting = $state(false);

	function addOption() {
		if (options.length < 5) options = [...options, { text: '', link: '' }];
	}

	function removeOption(i) {
		if (options.length > 2) options = options.filter((_, idx) => idx !== i);
	}

	async function submit() {
		const valid = options.filter((o) => o.text.trim());
		if (!question.trim() || valid.length < 2) {
			toasts.add('Need a question and at least 2 options', 'error');
			return;
		}
		if (useCustomSchedule) {
			const now = Date.now() / 1000;
			const s = parseDt(startDt);
			const e = parseDt(endDt);
			if (s && s < now) {
				toasts.add('Start time cannot be in the past', 'error');
				return;
			}
			if (!e) {
				toasts.add('End time is required', 'error');
				return;
			}
			if (e > now + 10368000) {
				toasts.add('End time cannot be more than 4 months from now', 'error');
				return;
			}
			if (s && e <= s) {
				toasts.add('End time must be after start time', 'error');
				return;
			}
		}
		submitting = true;
		try {
			const data = await api.createPoll({
				question: question.trim(),
				description: description.trim() || undefined,
				questionLink: questionLink.trim() || undefined,
				options: valid.map((o) => o.text.trim()),
				optionLinks: valid.map((o) => o.link.trim()),
				expiry: useCustomSchedule ? undefined : expiry || undefined,
				startsAt: useCustomSchedule ? parseDt(startDt) : undefined,
				endsAt: useCustomSchedule ? parseDt(endDt) : undefined,
				anonCreator,
				anonVoters,
				visibleVoters: !anonVoters && visibleVoters,
				private: isPrivate
			});
			toasts.add('Poll created!', 'success');
			goto(`/p/${data.pollId}`);
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head><title>Pulse — Create</title></svelte:head>
<div class="page">
	<h1>Create Poll</h1>

	<form
		onsubmit={(e) => {
			e.preventDefault();
			submit();
		}}
	>
		<label>
			<span>Question <small>({140 - question.length} chars left)</small></span>
			<input type="text" bind:value={question} placeholder="What do you want to ask?" maxlength="140" />
		</label>

		<label>
			<span>Description <small>(optional, {160 - description.length} chars left)</small></span>
			<input type="text" bind:value={description} placeholder="Brief context for voters" maxlength="160" />
		</label>

		<label>
			<span>Question Link <small>(optional)</small></span>
			<input type="url" bind:value={questionLink} placeholder="https://..." />
		</label>

		<fieldset>
			<legend>Options</legend>
			{#each options as opt, i}
				<div class="option-group">
					<div class="option-row">
						<input type="text" bind:value={options[i].text} placeholder="Option {i + 1}" maxlength="140" />
						<span class="char-count">{140 - options[i].text.length} left</span>
						{#if options.length > 2}
							<button type="button" class="remove-btn" onclick={() => removeOption(i)}>×</button>
						{/if}
					</div>
					<input type="url" class="link-input" bind:value={options[i].link} placeholder="Link (optional)" />
				</div>
			{/each}
			{#if options.length < 5}
				<button type="button" class="add-btn" onclick={addOption}>+ Add option</button>
			{/if}
		</fieldset>

		<fieldset>
			<legend>Schedule</legend>
			<label class="toggle">
				<span>
					<strong>Custom schedule</strong>
					<small>Set specific start and end times</small>
				</span>
				<input
					type="checkbox"
					bind:checked={useCustomSchedule}
					onchange={() => {
						if (useCustomSchedule) initScheduleDefaults();
					}}
				/>
				<span class="pill"></span>
			</label>

			{#if useCustomSchedule}
				<label>
					<span>Start <small>(optional — leave empty to start immediately)</small></span>
					<input type="text" bind:value={startDt} placeholder="YYYY-MM-DD HH:MM" maxlength="16" class="dt-input" />
				</label>
				<label>
					<span>End <small>(required)</small></span>
					<input type="text" bind:value={endDt} placeholder="YYYY-MM-DD HH:MM" maxlength="16" class="dt-input" />
				</label>
			{:else}
				<label>
					<span>Voting duration</span>
					<select bind:value={expiry}>
						<option value="1h">1 hour</option>
						<option value="6h">6 hours</option>
						<option value="24h">24 hours</option>
						<option value="7d">7 days</option>
						<option value="30d">30 days</option>
						<option value="4mo">4 months</option>
					</select>
				</label>
			{/if}
			<small class="hint">All poll data is automatically deleted 6 months after creation.</small>
		</fieldset>

		<fieldset class="toggles">
			<legend>Privacy</legend>

			<label class="toggle">
				<span>
					<strong>Private Poll</strong>
					<small>Only accessible via direct link — hidden from Recent</small>
				</span>
				<input type="checkbox" bind:checked={isPrivate} />
				<span class="pill"></span>
			</label>

			<label class="toggle">
				<span>
					<strong>Anonymous Creator</strong>
					<small>Hide your identity from voters</small>
				</span>
				<input type="checkbox" bind:checked={anonCreator} />
				<span class="pill"></span>
			</label>

			<label class="toggle">
				<span>
					<strong>Anonymous Voters</strong>
					<small>Hide who voted for what from everyone</small>
				</span>
				<input type="checkbox" bind:checked={anonVoters} />
				<span class="pill"></span>
			</label>

			<label class="toggle" class:disabled={anonVoters}>
				<span>
					<strong>Visible Voters</strong>
					<small>Show who voted for each option</small>
				</span>
				<input type="checkbox" bind:checked={visibleVoters} disabled={anonVoters} />
				<span class="pill"></span>
			</label>
		</fieldset>

		<button type="submit" class="submit-btn" disabled={submitting}>
			{submitting ? 'Creating…' : 'Create Poll'}
		</button>
	</form>
</div>

<style>
	.page h1 {
		font-size: 1.3rem;
		font-weight: 600;
		margin-bottom: 1.5rem;
	}
	form {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}
	label > span {
		font-size: 0.82rem;
		font-weight: 500;
		color: var(--text-muted);
	}
	.hint {
		font-size: 0.75rem;
		color: var(--text-muted);
		opacity: 0.7;
	}
	.dt-input {
		font-family: var(--font);
		font-variant-numeric: tabular-nums;
		letter-spacing: 0.03em;
	}
	fieldset {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	legend {
		font-size: 0.82rem;
		font-weight: 500;
		color: var(--text-muted);
		padding: 0 0.4rem;
	}
	.option-group {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.option-row {
		display: flex;
		gap: 0.4rem;
	}
	.option-row input {
		flex: 1;
	}
	.remove-btn {
		width: 2rem;
		background: var(--bg-hover);
		color: var(--text-muted);
		border-radius: var(--radius-sm);
		font-size: 1.1rem;
		transition: color var(--transition);
	}
	.char-count {
		font-size: 0.7rem;
		color: var(--text-muted);
		opacity: 0.5;
		min-width: 1.5rem;
		text-align: right;
	}
	.remove-btn:hover {
		color: var(--danger);
	}
	.link-input {
		font-size: 0.8rem;
		padding: 0.4rem 0.8rem;
		opacity: 0.7;
	}
	.link-input:focus {
		opacity: 1;
	}
	.add-btn {
		padding: 0.5rem;
		background: var(--accent-soft);
		color: var(--accent);
		border-radius: var(--radius-sm);
		font-size: 0.82rem;
		transition: background var(--transition);
	}
	.add-btn:hover {
		background: var(--accent);
		color: white;
	}
	.toggles {
		gap: 0.75rem;
	}
	.toggle {
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		cursor: pointer;
		padding: 0.5rem 0;
	}
	.toggle span:first-child {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}
	.toggle strong {
		font-size: 0.88rem;
		font-weight: 500;
		color: var(--text);
	}
	.toggle small {
		font-size: 0.75rem;
		color: var(--text-muted);
	}
	.toggle input {
		display: none;
	}
	.pill {
		width: 40px;
		height: 22px;
		background: var(--border);
		border-radius: 999px;
		position: relative;
		transition: background var(--transition);
		flex-shrink: 0;
	}
	.pill::after {
		content: '';
		position: absolute;
		top: 3px;
		left: 3px;
		width: 16px;
		height: 16px;
		background: white;
		border-radius: 50%;
		transition: transform var(--transition);
	}
	.toggle input:checked + .pill {
		background: var(--accent);
	}
	.toggle input:checked + .pill::after {
		transform: translateX(18px);
	}
	.toggle.disabled {
		opacity: 0.35;
		pointer-events: none;
	}
	.submit-btn {
		padding: 0.7rem;
		background: var(--accent);
		color: white;
		border-radius: var(--radius-sm);
		font-size: 0.9rem;
		font-weight: 500;
		transition: background var(--transition);
	}
	.submit-btn:hover:not(:disabled) {
		background: var(--accent-hover);
	}
	.submit-btn:disabled {
		opacity: 0.5;
	}
</style>
