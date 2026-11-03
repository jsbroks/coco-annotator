import { describe, it, expect } from "vitest";
import { ancestors, buildTree, byName, findNode, isUnder, normalizePath, parseParents, pathLabel } from "../parents";

describe("parent paths", () => {
  it("normalizes and labels paths", () => {
    expect(normalizePath(" 交通工具 / 陸地 ")).toBe("交通工具/陸地");
    expect(parseParents("交通工具/陸地, 交通工具／水上")).toEqual(["交通工具/陸地", "交通工具/水上"]);
    expect(pathLabel("交通工具/陸地")).toBe("交通工具 › 陸地");
    expect(pathLabel("交通工具/陸地/汽車", "交通工具")).toBe("陸地 › 汽車");
    expect(ancestors("a/b/c")).toEqual(["a", "a/b", "a/b/c"]);
    expect(isUnder("a/b", "a")).toBe(true);
    expect(isUnder("ab", "a")).toBe(false);
  });

  it("sorts Chinese numbers as numbers", () => {
    const names = ["第十二區", "第二區", "第一區", "第十區", "第三區"];
    expect([...names].sort(byName)).toEqual(["第一區", "第二區", "第三區", "第十區", "第十二區"]);
  });

  it("builds a tree with the same name under different parents", () => {
    const cats = [
      { id: 1, name: "人", supercategories: ["場景/A 區"] },
      { id: 2, name: "人", supercategories: ["場景/B 區"] },
      { id: 3, name: "車", supercategories: ["場景/A 區"] },
      { id: 4, name: "樹", supercategories: [] }
    ];
    const tree = buildTree(cats);
    expect(tree.children.map(n => n.name)).toEqual(["場景"]);
    const scene = findNode(tree, "場景");
    expect(scene.all.map(c => c.id)).toEqual([1, 2, 3]);
    expect(scene.items).toEqual([]);
    expect(scene.children.map(n => n.name)).toEqual(["A 區", "B 區"]);
    expect(findNode(tree, "場景/A 區").items.map(c => c.id)).toEqual([1, 3]);
    expect(findNode(tree, "nope")).toBe(null);
  });
});
