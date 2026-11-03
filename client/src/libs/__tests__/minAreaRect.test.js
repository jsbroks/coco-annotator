import { describe, it, expect } from "vitest";
import { minAreaRect, convexHull } from "../minAreaRect";

const rot = (p, deg, c = { x: 0, y: 0 }) => {
  const t = (deg * Math.PI) / 180;
  const x = p.x - c.x, y = p.y - c.y;
  return { x: c.x + x * Math.cos(t) - y * Math.sin(t), y: c.y + x * Math.sin(t) + y * Math.cos(t) };
};

describe("minAreaRect", () => {
  it("finds a rotated rectangle from its outline plus inner points", () => {
    const rect = [{ x: -50, y: -10 }, { x: 50, y: -10 }, { x: 50, y: 10 }, { x: -50, y: 10 }];
    const inner = [{ x: 0, y: 0 }, { x: 20, y: 5 }, { x: -30, y: -8 }];
    const pts = [...rect, ...inner].map(p => rot(p, 30, { x: 0, y: 0 })).map(p => ({ x: p.x + 200, y: p.y + 100 }));
    const r = minAreaRect(pts);
    expect(r.w).toBeCloseTo(100, 6);
    expect(r.h).toBeCloseTo(20, 6);
    expect(r.angle).toBeCloseTo(30, 6);
    expect(r.cx).toBeCloseTo(200, 6);
    expect(r.cy).toBeCloseTo(100, 6);
  });

  it("puts the long side first, pointing right", () => {
    // a tall box tilted by 10°: long side is near vertical
    const pts = [{ x: -5, y: -40 }, { x: 5, y: -40 }, { x: 5, y: 40 }, { x: -5, y: 40 }].map(p => rot(p, 10));
    const r = minAreaRect(pts);
    expect(r.w).toBeCloseTo(80, 6);
    expect(r.h).toBeCloseTo(10, 6);
    expect(r.angle).toBeGreaterThan(-90);
    expect(r.angle).toBeLessThanOrEqual(90);
    expect(Math.abs(r.angle)).toBeCloseTo(80, 6);
    const [a, b] = r.corners;
    expect(Math.hypot(b.x - a.x, b.y - a.y)).toBeCloseTo(80, 6);
    expect(b.x).toBeGreaterThanOrEqual(a.x);
  });

  it("contains every point of a blob, and grows with padding", () => {
    const pts = [];
    for (let i = 0; i < 60; i++) {
      const t = (i / 60) * 2 * Math.PI;
      pts.push({ x: 300 + 80 * Math.cos(t) + (i % 7), y: 50 + 25 * Math.sin(t) - (i % 5) });
    }
    const r = minAreaRect(pts);
    const t = (r.angle * Math.PI) / 180;
    for (const p of pts) {
      const du = (p.x - r.cx) * Math.cos(t) + (p.y - r.cy) * Math.sin(t);
      const dv = -(p.x - r.cx) * Math.sin(t) + (p.y - r.cy) * Math.cos(t);
      expect(Math.abs(du)).toBeLessThanOrEqual(r.w / 2 + 1e-6);
      expect(Math.abs(dv)).toBeLessThanOrEqual(r.h / 2 + 1e-6);
    }
    const padded = minAreaRect(pts, 3);
    expect(padded.w).toBeCloseTo(r.w + 6, 6);
    expect(padded.h).toBeCloseTo(r.h + 6, 6);
  });

  it("handles degenerate input", () => {
    expect(minAreaRect([])).toBeNull();
    expect(minAreaRect([{ x: 1, y: 1 }])).toBeNull();
    expect(convexHull([{ x: 0, y: 0 }, { x: 1, y: 1 }, { x: 2, y: 2 }]).length).toBe(2);
  });
});
