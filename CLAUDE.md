# CLAUDE.md — Red vs. Blue: a self-improving cyber defense harness

Hackathon project (MongoDB "Harness Engineering" hackathon, NYC, 2026-09-26). Submission due the same afternoon: favor simple, working code over clever code. Build incrementally, test each step, stop at checkpoints marked >>>.

## Project
A turn-based game on a SIMULATED computer network. Everything is simulation: no real exploit code, no real network traffic.
- RED is a fixed curriculum of 5 scripted attacker levels (no LLM, no learning). Each level is harder and named after MITRE ATT&CK techniques.
- BLUE is an LLM agent inside a harness WE write. The harness improves itself: after games it writes lessons to MongoDB Atlas (embedded with Voyage, retrieved with $vectorSearch), and every generation it proposes a mutation to its own harness (playbook, signals, thresholds, memory policy, guardrails). A mutation is kept only if it beats the current version on evaluation games; otherwise it's rolled back.
- CURRICULUM: when Blue's win rate vs. the current Red level passes a threshold, the next level unlocks. The demo shows Blue climbing levels 1→5 as its defenses get more sophisticated.
- DEPLOYABILITY: Blue talks to the world only through an adapter interface (observe() / act()). Today the adapter is the simulator. Later it can be swapped for real systems (logs, firewall, Tailscale API) in shadow mode. Keep this boundary clean.

Targets the problem statement "Recursive Harnessing": a harness that evolves its own rules, context, and guardrails. MongoDB is the data + memory layer.

A separate team builds the UI (Next.js on Vercel). It reads from Atlas: network map on the left, event log on the right, plus charts. It depends on the data contract below. **DO NOT change these shapes without flagging it to the user.**

## Stack
- Python 3.11+, code in /backend. Our own harness loop, no agent framework.
- pymongo, voyageai, openai SDK pointed at OpenRouter (base_url="https://openrouter.ai/api/v1"), langsmith (@traceable on harness/agent/memory/evolve functions), python-dotenv
- DB name: redblue
- Embeddings: voyage-3.5, 1024 dims
- Vector index "lessons_vec" on redblue.lessons: vector path "embedding" (1024, cosine), filter fields "side" and "level". Created via code (backend/db.py) if possible, else paste JSON in the Atlas UI.
- .env at repo root (gitignored): MONGODB_URI, VOYAGE_API_KEY, OPENROUTER_API_KEY, LANGSMITH_API_KEY, LANGSMITH_TRACING=true, MOVE_MODEL (cheap/fast), EVOLVE_MODEL (stronger)
- Never print, log, or commit secrets.

## Network (sim)
7 nodes: internet, router, laptopA, laptopB, server, printer, database (crown jewel).
Edges: internet-router, router-laptopA, router-laptopB, laptopA-laptopB, laptopA-server, laptopB-printer, server-database, printer-database.
Red can only move along edges. Nodes have hidden state: patched, mfa, creds_stolen, backdoor, compromised, isolated, honeypot, logs_cleared.

## Turn loop
Red acts, then Blue acts. Max 20 turns. Partial observability: Blue sees only signals (alerts, login anomalies, outbound data spikes, new scheduled tasks) with some noise, not Red's true state. Scans reveal more but cost a turn.
Red wins: exfiltrates or ransoms the crown jewel, OR controls >= 50% of nodes. Blue wins: survives 20 turns OR evicts Red completely (no compromised nodes and no backdoors).

## Red levels (scripted, fixed odds, deterministic given a seed)
1. Noisy opportunist: brute force (T1110), exploit unpatched devices (T1190). Loud.
2. Phisher: phishing (T1566) → credential dumping (T1003) → lateral movement (T1021).
3. Quiet operator: uses stolen valid accounts (T1078), low alert signal, waits, avoids recently scanned nodes.
4. Persistent: plants a backdoor via scheduled task (T1053) so a password reset alone doesn't evict it; clears logs (T1070).
5. Advanced: loud decoy on one branch while the real attack goes down the other; hits backups first, then ransomware (T1486) or slow exfiltration (T1041).

## Blue actions (grouped like MITRE D3FEND)
- Detect: scan(node), hunt_persistence(node), review_logins(node), watch_egress(node)
- Harden: patch(node), enable_mfa(node), disable_service(node), firewall_block(a,b)
- Respond: isolate(node), reset_creds(node), remove_backdoor(node), restore(node)
- Deceive: deploy_honeypot(node), plant_honeytoken(node)

## Harness (what evolves)
A harness version = { playbook (rules text), signals (which signals get priority), thresholds (per-signal alert thresholds), memory_policy {k, filter by level?, recency weight}, guardrails (list of forbidden or required patterns, e.g. "never isolate database", "after reset_creds on a level-4+ suspect, also hunt_persistence") }.

