# Pulse — Real-Time Poll App

A minimalistic, open-source, real-time polling app built for small and large orgs that want quick decisions without the bloat.

Most polling tools are either buried inside heavy platforms (Slack, Teams, Google Forms), locked behind paywalls, or overloaded with features nobody asked for. Pulse is different — it's a standalone app that does one thing well: fast, neat, real-time polls.

**Why Pulse?**

- **Lightweight** — no frameworks, no ORMs, no bloat. Raw Python Lambdas, a single DynamoDB table, and a Svelte SPA under 50KB
- **Dirt cheap** — runs entirely on AWS serverless. Free tier covers most usage; heavy use costs ~$10/month
- **Aesthetic UI** — dark-first monochrome design with one accent color, generous whitespace, smooth animations. Every element earns its place
- **Real-time** — votes update live across all viewers via WebSocket. No refresh needed
- **Privacy-first** — anonymous creator, anonymous voters, and visible voters are all toggleable per poll. Anonymity is enforced server-side — the API never leaks data the frontend shouldn't show
- **Self-hosted** — deploy to your own AWS account in minutes with CDK. Your data, your rules
- **Open source** — MIT licensed. Fork it, extend it, make it yours

## Structure

```plaintext
pulse/
├── infra/                  # AWS CDK (Python)
│   ├── stack.py            # Main stack — composes all resources
│   └── resources/          # Modular CDK constructs
│       ├── database.py     # DynamoDB table + GSIs
│       ├── rest_api.py     # REST API Gateway + Lambdas + rate limits
│       ├── websocket_api.py # WebSocket API Gateway + Lambdas
│       └── frontend.py     # S3 + CloudFront + OAC
├── backend/                # Lambda functions (Python 3.12)
│   ├── handlers/           # Thin Lambda entry points
│   │   ├── auth.py         # Signup, verify, signin, forgot, reset
│   │   ├── rest_api.py     # Poll CRUD, voting, listing
│   │   ├── ws_connect.py   # WebSocket $connect
│   │   ├── ws_disconnect.py # WebSocket $disconnect
│   │   └── ws_subscribe.py # WebSocket subscribe
│   ├── lib/                # Business logic
│   │   ├── db/             # DynamoDB operations (users, polls, votes, connections)
│   │   ├── models/         # Dataclasses (User, Poll, Vote)
│   │   ├── auth_service.py # Password hashing, JWT tokens, SES email
│   │   ├── broadcast.py    # WebSocket broadcast to subscribers
│   │   ├── polls.py        # Poll response builder + anonymity enforcement
│   │   ├── response.py     # HTTP response helper + Decimal JSON encoder
│   │   └── utils.py        # Constants + helpers (gen_id, sanitize_url)
│   └── tests/              # pytest + moto (mocked DynamoDB/SES/SSM)
└── frontend/               # SvelteKit SPA (Svelte 5)
    └── src/
        ├── lib/            # API client, WebSocket store, auth, theme, toasts
        └── routes/         # Pages (recent, mine, new, auth, poll detail)
```

## Architecture

```plaintext
Browser → CloudFront → S3 (SPA static files)
                     → API Gateway (REST) → Lambda → DynamoDB
        → WebSocket API Gateway → Lambda → DynamoDB
                                ← Lambda (broadcast via API GW Management API)
```

### Frontend

- SvelteKit 5 SPA (SSR disabled) built to static files, served from S3 via CloudFront
- CloudFront handles HTTPS, SPA routing (404 → index.html), and proxies `/api/*` to API Gateway
- WebSocket connection to API Gateway for real-time vote updates
- JWT token stored in localStorage (remember me) or sessionStorage, sent as `Authorization: Bearer <token>` on all API calls
- Dark mode by default with light mode toggle, persisted to localStorage

### REST API

- Single API Gateway with all routes under `/api/`
- Auth routes (`/api/auth/*`): signup, email verification, signin, password reset — handled by `auth.py` Lambda
- Poll routes (`/api/polls/*`): CRUD, voting, edit, close/reopen — handled by `rest_api.py` Lambda
- Per-endpoint rate limiting enforced at API Gateway stage level
- CORS configured for all origins

### WebSocket API

- Handles `$connect`, `$disconnect`, and `subscribe` routes, each backed by a separate Lambda
- Clients subscribe to a poll ID after connecting — stored as `SUB#<pollId>/CONN#<connId>` in DynamoDB
- When a vote/edit/close happens, the REST Lambda broadcasts the updated poll to all subscribed connections via the API Gateway Management API
- Auto-reconnect on the frontend with 2-second backoff

### Auth

