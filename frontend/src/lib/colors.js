// Keep SVG colors aligned with the design tokens in index.css.
export const COLORS = {
  bg: "#101215", panel: "#15191E", elevated: "#20252D",
  heading: "#669AFF", text: "#D8DEE8", muted: "#929DAC",
  line: "#77869D", blue: "#669AFF", red: "#FF604C",
  amber: "#DDB65D", gray: "#77869D", green: "#B6D959",
};

// Real recorded node_states use "blue/amber/red/gray" directly (see
// NODE_STATE_TO_STATUS in data/network.js) -- these are the same four
// concepts as before, just relabeled for the intrusion scenario: a node is
// either safe, under active suspicion/attack, fully taken by Red, or
// offline (isolated by Blue, or simply not provisioned yet).
export const STATUS_COLORS = {
  safe: COLORS.blue,
  attacked: COLORS.amber,
  taken: COLORS.red,
  offline: COLORS.gray,
};

export const STATUS_LABELS = {
  safe: "Safe",
  attacked: "Under attack",
  taken: "Taken by Red",
  offline: "Offline / isolated",
};

export const SIDE_COLORS = {
  RED: COLORS.red,
  BLUE: COLORS.blue,
};
