# PR plan: `backend-foundation` → `main`

Handoff doc for the next agent. **Last updated 2026-09-26, afternoon (hackathon day).**
Read [CLAUDE.md](../CLAUDE.md) first: it has the full project brief, the agreed data contract and the original build order.

## TL;DR

- **End to end works:** simulator → Blue LLM harness → Atlas (games, events, lessons) → reflection → evolve → UI. Every piece has run against real Atlas data at least once.
- **Blocker right now: OpenRouter credits are exhausted** (HTTP 402). No LLM runs (Blue moves, reflection, evolve) can happen until someone adds credits at https://openrouter.ai/settings/credits. The account also has a new-account limit of 20 requests/min per model; `llm.py` now throttles to 18/min.
- **No evolve generation has completed yet**, so there is no "harness got better" result to show. This is the #1 thing to get for the demo.
- **Red has only one behavior**: the teammate engine has a single scripted Red, so levels 1–5 play identically and the curriculum can't show a climb.
- **The branch can't be PR'd yet** because it has no shared history with `origin/main`. It needs a rebase (see "What's left", step 6).

## Done

### Data layer and LLM plumbing (`backend/`)
| File | What it does | Tested? |
|---|---|---|
| `db.py` | Atlas client, collection handles, `ensure_indexes()` (including the `lessons_vec` vector index), and readable IDs via `next_id()` (`g_0042`, `L_0107`) | ✅ vs Atlas |
| `llm.py` | OpenRouter JSON call with token counts. Throttled with `LLM_RPM` (default 18) and retries on 429. Defaults: `anthropic/claude-haiku-4.5` for moves, `anthropic/claude-sonnet-5` for evolve. | ✅ |
| `memory.py` | `add_lessons()` and `recall()`. Uses `$vectorSearch` when `VOYAGE_API_KEY` is set; otherwise falls back to the latest k lessons at the same level. | ✅ fallback only; Voyage path untested |
| `store.py` | Harness versions (v0 seed, candidates, eval results, `level_unlocked`) and curriculum | ✅ |

### Game and harness loop
| File | What it does | Tested? |
|---|---|---|
| `adapter.py` | **The Env interface** (documented at the top of the file) plus `SimAdapter`, Blue's only view of the world: `observe`, `legal_actions`, `act`, `describe_actions` | ✅ |
| `sim.py` | **Env wrapper over the teammate's engine.** Translates node IDs (`laptop_a`→`laptopA`), actions, MITRE labels and event/result shapes, and adds a noisy signal feed (60% chance to see activity on a node, 5% false alarms) and action descriptions for Blue. `python -m backend.sim` runs a smoke test. | ✅ random Blue wins ~58% |
| `red-vs-blue/engine`, `red-vs-blue/agents`, `red-vs-blue/tests` | **The teammate's code, copied unchanged** from `origin/red-vs-blue` at the same paths so a merge stays clean. Game rules and Red behavior live here. | their tests |
| `runner.py` | Plays games and writes `games` and `events` live. CLI: `--env auto\|sim\|stub`, `--blue random\|llm`, `--reflect`, `--demo`, `--show-prompt`, `-v` | ✅ |
| `harness.py` | Builds the prompt (action descriptions, playbook, guardrails, signal priority and thresholds, recalled lessons, legal actions), makes 1 LLM call, checks legality and guardrails, retries once, falls back to `scan` | ✅ |
| `reflect.py` | Writes 1–3 lessons per game | ✅ |
| `evolve.py` | Each generation: train with reflection → propose one mutation → eval parent vs child on the same seeds → keep or roll back → curriculum | ✅ on stub only; the real run was cut off by the 402 |
| `compare.py` | Memory on vs off and v0 vs latest, written as `purpose:"eval"` games | ❌ not run |
| `stub_env.py` | A content-free world for plumbing tests. Don't demo it. | ✅ |

### UI
- **`web/`** is the teammate's React/Vite UI (network map, log, chart), adapted to our data. It shows:
  - Our node IDs.
  - A header with the game ID, level, harness version and memory on/off.
  - Blue's "why" and recalled lesson IDs in the log.
  - Red moves Blue never saw, shown faint.
  - A chart of win rate per harness version, falling back to a rolling win rate over games until evolve has run.
  - It builds with `npx vite build`.
- **`backend/api.py`** is a FastAPI app with the same endpoints as the teammate's API, reading our collections. "Play" replays stored games from Atlas move by move, newest first. Training is CLI-only; `/api/train` is a no-op. There's also `/api/generations`, which lists harness mutations and their eval results; the UI doesn't show it yet.
- Run it:
  ```bash
  .venv/bin/uvicorn backend.api:app --port 8000     # terminal 1
  cd web && npm install && npm run dev               # terminal 2 → http://localhost:5173
  ```

