/**
 * Parent categories ("supercategory"). A category can have several parents;
 * older categories only have the single COCO ``supercategory`` string.
 */

/**
 * A parent is a path: "Vehicles/Land" is "Land" inside "Vehicles", any
 * depth. The same category name can be used again under another parent.
 */
export const PATH_SEP = "/";

/** " Vehicles / Land " -> "Vehicles/Land" */
export function normalizePath(value) {
  return String(value || "").split(/[/／]/).map(s => s.trim()).filter(Boolean).join(PATH_SEP);
}

export function pathParts(path) {
  return normalizePath(path).split(PATH_SEP).filter(Boolean);
}

/** "Vehicles/Land" -> "Vehicles › Land" */
export function pathLabel(path, from = "") {
  let parts = pathParts(path);
  const base = pathParts(from);
  if (base.length && base.every((b, i) => parts[i] === b)) parts = parts.slice(base.length);
  return parts.join(" › ");
}

/** last level of a path ("Vehicles/Land" -> "Land") */
export function pathName(path) {
  const parts = pathParts(path);
  return parts[parts.length - 1] || "";
}

/** "a/b/c" -> ["a", "a/b", "a/b/c"] */
export function ancestors(path) {
  const parts = pathParts(path);
  return parts.map((_, i) => parts.slice(0, i + 1).join(PATH_SEP));
}

/** is ``path`` the same as or inside ``base`` */
export function isUnder(path, base) {
  path = normalizePath(path);
  base = normalizePath(base);
  return path === base || path.startsWith(base + PATH_SEP);
}

/** "a, b、c" or a list -> unique trimmed parent paths */
export function parseParents(value) {
  const items = Array.isArray(value) ? value : String(value || "").split(/[,，、;；\n]+/);
  const out = [];
  items.forEach(item => {
    const name = normalizePath(item);
    if (name && !out.includes(name)) out.push(name);
  });
  return out;
}

export function parentsOf(category) {
  if (!category) return [];
  if (Array.isArray(category.supercategories) && category.supercategories.length) {
    return parseParents(category.supercategories);
  }
  return parseParents(category.supercategory);
}

// "第十二區" sorts after "第二區": Chinese numbers compare as numbers
const CN_DIGITS = { 零: 0, 〇: 0, 一: 1, 二: 2, 兩: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 };
function cnNumber(text) {
  let total = 0;
  let current = 0;
  for (const ch of text) {
    if (ch in CN_DIGITS) current = CN_DIGITS[ch];
    else if (ch === "十") { total += (current || 1) * 10; current = 0; }
    else if (ch === "百") { total += (current || 1) * 100; current = 0; }
  }
  return total + current;
}
const sortKey = s => String(s).replace(/[零〇一二兩三四五六七八九十百]+/g, m => String(cnNumber(m)));
export const byName = (a, b) => sortKey(a).localeCompare(sortKey(b), undefined, { numeric: true }) || a.localeCompare(b);

/**
 * Categories grouped by parent: [{ parent, items }] sorted by parent name,
 * categories without a parent last (parent: null). With ``firstOnly`` a
 * category goes in its first parent's group only; otherwise in each.
 */
export function groupByParent(categories, { firstOnly = false } = {}) {
  const groups = new Map();
  const none = [];
  categories.forEach(c => {
    const parents = parentsOf(c);
    if (!parents.length) {
      none.push(c);
      return;
    }
    (firstOnly ? parents.slice(0, 1) : parents).forEach(p => {
      if (!groups.has(p)) groups.set(p, []);
      groups.get(p).push(c);
    });
  });
  const out = [...groups.keys()].sort(byName).map(parent => ({ parent, items: groups.get(parent) }));
  if (none.length) out.push({ parent: null, items: none });
  return out;
}

/** every parent path used by these categories (with the levels above them), sorted */
export function allParents(categories) {
  const names = new Set();
  categories.forEach(c => parentsOf(c).forEach(p => ancestors(p).forEach(a => names.add(a))));
  return [...names].sort(byName);
}

/**
 * The parent tree: { name, path, children: [node], items: [category directly
 * here], all: [categories here or below] }. The root has path "".
 */
export function buildTree(categories) {
  const root = { name: "", path: "", children: [], items: [], all: [], map: new Map() };
  const nodeAt = path => {
    let node = root;
    pathParts(path).forEach((part, i, parts) => {
      let child = node.map.get(part);
      if (!child) {
        child = { name: part, path: parts.slice(0, i + 1).join(PATH_SEP), children: [], items: [], all: [], map: new Map() };
        node.map.set(part, child);
        node.children.push(child);
      }
      node = child;
    });
    return node;
  };
  categories.forEach(c => {
    const parents = parentsOf(c);
    const seen = new Set();
    parents.forEach(p => {
      nodeAt(p).items.push(c);
      ancestors(p).forEach(a => {
        if (seen.has(a)) return;
        seen.add(a);
        nodeAt(a).all.push(c);
      });
    });
  });
  const sort = node => {
    node.children.sort((a, b) => byName(a.name, b.name));
    node.children.forEach(sort);
  };
  sort(root);
  return root;
}

/** the node at a path, or null */
export function findNode(tree, path) {
  let node = tree;
  for (const part of pathParts(path)) {
    node = node.map.get(part);
    if (!node) return null;
  }
  return node;
}

/** does the search text match the category or one of its parents */
export function matchesSearch(category, q) {
  if (!q) return true;
  q = q.toLowerCase();
  return (category.name || "").toLowerCase().includes(q) ||
    parentsOf(category).some(p => p.toLowerCase().includes(q) || pathLabel(p).toLowerCase().includes(q));
}
