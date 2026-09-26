# Red vs Blue — Design Brief

**How we made a self-improving agent legible in three seconds.**

This is the story behind the interface in `docs/visuals/`. The engineering
problem was *harness engineering*: an agent that rewrites its own strategy and
gets better over thousands of games. The design problem was harder — none of
that shows up on a screen by itself. A win-rate number climbing in a database
is invisible. Our job was to make the learning *watchable*.

> Everything shown is a **simulation** — colored game pieces moving on a map.
> No real systems, no real intrusions.

---

## The one thing a judge must see

A judge watches each demo for about three minutes and remembers **one image and
one number**. We designed the whole screen around a single sentence:

> *"The attacker started clumsy, wrote down what worked, and taught itself to win."*

- **The image:** an attack path lighting up across a network, and a **lesson card
  being pulled from memory** the moment the agent reuses something it learned.
- **The number:** a win-rate curve climbing from **14% → 71%** across 142 games.

Every design decision below serves that sentence. If an element didn't help a
newcomer feel the learning, we cut it.

---

## Three screens, one job each

| Screen | File | The job |
|---|---|---|
| **Arena** | `arena_red_learns.html` | Watch one game unfold — and watch the agent *recall a lesson* mid-move |
| **Progress** | `progress_red_learns.html` | Prove the learning with four charts a non-expert can read |
| **Concept** | `01_architecture`, `02_ddos_turn`, `05_any_node_rules` | Show how the harness, MongoDB and the model fit together |

Open any `.html` in a browser — the arena is animated.

---

## The design system

We built one small, strict token set so every screen reads as one product.

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
nothing else is. When green appears, the agent is *thinking with its past*. That
is the differentiator, so it gets its own color no other element may borrow.

**Type does the ranking.** Chakra Petch (a squared, technical face) for numbers
and labels that should feel like a game HUD; IBM Plex Sans for anything a person
reads as a sentence; IBM Plex Mono for machine details (turn tags, MITRE IDs,
match scores). Three roles, no drift.

**Motion is a pointer, not decoration.** Attack traffic flows *toward* its target
so the eye follows the threat. A node under attack pulses; a taken node stops.
The recall beam animates from the device to the lesson card so cause and effect
are unmistakable. Nothing moves that isn't telling you where to look.

---

## Making "memory" a game mechanic

The technical claim is "the agent stores lessons in MongoDB and retrieves them by
meaning with Vector Search." That sentence means nothing to most people. So we
turned it into something everyone already understands — **a deck of cards.**

- A **memory deck** in the corner shows the pool: *142 lessons in memory.*
- When the agent recalls one, a **card is drawn** and played: a lesson, a
  **match score of 0.92** (the vector-search similarity, shown as a card stat),
  and a **"+34% win chance"** buff.
- The card footer says exactly where it came from: *drawn from 142 lessons in
  MongoDB · matched by meaning.*

This is the demo's payoff. A viewer doesn't need to know what an embedding is to
watch the agent *pull a card it learned three games ago and win with it*. The
database stops being plumbing and becomes the move that wins the game.

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
screen.

---

## Why this wins the room

- **Technical demo (35%)** — the product *is* the demo: a live board where the
  agent visibly reuses memory to win, not a slide about it.
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
  nodes, the recall beam and card) in plain SVG + a small canvas backdrop.
- Diagrams are Mermaid — sources are the `.mmd` files, re-render with
  `npx @mermaid-js/mermaid-cli -i file.mmd -o file.png`.
- Designed at 1600×900 for the demo screen; the layout is the storyboard v0 and
  the frontend build follow.
