import axios from "axios";

const state = {
  isAuthenticated: false,
  isAuthenticatePending: true,
  isLogoutPending: false,
  error: null,
  user: null
};

const getters = {
  isAdmin(state) {
    if (!state.user) return false;
    return state.user.is_admin;
  },
  loginEnabled(state) {
    if (!state.user) return false;
    if (!state.user.anonymous) return true;
    return state.user.anonymous;
  },
  user(state) {
    return state.user;
  }
};

const mutations = {
  loggingIn(state) {
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
  loggingOut(state) {
    state.isLogoutPending = true;
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
  async register({ commit, state }, { user, successCallback, errorCallback }) {
    if (state.isAuthenticated) return false;

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
        commit("error", error);
        if (errorCallback != null) errorCallback(error);
        return false;
      });
  },
  async login({ commit, state }, { user, successCallback, errorCallback }) {
    if (state.isAuthenticated) return false;

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
        commit("error", error);
        if (errorCallback != null) errorCallback(error);
        return false;
      });
  },
  async logout({ commit, state }) {
    if (!state.isAuthenticated) return false;

    commit("loggingOut");
    commit("clearError");

    return axios
      .get("/api/user/logout")
      .then(() => {
        commit("loggedOut");
        return true;
      })
      .catch(error => {
        commit("error", error);
        return false;
      });
  }
};

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations
};
