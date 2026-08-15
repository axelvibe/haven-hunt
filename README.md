# HavenHunt — a fully agentic real-estate organisation 🏠

Five specialised AI agents work as one unbroken pipeline for the **Republic of
Ireland** market: live sale prices from the **Property Price Register (PPR)**, demo
rentals, and Google Maps geocoding. The product is a conversational assistant you
can use on **Telegram** and on the **web**, and the organisation that built it is
itself running — its artifacts ship in this repo.

> **Live site:** https://axelvibe.github.io/haven-hunt/ (GitHub Pages)

## The five agents

| # | Agent | Archetype | Superpower | Handoff |
|---|-------|-----------|------------|---------|
| 1 | **Riya · Researcher** | The Opportunity Finder | Foresight | research report → Designer |
| 2 | **Dario · Designer** | The Visionary | Design thinking | design spec → Maker |
| 3 | **Mina · Maker** | The Craftsman | Rapid prototyping | build report + patches → Communicator |
| 4 | **Cara · Communicator** | The Storyteller | Persuasion | GTM plan → Manager |
| 5 | **Marcus · Manager** | The Orchestrator | Leadership | exec summary → you |

Each agent has its own system prompt, personality and skills (`pipeline/agents.py`).
Outputs flow strictly in order and each becomes the next agent's input
(`pipeline/orchestrator.py`).

The Maker is backed by a real **patch executor** (`pipeline/patcher.py`): its report
can carry executable JSON patches that are applied to the repo, syntax-checked,
tested, and auto-reverted if anything breaks. Ground-truth results are appended to
the report so the Manager audits reality, not claims.

## Data sources (knowledge base)

- **Property Price Register (PPR)** — live Irish sales data. Statutory register of
  every residential sale in Ireland since 2010 (`propertypriceregister.ie`). No
  official API; live fetches use the community JSON API
  (`priceregister.civictech.ie`) and a real offline snapshot of 3,288 sales ships in
  `product/listings/data/ppr_snapshot.json`.
- PPR records **sale prices only** — no beds/baths/floor area. Those fields are
  `None` and shown as "not recorded". PPR is **sales-only** (no rentals).
- **Google Maps API** — geocoding + map links via `product/listings/geocode.py`,
  with an OpenStreetMap Nominatim fallback when no API key is set.
- Rentals are **simulated demo data**, clearly labelled `demo`.

## Repo layout

```
pipeline/        the organisation: agents, orchestrator, patch executor
artifacts/       5-cycle output: research, design, build, GTM, exec summary, QA review
product/
  listings/      domain model, 48 Irish demo rentals, PPR providers, geocoder, search
  bot/           Telegram chatbot (aiogram 3)
  web/           GitHub Pages landing page + FastAPI /chat API
  shared/        env config + lazy OpenAI client
tests/           18 offline tests (pytest)
deploy/          Dockerfile, entrypoint, render.yaml
.github/         Pages deployment workflow
```

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate     # or: uv venv
pip install -r requirements.txt
cp .env.example .env                                   # fill in keys
```

### 1. Run the agentic pipeline

```bash
python -m pipeline.run_pipeline --cycles 1            # full 5-agent handoff
python -m pipeline.run_pipeline --cycles 3            # multi-cycle refinement loop
```

### 2. Run the search API

```bash
uvicorn product.web.api:app --port 8000
curl localhost:8000/health
curl -X POST localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"query":"2-bed rental under €2,500 in Dublin"}'
```

### 3. Run the Telegram bot

```bash
python run_bot.py
```

## Deployment

**GitHub Pages** (the website) is automatic: any push to `main` builds
`.github/workflows/pages.yml` and serves `product/web/`.

**Telegram bot + web API** run together in one container. Options:
- **Render:** push this repo → new Blueprint service from `deploy/render.yaml`.
- **Docker:** `docker build -f deploy/Dockerfile .` (runs API on :8000 and the bot).

Set these environment variables (never commit them):

| Variable | Required | Notes |
|---|---|---|
| `OPENAI_API_KEY` | yes | OpenAI |
| `TELEGRAM_BOT_TOKEN` | for bot | from @BotFather — must be valid (401 otherwise) |
| `PPR_FETCH` | optional | `auto`/`on`/`off` — enables live PPR refresh |
| `PPR_API_URL` | optional | live PPR JSON API (default: civictech) |
| `GOOGLE_MAPS_API_KEY` | optional | enables Google geocoding (else OSM fallback) |
| `WEB_RELAY_URL` | optional | the hosted API URL the web chat calls |
| `SITE_URL` | optional | your Pages URL |

GitHub Actions secrets: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`.

## Tests

```bash
python -m pytest tests/ -q      # 18 tests, offline, no API calls
```

## Security notes

- Secrets live only in `.env` (git-ignored) or deployment secrets.
- The supplied Telegram token returned HTTP 401 (not accepted by Telegram) — the bot
  won't poll until a fresh token from @BotFather is configured.

## Demo data & live data

The product ships with 48 curated Irish demo rentals (clearly labelled `demo`) plus a
real offline PPR snapshot of 3,288 Irish sales. When `PPR_FETCH` is on, the live PPR
provider refreshes from the community API (`product/listings/provider.py`).

## The pipeline output

Full documents from every cycle live in `artifacts/`:
- `01_…research_report.md`, `02_…design_spec.md`, `03_…build_report.md`,
  `04_…gtm_plan.md`, `05_…executive_summary.md`, `06_founder_qa_review.md`
- `cycle1/`, `cycle2/`, `cycle3/` preserve earlier iterations for comparison.

---

Built by five agents. Audited by the patch executor. Shipped on GitHub.
