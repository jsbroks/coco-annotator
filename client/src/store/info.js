import axios from "axios";

const state = {
  loading: true,
  success: true,
  allowRegistration: true,
  loginEnabled: true,
  version: "loading",
  totalUsers: 1,
  name: "COCO Annotator",
  socket: null
};

const getters = {};

const mutations = {
  socket(state, connected) {
    state.socket = connected;
  },
  increamentUserCount(state) {
    state.totalUsers++;
  },
  getServerInfo(state) {
    state.loading = true;
    axios
      .get("/api/info/")
      .then(response => {
        state.loading = false;
        state.success = true;

        let data = response.data;
        state.version = data.git.tag;
        state.allowRegistration = data.allow_registration;
        state.loginEnabled = data.login_enabled;
        state.totalUsers = data.total_users;
      })
      .catch(() => {
        state.loading = false;
        state.success = true;

        state.version = "unknown";
      });
  }
};

const actions = {};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
};
