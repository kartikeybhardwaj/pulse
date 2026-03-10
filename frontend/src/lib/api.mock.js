/**
 * Mock API client for demo mode — no backend required.
 * All data lives in localStorage. Pre-seeded with sample polls on first load.
 */

const STORAGE_KEY = 'pulse-demo-data';

function now() {
	return Math.floor(Date.now() / 1000);
}

function genId() {
	return Math.random().toString(36).slice(2, 10);
}

function load() {
	const raw = localStorage.getItem(STORAGE_KEY);
	if (raw) {
		const data = JSON.parse(raw);
		// Merge any new seed polls/votes/users that were added after the user's first visit
		const fresh = seed();
		const existingPollIds = new Set(data.polls.map((p) => p.pollId));
		for (const p of fresh.polls) {
			if (!existingPollIds.has(p.pollId)) data.polls.push(p);
		}
		const existingVoteKeys = new Set(data.votes.map((v) => `${v.pollId}:${v.alias}`));
		for (const v of fresh.votes) {
			if (!existingVoteKeys.has(`${v.pollId}:${v.alias}`)) data.votes.push(v);
		}
		for (const [k, u] of Object.entries(fresh.users)) {
			if (!data.users[k]) data.users[k] = u;
		}
		for (const [k, v] of Object.entries(fresh.emails)) {
			if (!data.emails[k]) data.emails[k] = v;
		}
		refreshTimestamps(data);
		save(data);
		return data;
	}
	const data = seed();
	save(data);
	return data;
}

