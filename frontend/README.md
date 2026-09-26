# Frontend

All frontend work for the Red-learner demo. Nothing here is deleted — older design
variants are preserved under `designs/` in case an earlier one reads better.

## Live app
- `index.html` — the working UI. Served by the backend at `http://localhost:8000/`
  (run `.venv/bin/uvicorn backend.api:app --port 8000`). Wired to the Atlas data:
  network map, play-by-play log, Red win-rate-by-harness-version curve, harness
  evolution (mutations kept/rolled), and a **Train Red** button that launches an
  evolve run in the background.

## Design variants (static mockups, from the `frontend` branch — reference only)
`designs/` (each `.html` has a matching `.png` preview):
- `ui_mockup_game.html` — richest: animated arena, 3D globe, botnet, playbook diff.
- `arena_red_learns.html` — arena view, Red-learns framing.
- `progress_red_learns.html` — the win-rate/progress view.
- `ui_mockup_flat.html` — flat/simple layout.

## Diagrams
`diagrams/` — architecture and turn-flow (`.mmd` source + `.png`).

## The older React app
`../web/` still exists (map/log/chart/harness-panel React components + Vite). The
single-file `index.html` here is the simpler, self-served version for the demo.
