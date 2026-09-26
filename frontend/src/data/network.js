// Topology matches the `node_states` keys in the real events.csv exactly
// (internet/router/laptopA/laptopB/server/printer/database) -- this is the
// MITRE-ATT&CK-flavored intrusion scenario the real backend actually
// generated data for, not the earlier DDoS mockup (that dataset doesn't
// exist; this one does, so it wins). Positions are a fresh hex-ish layout
// in the same 1000x560 viewBox as before.

export const NODES = [
  { id: "internet", name: "Internet", pos: [130, 280], r: 30 },
  { id: "router", name: "Router", pos: [320, 280], r: 32 },
  { id: "laptopA", name: "Laptop A", pos: [500, 150], r: 30 },
  { id: "laptopB", name: "Laptop B", pos: [500, 410], r: 30 },
  { id: "server", name: "Server", pos: [680, 150], r: 32 },
  { id: "printer", name: "Printer", pos: [680, 410], r: 28 },
  { id: "database", name: "Database", pos: [880, 280], r: 36, crownJewel: true },
];

export const EDGES = [
  ["internet", "router"],
  ["router", "laptopA"],
  ["router", "laptopB"],
  ["laptopA", "server"],
  ["laptopB", "printer"],
  ["server", "database"],
  ["printer", "database"],
];

// The four states real node_states values map onto -- see lib/colors.js.
export const NODE_STATE_TO_STATUS = {
  blue: "safe",
  amber: "attacked",
  red: "taken",
  gray: "offline",
};
