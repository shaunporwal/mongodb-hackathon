# Red vs Blue — Design Brief

**How we made a self-improving agent legible in one minute.**

This is the story behind the interface in `docs/visuals/`. The engineering
problem was *harness engineering*: an agent that rewrites its own strategy and
gets better over thousands of games. The design problem was harder — none of
that shows up on a screen by itself. A win-rate number climbing in a database is
invisible. Our job was to make the learning *watchable*, fast.

The judges first see a **60-second demo video**. That constraint drove every
decision: no element earns its place unless a newcomer understands it at a
glance, with no narration.

> Everything shown is a **simulation** — colored game pieces moving on a map.
> No real systems, no real intrusions.

---

## The 60-second cut

The video is the design target, not an afterthought. It carries **one image and
one number**, in this order:

| Time | On screen | The beat |
|---|---|---|
| 0–8s | Arena, attack path lighting up | "An AI attacker breaks into a pretend office." |
| 8–22s | A **lesson card drawn from memory**, match 0.92, win-chance buff | "It remembers what worked last time." |
| 22–34s | The move lands — Red reaches the crown jewel | "…and reuses it to win." |
| 34–48s | Win-rate curve **14% → 71%** | "Over 142 games it taught itself." |
| 48–58s | Memory **ON 71% vs OFF 38%** | "Turn the memory off and it forgets." |
| 58–60s | MongoDB + repo | "Its memory is MongoDB Atlas + Vector Search." |

If a viewer catches only two frames — the green lesson card and the climbing
curve — they've understood the project. Everything else supports those two.

---

## Three screens, one job each

| Screen | File | The job |
|---|---|---|
| **Arena** | `arena_red_learns.html` | Watch one game — and watch the agent *recall a lesson* mid-move |
| **Progress** | `progress_red_learns.html` | Prove the learning with four charts a non-expert can read |
| **Concept** | `01_architecture`, `02_ddos_turn`, `05_any_node_rules` | How the harness, MongoDB and the model fit together |

Open any `.html` in a browser — the arena is animated, and every frame of the
video is captured live from it.

---

## The design system

One small, strict token set, so every screen and every frame reads as one product.

**Color is meaning, never decoration.**

| Token | Value | Stands for |
|---|---|---|
| Red | `#FF4D55` | the attacker, and anything it controls |
| Blue | `#4C9AFF` | the defender, and anything still safe |
| Amber | `#FFB547` | under attack, not yet lost |
| Gold | `#FFD166` | the crown jewel (the database) |
| Green | `#3DDC97` | **memory** — recalled lessons, the thing that makes it learn |
| Ground | `#070B14` | near-black board, so the neon reads |

The most important choice: **green is reserved for memory.** Recall notes, the
lesson deck, the match score, the "lessons written" counter — all green, and
nothing else is. In a 60-second video the eye has no time to hunt, so when green
flashes, the viewer already knows: *the agent just used its past.*

**Type does the ranking.** Chakra Petch (squared, technical) for the HUD numbers
and labels; IBM Plex Sans for anything read as a sentence; IBM Plex Mono for
machine details (turn tags, MITRE IDs, match scores). Three roles, no drift.

**Motion is a pointer.** Attack traffic flows *toward* its target so the eye
follows the threat. A node under attack pulses; a taken node goes still. The
recall beam animates from the device to the lesson card so cause and effect are
unmistakable in a single pass. Nothing moves that isn't telling you where to look
— critical when there are only 60 seconds and no voice-over.

---

## Making "memory" a game mechanic

The technical claim is "the agent stores lessons in MongoDB and retrieves them by
meaning with Vector Search." That sentence means nothing to most people, and
there's no time to explain it. So we turned it into something everyone already
understands — **a deck of cards.**

- A **memory deck** in the corner shows the pool: *142 lessons in memory.*
- When the agent recalls one, a **card is drawn** and played: the lesson, a
  **match score of 0.92** (the vector-search similarity, shown as a card stat),
  and a **"+34% win chance"** buff.
- The card footer says exactly where it came from: *drawn from 142 lessons in
  MongoDB · matched by meaning.*

This is the video's payoff frame. A viewer doesn't need to know what an embedding
is to watch the agent *play a card it learned three games ago and win with it.*
The database stops being plumbing and becomes the move that wins the game.

---

## How each mechanic maps to a pixel

We refused any UI that wasn't backed by real game state (the data lives in
`games.csv`, `generations.csv`, `lessons.csv`, `scenarios.csv`).

| Game mechanic | What you see |
|---|---|
| Attacker takes a device | node turns red, edge lights up, packets flow |
| Attacker can't be seen yet | faint dashed edge until the defender scans |
| Lesson recalled (Vector Search) | green card drawn from the deck, match score, buff |
| Lesson written after a game | "+2 📝" and an XP bar on the *lessons written* panel |
| Climbing the defense levels | a level ladder: cleared, in-progress, locked |
| Getting smarter over time | the 14% → 71% win-rate curve — the centerpiece |
| Memory is what does it | a direct **memory ON 71% vs OFF 38%** comparison |

That last chart is the honest test of the whole idea: turn recall off and the
agent forgets the trick every game. The interface makes that falsifiable on
screen, in one shot.

---

## Why this wins the room

- **Technical demo (35%)** — the product *is* the demo: a live board where the
  agent visibly reuses memory to win, readable in 60 seconds with no narration.
- **Implementation difficulty (30%)** — the UI surfaces the hard parts
  (versioned strategy, vector recall, per-turn state) instead of hiding them.
- **Impact (20%)** — a self-improving adversary is a real, current problem;
  the simulation frames it responsibly.
- **Creativity (15%)** — treating agent memory as a collectible-card mechanic is
  a lens the judges haven't seen, and it makes an abstract system playful.

---

## Build notes

- Self-contained HTML: fonts from Google Fonts, everything else inline. No build
  step — open the file.
- The arena renders an animated map (rotating field, flowing traffic, pulsing
  nodes, the recall beam and card) in plain SVG + a small canvas backdrop, so the
  video is screen-captured from the real thing, not mocked.
- Diagrams are Mermaid — sources are the `.mmd` files, re-render with
  `npx @mermaid-js/mermaid-cli -i file.mmd -o file.png`.
- Designed at 1600×900 for the demo screen; the layout is the storyboard v0 and
  the frontend build follow.
