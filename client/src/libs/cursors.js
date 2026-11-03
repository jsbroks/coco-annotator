/**
 * A crosshair that stays visible on any picture: black lines with a white
 * outline, a gap in the middle (the point itself is not covered) and a small
 * red dot exactly on it. Replaces the browser's thin 1-pixel crosshair.
 */
const SIZE = 33;
const C = 16.5; // the centre (the cursor's hot spot is 16, 16)
const GAP = 4;
const ARM = 14;

function svg() {
  const lines = [
    [C - ARM, C, C - GAP, C], [C + GAP, C, C + ARM, C],
    [C, C - ARM, C, C - GAP], [C, C + GAP, C, C + ARM]
  ];
  const path = lines.map(([x1, y1, x2, y2]) => `M${x1} ${y1}L${x2} ${y2}`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}">`
    + `<path d="${path}" stroke="#fff" stroke-width="4" stroke-linecap="round"/>`
    + `<path d="${path}" stroke="#000" stroke-width="1.6" stroke-linecap="round"/>`
    + `<circle cx="${C}" cy="${C}" r="2" fill="#ff1744" stroke="#fff" stroke-width="1"/>`
    + `</svg>`;
}

export const CROSSHAIR = `url("data:image/svg+xml,${encodeURIComponent(svg())}") 16 16, crosshair`;

/** The cursor to show for what a tool asks for. */
export function toolCursor(name) {
  // drawing tools: the visible crosshair
  return ["crosshair", "copy", "cell"].includes(name) ? CROSSHAIR : name;
}
