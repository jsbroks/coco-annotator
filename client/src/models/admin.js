import axios from "axios";

const baseURL = "/api/admin/";

export default {
  getUsers(limit) {
    return axios.get(baseURL + `users?limit=${limit}`);
  },
  createUser(user) {
    return axios.post(baseURL + "user/", { ...user });
  },
  editUser(username, changes) {
    return axios.patch(baseURL + `user/${username}`, { ...changes });
  },
  deleteUser(username) {
    return axios.delete(baseURL + `user/${username}`);
  }
};
