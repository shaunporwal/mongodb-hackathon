# Red vs Blue — Design Brief

**The design process behind the UI visuals in `docs/visuals/`.**

The engineering problem was *harness engineering*: an agent that rewrites its own
strategy and gets better over thousands of games. The design problem was harder —
none of that shows up on a screen by itself. A win-rate number climbing in a
database is invisible. Our job was to make the learning *watchable*: to turn
abstract agent behavior into something a person can read at a glance.

This document explains how we got there — the principles, the system, and why
each element looks the way it does.

> Everything shown is a **simulation** — colored game pieces moving on a map.
> No real systems, no real intrusions.

---

## The design principle

We started from one sentence and refused any element that didn't serve it:

> *"The attacker started clumsy, wrote down what worked, and taught itself to win."*

That gave us two things a viewer must always be able to find:

- **The learning event** — the moment the agent reuses something it learned
  (a lesson recalled from memory).
- **The proof** — the win rate climbing across games.

Everything on screen either *is* one of those two things or points to them.
When a candidate element helped neither, we cut it.

---

## Three screens, one job each

| Screen | File | The job |
|---|---|---|
| **Arena** | `arena_red_learns.html` | Watch one game — and watch the agent *recall a lesson* mid-move |
| **Progress** | `progress_red_learns.html` | Prove the learning with four charts a non-expert can read |
| **Concept** | `01_architecture`, `02_ddos_turn`, `05_any_node_rules` | How the harness, MongoDB and the model fit together |

Open any `.html` in a browser — the arena is animated.

---

## The design system

One small, strict token set, so every screen reads as one product.

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
nothing else is. Memory is what separates this agent from a scripted one, so it
gets a color no other element may borrow. When green appears, the viewer knows
the agent is thinking with its past.

**Type does the ranking.** Chakra Petch (squared, technical) for the HUD numbers
and labels; IBM Plex Sans for anything read as a sentence; IBM Plex Mono for
machine details (turn tags, MITRE IDs, match scores). Three roles, no drift.

**Motion is a pointer, not an effect.** Attack traffic flows *toward* its target
so the eye follows the threat. A node under attack pulses; a taken node goes
still. The recall beam animates from the device to the lesson card so cause and
effect are unmistakable. Nothing moves unless it is telling you where to look.

**Layout is a HUD.** The board owns two-thirds of the screen; the play-by-play
log runs down the side; state (game, level, win rate, lessons) sits in a top bar
that reads like a game's status strip. Summary before detail, always.

---

## Making "memory" a game mechanic

The technical claim is "the agent stores lessons in MongoDB and retrieves them by
meaning with Vector Search." That sentence means little to most people, so we
translated it into something everyone already understands — **a deck of cards.**

- A **memory deck** in the corner shows the pool: *142 lessons in memory.*
- When the agent recalls one, a **card is drawn** and played: the lesson, a
  **match score of 0.92** (the vector-search similarity, shown as a card stat),
  and a **"+34% win chance"** buff.
- The card footer says exactly where it came from: *drawn from 142 lessons in
  MongoDB · matched by meaning.*

This reframes the database. It stops being plumbing and becomes the move that
wins the game — the recall you can watch happen. It's the clearest expression of
the whole design principle.

---

## How each mechanic maps to a pixel

We refused any UI that wasn't backed by real game state. The data lives in the
project's `games.csv`, `generations.csv`, `lessons.csv` and `scenarios.csv`, and
every visual element traces back to a real field.

| Game mechanic | What you see |
|---|---|
| Attacker takes a device | node turns red, edge lights up, packets flow |
| Attacker can't be seen yet | faint dashed edge until the defender scans |
| Lesson recalled (Vector Search) | green card drawn from the deck, match score, buff |
| Lesson written after a game | "+2 📝" and an XP bar on the *lessons written* panel |
| Climbing the defense levels | a level ladder: cleared, in-progress, locked |
| Getting smarter over time | the 14% → 71% win-rate curve — the centerpiece |
| Memory is what does it | a direct **memory ON 71% vs OFF 38%** comparison |

That last chart is the honest test of the idea: turn recall off and the agent
forgets the trick every game. The interface makes that falsifiable on screen.

---

## Build notes

- Self-contained HTML: fonts from Google Fonts, everything else inline. No build
  step — open the file.
- The arena renders an animated map (rotating field, flowing traffic, pulsing
  nodes, the recall beam and card) in plain SVG plus a small canvas backdrop —
  no framework, no external assets.
- Diagrams are Mermaid — sources are the `.mmd` files, re-render with
  `npx @mermaid-js/mermaid-cli -i file.mmd -o file.png`.
- Designed at 1600×900. These files are the storyboard the production frontend
  build follows.