Each Blue turn: observe() → recall lessons per memory_policy → build prompt from the harness version → one OpenRouter call (JSON) → validate against legal actions + guardrails (retry once, then a safe fallback like scan) → act() → write event.
After each game: reflect → 1-3 short lessons → memory.
Each generation: EVOLVE_MODEL reads recent losses, lessons, and the current harness → proposes ONE mutation with a short human-readable diff_summary → evaluate new vs. current over N games (same seeds, current level) → keep if win rate is higher, else roll back. Update the curriculum.

## Data contract (collections in redblue) — DO NOT CHANGE WITHOUT FLAGGING
Agreed 2026-09-26 from the team's sample CSVs (events/games/generations/lessons). All fields are real BSON types (node_states is an object, not a JSON string). IDs are readable strings: games "g_0042", lessons "L_0107" (sequential, via the `counters` collection).
- networks: { _id:"net1", nodes:[{id, type, label, crown:bool}], edges:[[a,b],...] }
- games: { _id:"g_0042", network_id:"net1", level, harness_version, memory_enabled:bool, seed, purpose:"eval"|"train"|"demo", winner:"red"|"blue", win_condition:"crown_jewel_stolen"|"half_network_taken"|"survived_20_turns"|"red_evicted", turns, time_to_detect:int|null, time_to_evict:int|null, max_nodes_red, false_alarms, collateral_nodes, lessons_written, tokens_in, tokens_out, started_at, ended_at }
- events: { game_id, turn, side:"red"|"blue", level, harness_version:int|null (null on red), action, category:"attack"|"detect"|"harden"|"respond"|"deceive", mitre:"T1566"|null, from:str|null, target, success:bool, detected:bool|null (null on blue), signals_seen:[str] (blue only, e.g. "alert:credential_access@laptopA"), recalled:[lesson_id], reason:str|null, guardrail_blocked:str|null, outcome:"true_catch"|"no_finding"|"recovery"|"false_alarm"|null, text, node_states:{nodeId:"blue"|"amber"|"red"|"gray"}, ts }
  - text = short plain-English log line, e.g. "Laptop A -> Server: login failed, passwords were reset (T1021)"
  - node_states = FULL board after the move, so the UI can redraw from any single event
  - Red's undetected moves: still write the event, with detected:false (UI shows these faintly)
- lessons: { _id:"L_0107", side:"blue", level, game_id, harness_version, text, embedding:[1024], created_at }
- harness_versions: { version, parent, playbook, signals, thresholds, memory_policy, guardrails, diff_summary, eval:{level, games, win_rate, parent_win_rate}, kept:bool, level_unlocked:int|null, created_at }
- curriculum: { _id:"blue", current_level, pass_threshold:0.7, history:[{level, cleared_at_version, cleared_at}] }
- counters (internal): { _id:"games"|"lessons", seq }

## Build order
1. CLAUDE.md, requirements.txt, .gitignore, .env.example
2. backend/db.py: client, collection handles, ping, index creation
3. backend/sim.py: network, hidden state, Red levels 1-5, Blue legal actions, signals/observation, apply(), winner(). Pure Python. Smoke test: random Blue vs. each level.
4. backend/adapter.py: SimAdapter with observe() and act(). Blue code ONLY touches the world through this.
5. backend/runner.py: play games and write games + events live. CLI: `python -m backend.runner --level 1 --games 3 --blue random`
   >>> CHECKPOINT: show one game doc and 3 event docs. Seed a "demo" set: a few random-Blue games at each level.
6. backend/memory.py: add_lesson(), recall(situation_text, memory_policy, level)
7. backend/harness.py: load harness version, build prompt, choose_action() via OpenRouter, guardrail + legality check, fallback. Seed version 0 = short generic playbook.
8. backend/reflect.py: post-game lessons.
   >>> CHECKPOINT: run 3 LLM-Blue games at level 1, show win rate, a sample prompt (no secrets), and lessons written.
9. backend/evolve.py: propose mutation → eval → keep/rollback → curriculum update. CLI: `python -m backend.evolve --generations 10 --eval-games 6`
10. backend/compare.py: memory on vs. off (and harness v0 vs. latest) at each level, written as games with purpose:"eval".

## Costs
One LLM call per Blue turn with a small prompt. Cap lessons to k from memory_policy. Log token usage per game to the games doc (tokens_in, tokens_out).

## Dev notes
- venv: `.venv` at repo root (`uv venv` + `uv pip install -r requirements.txt`). Run modules from repo root: `.venv/bin/python -m backend.<module>`.
