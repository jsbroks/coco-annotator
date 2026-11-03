/**
 * The smallest rotated rectangle around a set of points (rotating calipers
 * on the convex hull). Used to turn a mask / polygon into a rotated box.
 *
 * Points are {x, y}. The result is 4 corners in order; the first edge
 * (corner 0 -> 1) is a long side pointing right (angle in (-90°, 90°]),
 * so boxes of the same kind of object get the same heading.
 */

function cross(o, a, b) {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

/** Convex hull (monotone chain), counter-clockwise in y-up terms */
export function convexHull(points) {
  const pts = points
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y))
    .map(p => ({ x: p.x, y: p.y }))
    .sort((a, b) => a.x - b.x || a.y - b.y);
  if (pts.length < 3) return pts;
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

/**
 * @param {{x:number,y:number}[]} points
 * @param {number} pad grow every side outwards by this much (same units)
 * @returns {{corners: {x,y}[], cx, cy, w, h, angle}|null} angle in degrees
 */
export function minAreaRect(points, pad = 0) {
  const hull = convexHull(points);
  if (hull.length < 2) return null;

  let best = null;
  for (let i = 0; i < hull.length; i++) {
    const a = hull[i];
    const b = hull[(i + 1) % hull.length];
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    if (!len) continue;
    // the edge direction (u) and its normal (v)
    const ux = (b.x - a.x) / len, uy = (b.y - a.y) / len;
    const vx = -uy, vy = ux;
    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    for (const p of hull) {
      const du = p.x * ux + p.y * uy;
      const dv = p.x * vx + p.y * vy;
      if (du < minU) minU = du;
      if (du > maxU) maxU = du;
      if (dv < minV) minV = dv;
      if (dv > maxV) maxV = dv;
    }
    const area = (maxU - minU) * (maxV - minV);
    if (!best || area < best.area - 1e-9) best = { area, ux, uy, vx, vy, minU, maxU, minV, maxV };
  }
  if (!best) return null;

  let { ux, uy, minU, maxU, minV, maxV } = best;
  minU -= pad; maxU += pad; minV -= pad; maxV += pad;
  let w = maxU - minU, h = maxV - minV;
  const cu = (minU + maxU) / 2, cv = (minV + maxV) / 2;
  const cx = cu * ux + cv * best.vx;
  const cy = cu * uy + cv * best.vy;

  // heading: along the long side, pointing right
  let angle = Math.atan2(uy, ux);
  if (h > w) {
    angle += Math.PI / 2;
    [w, h] = [h, w];
  }
  let deg = (angle * 180) / Math.PI;
  deg = ((((deg + 90) % 180) + 180) % 180) - 90; // (-90, 90]
  if (deg === -90) deg = 90;
  const t = (deg * Math.PI) / 180;
  const ax = Math.cos(t), ay = Math.sin(t); // first edge direction
  const bx = -ay, by = ax;
  const hw = w / 2, hh = h / 2;
  const corners = [
    { x: cx - ax * hw - bx * hh, y: cy - ay * hw - by * hh },
    { x: cx + ax * hw - bx * hh, y: cy + ay * hw - by * hh },
    { x: cx + ax * hw + bx * hh, y: cy + ay * hw + by * hh },
    { x: cx - ax * hw + bx * hh, y: cy - ay * hw + by * hh }
  ];
  return { corners, cx, cy, w, h, angle: deg };
}
