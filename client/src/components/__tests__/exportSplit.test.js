import { describe, expect, it } from "vitest";
import { splitSizes, splitValid } from "../ExportSplit.vue";

// must match geometry/yolo_format.py split_images
describe("export split", () => {
  it("allocates like the server", () => {
    expect(splitSizes(100, { train: 70, val: 20, test: 10 })).toEqual({ train: 70, val: 20, test: 10 });
    expect(splitSizes(3, { train: 80, val: 10, test: 10 })).toEqual({ train: 1, val: 1, test: 1 });
    expect(splitSizes(1, { train: 50, val: 50, test: 0 })).toEqual({ train: 1, val: 0, test: 0 });
    expect(splitSizes(0, { train: 80, val: 20, test: 0 })).toEqual({ train: 0, val: 0, test: 0 });
  });
  it("validates percentages", () => {
    expect(splitValid({ train: 80, val: 10, test: 10 })).toBe(true);
    expect(splitValid({ train: 80, val: 10, test: 0 })).toBe(false);
    expect(splitValid({ train: 0, val: 50, test: 50 })).toBe(false);
    expect(splitValid({ train: "", val: 50, test: 50 })).toBe(false);
  });
});