- Email/password signup with 6-digit email verification code via SES
- Passwords hashed with PBKDF2-SHA256 (100k iterations) + random salt
- JWT tokens signed with HMAC-SHA256 using a secret stored in SSM Parameter Store (persists across Lambda cold starts)
- Password reset flow via 6-digit SES code (10-minute expiry)
- Email uniqueness enforced via `EMAIL#<email>` lookup item in DynamoDB
- Session expiry handling — expired JWT auto-logs out with toast notification
- Remember me — localStorage (persists) vs sessionStorage (cleared on browser close)

### Database

- DynamoDB single-table design with PK/SK pattern
- Key prefixes: `POLL#`, `VOTE#`, `USER#`, `EMAIL#`, `CONN#`, `SUB#`, `CREATOR#`
- GSI1: `POLLS` partition — recent polls listing (sorted by creation time)
- GSI2: `CREATOR#<alias>` partition — "My Polls" listing (no in-memory filtering)
- TTL on polls: data auto-deletes 6 months after creation
- Voting expiry: configurable per poll (1h to 4 months, default 24h)

### Anonymity

- Three creator-set toggles: anonymous creator, anonymous voters, visible voters
- Enforced server-side in `strip_poll_for_response()` — the API never returns data the frontend shouldn't show
- Anonymous creator: alias stored in DB for ownership but returned as "Anonymous" in responses
- Anonymous voters: votes tracked internally for one-vote-per-user enforcement but never returned in any response

### Infrastructure

- All resources defined in AWS CDK (Python), split into modular constructs
- S3 bucket with OAC (Origin Access Control) for CloudFront — returns 404 (not 403) for missing files
- CloudFront error response maps 404 → index.html for SPA client-side routing
- Lambda functions use Python 3.12, 256MB memory, 10s timeout
- SSM Parameter Store (standard tier, free) for JWT secret persistence

## Prerequisites

- Node.js 18+
- Python 3.12+
- AWS CDK CLI (`npm install -g aws-cdk`)
- An AWS account with credentials configured

## Deployment

### 1. Get AWS Credentials

Configure your AWS credentials via your preferred method (`aws configure`, environment variables, or SSO).

```bash
aws sts get-caller-identity
```

You should see your account ID in the output.

### 2. Build the Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

This outputs static files to `frontend/build/` which CDK will deploy to S3.

### 3. Deploy Infrastructure

```bash
cd infra
python3 -m venv .venv && source .venv/bin/activate
pip install .
```

Bootstrap CDK (first time only):

```bash
cdk bootstrap aws://<YOUR-AWS-ACCOUNT-ID>/us-east-1
```

Create JWT secret (first time only):

```bash
aws ssm put-parameter --name /pulse/jwt-secret --value $(openssl rand -hex 32) --type String --region us-east-1
```

Deploy:

```bash
SES_FROM_EMAIL=you@example.com cdk deploy --require-approval never
```

CDK will output:

| Output | Description |
| --- | --- |
| `RestApiUrl` | REST API endpoint |
| `WsApiUrl` | WebSocket API endpoint |
| `DistributionUrl` | CloudFront URL (your app) |
| `TableName` | DynamoDB table name |

### 4. Set WebSocket URL for Frontend

After the first deploy, grab the `WsApiUrl` from the CDK output and rebuild the frontend with it:

```bash
cd frontend
VITE_WS_URL=wss://<ws-api-id>.execute-api.us-east-1.amazonaws.com/prod npm run build
cd ../infra
SES_FROM_EMAIL=you@example.com cdk deploy --require-approval never
```

This second deploy pushes the updated frontend build with the WebSocket URL baked in.

### 5. Verify

Open the `DistributionUrl` in your browser. You should see the Pulse app. CloudFront may take a few minutes to propagate.

## Demo Mode

Pulse includes a fully functional demo mode that runs entirely in the browser — no backend or AWS account needed. All data is stored in localStorage with pre-seeded polls and users.

```bash
cd frontend
npm install
VITE_DEMO=true npm run build
npm run preview
```

Pre-seeded accounts:

| Email | Password | Role |
| --- | --- | --- |
| `demo@pulse.app` | `demo` | Owns 3 polls (techstack, spirit, private) |
| `alice@pulse.app` | `alice` | Has votes on multiple polls |
| `bob@pulse.app` | `bob` | Owns the lunch poll |

Or sign up with any new credentials. Clear localStorage to reset the demo to its seeded state.

## Local Development

### Frontend Dev Server

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` requests to `http://localhost:3001` (configure in `vite.config.js` if your local backend runs elsewhere).

> **Note:** WebSocket real-time updates are not available in local dev (no local WS server). The app works normally — votes just won't push live to other tabs. To test WebSocket, deploy to AWS and set `VITE_WS_URL`.

