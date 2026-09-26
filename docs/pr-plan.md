# PR plan: `backend-foundation` → `main`

Handoff doc for the next agent. Snapshot as of 2026-09-26 (hackathon day; submission due this afternoon).
Read [CLAUDE.md](../CLAUDE.md) first: it has the full project brief, the agreed data contract, and the build order.

## TL;DR

- **The whole Blue self-improvement loop is built and was tested end to end, but only against a stub world where Red does nothing.** The loop covers the adapter, runner, LLM harness, guardrails, reflection, evolve (keep or roll back), curriculum and compare.
- **UPDATE (later the same day): `backend/sim.py` now exists.** It wraps the teammate's engine, copied from `origin/red-vs-blue` into `red-vs-blue/engine`, `red-vs-blue/agents` and `red-vs-blue/tests` at the same paths so a merge stays clean. Checkpoint A passed: real games and events are in Atlas.
- **The remaining sim gap is Red levels.** The engine has ONE scripted Red (`red-vs-blue/agents/red.py`), so `level` 1–5 is recorded but Red plays the same at every level. Random Blue wins about 58% at every level. The curriculum can't show a climb until levels 2–5 exist in the engine.
- **This branch can't be opened as a PR against `main` yet.** It has no common history with `origin/main` and needs a rebase first (step 1 below).

## Current status

### Branch and remote state
| Branch | What's there |
|---|---|
| `backend-foundation` (this one, pushed) | Everything below. 2 commits: `6784d88`, `a38b331`. |
| `origin/main` | Only `README.md` (commits `bffea7a`, `3fed157`). **No shared history with this branch.** |
| `origin/red-vs-blue` | Teammate's separate project in `red-vs-blue/`: a pure-Python engine, scripted Red, Q-table Blue, FastAPI, a React UI, and its own Atlas collections. Branched from `main`. |

### Done (in `backend/`)
| File | Status | Notes |
|---|---|---|
| `db.py` | ✅ tested vs Atlas | Client, collection handles, `ping()`, `ensure_indexes()`, and `next_id("games"\|"lessons")`, which gives readable IDs like `g_0042` via the `counters` collection. Creates the `lessons_vec` vector index from code (this worked). |
| `llm.py` | ✅ tested vs OpenRouter | `chat_json(system, user, kind="move"\|"evolve")` returns `(dict, {"tokens_in", "tokens_out"})`. Default models are `anthropic/claude-haiku-4.5` (move) and `anthropic/claude-sonnet-5` (evolve); both slugs worked. |
| `memory.py` | ✅ tested (fallback path only) | `add_lesson(s)` and `recall(situation, memory_policy, level)`. **With no `VOYAGE_API_KEY`, lessons are stored without embeddings and recall returns the latest k at the level.** The `$vectorSearch` path is written but has not been run. |
| `store.py` | ✅ tested | Harness versions (`seed_v0`, `current_version`, `save_candidate`, `record_eval`) and curriculum (`get_curriculum`, `maybe_advance`, which also stamps `level_unlocked`). |
| `adapter.py` | ✅ | **The Env interface `sim.py` must implement is documented at the top of this file.** `SimAdapter` is Blue's only view of the world: `observe()`, `legal_actions()`, `act()`. |
| `harness.py` | ✅ tested on stub | Builds the prompt from the harness version, makes 1 LLM call, checks legality and guardrails, retries once, then falls back to `scan`. Filters signals by threshold and orders them by priority. Guardrails are machine-checked only in two forms: `never <action> [<target>]` and `after <a> ..., also <b>`. |
| `reflect.py` | ✅ tested on stub | Writes 1–3 lessons per game to memory. |
| `runner.py` | ✅ tested on stub | Plays games and writes `games` and `events` live, in the contract shape. `--env auto\|sim\|stub` (auto uses `sim.py` if present), `--demo`, `--show-prompt`, `-v`. |
| `evolve.py` | ✅ tested on stub (1 generation) | Each generation: train games with reflection → `EVOLVE_MODEL` proposes one validated mutation → parent and child evaluated on the same fixed seeds → kept only if the child is strictly better → curriculum advances using the surviving version's win rate. |
| `compare.py` | ✅ written, not run | Three arms, written as `purpose:"eval"` games: latest with memory, latest without memory, v0 with memory. |
| `stub_env.py` | ✅ | A stand-in world for plumbing tests (Red does nothing). **Not a game; don't demo it.** |

