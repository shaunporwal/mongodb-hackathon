// Fixed positions for the 7 default-topology nodes on a 0..100 canvas.
// Mirrors the board sketch in the design brief.
export const NODE_POS = {
  internet: { x: 8, y: 50 },
  router: { x: 26, y: 50 },
  laptop_a: { x: 48, y: 22 },
  laptop_b: { x: 48, y: 78 },
  server: { x: 74, y: 22 },
  printer: { x: 66, y: 78 },
  database: { x: 90, y: 50 },
};

export const NODE_LABEL = {
  internet: "Internet",
  router: "Router",
  laptop_a: "Laptop A",
  laptop_b: "Laptop B",
  server: "Server",
  printer: "Printer",
  database: "Database",
};

// Design-brief color scheme: safe=blue, under_attack=amber, taken=red, offline=gray.
export const STATE_COLOR = {
  safe: "#2f6fed",
  under_attack: "#f5a524",
  taken: "#e5484d",
  offline: "#8a8f98",
};
