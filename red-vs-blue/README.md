# Red vs. Blue — A Self-Improving Cyber Defense Arena

An AI **attacker (Red)** tries to break into a simulated computer network. An AI
**defender (Blue)** tries to stop it. They play thousands of games against each
other, and each game Blue gets a little better — **AlphaZero-style self-play
applied to cyber defense.**

Watch a single game unfold move-by-move at 1x, or crank it to 100x and watch
Blue's win rate climb over thousands of episodes. That climbing curve is the
whole point: the harness *learns*.

> Built for the MongoDB **Harness Engineering & Model Wrangling** Hackathon.
> Problem Statement Two — *Long Horizon Engineering*: a harness that
> relentlessly optimizes toward a long-term goal and learns from hard metric
> signals (win rate) across many episodes.

## Why MongoDB Atlas is the core

Atlas is the **harness memory** — the learning loop is meaningless without it:

| Collection | What it stores | Why it matters |
|---|---|---|
| `episodes` | Full move log of every game | Replay + training data |
| `policy_snapshots` | Versioned Blue policy (Q-table) over time | The *learned* artifact; lets us resume/branch training |
| `metrics` | Rolling win rate per episode window | Drives the live "learning" chart |
| `configs` | Network topology, attack/defense rules | The harness can **evolve its own rules** (Statement One) |

Blue's brain is loaded from Atlas at startup and checkpointed back to Atlas as it
learns, so training survives restarts and the whole history is queryable.

## Results

| Defender | Win rate vs. scripted Red (1,000 games) |
|---|---|
| Random baseline | ~52% |
| Trained Blue (greedy) | ~95% |

Blue's win rate climbs from ~52% to ~95% over ~20k self-play episodes, and the
result is stable across independent runs (94.6–95.7%).

## Architecture

```
engine/       Pure-Python game engine (no deps — runs anywhere)
agents/       Red + Blue policies and the self-play learning loop
persistence/  MongoDB Atlas layer (pymongo) + bootstrap script
api/          FastAPI backend that streams live games + metrics
web/          React frontend (network map, log, controls, win-rate chart)
train.py      Headless self-play trainer (stdlib only)
```

The **engine and learning loop use only the Python standard library**, so you can
train and see the win rate climb with zero installs. Atlas + web layers add the
persistence and visualization.

## Quick start (on a machine with internet + Atlas)

```bash
# 1. Configure your Atlas connection
cp .env.example .env         # then paste your Atlas URI into .env

# 2. Backend deps
pip install -r requirements.txt

# 3. Create collections + indexes in your cluster
python -m persistence.bootstrap_atlas

# 4. Train (writes episodes/metrics/policy to Atlas)
python train.py --episodes 5000 --atlas

# 5. Run the API + web app
uvicorn api.main:app --reload      # backend on :8000
cd web && npm install && npm run dev   # frontend on :5173
```

## Train with zero setup (no internet needed)

```bash
python train.py --episodes 5000        # pure stdlib, prints rising win rate
```
