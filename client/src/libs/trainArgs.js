// Ultralytics arguments as typed on the training page

/** "0.01" -> 0.01, "true" -> true, "[0, 1]" -> [0, 1]; other text stays text */
export function parseArgValue(text) {
  const t = String(text).trim();
  if (/^(true|false)$/i.test(t)) return t.toLowerCase() === "true";
  if (/^(none|null)$/i.test(t)) return null;
  if (/^-?(\d+\.?\d*|\.\d+)(e-?\d+)?$/i.test(t)) return Number(t);
  if (/^\[.*\]$/.test(t)) {
    try {
      return JSON.parse(t.replace(/'/g, '"'));
    } catch {
      return t;
    }
  }
  return t;
}

export function showValue(v) {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return `[${v.join(", ")}]`;
  return String(v);
}
