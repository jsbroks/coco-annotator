import axios from "axios";

const baseURL = "/api/admin/";

export default {
  getUsers(limit) {
    return axios.get(baseURL + `users?limit=${limit}`);
  },
  createUser(user) {
    return axios.post(baseURL + "user/", { ...user });
  },
  deleteUser(username) {
    return axios.delete(baseURL + `user/${username}`);
  }
};