Measured on the stub: about 9k tokens in and 1.2k out per 20-turn LLM game, with a prompt of roughly 450 tokens per turn.

### Atlas state (db `redblue`, cluster `cluster0.nrzr6g`, in a teammate's project)
- Clean. Stub test data was wiped. `harness_versions` holds only v0, and `curriculum` is `{current_level: 1, pass_threshold: 0.7, history: []}`. `counters` was reset.
- The `lessons_vec` vector index exists.
- The teammate's `red-vs-blue` code **also defaults to db `redblue`**, with different collections: `episodes`, `policy_snapshots`, `metrics`, `configs`. There are no name collisions with ours, but be careful with any wipes: delete only our collections (`games`, `events`, `lessons`, `harness_versions`, `curriculum`, `counters`, `networks`).

### `.env` (repo root, gitignored)
- Set: `MONGODB_URI`, `OPENROUTER_API_KEY`.
- Missing: `VOYAGE_API_KEY` (recommended), `LANGSMITH_API_KEY` (optional; tracing turns itself off without it).
- Never print, log or commit values.

## What's left, in order

### 1. Make the branch PR-able
```bash
git fetch origin
git rebase --onto origin/main --root backend-foundation   # replay our 2 commits on top of main's README commits
git push --force-with-lease origin backend-foundation
gh pr create --base main --head backend-foundation
```
Only `README.md` exists on main, so expect no conflicts. Confirm with the user before force-pushing.

### 2. `backend/sim.py`: done as a wrapper; Red levels still needed
**Status:** done. `backend/sim.py` translates the teammate engine to our Env interface. It maps `laptop_a`→`laptopA`, maps actions (`scan`, `patch`, `firewall_block`, `reset_creds`, `isolate`, `restore`), adds MITRE labels, and adds a noisy signal feed (60% chance to see activity on a node, 5% false alarms). Run `python -m backend.sim` for a smoke test. The engine has no `laptopA-laptopB` edge and only 6 Blue actions, a subset of the brief's 14.

**Left:** add Red levels 2–5 in the engine, e.g. `ScriptedRed(seed, level)`, in coordination with the teammate, then pass `level` through in `EngineEnv.__init__`. Engine quirks worth raising with the teammate: Red sometimes targets `internet` itself ("Guessed passwords on Internet"), and failed initial-access moves log `from: internet`.

The original notes follow for reference.
It must export `make_env(level, seed)`, returning an object with this interface (full contract in [backend/adapter.py](../backend/adapter.py)):
`network`, `red_step(turn)`, `observe(turn)`, `legal_actions()`, `blue_act(turn, action, target)`, `result(turn)`, `metrics()`.

**Option A (recommended): wrap the teammate's engine.**
- The engine is on `origin/red-vs-blue` in `red-vs-blue/engine/{game,state,actions,topology}.py` and `agents/red.py`.
- `engine.game.Game` has `step(red_agent, blue_agent)`, `_apply_red`, `_apply_blue`, `blue_visible_threats()`, `snapshot()` and `_check_end()`. That's close to what we need, but its loop drives both agents together, so `red_step` and `blue_act` must be split out, or Blue made into a "puppet" agent that returns the action we pass in.
- Its node IDs are `laptop_a` and `laptop_b`; ours are `laptopA` and `laptopB`. It also has no `laptopA-laptopB` edge. Map the IDs in the wrapper and tell the UI team which topology is canonical.
- Check whether its Red supports our 5 levels. If not, add the levels there.
- Ask the user or teammate before copying or vendoring their code into `backend/`.

**Option B: write `sim.py` from scratch** from CLAUDE.md ("Network", "Turn loop", "Red levels", "Blue actions") and the team's `scenarios.csv`, which gives success and detection odds, preconditions and effects per level and step. The user has this file; it isn't in the repo.

**Note for the agent:** the previous agent (Claude) was repeatedly stopped by a safety classifier while writing the Red and simulator code, even though it's pure simulation (probability rolls on booleans). That's why this piece is missing. If you hit the same wall, say so plainly and use Option A or a human-written sim rather than retrying.