### Checkpoints
- **A ✅:** real games and events are in Atlas in the contract shape. The first one is `g_0001`, random Blue.
- **B ✅ (ran):** 3 LLM-Blue games at level 1 with reflection. **Blue won 0/3**; random Blue wins about 58%.
  - The first attempt showed the model patching and firewalling nodes that were already compromised, which doesn't remove Red.
  - The fix was action descriptions via `describe_actions()`. It still loses, but the choices now make sense.
  - The v0 playbook is deliberately generic, so this gives evolution a clear gap to close.
  - Prompt size is about 600 tokens per turn; a game costs about 4–9k tokens in.

### Current Atlas state (db `redblue`)
- 8 finished games: `g_0001` (random Blue, win) and `g_0002`–`g_0008` (LLM Blue, mostly losses).
- 18 lessons, un-embedded because there's no Voyage key.
- Only harness v0 exists. The curriculum is at level 1.
- The teammate's own code also uses db `redblue`, with different collections (`episodes`, `policy_snapshots`, `metrics`, `configs`). Only ever wipe ours: `games`, `events`, `lessons`, `harness_versions`, `curriculum`, `counters`, `networks`.

## What's left (priority order for the demo)

1. **Add OpenRouter credits.** This unblocks everything below.
2. **Run evolve at level 1 and get at least one KEPT mutation:**
   ```bash
   .venv/bin/python -m backend.evolve --env sim --generations 3 --eval-games 3 --train-games 1
   ```
   - At 18 requests/min, a 20-turn game takes about 1 minute, so one generation (1 train + 2×3 eval games) takes about 8 minutes.
   - With only 3 eval games, ties are common and roll back. Use `--eval-games 4` or more if there's time.
   - If a failed run leaves a game with `winner: null` or a harness version with `eval: null`, delete those before continuing.
3. **Red levels 2–5.** The teammate should add these to `red-vs-blue/agents/red.py`, e.g. `ScriptedRed(seed, level)`, following CLAUDE.md "Red levels" and the team's `scenarios.csv`. Then pass `level` through in `EngineEnv.__init__` in `backend/sim.py`. Without this, levels are cosmetic.
   - The previous agent (Claude) was repeatedly stopped by a safety classifier when writing Red or simulator logic, even though it's simulation only. Have a human write this part, or reuse existing code.
4. **Seed demo data:** run `python -m backend.runner --env sim --demo` (random Blue, 3 games per level, no LLM cost).
5. **Run compare:** `python -m backend.compare --env sim --games 4`. This spends LLM credits.
6. **Open the PR:**
   ```bash
   git fetch origin
   git rebase --onto origin/main --root backend-foundation   # main only has README.md
   git push --force-with-lease origin backend-foundation     # confirm with the user first
   gh pr create --base main --head backend-foundation
   ```
7. **Nice-to-have:**
   - A "harness evolution" panel in the UI listing `/api/generations` (diff_summary, kept or rolled back, win rates).
   - Enable Voyage: add `VOYAGE_API_KEY` and delete the un-embedded lessons first. Keys from Atlas → AI Model APIs may need a different base URL.
   - Add a LangSmith key for traces.

## Known issues and limitations
- **Engine quirks, owned by the teammate:**
  - Red sometimes targets `internet` itself ("Guessed passwords on Internet").
  - Initial-access moves log `from: internet` even when they fail.
  - `firewall_block` blocks the first neighbor link, not a chosen one.
  - The topology has no `laptopA–laptopB` edge.
  - There are only 6 Blue actions, not the brief's 14.
- **Signals:** only `alert:suspicious_activity@X` and `alert:confirmed_intruder@X`, with no scores, so harness thresholds have no effect yet. Evolve can still reorder priorities and change the playbook, guardrails and memory policy.
- **Evolve:**
  - Ties roll back.
  - The parent is re-evaluated every generation, which is fair but doubles eval cost.
  - Only two guardrail forms are enforced in code: `never <action> [<target>]` and `after <a> ..., also <b>`.
- **UI:**
  - "Play" replays games; it doesn't run new ones.
  - `patched` and `blocked` aren't in our event contract, so the map never shows shields or blocked links.
- **Data contract:** it was updated from the team's CSVs (see CLAUDE.md). The UI team needs that version.
- **Security cleanup after the hackathon:**
  - The Atlas user `redblue` has `atlasAdmin` and a weak password. Downgrade or delete it.
  - The OpenRouter key was pasted in a chat. Rotate it.

## Useful commands
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m backend.db          # ping + indexes
.venv/bin/python -m backend.llm         # 1 tiny OpenRouter call (checks credits)
.venv/bin/python -m backend.store       # current harness + curriculum
.venv/bin/python -m backend.sim         # engine smoke test (no LLM)
.venv/bin/python -m backend.runner --env sim --level 1 --games 3 --blue llm --reflect --show-prompt
```
