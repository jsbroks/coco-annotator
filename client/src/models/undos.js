import axios from "axios";

const baseURL = "/api/undo/";

export default {
  all(limit, instance) {
    return axios.get(baseURL + `list/?limit=${limit}&type=${instance}`);
  },
  undo(id, instance) {
    return axios.post(baseURL + `?id=${id}&instance=${instance}`);
  },
  delete(id, instance) {
    return axios.delete(baseURL + `?id=${id}&instance=${instance}`);
  }
};
