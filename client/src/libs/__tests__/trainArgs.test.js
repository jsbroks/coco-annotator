import { describe, it, expect } from "vitest";
import { parseArgValue, showValue } from "../trainArgs";

describe("training arguments", () => {
  it("reads values as Ultralytics would", () => {
    expect(parseArgValue("0.002")).toBe(0.002);
    expect(parseArgValue(" 10 ")).toBe(10);
    expect(parseArgValue("1e-4")).toBe(0.0001);
    expect(parseArgValue("True")).toBe(true);
    expect(parseArgValue("false")).toBe(false);
    expect(parseArgValue("None")).toBe(null);
    expect(parseArgValue("[0, 1, 2]")).toEqual([0, 1, 2]);
    expect(parseArgValue("['a', 'b']")).toEqual(["a", "b"]);
    expect(parseArgValue("AdamW")).toBe("AdamW");
  });
  it("shows them back", () => {
    expect(showValue(true)).toBe("True");
    expect(showValue(null)).toBe("None");
    expect(showValue([0, 1])).toBe("[0, 1]");
    expect(showValue(0.01)).toBe("0.01");
  });
});