**Output requirements the rest of the pipeline relies on:**
- **Red events:** `action`, `category:"attack"`, `mitre` (e.g. `"T1566"` or `None`), `from`, `target`, `success`, `detected`, `text`, `node_states`. Write undetected moves too, with `detected: False`.
- **`text`** is a short plain-English log line, e.g. `"Laptop A -> Server: login failed, passwords were reset (T1021)"`.
- **`node_states`** is the FULL board after the move: `{nodeId: "blue"|"amber"|"red"|"gray"}`.
- **`observe()`** returns `{"turn", "signals": [...], ...}`. Signal strings follow `type:detail@node[:score]`, e.g. `alert:credential_access@laptopA:0.7`. The harness groups signals by the `type` prefix; its default thresholds are `alert`, `login_anomaly`, `egress` and `sched_task`, which evolve can change. Signals without a score always pass the threshold filter. Blue must see only noisy signals, never the true state.
- **`blue_act()`** returns `category` (`detect`/`harden`/`respond`/`deceive`), `success`, `outcome` (`true_catch`/`no_finding`/`recovery`/`false_alarm`/`None`), `text` and `node_states`.
- **`result()`** returns `{"winner", "win_condition"}`, where `win_condition` is one of `crown_jewel_stolen`, `half_network_taken`, `survived_20_turns` or `red_evicted`.
- **`metrics()`** returns `time_to_detect`, `time_to_evict`, `max_nodes_red`, `false_alarms` and `collateral_nodes`.
- **Determinism:** everything must be deterministic given `(level, seed)`. Evolve compares parent and child on identical seeds.
- **Sanity check:** random Blue should lose most games at level 3 and above, or there's no curriculum to climb.

### 3. Checkpoint A (user wants to see this)
```bash
.venv/bin/python -m backend.runner --demo                       # 3 random-Blue games per level, purpose=demo
.venv/bin/python -m backend.runner --level 1 --games 3 --blue random -v
```
Show the user one `games` doc and three `events` docs. The UI team needs real data as soon as possible.

### 4. Checkpoint B
```bash
.venv/bin/python -m backend.runner --level 1 --games 3 --blue llm --reflect --show-prompt
```
Show the win rate, the sample prompt (no secrets) and the lessons written (`db.lessons`).

### 5. Voyage
- Add `VOYAGE_API_KEY`. Keys from Atlas → Services → AI Model APIs may need a different base URL than the `voyageai` client's default; if `python -m backend.memory` fails, check this first.
- Lessons stored before the key existed have no `embedding` and are invisible to `$vectorSearch`. Delete them or backfill embeddings.

### 6. Evolve and compare runs
```bash
.venv/bin/python -m backend.evolve --generations 10 --eval-games 6
.venv/bin/python -m backend.compare --games 4
```
**Cost:** each generation plays `train_games + 2 × eval_games` LLM games, about 14 games or 150k tokens at the defaults. Start with `--generations 3 --eval-games 4`.

### 7. Coordinate with the UI team
- Send them the "Data contract" section of CLAUDE.md. It was expanded from their CSVs: extra `games` and `events` fields, string IDs, `network_id:"net1"`, and `node_states` as a real object.
- Settle the topology and node IDs (see step 2).
- The teammate's `red-vs-blue/web` UI reads *their* collections, not ours. Decide which backend the demo uses.

## Known limitations and possible follow-ups
- **Ties roll back:** `kept` requires strictly better. With few eval games, ties are common; consider more eval games or a tie-breaker (e.g. fewer turns to evict).
- **Parent re-evaluation:** the parent is re-evaluated every generation, for fairness since memory changes between generations, at the cost of 2× eval spend. You could cache it when the level and seeds are unchanged.
- **Guardrails:** only two forms are enforced in code. Others are advisory text in the prompt.
- **No compare summary doc:** `compare.py` prints a table but doesn't store a summary. The UI aggregates `purpose:"eval"` games by `(level, harness_version, memory_enabled)`.
- **Memory leaks across evaluation:** eval games don't reflect, but train games do, so memory grows between generations and can confound parent-vs-child comparisons across generations. Within one generation it's fair.
- **Security cleanup after the hackathon:**
  - The Atlas user `redblue` has the `atlasAdmin` role and a weak password. Downgrade it to readWrite on `redblue`, or delete it.
  - The OpenRouter key was pasted into a chat. Rotate it.

## Useful commands
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m backend.db        # ping + indexes
.venv/bin/python -m backend.llm       # 1 tiny OpenRouter call
.venv/bin/python -m backend.store     # show current harness + curriculum
.venv/bin/python -m backend.runner --env stub --games 1 --blue llm --reflect --show-prompt   # plumbing test (then wipe stub data!)
```
