# Red vs Blue — Replay lab

Visual reference: [RULED by Andrii Chervenshchuk](https://www.behance.net/gallery/255864543/RULED-Robotics-Website-Design-UIUX-3D-Motion). Adapted for a recorded adversarial-learning dashboard.

## Current dark appearance

Default canvas: #101215; device surface: #15191E; text: #D8DEE8; headings and defender: #669AFF; attacker: #FF604C. Primary filled controls use #245DC7 with white text. Lime surfaces use dark #182300 text. The original palette below remains the reference, not the active theme.

The page introduction is reduced to “Replay lab”. Red activity markers are 9 px. The current event device scales to 1.22 with a 250 ms ease-out transition while its halo expands to 1.7. Labels stay fixed. Reduced-motion preferences disable scaling and moving edge particles.

## Reference color

| Token | Value | Use |
| --- | --- | --- |
| Paper | #FAFAFA | Page and panels |
| Primary blue | #08359B | Identity, headings, controls, defender |
| Slate | #768AAE | Diagram connections and offline states |
| Lime | #CDFA00 | Selected speed and cleared levels |
| Vermilion | #FA2815 | Attacker and attack indicators |
| Ink | #202C43 | Body text |
| Secondary text | #626F84 | Notes and metadata with readable contrast |

Color is paired with text, labels, or position. Lime is a surface with blue text, never light text on white. Main tokens live in src/index.css; SVG colors in src/lib/colors.js mirror them.

## Typography

Self-hosted Manrope, with its OFL license in public/fonts. Regular for body copy, semibold for labels and event summaries, bold for selective emphasis. Monospace is restricted to compact event coordinates and level labels. Tabular numerals stabilize changing metrics.

Display: 32–56 px, line-height 1.08. Section headings: 14 px. Activity text: 12–14 px. Detail: 11–12 px. Metadata: 9–10 px. Avoid all-caps paragraphs and heavy weights across every element.

## Structure

Use a continuous grid and 1 px dividers, not nested floating cards. Page margins: 32 px desktop, 16 px phone. Panel padding: 22 px desktop, 18 px phone. Controls have a 3 px corner radius; major panels are square. Use the dotted diagram field only on the network panel.

Desktop pairs the network with activity; three supporting modules sit underneath. At 1000 px the supporting grid wraps, and at 680 px all modules stack. Page scroll remains available; the activity feed scrolls independently.

## Interaction

Explicit focus rings, named icon buttons, pressed state for speed controls, pointer-only hover treatments. Preserve recorded-game data and replay behavior. No decorative page-entry motion. A lazy-loaded WebGL sphere sits behind the network, with a red/blue Fresnel rim, wireframe, and slow orbital rings. It never intercepts pointers. Reduced motion freezes rotation; offscreen and hidden-page rendering uses demand frames. Pixel ratio is capped at 1.5, and WebGL failure leaves the SVG network available. Result feedback sits near the bottom rather than covering the network center.
