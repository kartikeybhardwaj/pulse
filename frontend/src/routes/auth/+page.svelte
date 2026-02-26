<script>
	import { api } from '$lib/api.js';
	import { login, isLoggedIn } from '$lib/user.js';
	import { toasts } from '$lib/toast.js';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($isLoggedIn) goto('/');
	});

	let mode = $state('signin'); // signin | signup | verify
	let email = $state('');
	let password = $state('');
	let username = $state('');
	let verifyEmail = $state('');
	let verifyPassword = $state('');
	let code = $state('');
	let verifyEmailAddr = $state('');
	let remember = $state(false);
	let submitting = $state(false);

	async function handleSignup() {
		if (!username.trim() || !email.trim() || !password) {
			toasts.add('All fields are required', 'error');
			return;
		}
		if (email !== verifyEmail) {
			toasts.add('Emails do not match', 'error');
			return;
		}
		if (password !== verifyPassword) {
			toasts.add('Passwords do not match', 'error');
			return;
		}
		if (password.length < 6) {
			toasts.add('Password must be at least 6 characters', 'error');
			return;
		}
		submitting = true;
		try {
			const res = await api.signup({ username: username.trim(), email: email.trim(), password });
			verifyEmailAddr = res.email;
			mode = 'verify';
			toasts.add('Verification code sent to your email', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			submitting = false;
		}
	}

	async function handleVerify() {
		if (!code.trim()) {
			toasts.add('Enter the 6-digit code', 'error');
			return;
		}
		submitting = true;
		try {
			const res = await api.verify({ email: verifyEmailAddr, code: code.trim() });
			login(res.token, res.username);
			toasts.add('Email verified!', 'success');
			goto('/');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			submitting = false;
		}
	}

	async function handleResend() {
		try {
			await api.resend({ email: verifyEmailAddr });
			toasts.add('New code sent', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		}
	}

	async function handleSignin() {
		if (!email.trim() || !password) {
			toasts.add('Email and password required', 'error');
			return;
		}
		submitting = true;
		try {
			const res = await api.signin({ email: email.trim(), password });
			if (res.needsVerification) {
				verifyEmailAddr = res.email;
				mode = 'verify';
				toasts.add('Please verify your email first', 'error');
			} else {
				login(res.token, res.username, remember);
				toasts.add('Welcome back!', 'success');
				goto('/');
			}
		} catch (e) {
			// Check if the error response has needsVerification
			if (e.message === 'Email not verified') {
				verifyEmailAddr = email.trim();
				mode = 'verify';
				handleResend();
			} else {
				toasts.add(e.message, 'error');
			}
		} finally {
			submitting = false;
		}
	}

	let resetEmail = $state('');
	let newPassword = $state('');
	let verifyNewPassword = $state('');

	async function handleForgot() {
		if (!resetEmail.trim()) {
			toasts.add('Enter your email', 'error');
			return;
		}
		submitting = true;
		try {
			await api.forgot({ email: resetEmail.trim() });
			mode = 'reset';
			toasts.add('If that email is registered, a reset code has been sent', 'success');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			submitting = false;
		}
	}

	async function handleReset() {
		if (!code.trim() || !newPassword) {
			toasts.add('Code and new password required', 'error');
			return;
		}
		if (newPassword !== verifyNewPassword) {
			toasts.add('Passwords do not match', 'error');
			return;
		}
		if (newPassword.length < 6) {
			toasts.add('Password must be at least 6 characters', 'error');
			return;
		}
		submitting = true;
		try {
			const res = await api.resetPassword({ email: resetEmail.trim(), code: code.trim(), password: newPassword });
			login(res.token, res.username);
			toasts.add('Password reset!', 'success');
			goto('/');
		} catch (e) {
			toasts.add(e.message, 'error');
		} finally {
			submitting = false;
		}
	}

	function switchMode(m) {
		mode = m;
		email = '';
		password = '';
		username = '';
		verifyEmail = '';
		verifyPassword = '';
		code = '';
		resetEmail = '';
		newPassword = '';
		verifyNewPassword = '';
	}
</script>

<svelte:head><title>Pulse — Sign In</title></svelte:head>

<div class="auth-page">
	<div class="auth-card">
		<h1>◉ Pulse</h1>

		{#if mode === 'verify'}
			<div class="verify-section">
				<p class="verify-msg">Enter the 6-digit code sent to <strong>{verifyEmailAddr}</strong></p>
				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleVerify();
					}}
				>
					<input
						type="text"
						bind:value={code}
						placeholder="000000"
						maxlength="6"
						class="code-input"
						autocomplete="one-time-code"
					/>
					<button type="submit" class="submit-btn" disabled={submitting}>
						{submitting ? 'Verifying…' : 'Verify'}
					</button>
				</form>
				<button class="link-btn" onclick={handleResend}>Resend code</button>
				<button class="link-btn" onclick={() => switchMode('signin')}>Back to sign in</button>
			</div>
		{:else if mode === 'forgot'}
			<div class="verify-section">
				<p class="verify-msg">Enter your email to receive a reset code</p>
				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleForgot();
					}}
				>
					<input type="email" bind:value={resetEmail} placeholder="Email" autocomplete="email" />
					<button type="submit" class="submit-btn" disabled={submitting}>
						{submitting ? 'Sending…' : 'Send reset code'}
					</button>
				</form>
				<button class="link-btn" onclick={() => switchMode('signin')}>Back to sign in</button>
			</div>
		{:else if mode === 'reset'}
			<div class="verify-section">
				<p class="verify-msg">Enter the code sent to <strong>{resetEmail}</strong> and your new password</p>
				<form
					onsubmit={(e) => {
						e.preventDefault();
						handleReset();
					}}
				>
					<input
						type="text"
						bind:value={code}
						placeholder="000000"
						maxlength="6"
						class="code-input"
						autocomplete="one-time-code"
					/>
					<input
						type="password"
						bind:value={newPassword}
						placeholder="New password (6+ chars)"
						autocomplete="new-password"
					/>
					<input
						type="password"
						bind:value={verifyNewPassword}
						placeholder="Verify new password"
						autocomplete="new-password"
					/>
					<button type="submit" class="submit-btn" disabled={submitting}>
						{submitting ? 'Resetting…' : 'Reset password'}
					</button>
				</form>
				<button class="link-btn" onclick={handleForgot}>Resend code</button>
				<button class="link-btn" onclick={() => switchMode('signin')}>Back to sign in</button>
			</div>
		{:else}
			<div class="tabs">
				<button class:active={mode === 'signin'} onclick={() => switchMode('signin')}>Sign In</button>
				<button class:active={mode === 'signup'} onclick={() => switchMode('signup')}>Sign Up</button>
			</div>

			<form
				onsubmit={(e) => {
					e.preventDefault();
					mode === 'signup' ? handleSignup() : handleSignin();
				}}
			>
				{#if mode === 'signup'}
					<input type="text" bind:value={username} placeholder="Username" maxlength="30" autocomplete="username" />
					<input type="email" bind:value={email} placeholder="Email" autocomplete="email" />
					<input type="email" bind:value={verifyEmail} placeholder="Verify email" />
					<input type="password" bind:value={password} placeholder="Password (6+ chars)" autocomplete="new-password" />
					<input
						type="password"
						bind:value={verifyPassword}
						placeholder="Verify password"
						autocomplete="new-password"
					/>
					<button type="submit" class="submit-btn" disabled={submitting}>
						{submitting ? 'Creating account…' : 'Sign Up'}
					</button>
				{:else}
					<input type="email" bind:value={email} placeholder="Email" autocomplete="email" />
					<input type="password" bind:value={password} placeholder="Password" autocomplete="current-password" />
					<label class="remember">
						<input type="checkbox" bind:checked={remember} />
						<span>Remember me</span>
					</label>
					<button type="submit" class="submit-btn" disabled={submitting}>
						{submitting ? 'Signing in…' : 'Sign In'}
					</button>
					<button
						type="button"
						class="link-btn"
						onclick={() => {
							resetEmail = email;
							switchMode('forgot');
						}}>Forgot password?</button
					>
				{/if}
			</form>
		{/if}
	</div>
</div>

<style>
	.auth-page {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 60vh;
	}
	.auth-card {
		width: 100%;
		max-width: 360px;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	.auth-card h1 {
		text-align: center;
		font-size: 1.5rem;
		font-weight: 600;
	}
	.tabs {
		display: flex;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}
	.tabs button {
		flex: 1;
		padding: 0.55rem;
		font-size: 0.85rem;
		background: var(--bg-card);
		color: var(--text-muted);
		transition: all var(--transition);
	}
	.tabs button.active {
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 500;
	}
	form {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}
	.submit-btn {
		padding: 0.65rem;
		background: var(--accent);
		color: white;
		border-radius: var(--radius-sm);
		font-size: 0.9rem;
		font-weight: 500;
		transition: background var(--transition);
		margin-top: 0.3rem;
	}
	.submit-btn:hover:not(:disabled) {
		background: var(--accent-hover);
	}
	.submit-btn:disabled {
		opacity: 0.5;
	}
	.remember {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.82rem;
		color: var(--text-muted);
		cursor: pointer;
	}
	.remember input {
		width: auto;
		padding: 0;
	}
	.verify-section {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		text-align: center;
	}
	.verify-msg {
		font-size: 0.9rem;
		color: var(--text-muted);
	}
	.code-input {
		text-align: center;
		font-size: 1.5rem;
		letter-spacing: 0.5rem;
		font-weight: 600;
	}
	.link-btn {
		background: none;
		color: var(--accent);
		font-size: 0.82rem;
		padding: 0.3rem;
	}
	.link-btn:hover {
		text-decoration: underline;
	}
</style>
