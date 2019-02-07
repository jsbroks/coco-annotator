import axios from "axios";

const baseURL = "/api/tasks/";

export default {
  get() {
    return axios.get(baseURL);
  },
  delete(id) {
    return axios.delete(baseURL + id);
  },
  getLogs(id) {
    return axios.get(baseURL + id + "/logs");
  }
};
