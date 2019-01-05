import Vue from "vue";
import Vuex from "vuex";

import user from "./user";

Vue.use(Vuex);

export default new Vuex.Store({
  modules: {
    user
  },
  state: {
    process: [],
    undo: [],
    numberOfUsers: 1
  },
  mutations: {
    setNumberOfUsers(state, numberOfUsers) {
      state.numberOfUsers = numberOfUsers;
    },
    addProcess(state, process) {
      state.process.push(process);
    },
    removeProcess(state, process) {
      let index = state.process.indexOf(process);
      if (index > -1) {
        state.process.splice(index, 1);
      }
    },
    resetUndo(state) {
      state.undo = [];
    },
    addUndo(state, action) {
      state.undo.push(action);
    },
    undo(state) {
      let action = state.undo.pop();
      if (action != null) {
        action.undo();
      }
    },
    removeUndos(state, action) {
      state.undo = state.undo.filter(undo => undo.action !== action);
    }
  },
  actions: {}
});
