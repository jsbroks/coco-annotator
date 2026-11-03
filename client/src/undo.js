import axios from "axios";

export default class UndoAction {
  constructor({ name, action, func, args }) {
    this.name = name;
    this.action = action;
    this.func = func;
    this.args = args;
  }

  undo() {
    return this.func(this.args);
  }
}

/**
 * Undo for deleted annotations: restore them on the server (deleting only
 * marks them as deleted) and put them back in their category lists, with
 * the shape they had when they were deleted.
 * @param {Array<{category: Object, data: Object}>} snapshots
 */
export function restoreAnnotations(snapshots) {
  const ids = snapshots.map(({ data }) => data.id);
  return axios.post("/api/trash/restore", {
    items: [{ type: "annotation", ids }],
    include_parents: true
  }).then(() => {
    snapshots.forEach(({ category, data }) => {
      if (!category.annotations.some(a => a.id === data.id)) {
        category.annotations.push(data);
      }
    });
  });
}
