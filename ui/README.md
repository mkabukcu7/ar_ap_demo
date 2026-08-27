# Finance Operations Command Center — UI

A React + TypeScript + Fluent UI v9 dashboard for the Finance Operations Agent Accelerator, built with [Vite](https://vite.dev/).

## Prerequisites

- Node.js ≥ 18
- npm ≥ 9

## Install

```bash
cd ui/webapp
npm install
```

## Development

```bash
npm run dev
```

Opens at <http://localhost:5173>. The Vite dev server proxies `/api/*` to the backend (default `http://localhost:8000`). If the backend is unreachable, the app automatically falls back to bundled mock data and shows a **Demo Data** badge.

### Configure the API base URL

Set `VITE_API_BASE_URL` to override the proxy target:

```bash
# .env.local (inside ui/webapp/)
VITE_API_BASE_URL=http://my-backend-host:8000
```

Or inline:

```bash
VITE_API_BASE_URL=http://my-backend-host:8000 npm run dev
```

## Build

```bash
npm run build
```

Output goes to `ui/webapp/dist/`. Serve with any static file host or `npx serve dist`.

## Lint

```bash
npm run lint
```

## Dashboard panels

| Tab | Description |
|-----|-------------|
| **AP Metrics** | KPI cards: total invoices, approval queue, touchless rate, cycle time, exception rate, spend |
| **AR Metrics** | Open AR, DSO, past-due %, collections at risk |
| **Invoice Pipeline** | Stage funnel: Received → Extracted → Validated → Matched → Approval → Posted |
| **Approval Queue** | Table of pending invoices with single and bulk-approve actions |
| **Cash Application** | Applied / partially applied / unapplied remittances with totals |
| **Exceptions** | Unified AP + AR exception table with severity badges |
| **Agent Activity** | Live streaming feed of agent actions and statuses |
| **Copilot Chat** | Conversational finance assistant with citations, agent trace, and 7 canned demo prompts |

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `""` (relative) | Backend origin. Vite dev proxy forwards `/api` here. |