### Backend Tests

```bash
cd infra && source .venv/bin/activate
pip install -e "../backend[dev]"
cd ../backend && python -m pytest tests/ -v
```

### Formatting

```bash
# Backend (Python)
cd backend && ruff format . && ruff check .

# Frontend (Svelte/JS)
cd frontend && npx prettier --write "src/**/*.{js,svelte}"
```

## Redeployment

```bash
# If frontend changed
cd frontend && VITE_WS_URL=wss://<ws-api-id>.execute-api.us-east-1.amazonaws.com/prod npm run build && cd ..

# Deploy
cd infra && source .venv/bin/activate && SES_FROM_EMAIL=you@example.com cdk deploy --require-approval never
```

## Cleanup

```bash
cd infra
source .venv/bin/activate
cdk destroy
```

This removes all resources (DynamoDB table, Lambdas, API Gateways, S3 bucket, CloudFront distribution).

## Environment Variables

| Variable | Where | Description |
| --- | --- | --- |
| `VITE_WS_URL` | Frontend build | WebSocket API URL (from CDK output) |
| `SES_FROM_EMAIL` | CDK deploy | SES verified sender email |
| `TABLE_NAME` | Lambda (auto) | DynamoDB table name (set by CDK) |
| `WS_API_ENDPOINT` | Lambda (auto) | WebSocket management URL (set by CDK) |
| `JWT_SECRET_PARAM` | Lambda (auto) | SSM parameter name for JWT secret |

## Rate Limits

All limits are per-second (rate) with burst capacity. Enforced at API Gateway level — returns `429 Too Many Requests` when exceeded.

| Endpoint | Rate (req/s) | Burst |
| --- | --- | --- |
| `POST /auth/signup` | 5 | 10 |
| `POST /auth/signin` | 10 | 20 |
| `POST /auth/verify` | 5 | 10 |
| `POST /auth/resend` | 2 | 5 |
| `POST /auth/forgot` | 2 | 5 |
| `POST /auth/reset` | 5 | 10 |
| `GET /auth/me` | 50 | 100 |
| `GET /polls` | 30 | 60 |
| `POST /polls` | 10 | 20 |
| `GET /polls/:id` | 30 | 60 |
| `POST /polls/:id/vote` | 20 | 40 |
| `PUT /polls/:id` (edit) | 5 | 10 |
| `PATCH /polls/:id` (close/reopen) | 5 | 10 |
| `DELETE /polls/:id` | 5 | 10 |
| Global default | 50 | 100 |

## Hosting Cost Estimate

Based on **AWS pricing (March 2026)** for `us-east-1`. Most services fall within the AWS Free Tier for low-to-moderate usage.

### 1. Always Free (Perpetual)

These limits reset monthly and never expire. "Overage Price" applies only if you exceed these limits.

| Service | Pulse Usage | Free Tier Limit | Overage Price (if exceeded) |
| :--- | :--- | :--- | :--- |
| **Lambda** | 6 functions | **1M requests** + 400k GB-s | **$0.20** / 1M requests + $0.0000167/GB-s |
| **CloudFront** | CDN Proxy | **1 TB** Data Transfer Out | **$0.085** / GB (US/Europe) |
| **SSM Params** | JWT Secret | **10,000** standard params | **$0.05** / param (Must upgrade to "Advanced") |
| **DynamoDB** | Database | **25 GB** Storage | **$0.25** / GB |

### 2. Free Tier (First 12 Months)

These expire 1 year after sign-up. Standard rates apply afterwards.

| Service | Pulse Usage | Free Tier (Monthly) | Standard Price (Post-Trial) |
| :--- | :--- | :--- | :--- |
| **API Gateway** | REST API | 1M calls | **$3.50** / million calls |
| **API Gateway** | WebSocket | 1M msgs + 750k conn-min | **$1.00** / million msgs |
| **S3** | Static Assets | 5 GB Storage + 20k GETs | **$0.023** / GB |
| **SES** | Emails | 3,000 emails | **$0.10** / 1,000 emails |

### Estimated Monthly Cost

| Usage Level | Estimated Cost | Notes |
| :--- | :--- | :--- |
| **Light** (< 100 users) | **$0.00** | Fully covered by Free Tier (using Provisioned DynamoDB) |
| **Medium** (~50k votes) | **~$1.25** | Primary cost is DynamoDB Write Units |
| **Heavy** (~500k votes) | **~$18.50** | Driven by API Gateway & Database throughput |

All pricing is for `us-east-1`. Use the [AWS Pricing Calculator](https://calculator.aws) for precise estimates.
