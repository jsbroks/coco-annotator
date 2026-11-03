import { describe, it, expect } from "vitest";
import { smooth, niceTicks, fmtNumber, fmtTick } from "../scalars";

describe("training curves", () => {
  it("smooths like TensorBoard (debiased)", () => {
    const pts = [[1, 10], [2, 10], [3, 10]];
    expect(smooth(pts, 0.9).map(p => p[1])).toEqual([10, 10, 10].map(v => expect.closeTo(v, 9)));
    const s = smooth([[1, 0], [2, 10]], 0.5);
    expect(s[0][1]).toBe(0);
    expect(s[1][1]).toBeCloseTo(10 * 0.5 / 0.75);
    expect(smooth(pts, 0)).toBe(pts);
  });
  it("picks round ticks", () => {
    expect(niceTicks(0, 1).ticks).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
    expect(niceTicks(0.31, 0.38).ticks[0]).toBeCloseTo(0.32);
    expect(niceTicks(2, 2).ticks.length).toBeGreaterThan(1);
  });
  it("labels ticks by their step", () => {
    expect([0, 0.25, 0.5].map(v => fmtTick(v, 0.25))).toEqual(["0", "0.25", "0.50"]);
    expect([2, 4].map(v => fmtTick(v, 2))).toEqual(["2", "4"]);
    expect(fmtTick(2.5, 2.5)).toBe("2.5");
    expect(fmtTick(0.0005, 0.0005)).toBe("5.0e-4");
    expect(fmtTick(0.02, 0.005)).toBe("0.020");
  });
  it("formats numbers", () => {
    expect(fmtNumber(0.012345)).toBe("0.012");
    expect(fmtNumber(0.0001)).toBe("1.0e-4");
    expect(fmtNumber(12.34)).toBe("12.3");
  });
});
