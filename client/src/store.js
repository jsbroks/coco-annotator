import Vue from "vue";
import Vuex from "vuex";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    process: []
  },
  mutations: {
    addProcess(state, process) {
      state.process.push(process);
    },
    removeProcess(state, process) {
      var index = state.process.indexOf(process);
      if (index > -1) {
        state.process.splice(index, 1);
      }
    }
  },
  actions: {}
});