function save(data) {
	localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// Seed poll IDs — only these get their timestamps refreshed
const SEED_IDS = new Set(['techstack', 'lunch', 'spirit', 'hackathon', 'private1']);

// Offsets from now() for each seed poll: [createdAt offset, expiresAt offset]
const SEED_TIMES = {
	techstack: [-3600, 86400],
	lunch: [-7200, 172800],
	spirit: [-1800, 604800],
	hackathon: [-600, 259200],
	private1: [-900, 604800],
	expired1: [-172800, -3600]
};

function refreshTimestamps(data) {
	const t = now();
	for (const p of data.polls) {
		const offsets = SEED_TIMES[p.pollId];
		if (!offsets) continue;
		p.createdAt = t + offsets[0];
		p.expiresAt = t + offsets[1];
		p.deletesAt = t + 15552000;
	}
}

function getUser() {
	// Check both storages — matches the logic in user.js
	return localStorage.getItem('pulse-user') || sessionStorage.getItem('pulse-user') || 'anonymous';
}

// ── Seed data ──

function seed() {
	const t = now();
	return {
		users: {
			demo: { username: 'demo', email: 'demo@pulse.app', passwordHash: 'demo', salt: '', verified: true, createdAt: t },
			alice: {
				username: 'alice',
				email: 'alice@pulse.app',
				passwordHash: 'alice',
				salt: '',
				verified: true,
				createdAt: t
			},
			bob: { username: 'bob', email: 'bob@pulse.app', passwordHash: 'bob', salt: '', verified: true, createdAt: t }
		},
		emails: { 'demo@pulse.app': 'demo', 'alice@pulse.app': 'alice', 'bob@pulse.app': 'bob' },
		polls: [
			{
				pollId: 'techstack',
				question: 'What should we use for our next internal tool?',
				description: 'We need a lightweight frontend framework for a dashboard project',
				questionLink: 'https://2024.stateofjs.com/en-US/libraries/front-end-frameworks/',
				options: ['React', 'Svelte', 'Vue', 'HTMX'],
				optionLinks: ['https://react.dev', 'https://svelte.dev', 'https://vuejs.org', 'https://htmx.org'],
				creator: 'demo',
				status: 'active',
				createdAt: t - 3600,
				expiresAt: t + 86400,
				deletesAt: t + 15552000,
				anonCreator: false,
				anonVoters: false,
				visibleVoters: true,
				private: false
			},
			{
				pollId: 'lunch',
				question: 'Where should we order lunch from on Friday?',
				description: 'Budget is $15 per person, needs vegetarian options',
				questionLink: null,
				options: ['Chipotle', 'Sweetgreen', 'Cava'],
				optionLinks: ['https://www.chipotle.com/menu', 'https://www.sweetgreen.com/menu', 'https://cava.com/menu'],
				creator: 'alice',
				status: 'active',
				createdAt: t - 7200,
				expiresAt: t + 172800,
				deletesAt: t + 15552000,
				anonCreator: false,
				anonVoters: false,
				visibleVoters: false,
				private: false
			},
			{
				pollId: 'spirit',
				question: "What's your spirit animal at work?",
				description: 'Be honest. No judgment.',
				questionLink: null,
				options: [
					'Coffee addict ☕',
					'Procrastinator supreme 🦥',
					'Meeting survivor 📅',
					'Slack lurker 👀',
					'Keyboard warrior ⌨️'
				],
				optionLinks: [null, null, null, null, null],
				creator: 'demo',
				status: 'active',
				createdAt: t - 1800,
				expiresAt: t + 604800,
				deletesAt: t + 15552000,
				anonCreator: true,
				anonVoters: true,
				visibleVoters: false,
				private: false
			},
			{
				pollId: 'hackathon',
				question: 'What should our next hackathon theme be?',
				description: '2-day event in March, teams of 3-5',
				questionLink: 'https://en.wikipedia.org/wiki/Hackathon',
				options: ['AI/ML tools', 'Developer productivity', 'Sustainability', 'Open source'],
				optionLinks: [
					'https://huggingface.co',
					'https://github.com/features/copilot',
					'https://www.thegreenwebfoundation.org',
					'https://opensource.guide'
				],
				creator: 'bob',
				status: 'active',
				createdAt: t - 600,
				expiresAt: t + 259200,
				deletesAt: t + 15552000,
				anonCreator: false,
				anonVoters: false,
				visibleVoters: true,
				private: false
			},
			{
				pollId: 'private1',
				question: 'Should we switch to 4-day work weeks?',
				description: 'Confidential team survey — link only',
				questionLink: null,
				options: ['Yes, absolutely', 'Maybe, trial first', 'No, keep 5 days'],
				optionLinks: [null, null, null],
				creator: 'demo',
				status: 'active',
				createdAt: t - 900,
				expiresAt: t + 604800,
				deletesAt: t + 15552000,
				anonCreator: false,
				anonVoters: true,
				visibleVoters: false,
				private: true
			},
			{
				pollId: 'expired1',
				question: 'Should we adopt a monorepo?',
				description: 'This poll has ended — results are final',
				questionLink: null,
				options: ['Yes, single repo', 'No, keep multi-repo', 'Hybrid approach'],
				optionLinks: [null, null, null],
				creator: 'bob',
				status: 'expired',
				createdAt: t - 172800,
				expiresAt: t - 3600,
				deletesAt: t + 15552000,
				anonCreator: false,
				anonVoters: false,
				visibleVoters: true,
				private: false
			}
		],
		votes: [
			{ pollId: 'techstack', alias: 'demo', option: 'Svelte' },
			{ pollId: 'techstack', alias: 'alice', option: 'Svelte' },
			{ pollId: 'techstack', alias: 'bob', option: 'React' },
			{ pollId: 'techstack', alias: 'carol', option: 'Svelte' },
			{ pollId: 'techstack', alias: 'dave', option: 'HTMX' },
			{ pollId: 'lunch', alias: 'demo', option: 'Sweetgreen' },
			{ pollId: 'lunch', alias: 'bob', option: 'Chipotle' },
			{ pollId: 'lunch', alias: 'carol', option: 'Cava' },
			{ pollId: 'lunch', alias: 'dave', option: 'Chipotle' },
			{ pollId: 'spirit', alias: 'alice', option: 'Coffee addict ☕' },
			{ pollId: 'spirit', alias: 'bob', option: 'Slack lurker 👀' },
			{ pollId: 'spirit', alias: 'carol', option: 'Procrastinator supreme 🦥' },
			{ pollId: 'spirit', alias: 'demo', option: 'Keyboard warrior ⌨️' },
			{ pollId: 'hackathon', alias: 'alice', option: 'AI/ML tools' },
			{ pollId: 'hackathon', alias: 'carol', option: 'Open source' },
			{ pollId: 'hackathon', alias: 'dave', option: 'AI/ML tools' },
			{ pollId: 'hackathon', alias: 'demo', option: 'Developer productivity' },
			{ pollId: 'private1', alias: 'demo', option: 'Maybe, trial first' },
			{ pollId: 'private1', alias: 'alice', option: 'Yes, absolutely' },
			{ pollId: 'private1', alias: 'bob', option: 'Yes, absolutely' },
			{ pollId: 'expired1', alias: 'demo', option: 'Hybrid approach' },
			{ pollId: 'expired1', alias: 'alice', option: 'Yes, single repo' },
			{ pollId: 'expired1', alias: 'bob', option: 'Hybrid approach' },
			{ pollId: 'expired1', alias: 'carol', option: 'No, keep multi-repo' },
			{ pollId: 'expired1', alias: 'dave', option: 'Hybrid approach' }
		]
	};
}

// ── Helpers ──

function buildPollResponse(poll, votes, requester) {
	const pollVotes = votes.filter((v) => v.pollId === poll.pollId);
	const counts = {};
	const voterMap = {};
	let myVote = null;

	for (const opt of poll.options) {
		counts[opt] = 0;
		voterMap[opt] = [];
	}
	for (const v of pollVotes) {
		counts[v.option] = (counts[v.option] || 0) + 1;
		if (!poll.anonVoters && poll.visibleVoters) voterMap[v.option].push(v.alias);
		if (v.alias === requester && requester !== 'anonymous') myVote = v.option;
	}

	const results = poll.options.map((opt, i) => {
		const entry = { option: opt, count: counts[opt] || 0 };
		if (poll.optionLinks?.[i]) entry.link = poll.optionLinks[i];
		if (!poll.anonVoters && poll.visibleVoters) entry.voters = voterMap[opt];
		return entry;
	});

	return {
		pollId: poll.pollId,
		question: poll.question,
		description: poll.description,
		questionLink: poll.questionLink,
		options: poll.options,
		results,
		totalVotes: pollVotes.length,
		status: poll.status,
		createdAt: poll.createdAt,
		startsAt: poll.startsAt || null,
		expiresAt: poll.expiresAt,
		deletesAt: poll.deletesAt,
		anonCreator: poll.anonCreator,
		anonVoters: poll.anonVoters,
		visibleVoters: poll.visibleVoters,
		private: poll.private,
		myVote,
		creator: poll.anonCreator ? 'Anonymous' : poll.creator,
		isOwner: poll.creator === requester
	};
}

// ── Mock delay ──

function delay(ms = 150) {
	return new Promise((r) => setTimeout(r, ms));
}

// ── API ──

export const api = {
	// Auth
	async signup({ username, email, password }) {
		await delay();
		const data = load();
		if (data.users[username]) throw new Error('Username already taken');
		if (data.emails[email]) throw new Error('Email already registered');
		data.users[username] = {
			username,
			email,
			passwordHash: password,
			salt: '',
			verified: false,
			verifyCode: '123456',
			createdAt: now()
		};
		data.emails[email] = username;
		save(data);
		return { message: 'Verification code sent', email };
	},

	async verify({ email, code }) {
		await delay();
		const data = load();
		const username = data.emails[email];
		if (!username) throw new Error('Email not found');
		const user = data.users[username];
		// Accept any 6-digit code in demo mode
		if (code.length !== 6) throw new Error('Invalid code');
		user.verified = true;
		delete user.verifyCode;
		save(data);
		return { token: `demo-token-${username}`, username };
	},

	async resend({ email }) {
		await delay();
		return { message: 'New code sent' };
	},

	async signin({ email, password }) {
		await delay();
		const data = load();
		const username = data.emails[email];
		if (!username) throw new Error('Invalid email or password');
		const user = data.users[username];
		if (!user.verified) throw new Error('Email not verified');
		if (user.passwordHash !== password) throw new Error('Invalid email or password');
		return { token: `demo-token-${username}`, username };
	},

	async forgot({ email }) {
		await delay();
		return { message: 'If that email is registered, a reset code has been sent' };
	},

	async resetPassword({ email, code, password }) {
		await delay();
		const data = load();
		const username = data.emails[email];
		if (!username) throw new Error('Invalid code');
		data.users[username].passwordHash = password;
		save(data);
		return { token: `demo-token-${username}`, username };
	},

	async me() {
		await delay(50);
		const user = getUser();
		if (!user || user === 'anonymous') throw new Error('Not authenticated');
		return { username: user };
	},

	// Polls
	async createPoll(body) {
		await delay();
		const data = load();
		const poll = {
			pollId: genId(),
			question: body.question,
			description: body.description || null,
			questionLink: body.questionLink || null,
			options: body.options,
			optionLinks: body.optionLinks || [],
			creator: getUser(),
			status: body.startsAt && body.startsAt > now() ? 'scheduled' : 'active',
			createdAt: now(),
			startsAt: body.startsAt || null,
			expiresAt: body.endsAt || now() + 86400,
			deletesAt: now() + 15552000,
			anonCreator: !!body.anonCreator,
			anonVoters: !!body.anonVoters,
			visibleVoters: !!body.visibleVoters,
			private: !!body.private
		};
		data.polls.unshift(poll);
		save(data);
		return { pollId: poll.pollId };
	},

	async getPolls(filter = 'recent', cursor = '') {
		await delay();
		const data = load();
		const user = getUser();
		let polls = data.polls;
		if (filter === 'mine') {
			polls = polls.filter((p) => p.creator === user);
		} else {
			polls = polls.filter((p) => !p.private);
		}
		return {
			polls: polls.map((p) => ({
				...buildPollResponse(p, data.votes, user),
				totalVotes: data.votes.filter((v) => v.pollId === p.pollId).length
			})),
			nextCursor: null
		};
	},

	async getPoll(id) {
		await delay();
		const data = load();
		const poll = data.polls.find((p) => p.pollId === id);
		if (!poll) throw new Error('Poll not found');
		return buildPollResponse(poll, data.votes, getUser());
	},

	async closePoll(id) {
		await delay();
		const data = load();
		const poll = data.polls.find((p) => p.pollId === id);
		if (!poll) throw new Error('Poll not found');
		if (poll.status === 'expired') throw new Error('Expired polls cannot be reopened');
		poll.status = poll.status === 'closed' ? 'active' : 'closed';
		save(data);
		return { status: poll.status };
	},

	async editPoll(id, body) {
		await delay();
		const data = load();
		const poll = data.polls.find((p) => p.pollId === id);
		if (!poll) throw new Error('Poll not found');
		const optionsChanged = JSON.stringify(body.options) !== JSON.stringify(poll.options);
		poll.question = body.question;
		poll.description = body.description || null;
		poll.questionLink = body.questionLink || null;
		poll.options = body.options;
		poll.optionLinks = body.optionLinks || [];
		if (optionsChanged) data.votes = data.votes.filter((v) => v.pollId !== id);
		save(data);
		return { edited: true, votesReset: optionsChanged };
	},

	async deletePoll(id) {
		await delay();
		const data = load();
		data.polls = data.polls.filter((p) => p.pollId !== id);
		data.votes = data.votes.filter((v) => v.pollId !== id);
		save(data);
		return { deleted: true };
	},

	async vote(id, option) {
		await delay();
		const data = load();
		const user = getUser();
		const existing = data.votes.find((v) => v.pollId === id && v.alias === user);
		if (existing && existing.option === option) {
			// Undo
			data.votes = data.votes.filter((v) => !(v.pollId === id && v.alias === user));
			save(data);
			return { voted: null };
		}
		// Remove old vote if switching
		data.votes = data.votes.filter((v) => !(v.pollId === id && v.alias === user));
		data.votes.push({ pollId: id, alias: user, option });
		save(data);
		return { voted: option };
	}
};
