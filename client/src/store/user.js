import axios from "axios";

const state = {
  isAuthenticated: false,
  isAuthenticatePending: true,
  isLogoutPending: false,
  error: null,
  user: null
};

const getters = {};

const mutations = {
  loggingIn(state) {
    state.isAuthenticated = false;
    state.isAuthenticatePending = true;
  },
  loggedIn(state, user) {
    state.user = user;
    state.isAuthenticatePending = false;
    state.isAuthenticated = true;
  },
  error(state, error) {
    state.error = error;
    state.isAuthenticatePending = false;
    state.isLogoutPending = false;
  },
  loggedOut(state) {
    state.user = null;
    state.isAuthenticated = false;
    state.isLogoutPending = false;
  },
  clearError(state) {
    state.error = null;
  },
  setUserInfo(state) {
    state.isAuthenticatePending = true;
    axios
      .get("/api/user/")
      .then(response => {
        state.user = response.data.user;
        state.isAuthenticated = true;
        state.isAuthenticatePending = false;
      })
      .catch(() => {
        state.isAuthenticated = false;
        state.isAuthenticatePending = false;
      });
  }
};

const actions = {
  register({ commit }, { user, successCallback, errorCallback }) {
    commit("clearError");
    commit("loggingIn");

    return axios
      .post("/api/user/register", {
        ...user
      })
      .then(response => {
        commit("loggedIn", response.data.user);
        if (successCallback != null) successCallback(response);
        return true;
      })
      .catch(error => {
        commit("loginError", error);
        if (errorCallback != null) errorCallback(error);
        return false;
      });
  },
  login({ commit }, { user, successCallback, errorCallback }) {
    commit("clearError");
    commit("loggingIn");

    return axios
      .post("/api/user/login", {
        ...user
      })
      .then(response => {
        commit("loggedIn", response.data.user);
        if (successCallback != null) successCallback(response);
        return true;
      })
      .catch(error => {
        commit("loginError", error);
        if (errorCallback != null) errorCallback(error);
        return false;
      });
  },
  logout() {}
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
};
