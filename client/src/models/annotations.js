import axios from "axios";

const baseURL = "/api/annotation/";

export default {
  create(annotation) {
    return axios.post(baseURL, annotation);
  },
  delete(id) {
    return axios.delete(`${baseURL}${id}`);
  }
};
