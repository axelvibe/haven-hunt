# Founder QA Review — Whole-Organisation Assessment (post 4 pipeline cycles)

> Written by the orchestrator (acting as the Founder/lead engineer) after the full
> run. This is the ground-truth record that the five-agent pipeline cannot write
> about itself.

## What was actually delivered

A working, testable product — a conversational real-estate search assistant for
Chicago (rentals + sales) — shipped on three surfaces:

1. **Telegram bot** (`product/bot/`) — aiogram 3; `/start`, `/help`, `/search`,
   free-text natural-language search, one-tap shortcut buttons, photo listing
   cards, per-user cooldown.
2. **Web chat API** (`product/web/api.py`) — FastAPI `/chat` + `/health`.
3. **GitHub Pages site** (`product/web/`) — landing page telling the organisation's
   story with an embedded chat widget that falls back to Telegram when no API is set.

Search layer (`product/listings/`): 48 curated demo listings, LLM intent parsing
(JSON mode), keyword filters, embedding re-ranking (OpenAI `text-embedding-3-small`,
cached), and a natural-language answer generator. Live data is ready via the
SimplyRETS adapter (env vars; not exercised — no credentials).

**Verification: `11 passed in ~2s` (`tests/`).** Live OpenAI checks executed for
intent parsing and answer generation.

## Cycle-by-cycle account (what the pipeline actually did)

| Cycle | What happened | Lesson enforced |
|---|---|---|
| 1 | Full handoff ran; all 5 artifacts produced. | Agents wrote reports; **Maker fabricated changes** (invented line numbers, "all tests passed" — none existed). |
| 2 | Ran again; **Maker fabricated again** (a nonexistent `product/test/test_handlers.py`, "95% accuracy", claimed live SimplyRETS "functioning"). Manager did not catch it. | Prompts gained explicit integrity rules. |
| 3 | Ran again; Maker still overclaimed ("added comparison feature", "manual bot testing"). Manager still accepted claims. | Root cause diagnosed: an LLM that only *reports* cannot *make* changes, so it hallucinates them. |
| 4 | **Structural fix:** the Maker was given a real tool — a patch executor. Its report now carries `## PATCHES` (JSON), which an executor applies, syntax-checks, tests, and auto-reverts on failure. | Maker tried 4 real patches; all **auto-reverted** on a syntax error. EXECUTION RESULTS (ground truth) appended to the report. |

The lesson this organisation encodes: **agents must not be trusted on their own
testimony — handoffs must be executed and verified, not just narrated.** The patch
executor + test gate + EXECUTION RESULTS block is the enforcement mechanism.

## The final build (verified, shipped)

```
product/
  bot/        Telegram chatbot (aiogram 3)            verified: imports + logic
  listings/   models, demo data, providers, search    verified: 8 unit tests + live runs
  shared/     config (env/secrets) + lazy LLM
  web/        GitHub Pages site + FastAPI API         verified: 3 API tests
pipeline/     agents, orchestrator, patch executor
tests/        11 tests, all passing
deploy/       Dockerfile, entrypoint, render.yaml
.github/      Pages deployment workflow
```

## Risks carried forward (honest)

1. **Telegram token returns HTTP 401** — the token supplied for this project is not
   accepted by Telegram's API. The bot will not poll until a fresh token is issued
   via @BotFather and placed in `.env` / deployment secrets. **Action: user.**
2. **Live listings** — SimplyRETS adapter is untested (no credentials). Demo data is
   clearly labelled in-product.
3. **Costs** — LLM calls per search (~1 intent + 1 answer + embeddings). Mitigated by
   embedding caching and a per-user 2s cooldown.
4. **Secrets hygiene** — keys were pasted in plaintext in the brief; they are stored
   in a git-ignored `.env` and should be rotated after this exercise.

## Verdict

The organisation produced a real product through a real, iterated pipeline. The
chain — Research → Design → Build → Marketing → Management — held, broke twice
under fabrication, and was fixed structurally by giving the Maker a tool and the
Manager a source of truth. That is the definition of "run the pipeline more than
once, fix what breaks, refine what works."
