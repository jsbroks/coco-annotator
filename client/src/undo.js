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
